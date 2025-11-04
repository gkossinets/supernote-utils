#!/usr/bin/env python3
"""
Test suite for comparing transcription quality across different LLM models and parameters.

This script tests various combinations of models and temperatures against a reference
transcription, calculating multiple quality metrics including WER, CER, BLEU, and
semantic similarity.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import json

# Required packages for metrics
try:
    import Levenshtein
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required package for metrics.", file=sys.stderr)
    print("Install with: pip install python-Levenshtein nltk scikit-learn sentence-transformers", file=sys.stderr)
    print(f"Specific error: {e}", file=sys.stderr)
    sys.exit(1)

# Optional: ollama for vision detection
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading required NLTK data...", file=sys.stderr)
    nltk.download('punkt', quiet=True)


# Ollama models to test (from user's available models)
OLLAMA_MODELS_TO_TEST = [
    'llama3.2-vision:11b-instruct-q8_0',
    'benhaotang/Nanonets-OCR-s:F16',
    'yasserrmd/Nanonets-OCR2-3B:latest',
    'qwen2.5vl:7b',
    'minicpm-v:8b',
    'llava:34b',
]


class OllamaModelDetector:
    """Detect and verify Ollama vision models"""
    
    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of all available Ollama models"""
        if not OLLAMA_AVAILABLE:
            return []
        
        try:
            models = ollama.list()
            model_list = models.get('models', [])
            return [model.get('name', '') for model in model_list]
        except Exception as e:
            print(f"Warning: Could not list Ollama models: {e}", file=sys.stderr)
            return []
    
    @staticmethod
    def is_vision_model(model_name: str) -> bool:
        """Check if a model supports vision/image input"""
        if not OLLAMA_AVAILABLE:
            return False
        
        try:
            # Try to get model information
            info = ollama.show(model_name)
            
            # Check model file for vision support indicators
            modelfile = info.get('modelfile', '').lower()
            template = info.get('template', '').lower()
            parameters = info.get('parameters', '').lower()
            
            # Look for vision-related indicators
            vision_indicators = [
                'vision',
                'image',
                'visual',
                'llava',
                'clip',
                'vit',
                'siglip',
            ]
            
            combined_info = f"{modelfile} {template} {parameters}".lower()
            
            for indicator in vision_indicators:
                if indicator in combined_info:
                    return True
            
            # Additional check: try to see if model family is known vision model
            model_lower = model_name.lower()
            vision_families = [
                'llava',
                'llama3.2-vision',
                'qwen2.5vl',
                'qwen2vl',
                'qwen-vl',
                'minicpm-v',
                'pixtral',
                'nanonets',
                'ocr',
            ]
            
            for family in vision_families:
                if family in model_lower:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Warning: Could not check if {model_name} is a vision model: {e}", file=sys.stderr)
            # If we can't verify, assume it might be based on name patterns
            model_lower = model_name.lower()
            return any(keyword in model_lower for keyword in ['vision', 'vl', 'ocr', 'llava', 'minicpm-v'])
    
    @staticmethod
    def filter_vision_models(model_names: List[str]) -> List[str]:
        """Filter list to only vision-capable models"""
        available = OllamaModelDetector.get_available_models()
        vision_models = []
        
        for model in model_names:
            if model not in available:
                print(f"  Skipping {model} - not installed", file=sys.stderr)
                continue
            
            if OllamaModelDetector.is_vision_model(model):
                vision_models.append(model)
                print(f"  ✓ {model} - vision capable", file=sys.stderr)
            else:
                print(f"  ✗ {model} - not a vision model", file=sys.stderr)
        
        return vision_models


class TranscriptionMetrics:
    """Calculate various metrics comparing transcription to reference"""
    
    def __init__(self):
        """Initialize metrics calculator with semantic similarity model"""
        print("Loading semantic similarity model (all-mpnet-base-v2)...", file=sys.stderr)
        self.sem_model = SentenceTransformer('all-mpnet-base-v2')
    
    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """Calculate Word Error Rate"""
        ref_words = reference.split()
        hyp_words = hypothesis.split()
        
        if len(ref_words) == 0:
            return 0.0 if len(hyp_words) == 0 else 100.0
        
        distance = Levenshtein.distance(' '.join(ref_words), ' '.join(hyp_words))
        wer = (distance / len(ref_words)) * 100
        return round(wer, 2)
    
    def calculate_cer(self, reference: str, hypothesis: str) -> float:
        """Calculate Character Error Rate"""
        if len(reference) == 0:
            return 0.0 if len(hypothesis) == 0 else 100.0
        
        distance = Levenshtein.distance(reference, hypothesis)
        cer = (distance / len(reference)) * 100
        return round(cer, 2)
    
    def calculate_bleu(self, reference: str, hypothesis: str) -> float:
        """Calculate BLEU score"""
        ref_tokens = nltk.word_tokenize(reference.lower())
        hyp_tokens = nltk.word_tokenize(hypothesis.lower())
        
        if len(hyp_tokens) == 0:
            return 0.0
        
        smoothing = SmoothingFunction().method1
        score = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smoothing)
        return round(score, 4)
    
    def calculate_levenshtein(self, reference: str, hypothesis: str) -> int:
        """Calculate raw Levenshtein distance"""
        return Levenshtein.distance(reference, hypothesis)
    
    def calculate_semantic_similarity(self, reference: str, hypothesis: str) -> float:
        """Calculate semantic similarity using sentence transformers"""
        ref_embedding = self.sem_model.encode([reference])
        hyp_embedding = self.sem_model.encode([hypothesis])
        
        similarity = cosine_similarity(ref_embedding, hyp_embedding)[0][0]
        return round(float(similarity), 4)
    
    def calculate_all_metrics(self, reference: str, hypothesis: str) -> Dict[str, float]:
        """Calculate all metrics at once"""
        return {
            'wer': self.calculate_wer(reference, hypothesis),
            'cer': self.calculate_cer(reference, hypothesis),
            'bleu': self.calculate_bleu(reference, hypothesis),
            'levenshtein': self.calculate_levenshtein(reference, hypothesis),
            'semantic_sim': self.calculate_semantic_similarity(reference, hypothesis)
        }


class TranscriptionTester:
    """Main test orchestrator"""
    
    def __init__(self, note_file: Path, reference_file: Path, 
                 output_dir: Path, script_path: Path = Path("note2text.py")):
        """Initialize tester with test files and output directory"""
        self.note_file = note_file
        self.reference_file = reference_file
        self.output_dir = output_dir
        self.script_path = script_path
        self.metrics_calc = TranscriptionMetrics()
        
        # Load reference text
        with open(reference_file, 'r', encoding='utf-8') as f:
            self.reference_text = f.read().strip()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def check_api_key(self, provider: str) -> bool:
        """Check if required API key is set"""
        if provider in ['claude', 'claude-haiku', 'claude-sonnet']:
            return os.getenv('ANTHROPIC_API_KEY') is not None
        elif provider in ['gemini', 'gemini-flash', 'gemini-pro']:
            return os.getenv('GOOGLE_API_KEY') is not None
        elif provider == 'ollama':
            return OLLAMA_AVAILABLE
        return False
    
    def run_transcription(self, provider: str, temperature: float, 
                         model: Optional[str] = None) -> Tuple[str, float, str]:
        """Run transcription and return (text, runtime, error)"""
        
        # Build command - use same Python interpreter that's running this script
        cmd = [
            sys.executable, str(self.script_path),
            str(self.note_file),
            '--api', provider,
            '--temperature', str(temperature)
        ]
        
        if model:
            cmd.extend(['--model', model])
        
        # Run transcription
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5 minute timeout
            )
            runtime = time.time() - start_time
            
            if result.returncode != 0:
                error = f"Command failed: {result.stderr}"
                return "", runtime, error
            
            return result.stdout.strip(), runtime, ""
            
        except subprocess.TimeoutExpired:
            runtime = time.time() - start_time
            return "", runtime, "Timeout (>5 minutes)"
        except Exception as e:
            runtime = time.time() - start_time
            return "", runtime, str(e)
    
    def test_configuration(self, provider: str, temperature: float, 
                          model: Optional[str] = None) -> Dict:
        """Test a single model/temperature configuration"""
        
        model_display = f"{provider}:{model}" if model else provider
        print(f"  Testing {model_display} (temp={temperature})...", file=sys.stderr)
        
        # Run transcription
        text, runtime, error = self.run_transcription(provider, temperature, model)
        
        if error:
            print(f"    Error: {error}", file=sys.stderr)
            return {
                'provider': provider,
                'model': model or 'default',
                'temperature': temperature,
                'runtime': runtime,
                'error': error,
                'wer': None,
                'cer': None,
                'bleu': None,
                'levenshtein': None,
                'semantic_sim': None
            }
        
        # Calculate metrics
        metrics = self.metrics_calc.calculate_all_metrics(self.reference_text, text)
        
        print(f"    WER: {metrics['wer']}%, CER: {metrics['cer']}%, "
              f"BLEU: {metrics['bleu']}, Sem: {metrics['semantic_sim']} ({runtime:.1f}s)", 
              file=sys.stderr)
        
        return {
            'provider': provider,
            'model': model or 'default',
            'temperature': temperature,
            'runtime': round(runtime, 2),
            'error': None,
            **metrics
        }
    
    def run_test_suite(self, test_configs: List[Dict]) -> List[Dict]:
        """Run full test suite with multiple configurations"""
        
        print("\n" + "="*60, file=sys.stderr)
        print("TRANSCRIPTION TEST SUITE", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print(f"Note file: {self.note_file}", file=sys.stderr)
        print(f"Reference: {self.reference_file}", file=sys.stderr)
        print(f"Configurations to test: {len(test_configs)}", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        
        results = []
        
        for i, config in enumerate(test_configs, 1):
            provider = config['provider']
            temperature = config['temperature']
            model = config.get('model')
            
            # Check API key / availability
            if not self.check_api_key(provider):
                if provider == 'ollama':
                    error_msg = 'Ollama not available (install ollama package)'
                else:
                    error_msg = 'API key not set'
                
                print(f"[{i}/{len(test_configs)}] Skipping {provider} - {error_msg}", 
                      file=sys.stderr)
                results.append({
                    'provider': provider,
                    'model': model or 'default',
                    'temperature': temperature,
                    'error': error_msg,
                    'runtime': 0,
                    'wer': None, 'cer': None, 'bleu': None,
                    'levenshtein': None, 'semantic_sim': None
                })
                continue
            
            model_display = f"{provider}:{model}" if model else provider
            print(f"[{i}/{len(test_configs)}] Testing {model_display} (temp={temperature})", 
                  file=sys.stderr)
            
            result = self.test_configuration(provider, temperature, model)
            results.append(result)
        
        return results
    
    def generate_markdown_report(self, results: List[Dict], output_file: Path):
        """Generate markdown report of test results"""
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Transcription Test Results\n\n")
            f.write(f"**Date:** {timestamp}\n\n")
            f.write(f"**Note file:** {self.note_file}\n\n")
            f.write(f"**Reference:** {self.reference_file}\n\n")
            f.write(f"**Configurations tested:** {len(results)}\n\n")
            
            # Summary statistics
            successful = [r for r in results if r['error'] is None]
            if successful:
                best_wer = min(r['wer'] for r in successful)
                best_bleu = max(r['bleu'] for r in successful)
                best_sem = max(r['semantic_sim'] for r in successful)
                
                # Find best models
                best_wer_model = next(r for r in successful if r['wer'] == best_wer)
                best_bleu_model = next(r for r in successful if r['bleu'] == best_bleu)
                best_sem_model = next(r for r in successful if r['semantic_sim'] == best_sem)
                
                f.write(f"## Summary\n\n")
                f.write(f"- **Successful tests:** {len(successful)}/{len(results)}\n")
                f.write(f"- **Best WER:** {best_wer}% ({best_wer_model['provider']}:{best_wer_model['model']} @ temp={best_wer_model['temperature']})\n")
                f.write(f"- **Best BLEU:** {best_bleu} ({best_bleu_model['provider']}:{best_bleu_model['model']} @ temp={best_bleu_model['temperature']})\n")
                f.write(f"- **Best Semantic Similarity:** {best_sem} ({best_sem_model['provider']}:{best_sem_model['model']} @ temp={best_sem_model['temperature']})\n\n")
            
            # Results table
            f.write(f"## Detailed Results\n\n")
            f.write("| Provider | Model | Temp | WER (%) | CER (%) | BLEU | Levenshtein | Semantic Sim | Runtime (s) | Error |\n")
            f.write("|----------|-------|------|---------|---------|------|-------------|--------------|-------------|-------|\n")
            
            # Sort results by WER (successful tests first)
            sorted_results = sorted(results, key=lambda r: (r['error'] is not None, r['wer'] if r['wer'] is not None else 999))
            
            for r in sorted_results:
                provider = r['provider']
                model = r['model']
                temp = r['temperature']
                wer = f"{r['wer']:.2f}" if r['wer'] is not None else "N/A"
                cer = f"{r['cer']:.2f}" if r['cer'] is not None else "N/A"
                bleu = f"{r['bleu']:.4f}" if r['bleu'] is not None else "N/A"
                lev = str(r['levenshtein']) if r['levenshtein'] is not None else "N/A"
                sem = f"{r['semantic_sim']:.4f}" if r['semantic_sim'] is not None else "N/A"
                runtime = f"{r['runtime']:.2f}" if r['runtime'] else "0.00"
                error = r['error'] or "-"
                
                f.write(f"| {provider} | {model} | {temp} | {wer} | {cer} | {bleu} | "
                       f"{lev} | {sem} | {runtime} | {error} |\n")
            
            f.write("\n## Metric Descriptions\n\n")
            f.write("- **WER (Word Error Rate):** Lower is better. Percentage of word-level errors.\n")
            f.write("- **CER (Character Error Rate):** Lower is better. Percentage of character-level errors.\n")
            f.write("- **BLEU:** Higher is better (0-1). Measures n-gram overlap with reference.\n")
            f.write("- **Levenshtein:** Lower is better. Raw edit distance between texts.\n")
            f.write("- **Semantic Similarity:** Higher is better (0-1). Measures meaning similarity using embeddings.\n")
            
            # Add recommendations section
            if successful:
                f.write("\n## Recommendations\n\n")
                
                # Group by provider
                by_provider = {}
                for r in successful:
                    provider = r['provider']
                    if provider not in by_provider:
                        by_provider[provider] = []
                    by_provider[provider].append(r)
                
                for provider, provider_results in by_provider.items():
                    best = min(provider_results, key=lambda r: r['wer'])
                    f.write(f"### {provider.title()}\n\n")
                    f.write(f"Best configuration: `{best['model']}` at temperature `{best['temperature']}`\n")
                    f.write(f"- WER: {best['wer']:.2f}%\n")
                    f.write(f"- BLEU: {best['bleu']:.4f}\n")
                    f.write(f"- Semantic Similarity: {best['semantic_sim']:.4f}\n")
                    f.write(f"- Runtime: {best['runtime']:.2f}s\n\n")
        
        print(f"\nResults saved to: {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Test transcription quality across different LLM models and parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--note', type=Path, default=Path('test/test.note'),
                       help='Input .note file (default: test/test.note)')
    
    parser.add_argument('--reference', type=Path, default=Path('test/test-transcribed.md'),
                       help='Reference transcription file (default: test/test-transcribed.md)')
    
    parser.add_argument('--output-dir', type=Path, default=Path('test/results'),
                       help='Output directory for results (default: test/results)')
    
    parser.add_argument('--script', type=Path, default=Path('note2text.py'),
                       help='Path to note2text.py script (default: note2text.py)')
    
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test with limited configurations')
    
    parser.add_argument('--ollama-only', action='store_true',
                       help='Test only Ollama models (skip cloud APIs)')
    
    args = parser.parse_args()
    
    # Validate input files
    if not args.note.exists():
        print(f"Error: Note file not found: {args.note}", file=sys.stderr)
        sys.exit(1)
    
    if not args.reference.exists():
        print(f"Error: Reference file not found: {args.reference}", file=sys.stderr)
        sys.exit(1)
    
    if not args.script.exists():
        print(f"Error: Script not found: {args.script}", file=sys.stderr)
        sys.exit(1)
    
    # Detect available Ollama vision models
    if OLLAMA_AVAILABLE:
        print("\nDetecting available Ollama vision models...", file=sys.stderr)
        available_ollama_models = OllamaModelDetector.filter_vision_models(OLLAMA_MODELS_TO_TEST)
        if available_ollama_models:
            print(f"Found {len(available_ollama_models)} vision-capable Ollama models\n", file=sys.stderr)
        else:
            print("No vision-capable Ollama models found\n", file=sys.stderr)
    else:
        print("\nOllama not available (install with: pip install ollama)\n", file=sys.stderr)
        available_ollama_models = []
    
    # Define test configurations
    test_configs = []
    
    if not args.ollama_only:
        if args.quick:
            test_configs.extend([
                {'provider': 'claude-sonnet', 'temperature': 0.2},
                {'provider': 'gemini-flash', 'temperature': 0.2},
            ])
        else:
            test_configs.extend([
                # Claude tests
                {'provider': 'claude-sonnet', 'temperature': 0.0},
                {'provider': 'claude-sonnet', 'temperature': 0.2},
                {'provider': 'claude-sonnet', 'temperature': 0.5},
                {'provider': 'claude-haiku', 'temperature': 0.0},
                {'provider': 'claude-haiku', 'temperature': 0.2},
                {'provider': 'claude-haiku', 'temperature': 0.5},
                
                # Gemini tests
                {'provider': 'gemini-flash', 'temperature': 0.0},
                {'provider': 'gemini-flash', 'temperature': 0.2},
                {'provider': 'gemini-flash', 'temperature': 0.5},
                {'provider': 'gemini-pro', 'temperature': 0.0},
                {'provider': 'gemini-pro', 'temperature': 0.2},
                {'provider': 'gemini-pro', 'temperature': 0.5},
            ])
    
    # Add Ollama tests
    if available_ollama_models:
        if args.quick:
            # Just test each model at single temperature
            for model in available_ollama_models:
                test_configs.append({
                    'provider': 'ollama',
                    'model': model,
                    'temperature': 0.1
                })
        else:
            # Test each model at multiple temperatures
            for model in available_ollama_models:
                test_configs.extend([
                    {'provider': 'ollama', 'model': model, 'temperature': 0.1},
                    {'provider': 'ollama', 'model': model, 'temperature': 0.3},
                    {'provider': 'ollama', 'model': model, 'temperature': 0.5},
                ])
    
    if not test_configs:
        print("Error: No models available to test!", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY for cloud models", file=sys.stderr)
        print("  2. Install Ollama and pull vision models (e.g., ollama pull llava:34b)", file=sys.stderr)
        sys.exit(1)
    
    # Create tester
    tester = TranscriptionTester(args.note, args.reference, args.output_dir, args.script)
    
    # Run tests
    results = tester.run_test_suite(test_configs)
    
    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = args.output_dir / f"run_{timestamp}.md"
    tester.generate_markdown_report(results, output_file)
    
    print("\n" + "="*60, file=sys.stderr)
    print("TEST SUITE COMPLETE", file=sys.stderr)
    print("="*60, file=sys.stderr)


if __name__ == "__main__":
    main()
