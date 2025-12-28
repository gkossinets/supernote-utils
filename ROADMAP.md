# Supernote Transcriber - Product Roadmap

**Created:** 2025-12-28  
**Last Updated:** 2025-12-28  
**Status:** Planning  
**Target:** Cross-platform desktop app (macOS + Windows)

---

## Executive Summary

Transform the existing CLI-based supernote-utils into a user-friendly desktop application for non-technical users who want to transcribe handwritten notes from Ratta Supernote tablets using LLM vision models.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **App Name** | Supernote Transcriber | Clear purpose, niche appeal to Supernote community |
| **Framework** | Tauri + React | Cross-platform, small bundle, App Store ready |
| **Backend** | Rust | Port Python logic for clean distribution |
| **Distribution** | App Stores + Direct | Apple App Store, Microsoft Store, GitHub releases |
| **Pricing** | Free + Tip Jar | Calibre model - works fully, optional donations |
| **API Model** | BYOK (Bring Your Own Key) | User provides API keys with streamlined wizard |
| **Default Provider** | Gemini (recommended) | Easiest API key setup, good quality, reasonable free tier |
| **Input Formats** | .note, PDF, PNG, JPEG | All supported from v1.0 |

---

## Table of Contents

1. [Business Model](#business-model)
2. [API Strategy & Free Tier Analysis](#api-strategy--free-tier-analysis)
3. [Technology Stack](#technology-stack)
4. [Architecture](#architecture)
5. [Feature Specifications](#feature-specifications)
6. [User Experience Design](#user-experience-design)
7. [App Store Requirements](#app-store-requirements)
8. [Porting Strategy](#porting-strategy)
9. [Development Phases](#development-phases)
10. [Competitive Analysis](#competitive-analysis)

---

## Business Model

### Pricing: Free + Tip Jar (Calibre Model)

The app is **completely free** with full functionality. Users are encouraged but never required to support development.

**Implementation:**
- App works fully without any payment
- Settings includes "Support Development" link
- Options: Ko-fi, Buy Me a Coffee, GitHub Sponsors, or PayPal
- No features locked behind payment
- No nag screens or usage limits

**Rationale:**
- Follows successful open-source pattern (Calibre, VLC, 7-Zip)
- Removes friction for adoption
- Builds goodwill in Supernote community
- API costs are borne by users (BYOK model)

### Why Not Freemium/Subscription?

- App itself has no ongoing costs (no server, no bundled API)
- Complexity of payment processing not worth it for niche audience
- Community trust more valuable than direct revenue
- Can always add premium features later if demand exists

---

## API Strategy & Free Tier Analysis

### The Challenge (December 2025)

Non-technical users face significant friction obtaining API keys. The ideal "works out of box" experience requires either:
1. Bundled API credits (expensive, complex)
2. Generous free tier from providers (no longer exists)
3. Excellent onboarding wizard (our approach)

### Free Tier Landscape (Late December 2025)

Google dramatically reduced free tier limits in early December 2025:

| Provider | Model | Free Tier | Paid Pricing | Notes |
|----------|-------|-----------|--------------|-------|
| **Google** | Gemini 3 Flash | ~5 RPM, limited daily | $0.50/$3.00 per 1M tokens | New model, excellent quality |
| **Google** | Gemini 2.5 Flash | ~20 RPD (down from 250) | $0.30/$2.50 per 1M tokens | 92% reduction in Dec 2025 |
| **Google** | Gemini 2.5 Flash-Lite | 1,000 RPD | $0.10/$0.40 per 1M tokens | Best free tier remaining |
| **Google** | Gemini 2.5 Pro | **Removed from free tier** | $1.25/$10.00 per 1M tokens | No longer free |
| **Anthropic** | Claude Sonnet 4.5 | None | $3.00/$15.00 per 1M tokens | Best quality, no free tier |
| **Anthropic** | Claude Haiku 4.5 | None | $0.80/$4.00 per 1M tokens | Fast, no free tier |
| **OpenAI** | GPT-4o | None (initial credits only) | $2.50/$10.00 per 1M tokens | No ongoing free tier |
| **OpenAI** | GPT-4o-mini | None | $0.15/$0.60 per 1M tokens | Cheapest OpenAI option |
| **Ollama** | Various | Unlimited (local) | Free | Requires local setup |

### Our Strategy: BYOK with Streamlined Onboarding

Since no provider offers a sustainable free tier for production use, we embrace BYOK (Bring Your Own Key) with the best possible user experience:

**First-Run Experience:**
1. Welcome screen explaining the app needs an AI service
2. Provider comparison card:
   - **Gemini (Recommended)**: "Easiest setup, free tier available, great quality"
   - **Claude**: "Best accuracy, premium pricing"
   - **GPT-4o**: "OpenAI's vision model, familiar interface"
   - **Ollama**: "Free & private, runs on your computer (advanced)"
3. Step-by-step wizard for selected provider:
   - Direct link to API console (opens in browser)
   - Annotated screenshots showing exactly where to click
   - "Copy Key" → "Paste Here" interface
   - Test connection button with success/failure feedback
4. Estimated costs shown: "Transcribing 10 pages costs approximately $0.01-0.05"

**Why Gemini is Recommended Default:**
- Google AI Studio has simplest key creation flow
- No credit card required for free tier
- Gemini 3 Flash quality rivals Claude Sonnet
- Commercial use explicitly permitted
- Clear, predictable pricing

### Cost Reality Check

For typical usage, API costs are negligible:

| Usage Level | Pages/Month | Estimated Cost |
|-------------|-------------|----------------|
| Light | 50 pages | $0.05-0.25 |
| Moderate | 200 pages | $0.20-1.00 |
| Heavy | 1000 pages | $1.00-5.00 |

*Based on ~2K tokens per page, Gemini 3 Flash pricing*

---

## Technology Stack

### Supported LLM Providers (v1.0)

| Provider | Models | Use Case |
|----------|--------|----------|
| **Anthropic (Claude)** | Claude Sonnet 4.5, Claude Haiku 4.5 | Best accuracy, premium |
| **Google (Gemini)** | Gemini 3 Flash, 2.5 Flash, 2.5 Pro | Recommended default |
| **OpenAI (GPT)** | GPT-4o, GPT-4o-mini | Alternative, familiar brand |
| **Ollama (Local)** | qwen2.5-vl, llama3.2-vision, etc. | Privacy, offline, free |

### Why Tauri + React

| Consideration | Tauri | Electron | Native (Swift/C#) |
|---------------|-------|----------|-------------------|
| Bundle size | 10-20 MB | 100+ MB | 5-10 MB |
| Memory usage | Low | High | Low |
| Cross-platform | ✅ Single codebase | ✅ Single codebase | ❌ Two codebases |
| App Store ready | ✅ Both stores | ⚠️ Possible | ✅ Best |
| Claude Code support | Excellent (Rust + React) | Excellent | Good |
| Security | Rust memory safety | Node.js concerns | Native |

### Stack Components

```
Frontend:
- React 18+ with TypeScript
- Tailwind CSS for styling
- Zustand or Jotai for state management
- React Query for async operations

Backend (Tauri/Rust):
- tauri (app framework)
- reqwest (HTTP client for API calls)
- serde (JSON serialization)
- keyring (secure credential storage)
- tokio (async runtime)

File Processing:
- Custom .note parser (ported from Python)
- image (Rust image processing)
- pdf (PDF generation/reading)
- docx-rs (Word document generation)
```

---

## Architecture

### High-Level Design

```
┌────────────────────────────────────────────────────────────────┐
│                        Tauri Application                        │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 React Frontend (WebView)                  │  │
│  │                                                           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │  │
│  │  │ Drop Zone   │ │ Settings    │ │ Transcription View  │ │  │
│  │  │ (.note/PDF/ │ │ Panel       │ │ (Progress/Results)  │ │  │
│  │  │  PNG/JPEG)  │ │             │ │                     │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │              Prompt Editor (Advanced Mode)           │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ Tauri Commands (IPC)              │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Rust Backend                           │  │
│  │                                                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │  │
│  │  │ File Parsers │ │ LLM Clients  │ │ Export Engine    │  │  │
│  │  │ .note/PDF/   │ │ Claude/Gem/  │ │ (MD/TXT/DOCX)    │  │  │
│  │  │ PNG/JPEG     │ │ GPT/Ollama   │ │                  │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘  │  │
│  │                                                           │  │
│  │  ┌──────────────┐ ┌──────────────┐                       │  │
│  │  │ Credential   │ │ Config       │                       │  │
│  │  │ Manager      │ │ Storage      │                       │  │
│  │  │ (Keychain)   │ │ (JSON)       │                       │  │
│  │  └──────────────┘ └──────────────┘                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

### Supported Input Formats

| Format | Source | Processing |
|--------|--------|------------|
| `.note` | Supernote tablet | Parse binary format, extract page images |
| PDF | Exported from Supernote, scanned docs | Extract embedded images or render pages |
| PNG | Photos of paper notebooks | Direct use |
| JPEG | Photos of paper notebooks | Direct use |

### Data Flow

```
1. User drops file onto app (.note / PDF / PNG / JPEG)
                │
                ▼
2. Frontend sends file path to Rust backend via Tauri command
                │
                ▼
3. Rust detects file type and extracts/loads images
   - .note: Parse binary, extract page bitmaps
   - PDF: Extract embedded images or render pages
   - PNG/JPEG: Load directly
                │
                ▼
4. Rust calls selected LLM API with images + prompt + language hints
                │
                ▼
5. Streaming response displayed in frontend (real-time)
                │
                ▼
6. User edits/saves result as MD/TXT/DOCX
```

---

## Feature Specifications

### MVP (v1.0) - "It Just Works"

**Core Functionality:**
- [ ] Drag-and-drop support for: .note, PDF, PNG, JPEG
- [ ] Provider selection: Claude, Gemini, GPT-4o, Ollama
- [ ] Model selection within each provider
- [ ] API key setup wizard with:
  - Provider comparison cards
  - Step-by-step instructions with screenshots
  - Direct links to API consoles
  - Test connection button
- [ ] Secure credential storage (Keychain/Credential Manager)
- [ ] Transcription with progress indicator
- [ ] Cancel operation button
- [ ] Output formats: Markdown, Plain Text
- [ ] Copy to clipboard
- [ ] Save to file (with file picker)

**Language Support:**
- [ ] Primary language dropdown (English, German, Russian, Spanish, French, etc.)
- [ ] Secondary language dropdown (optional)
- [ ] Language hints injected into transcription prompt
- [ ] Improves accuracy for multilingual notes

**Settings (Basic Mode):**
- [ ] Provider/model selection
- [ ] Language preferences
- [ ] Output format preference
- [ ] Default save location

**First-Run Experience:**
- [ ] Welcome screen explaining the app
- [ ] Provider selection with recommendations
- [ ] API key setup wizard (provider-specific)
- [ ] Test transcription with sample
- [ ] Optional: Ollama auto-detection for local users

**Support Development:**
- [ ] "Support Development" link in Settings
- [ ] Links to Ko-fi / Buy Me a Coffee / GitHub Sponsors
- [ ] Non-intrusive, appears only in Settings

### v1.1 - "Power User Features"

**Advanced Settings:**
- [ ] Temperature control (slider with tooltips explaining effect)
- [ ] Custom prompt editor:
  - Default prompt shown (editable)
  - Preset prompts: Journal, Scientific, Meeting Notes, Creative Writing
  - Save custom presets
  - Reset to default button
- [ ] Batch processing (drag folder or multiple files)
- [ ] Processing queue with status per file

**Quality of Life:**
- [ ] Recent files list (last 10)
- [ ] Remember window size/position
- [ ] Dark mode support (follow system)
- [ ] Keyboard shortcuts (⌘O open, ⌘S save, etc.)

### v1.2 - "Professional Features"

**Enhanced Output:**
- [ ] Word document (.docx) export with formatting
- [ ] Side-by-side view: original image | transcription
- [ ] Page-by-page navigation for multi-page documents
- [ ] Edit transcription before saving

**Workflow Integration:**
- [ ] Obsidian vault folder picker (auto-save there)
- [ ] Google Docs export (via API)
- [ ] Watch folder mode (auto-process new files)

### v2.0 - "Expert Mode"

**Advanced Features:**
- [ ] Custom vocabulary/dictionary for proper nouns
- [ ] Multi-model verification (run through 2 models, highlight differences)
- [ ] Transcription history with search
- [ ] Usage statistics (API calls, costs estimate)
- [ ] Plugin system for custom post-processing

---

## User Experience Design

### Design Principles

1. **Progressive Disclosure**: Basic mode by default, advanced features hidden but accessible
2. **No Jargon**: "AI Service" not "LLM Provider", "Creativity" not "Temperature"
3. **Fail Gracefully**: Every error has a plain-English explanation and suggested action
4. **Instant Feedback**: Always show what's happening (progress, status messages)
5. **Respect User Time**: Remember preferences, minimize clicks for common tasks

### Main Window Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  Supernote Transcriber                              [─] [□] [×] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │         ┌──────────────────────────────────┐              │  │
│  │         │                                   │              │  │
│  │         │     📄 Drop your file here       │              │  │
│  │         │                                   │              │  │
│  │         │   .note  PDF  PNG  JPEG          │              │  │
│  │         │                                   │              │  │
│  │         │     or click to browse           │              │  │
│  │         │                                   │              │  │
│  │         └──────────────────────────────────┘              │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ AI Service          │  │ Output Format                    │  │
│  │ [Gemini 3 Flash ▼]  │  │ ○ Markdown  ○ Plain Text        │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ Primary Language    │                                        │
│  │ [English        ▼]  │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  [⚙️ Settings]                              [✨ Transcribe]     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### API Key Setup Wizard

```
┌─────────────────────────────────────────────────────────────────┐
│  Set Up AI Service                                          [×] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Choose your AI service:                                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ⭐ RECOMMENDED                                           │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ 🔷 Gemini (Google)                                  │ │   │
│  │ │                                                      │ │   │
│  │ │ • Easiest setup - just a Google account            │ │   │
│  │ │ • Free tier available (limited)                    │ │   │
│  │ │ • Excellent handwriting recognition                │ │   │
│  │ │ • Cost: ~$0.01 per 10 pages                        │ │   │
│  │ │                                          [Set Up →] │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟣 Claude (Anthropic)                                   │   │
│  │ Best accuracy • Premium pricing            [Set Up →]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟢 GPT-4o (OpenAI)                                      │   │
│  │ Familiar brand • Good quality              [Set Up →]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🖥️ Ollama (Local)                                       │   │
│  │ Free & private • Runs on your computer     [Set Up →]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Gemini API Key Wizard (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────────┐
│  Set Up Gemini                                    Step 1 of 3   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Get your free API key from Google AI Studio                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │     [Screenshot: Google AI Studio "Get API Key" button]   │  │
│  │                                                            │  │
│  │     1. Click the button below to open Google AI Studio    │  │
│  │     2. Sign in with your Google account                   │  │
│  │     3. Click "Get API key" in the left sidebar            │  │
│  │     4. Click "Create API key"                             │  │
│  │     5. Copy the key that appears                          │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [🌐 Open Google AI Studio]                                     │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Paste your API key here:                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ AIza...                                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│                                      [Back]  [Test & Continue]  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Panel

```
┌─────────────────────────────────────────────────────────────────┐
│  Settings                                                   [×] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AI Services                                                    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ☑ Gemini (Google)                             [Change Key]     │
│    API Key: ••••••••••••AIza                                    │
│    Status: ✅ Connected                                         │
│                                                                  │
│  ☑ Claude (Anthropic)                          [Change Key]     │
│    API Key: ••••••••••••sk-ant                                  │
│    Status: ✅ Connected                                         │
│                                                                  │
│  ☑ GPT-4o (OpenAI)                             [Change Key]     │
│    API Key: ••••••••••••sk-proj                                 │
│    Status: ✅ Connected                                         │
│                                                                  │
│  ☑ Ollama (Local)                                               │
│    Status: ✅ Running (3 vision models available)               │
│                                                                  │
│  Language                                                       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Primary Language    [English               ▼]                  │
│  Secondary Language  [None                  ▼]                  │
│                                                                  │
│  💡 Setting languages helps the AI recognize words correctly    │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ☐ Show advanced options                                        │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ❤️ Support Development                                         │
│     [☕ Buy Me a Coffee]  [♥ GitHub Sponsors]                   │
│                                                                  │
│                                      [Cancel]  [Save Settings]  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## App Store Requirements

### Apple App Store (macOS)

**Technical Requirements:**
- [ ] Signed with Apple Developer certificate ($99/year)
- [ ] Notarized by Apple
- [ ] Sandboxed (limited file system access)
- [ ] Hardened runtime enabled
- [ ] No private API usage

**Submission Materials:**
- [ ] App icon (1024×1024 + smaller sizes)
- [ ] Screenshots (minimum 3, various sizes)
- [ ] App description (4000 chars max)
- [ ] Keywords (100 chars max)
- [ ] Privacy policy URL
- [ ] Support URL
- [ ] Category: Productivity
- [ ] Age rating: 4+ (no objectionable content)

**Privacy Considerations:**
- [ ] Declare data collection (API keys stored locally)
- [ ] Disclose that images are sent to third-party AI services
- [ ] No tracking or analytics without consent

**Sandbox Entitlements Needed:**
```xml
<key>com.apple.security.network.client</key>
<true/>  <!-- For API calls -->

<key>com.apple.security.files.user-selected.read-write</key>
<true/>  <!-- For file picker -->

<key>com.apple.security.files.downloads.read-write</key>
<true/>  <!-- For drag-and-drop -->
```

### Microsoft Store (Windows)

**Technical Requirements:**
- [ ] MSIX package format
- [ ] Signed with code signing certificate
- [ ] Pass Windows App Certification Kit (WACK)
- [ ] 64-bit support required

**Submission Materials:**
- [ ] Store logo (300×300)
- [ ] Screenshots (minimum 1, recommended 4+)
- [ ] App description
- [ ] Privacy policy URL
- [ ] Support contact

---

## Porting Strategy

### Phase 1: Rust Backend Core

Port the essential Python modules to Rust:

**1. File Parsers**

| Python Module | Rust Equivalent | Complexity | Notes |
|---------------|-----------------|------------|-------|
| `note_format/parser.py` | `parser.rs` | Medium | Binary parsing |
| `note_format/decoder.py` | `decoder.rs` | High | RLE decompression |
| `sources/pdf.py` | `pdf.rs` | Medium | Use `pdf` crate |
| (new) | `image_loader.rs` | Low | PNG/JPEG loading |

**2. LLM Clients**

| Provider | Rust Module | Complexity |
|----------|-------------|------------|
| Anthropic (Claude) | `anthropic.rs` | Low |
| Google (Gemini) | `google.rs` | Low |
| OpenAI (GPT-4o) | `openai.rs` | Low |
| Ollama | `ollama.rs` | Low |

**Strategy:**
- Use `reqwest` for HTTP
- Implement streaming for real-time progress
- Share auth/retry logic via traits

### Phase 2: Tauri Commands

```rust
// src-tauri/src/commands.rs

#[tauri::command]
async fn transcribe_file(
    path: String,
    provider: String,
    model: String,
    temperature: f32,
    prompt: String,
    primary_language: String,
    secondary_language: Option<String>,
) -> Result<TranscriptionResult, String> { ... }

#[tauri::command]
async fn get_providers() -> Vec<ProviderInfo> { ... }

#[tauri::command]
async fn test_api_key(provider: String, key: String) -> Result<bool, String> { ... }

#[tauri::command]
fn save_api_key(provider: String, key: String) -> Result<(), String> { ... }

#[tauri::command]
fn get_ollama_models() -> Result<Vec<ModelInfo>, String> { ... }
```

---

## Development Phases

### Phase 1: Foundation (Weeks 1-3)

**Goals:**
- [ ] Set up Tauri + React project structure
- [ ] Implement basic .note parser in Rust (read-only)
- [ ] PNG/JPEG image loading
- [ ] Single LLM provider working (Gemini)
- [ ] Basic UI: drop zone, progress, results display

**Deliverable:** Internal alpha that can transcribe a single file

### Phase 2: Core Features (Weeks 4-6)

**Goals:**
- [ ] All four providers (Claude, Gemini, GPT-4o, Ollama)
- [ ] PDF support (embedded image extraction)
- [ ] API key setup wizard with step-by-step guide
- [ ] Secure credential storage
- [ ] Language preference settings
- [ ] Error handling with user-friendly messages

**Deliverable:** Feature-complete beta for personal testing

### Phase 3: Polish & UX (Weeks 7-8)

**Goals:**
- [ ] First-run wizard
- [ ] Dark mode
- [ ] Keyboard shortcuts
- [ ] Recent files
- [ ] App icon and branding
- [ ] Support development links

**Deliverable:** Release candidate for external testing

### Phase 4: App Store Submission (Weeks 9-10)

**Goals:**
- [ ] macOS code signing and notarization
- [ ] Sandbox compliance
- [ ] Screenshots and marketing materials
- [ ] Privacy policy
- [ ] Submit to App Store review

**Deliverable:** v1.0 on Mac App Store

### Phase 5: Windows Release (Weeks 11-12)

**Goals:**
- [ ] Windows build and testing
- [ ] MSIX packaging
- [ ] Microsoft Store submission
- [ ] Direct download option (GitHub releases)

**Deliverable:** v1.0 on Microsoft Store + direct download

---

## Competitive Analysis

### Existing Solutions

| Solution | Platforms | Approach | Limitations |
|----------|-----------|----------|-------------|
| **supernote-tool (jya)** | CLI | Python scripts | Technical users only |
| **Supernote Cloud** | Web | Official Ratta service | Limited AI features |
| **Generic OCR apps** | Various | General OCR | Poor handwriting support |
| **ChatGPT/Claude web** | Browser | Manual upload | Tedious for multi-page |

### Our Differentiation

1. **Purpose-built for Supernote** - Native .note support, also PDF/images
2. **Best-in-class AI** - Claude, Gemini, GPT-4o, local Ollama (user choice)
3. **Non-technical users** - No CLI, guided setup wizard
4. **Privacy options** - Local processing via Ollama
5. **Cross-platform** - Mac and Windows from same codebase
6. **Language support** - Explicit language hints for multilingual notes
7. **Free forever** - No subscriptions, just tip jar

---

## Changelog

### 2025-12-28
- Initial roadmap created
- Added OpenAI GPT-4o as fourth provider option
- Added comprehensive free tier analysis (December 2025 landscape)
- Decided on BYOK model with streamlined Gemini-first onboarding
- Added language preference feature (primary + secondary)
- Confirmed app name: "Supernote Transcriber"
- Confirmed pricing: Free + tip jar (Calibre model)
- Confirmed input formats: .note, PDF, PNG, JPEG from v1.0
- Confirmed 12-week development timeline

---

*This roadmap is a living document. Update as decisions are made and progress occurs.*
