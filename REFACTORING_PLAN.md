# Supernote Utils - Refactoring Plan

## Project Analysis

### Purpose
**Supernote Utils** is a Python toolkit for transcribing handwritten notes from Ratta Supernote tablets to text/markdown using LLM vision APIs (Claude, Gemini, Ollama).

### Current Structure

```
supernote-utils/
├── note2text.py              (437 lines) - .note → Markdown via LLM
├── script2text.py            (333 lines) - PDF → Markdown via LLM
├── note2pdf.py               (53 lines)  - .note → PDF
├── transcription_prompt.py   (27 lines)  - Shared prompt
├── requirements.txt
├── supernotelib/             (vendored dependency)
└── test/
    ├── test_transcription.py
    ├── test_note2pdf.py
    └── test_ollama_detection.py
```

**Total LOC**: ~850 lines across 4 main scripts

---

## Issues Identified

### 1. **Code Duplication (High Priority)**

**Problem**: `note2text.py` and `script2text.py` share ~70% of their code:
- Duplicate API client initialization (3 providers × 2 files = 6 implementations)
- Duplicate image processing logic (`_image_to_base64`, `process_with_*`)
- Duplicate Ollama model detection (`_detect_vision_model`)
- Duplicate argument parsing patterns
- Duplicate error handling

**Impact**:
- Changes require updating multiple files
- High risk of inconsistencies
- Harder to add new API providers
- Increased maintenance burden

**Evidence**:
```python
# note2text.py lines 40-118: OllamaVisionAPI class (78 lines)
# script2text.py lines 133-152: _detect_ollama_vision_model (20 lines)
# Both duplicate the same vision model detection logic

# note2text.py lines 185-210: _process_with_anthropic
# script2text.py lines 162-173: process_with_anthropic
# Nearly identical implementations
```

### 2. **No Package Structure (High Priority)**

**Problem**: Project is a collection of scripts, not an installable package
- No `setup.py` or `pyproject.toml`
- Can't install with `pip install -e .`
- No entry points for CLI commands
- Can't import as library: `from supernote_utils import TranscriptionAPI`

**Impact**:
- Users must run scripts directly with paths
- Hard to use as dependency in other projects
- No version management
- Can't distribute via PyPI

### 3. **Inconsistent Naming & CLI (Medium Priority)**

**Problem**: Mixed naming conventions and CLI patterns
- `note2text.py` vs `script2text.py` vs `note2pdf.py` (inconsistent naming)
- Different argument patterns: `--md`, `--out`, `--pdf`
- `script2text.py` uses `--page_separator` (underscore) vs others use kebab-case
- No unified CLI interface

**Impact**:
- Confusing for users
- Hard to remember command syntax
- Inconsistent user experience

### 4. **Tight Coupling (Medium Priority)**

**Problem**: Business logic tightly coupled with infrastructure
- API initialization mixed with conversion logic in `NoteToTextConverter`
- Image extraction coupled with transcription in same class
- CLI argument parsing mixed with processing logic

**Impact**:
- Hard to test components in isolation
- Can't reuse API clients across scripts
- Difficult to swap implementations

### 5. **Limited Extensibility (Medium Priority)**

**Problem**: Hard to extend with new capabilities
- Adding new API provider requires editing multiple files
- No plugin system for custom processors
- Hardcoded model names and endpoints
- No abstraction for image sources

**Impact**:
- Vendor lock-in to current APIs
- Can't easily add custom LLM providers
- Hard to support new Supernote formats

### 6. **No Configuration Management (Low Priority)**

**Problem**: Settings scattered throughout code
- Hardcoded temperature defaults in multiple places
- Model names embedded in if/else chains
- No way to save user preferences
- Environment variables only option for API keys

**Impact**:
- Users can't save preferred settings
- Hard to manage different profiles
- Repetitive command-line arguments

### 7. **Inadequate Error Handling (Low Priority)**

**Problem**: Inconsistent error handling and logging
- Mix of print statements and exceptions
- Errors go to stderr without structured logging
- No retry logic for API failures
- Limited user-friendly error messages

### 8. **Test Organization (Low Priority)**

**Problem**: Tests lack structure
- All tests in single directory
- No separation of unit/integration/e2e tests
- Test utilities not reusable
- No mocking of API calls (hits real APIs)

---

## Proposed Refactoring Plan

### Phase 1: Core Architecture (Breaking Changes)

**Goal**: Establish proper package structure and eliminate code duplication

#### 1.1 Create Package Structure

```
supernote-utils/
├── pyproject.toml              # Modern Python packaging
├── README.md
├── supernote_utils/            # Main package
│   ├── __init__.py
│   ├── __version__.py
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── transcriber.py      # Main transcription logic
│   │   ├── image_processor.py  # Image handling
│   │   └── prompts.py          # Prompt management
│   ├── providers/              # API provider implementations
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base class
│   │   ├── anthropic.py        # Claude implementation
│   │   ├── google.py           # Gemini implementation
│   │   └── ollama.py           # Ollama implementation
│   ├── sources/                # Input source handlers
│   │   ├── __init__.py
│   │   ├── note.py             # .note file handling
│   │   └── pdf.py              # PDF handling
│   ├── cli/                    # CLI commands
│   │   ├── __init__.py
│   │   ├── main.py             # Main CLI entry
│   │   ├── note2text.py
│   │   ├── script2text.py
│   │   └── note2pdf.py
│   ├── config.py               # Configuration management
│   └── exceptions.py           # Custom exceptions
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── scripts/                    # Legacy scripts (deprecated)
    └── migrate.sh
```

**Benefits**:
- Importable as library
- Clear separation of concerns
- Easy to test and maintain
- Standard Python project layout

#### 1.2 Extract Provider Interface

Create abstract base class for LLM providers:

```python
# supernote_utils/providers/base.py
from abc import ABC, abstractmethod
from PIL import Image

class VisionProvider(ABC):
    """Abstract base for vision LLM providers"""

    @abstractmethod
    def __init__(self, model: str = None, temperature: float = 0.2):
        pass

    @abstractmethod
    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe handwritten image to text"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available"""
        pass
```

**Benefits**:
- Easy to add new providers
- Consistent interface
- Testable with mocks
- Reduces duplication by ~300 lines

#### 1.3 Unified Transcription Engine

Consolidate duplicate logic into single engine:

```python
# supernote_utils/core/transcriber.py
class Transcriber:
    """Unified transcription engine"""

    def __init__(self, provider: VisionProvider, config: TranscriptionConfig):
        self.provider = provider
        self.config = config

    def transcribe_images(self, images: List[Image.Image]) -> str:
        """Transcribe multiple images to markdown"""
        # Single implementation used by all commands
        pass
```

**Benefits**:
- Eliminates duplication
- Single source of truth
- Easier to optimize
- Better error handling

#### 1.4 Standardized CLI

Create unified CLI with subcommands:

```bash
# New interface
supernote transcribe note input.note -o output.md --api claude
supernote transcribe pdf input.pdf -o output.md --api gemini
supernote convert note2pdf input.note output.pdf

# Or backwards-compatible scripts
note2text input.note -o output.md --api claude
```

**Benefits**:
- Consistent interface
- Easier to learn
- Better help system
- Entry points in pyproject.toml

### Phase 2: Enhanced Capabilities (Non-Breaking)

#### 2.1 Configuration System

Add user configuration file support:

```yaml
# ~/.supernote/config.yaml
default_provider: claude-sonnet
temperature: 0.2
providers:
  claude:
    model: claude-sonnet-4-5-20250929
  gemini:
    model: gemini-2.5-flash
  ollama:
    model: qwen2.5-vl:7b
    base_url: http://localhost:11434
```

#### 2.2 Enhanced Error Handling

- Structured logging with `logging` module
- Retry logic for API failures
- Better error messages with suggestions
- Progress bars for batch processing

#### 2.3 Advanced Features

- Batch processing multiple files
- Output format plugins (JSON, HTML, plain text)
- Custom prompt templates
- Result caching to avoid reprocessing

### Phase 3: Quality & Polish

#### 3.1 Test Improvements

- Separate unit/integration/e2e tests
- Mock API providers for unit tests
- Property-based testing for image processing
- CI/CD pipeline with pytest

#### 3.2 Documentation

- API documentation with Sphinx
- Developer guide
- Migration guide from old scripts
- Architecture decision records (ADRs)

#### 3.3 Distribution

- Publish to PyPI as `supernote-utils`
- Docker image for easy deployment
- Pre-built binaries with PyInstaller

---

## Implementation Steps

### Step 1: Setup Package Structure (2-3 hours)

**Tasks**:
1. Create `pyproject.toml` with dependencies
2. Create package directory structure
3. Add `__init__.py` files
4. Setup entry points for CLI

**Validation**:
- `pip install -e .` works
- `supernote --help` shows help
- Package imports work

### Step 2: Extract Provider Interface (2-3 hours)

**Tasks**:
1. Create `providers/base.py` with abstract class
2. Extract Anthropic provider to `providers/anthropic.py`
3. Extract Google provider to `providers/google.py`
4. Extract Ollama provider to `providers/ollama.py`
5. Add provider factory

**Validation**:
- All providers pass same test suite
- No duplicate code between providers
- Can swap providers without changing caller

### Step 3: Consolidate Image Processing (1-2 hours)

**Tasks**:
1. Create `core/image_processor.py`
2. Move image conversion logic
3. Create `sources/note.py` for .note extraction
4. Create `sources/pdf.py` for PDF extraction

**Validation**:
- Both CLI tools use same image processing
- Clean separation of concerns

### Step 4: Unified Transcription Engine (2-3 hours)

**Tasks**:
1. Create `core/transcriber.py`
2. Consolidate transcription logic
3. Add configuration support
4. Move prompt management to `core/prompts.py`

**Validation**:
- Single code path for transcription
- All features still work
- Tests pass

### Step 5: Standardize CLI (2-3 hours)

**Tasks**:
1. Create unified CLI in `cli/main.py`
2. Convert scripts to subcommands
3. Standardize arguments
4. Add backwards-compatible wrapper scripts

**Validation**:
- New CLI works
- Old scripts still work (deprecated)
- Consistent help messages

### Step 6: Testing & Documentation (2-4 hours)

**Tasks**:
1. Add unit tests for all modules
2. Add integration tests
3. Update README
4. Add migration guide
5. Test installation process

**Validation**:
- 80%+ test coverage
- All examples in README work
- Installation is smooth

---

## Migration Strategy

### Backwards Compatibility

Keep old scripts working during transition:

```python
# Legacy note2text.py (deprecated)
import warnings
from supernote_utils.cli.note2text import main

warnings.warn(
    "note2text.py is deprecated. Use 'supernote transcribe note' instead.",
    DeprecationWarning
)

if __name__ == "__main__":
    main()
```

### Deprecation Timeline

- **v0.1.0**: Old scripts work, warnings shown
- **v0.2.0**: Old scripts moved to `scripts/legacy/`
- **v1.0.0**: Old scripts removed, new CLI only

---

## Success Metrics

### Code Quality
- [ ] Reduce total LOC by 30% through deduplication
- [ ] Achieve 80%+ test coverage
- [ ] Zero code duplication in core logic
- [ ] All linting passes (ruff, mypy)

### User Experience
- [ ] Single command to install: `pip install supernote-utils`
- [ ] Consistent CLI across all commands
- [ ] 90% of use cases need <3 arguments
- [ ] Error messages include actionable suggestions

### Maintainability
- [ ] Adding new provider takes <30 minutes
- [ ] All components independently testable
- [ ] Documentation covers all public APIs
- [ ] CI/CD runs in <5 minutes

---

## Risk Assessment

### High Risk
- **Breaking changes**: Users with scripts may need updates
  - **Mitigation**: Keep old scripts working with deprecation warnings

### Medium Risk
- **Testing gaps**: May miss edge cases during refactor
  - **Mitigation**: Comprehensive test suite before refactoring

- **Scope creep**: Adding too many features
  - **Mitigation**: Stick to 3-phase plan, defer nice-to-haves

### Low Risk
- **API changes**: LLM providers changing APIs
  - **Mitigation**: Provider abstraction isolates changes

---

## Timeline Estimate

- **Phase 1 (Core Architecture)**: 12-16 hours
- **Phase 2 (Enhanced Capabilities)**: 8-12 hours
- **Phase 3 (Quality & Polish)**: 8-12 hours

**Total**: 28-40 hours for complete refactoring

**Minimum Viable Refactor** (Phase 1 only): 12-16 hours

---

## Conclusion

This refactoring will transform supernote-utils from a collection of scripts into a professional Python package with:
- **70% less code duplication**
- **Proper package structure** for pip installation
- **Extensible architecture** for new providers/features
- **Consistent CLI** for better UX
- **Comprehensive tests** for reliability

The phased approach allows incremental delivery while maintaining backwards compatibility during migration.
