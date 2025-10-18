#!/usr/bin/env python3
"""
PDF Handwritten Text Recognition using LLM APIs
Processes PDF pages and extracts handwritten text using Anthropic Claude, Google Gemini, or OpenAI GPT.

To get a list of available Claude models, run the following command in your terminal (make sure ANTHROPIC_API_KEY is set):
curl -s https://api.anthropic.com/v1/models --header "x-api-key: $ANTHROPIC_API_KEY" --header "anthropic-version: 2023-06-01" | jq . | grep \"id\"
      "id": "claude-haiku-4-5-20251001",
      "id": "claude-sonnet-4-5-20250929",
      "id": "claude-opus-4-1-20250805",
      "id": "claude-opus-4-20250514",
      "id": "claude-sonnet-4-20250514",
      "id": "claude-3-7-sonnet-20250219",
      "id": "claude-3-5-sonnet-20241022",
      "id": "claude-3-5-haiku-20241022",
      "id": "claude-3-5-sonnet-20240620",
      "id": "claude-3-haiku-20240307",
      "id": "claude-3-opus-20240229",

"""

import argparse
import base64
import io
import json
import sys
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple, Union

# Required packages - install with:
# pip install anthropic google-generativeai openai PyPDF2 pdf2image pillow

try:
    import anthropic
    import google.generativeai as genai
    import openai
    from PIL import Image
    import PyPDF2
    from pdf2image import convert_from_path
except ImportError as e:
    print(f"Error: Missing required package. Install with:")
    print("pip install anthropic google-generativeai openai PyPDF2 pdf2image pillow")
    print(f"Specific error: {e}")
    sys.exit(1)

DEFAULT_PROMPT = """You are an expert transcriber of handwritten documents. Your two most important goals are **semantic fidelity** (the text must mean the same thing) and **output purity** (you must only output the transcription).

**Output Purity: Provide ONLY the transcribed text as standard Markdown. Absolutely no introductions, summaries, or commentary.**

**1. Guiding Principles for Transcription**

* **Logic is Law:** The final transcription of any sentence **must** make logical sense. Be skeptical of odd phrases. For example, a phrase like "moon year" is less probable in a personal journal than "mood repair." Prioritize the interpretation that fits the context of personal reflection over a simple visual match.
* **The Conservative Principle for Proper Nouns (Very Important):**
    * Proper nouns are the most common source of error. **Do not guess or substitute a more common name.** 
    * If a name is highly ambiguous, transcribe it phonetically as best as you can, even if it does not form a known word. It is better to have a close phonetic match than a completely different name.
* **Context Over Shape:** Use the surrounding context to resolve ambiguity. A word in a "scary legend" is more likely to be "witch" than "wheel," even if the handwriting is unclear. "Writing" is more probable than "Ugh" near "filmmaking".

**2. Formatting Rules (Strict)**

* **Paragraphs:** Join all lines in a visually contiguous block of text into a single flowing paragraph. Separate distinct text blocks with one blank line.
* **Headers:** Use Markdown bolding for headers (highlighted inverted text). **Do not** use '#' heading symbols.
* **Highlighting & Symbols:** Pay extremely close attention to special formatting.
    * Only enclose text in `==highlight tags==` if it is explicitly highlighted.
    * Accurately place all symbols like em-dashes (—), exclamation points (!), and stars (☆ or ★).

**Final Review:** Before concluding, perform one last check of your output, specifically for misspelled proper nouns and to ensure no introductory commentary has been added.
"""

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
                        # print(f"Found {len(page.images)} embedded image(s) on page {page_num}", file=sys.stderr)
                        for image_file_object in page.images:
                            try:
                                img = Image.open(io.BytesIO(image_file_object.data))
                                if img.width > 100 and img.height > 100:
                                    images.append(img)
                            except Exception:
                                continue # Ignore images that can't be opened
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
    def __init__(self, api_provider: str, additional_prompt: str = ""):
        """Initialize the OCR processor with specified API provider."""
        self.api_provider = api_provider.lower()
        self.prompt = DEFAULT_PROMPT
        
        if additional_prompt:
            self.prompt = f"{DEFAULT_PROMPT}\n\nAdditional instructions: {additional_prompt}\n\nExtracted text (Markdown):\n"
        
        self._init_api_clients()
    
    def _init_api_clients(self):
        """Initialize API clients based on provider with environment variables."""
        self.api_backend = None # Will be 'anthropic', 'google', or 'openai'
        
        if self.api_provider in ["claude", "claude-haiku", "claude-sonnet"]:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key: raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.api_backend = 'anthropic'
            if self.api_provider == "claude-sonnet":
                self.model = "claude-sonnet-4-5-20250929" 
                print("Using Claude Sonnet 4.5 model (powerful, higher accuracy)", file=sys.stderr)
            else:
                self.model = "claude-haiku-4-5-20251001" 
                print("Using Claude 4.5 Haiku model (faster, more cost-effective)", file=sys.stderr)

        elif self.api_provider in ["gemini", "gemini-flash", "gemini-pro"]:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key: raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            self.api_backend = 'google'
            if self.api_provider == "gemini-pro":
                self.client = genai.GenerativeModel('gemini-1.5-pro')
                print("Using Gemini 1.5 Pro model (powerful, higher accuracy)", file=sys.stderr)
            else:
                self.client = genai.GenerativeModel('gemini-1.5-flash')
                print("Using Gemini 1.5 Flash model (fast, free tier)", file=sys.stderr)
        
        elif self.api_provider in ["chatgpt", "gpt-4o"]:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key: raise ValueError("OPENAI_API_KEY environment variable not set.")
            self.client = openai.OpenAI(api_key=api_key)
            self.api_backend = 'openai'
            self.model = "gpt-4o"
            print("Using OpenAI GPT-4o model (powerful, high accuracy)", file=sys.stderr)
            
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")

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
                model=self.model, max_tokens=4096,
                messages=[{"role": "user","content": [{"type": "text","text": self.prompt},{"type": "image","source": {"type": "base64","media_type": "image/jpeg","data": base64_image}}]}]
            )
            return response.content[0].text
        except Exception as e: return f"Error processing with Anthropic: {str(e)}"

    def process_with_gemini(self, image: Image.Image) -> str:
        """Process image using Google Gemini API"""
        try:
            response = self.client.generate_content([self.prompt, image])
            return response.text
        except Exception as e: return f"Error processing with Gemini: {str(e)}"

    def process_with_openai(self, image: Image.Image) -> str:
        """Process image using OpenAI GPT API"""
        base64_image = self.image_to_base64(image)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e: return f"Error processing with OpenAI: {str(e)}"

    def process_page(self, image: Image.Image, page_num: int) -> Tuple[int, str]:
        """Process a single page image"""
        print(f"Processing page {page_num} (size: {image.size})...", file=sys.stderr)
        
        if self.api_backend == 'anthropic':
            text = self.process_with_anthropic(image)
        elif self.api_backend == 'google':
            text = self.process_with_gemini(image)
        elif self.api_backend == 'openai':
            text = self.process_with_openai(image)
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

                # --- MODIFICATION START ---
                # Added a call to the new cleanup function.
                text = self.strip_code_block_wrapper(text)
                # --- MODIFICATION END ---
                
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
  OPENAI_API_KEY    - Required for chatgpt/gpt-4o models
  ANTHROPIC_API_KEY - Required for Claude models
  GOOGLE_API_KEY    - Required for Gemini models

Examples:
  # Process with OpenAI's GPT-4o (recommended)
  %(prog)s --api gpt-4o input.pdf

  # Process with Gemini and save as a plain text file
  %(prog)s --api gemini --plain-text input.pdf --out result.txt

  # Process with Claude and add page separators
  %(prog)s --api claude-sonnet --page_separator scan.pdf > result.md
        """
    )
    
    parser.add_argument(
        '--api',
        choices=['chatgpt', 'gpt-4o', 'claude', 'claude-haiku', 'claude-sonnet', 'gemini', 'gemini-flash', 'gemini-pro'],
        default='claude-sonnet',
        help='LLM API service and model to use (default: claude-sonnet)'
    )
    
    parser.add_argument('input_pdf', type=Path, help='Input PDF file to process')
    parser.add_argument('--add_prompt', type=str, default='', help='Additional instructions to include in the prompt')
    parser.add_argument('--out', type=Path, default=None, help='Output file path (prints to stdout if not specified)')
    parser.add_argument('--force-render', action='store_true', help='Force rendering of pages instead of extracting embedded images')
    parser.add_argument('--dpi', type=int, default=100, help='DPI to use when rendering pages (default: 100)')
    parser.add_argument('--page_separator', action='store_true', help='Add a separator between pages')
    parser.add_argument('--plain-text', action='store_true', help='Output plain text by stripping Markdown formatting.')
    
    args = parser.parse_args()
    
    api_provider_map = {
        'claude': 'claude-haiku',
        'claude-haiku': 'claude-haiku',
        'claude-sonnet': 'claude-sonnet',
        'gemini': 'gemini-flash',
        'gemini-flash': 'gemini-flash', 
        'gemini-pro': 'gemini-pro',
        'gpt-4o': 'gpt-4o', 
        'chatgpt': 'gpt-4o'
    }
    api_provider = api_provider_map.get(args.api, args.api)
    
    try:
        ocr = PDFHandwritingOCR(api_provider, args.add_prompt)
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
