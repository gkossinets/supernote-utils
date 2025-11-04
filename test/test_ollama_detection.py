#!/usr/bin/env python3
"""Test script to verify Ollama model detection works correctly"""

import ollama

# Test the fixed detection logic
models = ollama.list()
model_list = models.get('models', [])

print('Testing fixed model detection:')
print(f'Found {len(model_list)} total models\n')

vision_keywords = ['qwen', 'llama3.2-vision', 'llava', 'minicpm', 'vision', 'ocr', 'nanonets']

vision_models = []
for model in model_list:
    name = getattr(model, 'model', model.get('model', ''))
    is_vision = any(keyword in name.lower() for keyword in vision_keywords)
    status = '✓ VISION' if is_vision else '  (text)'
    print(f'{status:10s} {name}')
    if is_vision:
        vision_models.append(name)

print(f'\n{len(vision_models)} vision models found:')
for name in vision_models:
    print(f'  - {name}')
