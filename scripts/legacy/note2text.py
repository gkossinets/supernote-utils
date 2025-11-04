#!/usr/bin/env python3
"""
note2text.py - Convert Supernote .note files to Markdown using LLM APIs

Directly extracts page images from .note files and sends them to LLM for transcription,
bypassing intermediate PDF conversion for optimal quality and speed.

Supports: Anthropic Claude, Google Gemini, and Ollama (local models)
"""

import argparse
import base64
import io
import os
import re
import sys
from pathlib import Path
from typing import Optional, List, Tuple

# Required packages
try:
    import anthropic
    import google.generativeai as genai
    import ollama
    from PIL import Image
    
    # Import supernotelib components
    from supernotelib import parser
    from supernotelib.converter import ImageConverter
    
    # Import shared transcription prompt
    from transcription_prompt import DEFAULT_PROMPT
except ImportError as e:
    print(f"Error: Missing required package.", file=sys.stderr)
    print("Install with: pip install anthropic google-generativeai ollama pillow supernotelib", file=sys.stderr)
    print(f"Specific error: {e}", file=sys.stderr)
    sys.exit(1)


class OllamaVisionAPI:
    """Wrapper for Ollama API to handle vision models"""
    
    def __init__(self, model_name: Optional[str] = None, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client and detect available vision models"""
        self.base_url = base_url
        
        if model_name:
            self.model = model_name
            print(f"Using specified Ollama model: {model_name}", file=sys.stderr)
        else:
            self.model = self._detect_vision_model()
            if self.model:
                print(f"Auto-detected Ollama vision model: {self.model}", file=sys.stderr)
            else:
                raise ValueError("No vision models found in Ollama. Please specify a model with --model")
    
    def _detect_vision_model(self) -> Optional[str]:
        """Detect first available vision model from Ollama"""
        try:
            models = ollama.list()
            model_list = models.get('models', [])
            
            # Prioritize qwen2.5-vl:7b, then other vision models
            # Comprehensive list of known vision-capable models
            vision_keywords = [
                'qwen2.5-vl:7b', 'qwen2.5-vl', 'qwen',  # Qwen vision models
                'llama3.2-vision',  # Llama vision
                'llava',  # LLaVA vision models
                'minicpm',  # MiniCPM vision
                'gemma3',  # Gemma 3 multimodal
                'vision',  # Generic vision indicator
                'ocr',  # OCR-specific models
                'nanonets'  # Nanonets OCR
            ]
            
            # First pass: check for exact qwen2.5-vl:7b match
            for model in model_list:
                # Ollama API returns model objects where name is in .model attribute
                name = getattr(model, 'model', model.get('model', ''))
                if 'qwen2.5-vl:7b' in name.lower():
                    return name
            
            # Second pass: check other patterns
            for model in model_list:
                # Ollama API returns model objects where name is in .model attribute
                name = getattr(model, 'model', model.get('model', ''))
                if any(keyword in name.lower() for keyword in vision_keywords[1:]):
                    return name
        except Exception as e:
            print(f"Warning: Could not auto-detect Ollama models: {e}", file=sys.stderr)
        return None
    
    def process_image(self, image: Image.Image, prompt: str, temperature: float = 0.2) -> str:
        """Process image with Ollama vision model"""
        try:
            # Convert PIL Image to bytes
            buffered = io.BytesIO()
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            image.save(buffered, format="JPEG")
            image_bytes = buffered.getvalue()
            
            # Call Ollama chat with image bytes
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_bytes]
                }],
                options={
                    'temperature': temperature,
                }
            )
            return response['message']['content']
        except Exception as e:
            return f"Error processing with Ollama: {str(e)}"


class NoteToTextConverter:
    """Main converter class for .note to Markdown transcription"""
    
    def __init__(self, api_provider: str, model_name: Optional[str] = None, 
                 additional_prompt: str = "", temperature: float = 0.2):
        """Initialize converter with specified API provider"""
        self.api_provider = api_provider.lower()
        self.temperature = temperature
        self.prompt = DEFAULT_PROMPT
        
        if additional_prompt:
            self.prompt = f"{DEFAULT_PROMPT}\n\nAdditional instructions: {additional_prompt}\n\n"
        
        self._init_api_client(model_name)
    
    def _init_api_client(self, model_name: Optional[str] = None):
        """Initialize API client based on provider"""
        self.api_backend = None
        
        if self.api_provider in ["claude", "claude-haiku", "claude-sonnet"]:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.api_backend = 'anthropic'
            
            if self.api_provider == "claude-sonnet":
                self.model = model_name or "claude-sonnet-4-5-20250929"
                print(f"Using Claude Sonnet 4.5 model (temperature={self.temperature})", file=sys.stderr)
            else:
                self.model = model_name or "claude-haiku-4-5-20251001"
                print(f"Using Claude 4.5 Haiku model (temperature={self.temperature})", file=sys.stderr)
        
        elif self.api_provider in ["gemini", "gemini-flash", "gemini-pro"]:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            self.api_backend = 'google'
            
            if self.api_provider == "gemini-pro":
                model = model_name or 'gemini-2.5-pro'
                self.client = genai.GenerativeModel(model)
                print(f"Using Gemini model: {model} (temperature={self.temperature})", file=sys.stderr)
            else:
                model = model_name or 'gemini-2.5-flash'
                self.client = genai.GenerativeModel(model)
                print(f"Using Gemini model: {model} (temperature={self.temperature})", file=sys.stderr)
        
        elif self.api_provider == "ollama":
            self.api_backend = 'ollama'
            self.client = OllamaVisionAPI(model_name=model_name)
            print(f"Using Ollama with temperature={self.temperature}", file=sys.stderr)
        
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def _process_with_anthropic(self, image: Image.Image) -> str:
        """Process image using Anthropic Claude API"""
        base64_image = self._image_to_base64(image)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=self.temperature,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error processing with Anthropic: {str(e)}"
    
    def _process_with_gemini(self, image: Image.Image) -> str:
        """Process image using Google Gemini API"""
        try:
            response = self.client.generate_content(
                [self.prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                )
            )
            return response.text
        except Exception as e:
            return f"Error processing with Gemini: {str(e)}"
    
    def _process_with_ollama(self, image: Image.Image) -> str:
        """Process image using Ollama local model"""
        return self.client.process_image(image, self.prompt, self.temperature)
    
    def process_page(self, image: Image.Image, page_num: int) -> Tuple[int, str]:
        """Process a single page image"""
        print(f"Processing page {page_num} (size: {image.size})...", file=sys.stderr)
        
        if self.api_backend == 'anthropic':
            text = self._process_with_anthropic(image)
        elif self.api_backend == 'google':
            text = self._process_with_gemini(image)
        elif self.api_backend == 'ollama':
            text = self._process_with_ollama(image)
        else:
            raise RuntimeError("API backend not configured correctly.")
        
        return page_num, text
    
    def _strip_code_block_wrapper(self, text: str) -> str:
        """Remove markdown code block wrapper if present"""
        pattern = r'^```(?:markdown)?\n(.*?)\n```$'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text
    
    def extract_images_from_note(self, note_path: Path) -> List[Image.Image]:
        """Extract page images directly from .note file"""
        print(f"Loading .note file: {note_path}", file=sys.stderr)
        
        try:
            # Load the notebook using supernotelib
            notebook = parser.load_notebook(str(note_path))
            
            # Create image converter
            converter = ImageConverter(notebook)
            
            # Extract images for all pages
            images = []
            total_pages = notebook.get_total_pages()
            print(f"Found {total_pages} pages in note file", file=sys.stderr)
            
            for i in range(total_pages):
                img = converter.convert(i)
                images.append(img)
            
            return images
            
        except Exception as e:
            print(f"Error loading .note file: {e}", file=sys.stderr)
            raise
    
    def process_note_file(self, note_path: Path, output_md: Optional[Path] = None,
                         output_pdf: Optional[Path] = None, 
                         page_separator: bool = False) -> None:
        """Process .note file and generate Markdown (and optionally PDF)"""
        
        if not note_path.exists():
            print(f"Error: Note file '{note_path}' not found", file=sys.stderr)
            sys.exit(1)
        
        # Extract images from .note file
        images = self.extract_images_from_note(note_path)
        
        if not images:
            print("Error: No pages could be extracted from the .note file", file=sys.stderr)
            sys.exit(1)
        
        # Set up output with proper UTF-8 encoding
        if output_md:
            output_stream = open(output_md, 'w', encoding='utf-8')
        else:
            # Ensure stdout uses UTF-8 encoding
            if sys.stdout.encoding != 'utf-8':
                output_stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
            else:
                output_stream = sys.stdout
        
        try:
            for i, image in enumerate(images, start=1):
                page_num, text = self.process_page(image, i)
                
                # Clean up markdown code block wrappers
                text = self._strip_code_block_wrapper(text)
                
                # Write output
                if i > 1:
                    output_stream.write("\n\n")
                if page_separator:
                    output_stream.write(f"---- Page {page_num} ----\n")
                output_stream.write(text.strip())
                output_stream.flush()
            
            output_stream.write("\n")
            
            if output_md:
                print(f"\nMarkdown saved to: {output_md}", file=sys.stderr)
        
        finally:
            if output_md:
                output_stream.close()
        
        # Generate PDF if requested
        if output_pdf:
            print(f"\nGenerating PDF: {output_pdf}", file=sys.stderr)
            self._generate_pdf(note_path, output_pdf)
    
    def _generate_pdf(self, note_path: Path, output_pdf: Path):
        """Generate PDF from .note file using supernotelib"""
        try:
            # Use the existing note2pdf.py logic
            with open(note_path, 'rb') as f:
                metadata = parser.parse_metadata(f)
                notebook = parser.load(f, metadata)
            
            from supernotelib.converter import PdfConverter
            pdf_converter = PdfConverter(notebook)
            pdf_data = pdf_converter.convert(-1)  # -1 means all pages
            
            with open(output_pdf, 'wb') as f:
                f.write(pdf_data)
            
            print(f"PDF saved to: {output_pdf}", file=sys.stderr)
        
        except Exception as e:
            print(f"Error generating PDF: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Supernote .note files to Markdown using LLM vision APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ANTHROPIC_API_KEY - Required for Claude models
  GOOGLE_API_KEY    - Required for Gemini models
  (Ollama requires local installation at http://localhost:11434)

Examples:
  # Basic usage with Claude Sonnet (outputs to stdout)
  %(prog)s input.note --md output.md --api claude-sonnet

  # Process with Gemini and save both Markdown and PDF
  %(prog)s input.note --md output.md --pdf output.pdf --api gemini

  # Use local Ollama model with custom temperature
  %(prog)s input.note --md output.md --api ollama --model llama3.2-vision:11b --temperature 0.1

  # Add page separators in output
  %(prog)s input.note --md output.md --page-separator
        """
    )
    
    parser.add_argument('input_note', type=Path, 
                       help='Input .note file from Supernote')
    
    parser.add_argument('--md', type=Path, default=None,
                       help='Output Markdown file (prints to stdout if not specified)')
    
    parser.add_argument('--pdf', type=Path, default=None,
                       help='Output PDF file (optional)')
    
    parser.add_argument('--api', 
                       choices=['claude', 'claude-haiku', 'claude-sonnet', 
                               'gemini', 'gemini-flash', 'gemini-pro', 'ollama'],
                       default='claude-sonnet',
                       help='LLM API provider (default: claude-sonnet)')
    
    parser.add_argument('--model', type=str, default=None,
                       help='Specific model name to use (optional, provider-specific defaults will be used)')
    
    parser.add_argument('--temperature', type=float, default=0.2,
                       help='Temperature for generation (0.0-2.0, default: 0.2, lower = more deterministic)')
    
    parser.add_argument('--add-prompt', type=str, default='',
                       help='Additional instructions to include in the transcription prompt')
    
    parser.add_argument('--page-separator', action='store_true',
                       help='Add page separator markers in output')
    
    args = parser.parse_args()
    
    try:
        converter = NoteToTextConverter(
            api_provider=args.api,
            model_name=args.model,
            additional_prompt=args.add_prompt,
            temperature=args.temperature
        )
        
        converter.process_note_file(
            note_path=args.input_note,
            output_md=args.md,
            output_pdf=args.pdf,
            page_separator=args.page_separator
        )
    
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
