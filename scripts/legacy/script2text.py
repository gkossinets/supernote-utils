#!/usr/bin/env python3
"""
PDF Handwritten Text Recognition using LLM APIs
Processes PDF pages and extracts handwritten text using Anthropic Claude, Google Gemini, or Ollama.
"""

import argparse
import base64
import io
import sys
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple

# Required packages
try:
    import anthropic
    import google.generativeai as genai
    import ollama
    from PIL import Image
    import PyPDF2
    from pdf2image import convert_from_path
    
    # Import shared transcription prompt
    from transcription_prompt import DEFAULT_PROMPT
except ImportError as e:
    print(f"Error: Missing required package. Install with:")
    print("pip install anthropic google-generativeai ollama PyPDF2 pdf2image pillow")
    print(f"Specific error: {e}")
    sys.exit(1)


class PDFImageExtractor:
    """Handles extraction of images from PDF files"""

    @staticmethod
    def extract_images_from_pdf(pdf_path: Path) -> List[Image.Image]:
        """Try to extract embedded images directly from PDF using a more robust method."""
        images = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    if page.images:
                        for image_file_object in page.images:
                            try:
                                img = Image.open(io.BytesIO(image_file_object.data))
                                if img.width > 100 and img.height > 100:
                                    images.append(img)
                            except Exception:
                                continue
            if images:
                print(f"Successfully extracted {len(images)} main embedded images", file=sys.stderr)
        except Exception as e:
            print(f"Could not extract embedded images: {str(e)}", file=sys.stderr)
            images = []
        return images

    @staticmethod
    def get_pdf_images(pdf_path: Path, force_render: bool = False, dpi: int = 150) -> List[Image.Image]:
        """Get images from PDF, either by extraction or rendering."""
        if not force_render:
            images = PDFImageExtractor.extract_images_from_pdf(pdf_path)
            if images:
                return images
            else:
                print("No suitable embedded images found, rendering pages instead...", file=sys.stderr)
        
        print(f"Rendering PDF pages at {dpi} DPI...", file=sys.stderr)
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            print(f"Rendered {len(images)} pages", file=sys.stderr)
            return images
        except Exception as e:
            print(f"Error rendering PDF: {str(e)}", file=sys.stderr)
            raise


class PDFHandwritingOCR:
    def __init__(self, api_provider: str, model_name: Optional[str] = None,
                 additional_prompt: str = "", temperature: float = 0.2):
        """Initialize the OCR processor with specified API provider."""
        self.api_provider = api_provider.lower()
        self.temperature = temperature
        self.prompt = DEFAULT_PROMPT
        
        if additional_prompt:
            self.prompt = f"{DEFAULT_PROMPT}\n\nAdditional instructions: {additional_prompt}\n\nExtracted text (Markdown):\n"
        
        self._init_api_clients(model_name)
    
    def _init_api_clients(self, model_name: Optional[str] = None):
        """Initialize API clients based on provider with environment variables."""
        self.api_backend = None
        
        if self.api_provider in ["claude", "claude-haiku", "claude-sonnet"]:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key: raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
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
            if not api_key: raise ValueError("GOOGLE_API_KEY environment variable not set.")
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
            self.model = model_name or self._detect_ollama_vision_model()
            if not self.model:
                raise ValueError("No vision models found in Ollama. Please specify a model with --model")
            print(f"Using Ollama model: {self.model} (temperature={self.temperature})", file=sys.stderr)
            
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")
    
    def _detect_ollama_vision_model(self) -> Optional[str]:
        """Detect first available vision model from Ollama"""
        try:
            models = ollama.list()
            model_list = models.get('models', [])
            
            vision_keywords = ['qwen2.5-vl:7b', 'qwen2.5-vl', 'llama3.2-vision', 'llava', 'minicpm', 'vision']
            
            for model in model_list:
                name = model.get('name', '')
                if 'qwen2.5-vl:7b' in name.lower():
                    return name
            
            for model in model_list:
                name = model.get('name', '')
                if any(keyword in name.lower() for keyword in vision_keywords[1:]):
                    return name
        except Exception as e:
            print(f"Warning: Could not auto-detect Ollama models: {e}", file=sys.stderr)
        return None

    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def process_with_anthropic(self, image: Image.Image) -> str:
        """Process image using Anthropic Claude API"""
        base64_image = self.image_to_base64(image)
        try:
            response = self.client.messages.create(
                model=self.model, 
                max_tokens=4096,
                temperature=self.temperature,
                messages=[{"role": "user","content": [{"type": "text","text": self.prompt},{"type": "image","source": {"type": "base64","media_type": "image/jpeg","data": base64_image}}]}]
            )
            return response.content[0].text
        except Exception as e: return f"Error processing with Anthropic: {str(e)}"

    def process_with_gemini(self, image: Image.Image) -> str:
        """Process image using Google Gemini API"""
        try:
            response = self.client.generate_content(
                [self.prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                )
            )
            return response.text
        except Exception as e: return f"Error processing with Gemini: {str(e)}"

    def process_with_ollama(self, image: Image.Image) -> str:
        """Process image using Ollama local model"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': self.prompt,
                }],
                images=[image],
                options={
                    'temperature': self.temperature,
                }
            )
            return response['message']['content']
        except Exception as e:
            return f"Error processing with Ollama: {str(e)}"

    def process_page(self, image: Image.Image, page_num: int) -> Tuple[int, str]:
        """Process a single page image"""
        print(f"Processing page {page_num} (size: {image.size})...", file=sys.stderr)
        
        if self.api_backend == 'anthropic':
            text = self.process_with_anthropic(image)
        elif self.api_backend == 'google':
            text = self.process_with_gemini(image)
        elif self.api_backend == 'ollama':
            text = self.process_with_ollama(image)
        else:
            raise RuntimeError("API backend not configured correctly.")
        return page_num, text
    
    def strip_code_block_wrapper(self, text: str) -> str:
        """Removes the markdown code block wrapper from a string if present."""
        pattern = r'^```(?:markdown)?\n(.*?)\n```$'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    def strip_markdown(self, text: str) -> str:
        """Removes common Markdown syntax from text."""
        text = re.sub(r'==(.*?)==', r'\1', text)
        text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
        text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
        return text
        
    def process_pdf(self, pdf_path: Path, output_path: Optional[Path] = None, 
                   force_render: bool = False, dpi: int = 150, 
                   page_separator: bool = False, plain_text: bool = False) -> None:
        """Process entire PDF file, writing output for each page as it completes."""
        if not pdf_path.exists():
            print(f"Error: PDF file '{pdf_path}' not found", file=sys.stderr)
            sys.exit(1)
        
        images = PDFImageExtractor.get_pdf_images(pdf_path, force_render, dpi)
        if not images:
            print("Error: No images could be extracted from the PDF", file=sys.stderr)
            sys.exit(1)
        
        print(f"Found {len(images)} pages to process", file=sys.stderr)
        output_stream = output_path.open('w', encoding='utf-8') if output_path else sys.stdout
        
        try:
            for i, image in enumerate(images, start=1):
                page_num, text = self.process_page(image, i)
                text = self.strip_code_block_wrapper(text)
                
                if plain_text: text = self.strip_markdown(text)
                if i > 1: output_stream.write("\n\n")
                if page_separator: output_stream.write(f"---- Page {page_num} ----\n")
                output_stream.write(text.strip())
                output_stream.flush()
            output_stream.write("\n")
        finally:
            if output_path:
                output_stream.close()
                print(f"Results saved to {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Extract handwritten text from PDF using LLM APIs. Output is Markdown by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ANTHROPIC_API_KEY - Required for Claude models
  GOOGLE_API_KEY    - Required for Gemini models
  (Ollama requires local installation at http://localhost:11434)

Examples:
  # Process with Claude Sonnet
  %(prog)s input.pdf --api claude-sonnet --temperature 0.2

  # Process with Gemini and save as plain text
  %(prog)s --api gemini --plain-text input.pdf --out result.txt

  # Process with Ollama local model
  %(prog)s --api ollama --model llama3.2-vision:11b input.pdf > result.md
        """
    )
    
    parser.add_argument(
        '--api',
        choices=['claude', 'claude-haiku', 'claude-sonnet', 
                'gemini', 'gemini-flash', 'gemini-pro', 'ollama'],
        default='claude-sonnet',
        help='LLM API service and model to use (default: claude-sonnet)'
    )
    
    parser.add_argument('input_pdf', type=Path, help='Input PDF file to process')
    
    parser.add_argument('--model', type=str, default=None,
                       help='Specific model name to use (optional, provider-specific defaults will be used)')
    
    parser.add_argument('--temperature', type=float, default=0.2,
                       help='Temperature for generation (0.0-2.0, default: 0.2, lower = more deterministic)')
    
    parser.add_argument('--add_prompt', type=str, default='', help='Additional instructions to include in the prompt')
    parser.add_argument('--out', type=Path, default=None, help='Output file path (prints to stdout if not specified)')
    parser.add_argument('--force-render', action='store_true', help='Force rendering of pages instead of extracting embedded images')
    parser.add_argument('--dpi', type=int, default=100, help='DPI to use when rendering pages (default: 100)')
    parser.add_argument('--page_separator', action='store_true', help='Add a separator between pages')
    parser.add_argument('--plain-text', action='store_true', help='Output plain text by stripping Markdown formatting.')
    
    args = parser.parse_args()
    
    try:
        ocr = PDFHandwritingOCR(
            api_provider=args.api,
            model_name=args.model,
            additional_prompt=args.add_prompt,
            temperature=args.temperature
        )
        ocr.process_pdf(args.input_pdf, args.out, args.force_render, args.dpi, args.page_separator, args.plain_text)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
