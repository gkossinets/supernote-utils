#!/usr/bin/env python3
"""
DEPRECATED: This script is deprecated and will be removed in v1.0.0

Use the new package interface instead:
  - Install: pip install -e .
  - New CLI: supernote transcribe note input.note -o output.md
  - Or use: note2text (entry point from package)

This wrapper is provided for backwards compatibility.
"""

import sys
import warnings

warnings.warn(
    "note2text.py is deprecated. Use 'supernote transcribe note' or the 'note2text' command after installing the package.",
    DeprecationWarning,
    stacklevel=2,
)

# Import and run the new implementation
from supernote_utils.cli.note2text import main

if __name__ == "__main__":
    main()
