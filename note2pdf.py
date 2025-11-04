#!/usr/bin/env python3
"""
DEPRECATED: This script is deprecated and will be removed in v1.0.0

Use the new package interface instead:
  - Install: pip install -e .
  - New CLI: supernote convert note2pdf input.note output.pdf
  - Or use: note2pdf (entry point from package)

This wrapper is provided for backwards compatibility.
"""

import sys
import warnings

warnings.warn(
    "note2pdf.py is deprecated. Use 'supernote convert note2pdf' or the 'note2pdf' command after installing the package.",
    DeprecationWarning,
    stacklevel=2,
)

# Import and run the new implementation
from supernote_utils.cli.note2pdf import main

if __name__ == "__main__":
    main()
