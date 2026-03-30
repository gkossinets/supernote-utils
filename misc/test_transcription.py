#!/usr/bin/env python3
"""
Test suite for comparing LLM transcription quality.

This script runs transcription tests across multiple LLMs and generates
a detailed comparison report with accuracy metrics.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import Levenshtein
    import ollama
except ImportError as e:
    print("Error: Required package missing", file=sys.stderr)
    print("Install with: pip install python-Levenshtein ollama", file=sys.stderr)
    print(f"Specific error: {e}", file=sys.stderr)
    sys.exit(1)


def detect_ollama_vision_models() -> List[Dict]:
    """Detect available Ollama vision models"""
    vision_models = []
    # Comprehensive list of known vision-capable model identifiers
    vision_keywords = [
        'qwen',  # Qwen vision models (including qwen2.5-vl)
        'llama3.2-vision',  # Llama vision
        'llava',  # LLaVA vision models
        'minicpm',  # MiniCPM vision
        'gemma3',  # Gemma 3 multimodal
        'vision',  # Generic vision indicator
        'ocr',  # OCR-specific models
        'nanonets'  # Nanonets OCR
    ]
    
    try:
        print("Detecting available Ollama vision models...", file=sys.stderr, end='')
        models = ollama.list()
        model_list = models.get('models', [])
        
        for model in model_list:
            # Ollama API returns model objects where name is in .model attribute
            name = getattr(model, 'model', model.get('model', ''))
            if name and any(keyword in name.lower() for keyword in vision_keywords):
                vision_models.append({
                    'name': name,
                    'api': 'ollama',
                    'model': name
                })
                print(f"\n  ✓ Found {name}", file=sys.stderr, end='')
            else:
                print(f"\n  Skipping {name} - not a vision model", file=sys.stderr, end='')
        
        print(file=sys.stderr)  # Final newline
        
    except Exception as e:
        print(f"\n  Warning: Could not detect Ollama models: {e}", file=sys.stderr)
    
    return vision_models


# Test configuration
TEST_MODELS = {
    'cloud': [
        {'name': 'claude-sonnet', 'api': 'claude-sonnet', 'model': None},
        {'name': 'gemini-pro', 'api': 'gemini-pro', 'model': None},
    ],
    'local': []  # Will be populated dynamically
}


class TranscriptionTester:
    """Test harness for LLM transcription quality"""
    
    def __init__(self, test_dir: Path, note_file: Path, ground_truth: Path):
        self.test_dir = test_dir
        self.note_file = note_file
        self.ground_truth_file = ground_truth
        self.output_dir = test_dir / 'outputs'
        self.output_dir.mkdir(exist_ok=True)
        
        # Load ground truth
        with open(ground_truth, 'r', encoding='utf-8') as f:
            self.ground_truth = f.read()
    
    @staticmethod
    def sanitize_model_name(name: str) -> str:
        """Sanitize model name for use in filenames"""
        return name.replace('/', '_').replace(':', '-')
    
    def run_transcription(self, model_config: Dict) -> Tuple[str, Optional[str]]:
        """Run transcription with specified model configuration"""
        # Sanitize model name for filename
        safe_name = self.sanitize_model_name(model_config['name'])
        output_file = self.output_dir / f"test-output-{safe_name}.md"
        
        # Build command
        cmd = [
            'python3',
            str(self.test_dir.parent / 'note2text.py'),
            str(self.note_file),
            '--md', str(output_file),
            '--api', model_config['api']
        ]
        
        if model_config.get('model'):
            cmd.extend(['--model', model_config['model']])
        
        print(f"Testing {model_config['name']}...", file=sys.stderr)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                print(f"  ❌ Failed: {error_msg}", file=sys.stderr)
                return model_config['name'], None
            
            # Read the output
            with open(output_file, 'r', encoding='utf-8') as f:
                transcription = f.read()
            
            print(f"  ✓ Complete", file=sys.stderr)
            return model_config['name'], transcription
            
        except subprocess.TimeoutExpired:
            print(f"  ❌ Timeout", file=sys.stderr)
            return model_config['name'], None
        except Exception as e:
            print(f"  ❌ Error: {e}", file=sys.stderr)
            return model_config['name'], None
    
    def calculate_metrics(self, transcription: str) -> Dict:
        """Calculate various accuracy metrics"""
        if not transcription:
            return {
                'char_accuracy': 0.0,
                'word_accuracy': 0.0,
                'line_accuracy': 0.0,
                'unicode_preservation': 0.0,
                'cyrillic_preserved': False,
                'structure_score': 0.0,
                'proper_noun_score': 0.0,
                'overall_score': 0.0
            }
        
        # Character-level accuracy (Levenshtein distance)
        char_distance = Levenshtein.distance(self.ground_truth, transcription)
        char_accuracy = 1.0 - (char_distance / max(len(self.ground_truth), len(transcription)))
        
        # Word-level accuracy
        gt_words = self.ground_truth.split()
        tr_words = transcription.split()
        word_matcher = SequenceMatcher(None, gt_words, tr_words)
        word_accuracy = word_matcher.ratio()
        
        # Line-level accuracy
        gt_lines = self.ground_truth.strip().split('\n')
        tr_lines = transcription.strip().split('\n')
        line_matcher = SequenceMatcher(None, gt_lines, tr_lines)
        line_accuracy = line_matcher.ratio()
        
        # Unicode symbol preservation
        unicode_symbols = ['☆', '★', '—', '==']
        unicode_score = sum(
            1 for sym in unicode_symbols 
            if (sym in self.ground_truth) == (sym in transcription)
        ) / len(unicode_symbols)
        
        # Cyrillic preservation (check if Cyrillic exists and is preserved)
        gt_cyrillic = bool(re.search(r'[А-Яа-я]', self.ground_truth))
        tr_cyrillic = bool(re.search(r'[А-Яа-я]', transcription))
        cyrillic_preserved = (not gt_cyrillic) or (gt_cyrillic and tr_cyrillic)
        
        # Structure score (tables, headers, lists)
        structure_elements = [
            (r'\*\*.*?\*\*', 'headers'),  # Bold headers
            (r'^\|.*\|$', 'tables'),      # Tables
            (r'^- ', 'lists'),            # Lists
        ]
        structure_matches = 0
        for pattern, _ in structure_elements:
            gt_has = bool(re.search(pattern, self.ground_truth, re.MULTILINE))
            tr_has = bool(re.search(pattern, transcription, re.MULTILINE))
            if gt_has == tr_has:
                structure_matches += 1
        structure_score = structure_matches / len(structure_elements)
        
        # Proper noun detection (simplified - checks capitalized words)
        gt_proper = set(re.findall(r'\b[A-Z][a-zäöüßÄÖÜ]+\b', self.ground_truth))
        tr_proper = set(re.findall(r'\b[A-Z][a-zäöüßÄÖÜ]+\b', transcription))
        if gt_proper:
            proper_noun_score = len(gt_proper & tr_proper) / len(gt_proper)
        else:
            proper_noun_score = 1.0
        
        # Overall weighted score
        overall_score = (
            char_accuracy * 0.30 +
            word_accuracy * 0.25 +
            unicode_score * 0.15 +
            structure_score * 0.15 +
            proper_noun_score * 0.15
        )
        
        return {
            'char_accuracy': char_accuracy,
            'word_accuracy': word_accuracy,
            'line_accuracy': line_accuracy,
            'unicode_preservation': unicode_score,
            'cyrillic_preserved': cyrillic_preserved,
            'structure_score': structure_score,
            'proper_noun_score': proper_noun_score,
            'overall_score': overall_score
        }
    
    def run_all_tests(self, test_cloud: bool = True, test_local: bool = True) -> Dict:
        """Run tests for all configured models"""
        results = {}
        
        models_to_test = []
        if test_cloud:
            models_to_test.extend(TEST_MODELS['cloud'])
        if test_local:
            # Dynamically detect available Ollama models
            local_models = detect_ollama_vision_models()
            if not local_models:
                print("No vision-capable Ollama models found", file=sys.stderr)
            models_to_test.extend(local_models)
        
        if not models_to_test:
            raise ValueError("No models available to test!")
        
        for model_config in models_to_test:
            name, transcription = self.run_transcription(model_config)
            metrics = self.calculate_metrics(transcription)
            results[name] = {
                'transcription': transcription,
                'metrics': metrics,
                'config': model_config
            }
        
        return results
    
    def generate_report(self, results: Dict, output_file: Path):
        """Generate a markdown report comparing all models"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = [
            "# LLM Transcription Quality Report",
            f"\nGenerated: {timestamp}",
            f"\nTest file: `{self.note_file.name}`",
            f"\nGround truth: `{self.ground_truth_file.name}`",
            "\n---\n",
            "## Summary Ranking",
            ""
        ]
        
        # Sort by overall score
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1]['metrics']['overall_score'],
            reverse=True
        )
        
        # Summary table
        report.append("| Rank | Model | Overall Score | Char Acc | Word Acc | Unicode | Structure | Proper Nouns |")
        report.append("|------|-------|---------------|----------|----------|---------|-----------|--------------|")
        
        for rank, (name, data) in enumerate(sorted_results, 1):
            m = data['metrics']
            report.append(
                f"| {rank} | {name} | {m['overall_score']:.2%} | "
                f"{m['char_accuracy']:.2%} | {m['word_accuracy']:.2%} | "
                f"{m['unicode_preservation']:.2%} | {m['structure_score']:.2%} | "
                f"{m['proper_noun_score']:.2%} |"
            )
        
        report.append("\n---\n")
        report.append("## Detailed Results\n")
        
        # Detailed breakdown for each model
        for name, data in sorted_results:
            m = data['metrics']
            config = data['config']
            
            report.append(f"### {name}")
            report.append(f"\n**Configuration:** API=`{config['api']}`" + 
                         (f", Model=`{config.get('model', 'default')}`" if config.get('model') else ""))
            report.append(f"\n**Overall Score:** {m['overall_score']:.2%}\n")
            
            report.append("**Metrics:**")
            report.append(f"- Character Accuracy: {m['char_accuracy']:.2%}")
            report.append(f"- Word Accuracy: {m['word_accuracy']:.2%}")
            report.append(f"- Line Accuracy: {m['line_accuracy']:.2%}")
            report.append(f"- Unicode Preservation: {m['unicode_preservation']:.2%}")
            report.append(f"- Cyrillic Preserved: {'✓' if m['cyrillic_preserved'] else '✗'}")
            report.append(f"- Structure Score: {m['structure_score']:.2%}")
            report.append(f"- Proper Noun Score: {m['proper_noun_score']:.2%}")
            
            # Output file location
            safe_name = self.sanitize_model_name(name)
            output_file_path = self.output_dir / f"test-output-{safe_name}.md"
            report.append(f"\n**Output:** `{output_file_path.relative_to(self.test_dir.parent)}`\n")
        
        report.append("\n---\n")
        report.append("## Notes\n")
        report.append("- **Character Accuracy**: Edit distance based (Levenshtein)")
        report.append("- **Word Accuracy**: Word-level sequence matching")
        report.append("- **Unicode Preservation**: Checks for ☆, ★, —, == symbols")
        report.append("- **Structure Score**: Presence of headers, tables, lists")
        report.append("- **Proper Noun Score**: Capitalized word matching (simplified)")
        report.append("- **Overall Score**: Weighted average (char: 30%, word: 25%, unicode: 15%, structure: 15%, proper nouns: 15%)")
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"\nReport saved to: {output_file}", file=sys.stderr)
        
        # Also print to stdout
        print('\n'.join(report))
    
    def save_results_json(self, results: Dict, output_file: Path):
        """Save detailed results as JSON for programmatic access"""
        # Remove transcription text to keep JSON manageable
        json_results = {}
        for name, data in results.items():
            # Sanitize name for filename
            safe_name = name.replace('/', '_').replace(':', '-')
            json_results[name] = {
                'metrics': data['metrics'],
                'config': data['config'],
                'output_file': str(self.output_dir / f"test-output-{safe_name}.md")
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)
        
        print(f"JSON results saved to: {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Test and compare LLM transcription quality",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--test-file',
        type=Path,
        default=Path(__file__).parent / 'test.note',
        help='Input .note file to test (default: test/test.note)'
    )
    
    parser.add_argument(
        '--ground-truth',
        type=Path,
        default=Path(__file__).parent / 'test-transcribed.md',
        help='Ground truth transcription (default: test/test-transcribed.md)'
    )
    
    parser.add_argument(
        '--cloud-only',
        action='store_true',
        help='Test only cloud models'
    )
    
    parser.add_argument(
        '--local-only',
        action='store_true',
        help='Test only local models'
    )
    
    parser.add_argument(
        '--ollama-only',
        action='store_true',
        help='Test only Ollama models (alias for --local-only)'
    )
    
    parser.add_argument(
        '--report',
        type=Path,
        default=Path(__file__).parent / 'outputs' / 'test-report.md',
        help='Output report file (default: test/outputs/test-report.md)'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.test_file.exists():
        print(f"Error: Test file not found: {args.test_file}", file=sys.stderr)
        sys.exit(1)
    
    if not args.ground_truth.exists():
        print(f"Error: Ground truth file not found: {args.ground_truth}", file=sys.stderr)
        sys.exit(1)
    
    # Run tests
    test_dir = Path(__file__).parent
    tester = TranscriptionTester(test_dir, args.test_file, args.ground_truth)
    
    # Handle --ollama-only as alias for --local-only
    if args.ollama_only:
        args.local_only = True
    
    test_cloud = not args.local_only
    test_local = not args.cloud_only
    
    print("Starting transcription tests...\n", file=sys.stderr)
    results = tester.run_all_tests(test_cloud=test_cloud, test_local=test_local)
    
    # Generate reports
    print("\nGenerating reports...", file=sys.stderr)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    tester.generate_report(results, args.report)
    
    # Save JSON
    json_file = args.report.with_suffix('.json')
    tester.save_results_json(results, json_file)
    
    print("\n✓ Testing complete!", file=sys.stderr)


if __name__ == '__main__':
    main()
