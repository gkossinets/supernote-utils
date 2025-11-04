#!/usr/bin/env python3
"""
DEPRECATED: This script is deprecated and will be removed in v1.0.0

Use the new package interface instead:
  - Install: pip install -e .
  - New CLI: supernote transcribe pdf input.pdf -o output.md
  - Or use: script2text (entry point from package)

This wrapper is provided for backwards compatibility.
"""

import sys
import warnings

warnings.warn(
    "script2text.py is deprecated. Use 'supernote transcribe pdf' or the 'script2text' command after installing the package.",
    DeprecationWarning,
    stacklevel=2,
)

# Import and run the new implementation
from supernote_utils.cli.script2text import main

if __name__ == "__main__":
    main()
