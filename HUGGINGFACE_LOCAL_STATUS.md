# HuggingFace Local Execution - Status Report

## Executive Summary

**Status**: ❌ **Not Working on macOS**
**Root Causes**: Multiple issues - incomplete models AND PyTorch compatibility
**Recommendation**: **Use HuggingFace API mode or Ollama for local execution**

## Investigation Results

### 1. Model Cache Analysis ✅

Scanned 419GB HuggingFace cache and found:

**Complete Models (9):**
- DavidAU/OpenAi-GPT-oss-20b (269.9 GB) - GGUF format
- moonshotai/Kimi-Linear-48B-A3B-Instruct (91.5 GB)
- **Qwen/Qwen3-8B (15.3 GB)** - Best for testing
- bosonai/higgs-audio-v2-generation-3B-base (10.8 GB)
- Others (embedding/audio models)

**Incomplete Models (3) - CAUSE OF INITIAL SEGFAULTS:**
- gpt2 (2.7 MB) - Missing `pytorch_model.bin`
- google/flan-t5-base (1.4 KB) - Only config
- google/medgemma-27b-text-it (23.6 KB) - Only README

### 2. Segfault Root Cause ✅

The initial segfaults when testing `gpt2` were due to:
- **Incomplete model downloads** - models had tokenizer files but no weight files
- When transformers tries to load missing weights, it crashes in C++ code
- This was NOT a PyTorch 2.5 compatibility issue initially

### 3. Complete Model Testing ❌

Attempted to test Qwen3-8B (complete 15.3GB model):
- ✅ Tokenizer loads successfully
- ❌ Model loading hangs/crashes even on CPU
- ❌ No output, process terminates silently
- Environment: PyTorch 2.4.1 (Poetry) / 2.9.1 (system)

**Conclusion**: Even with complete models, local execution doesn't work reliably on macOS.

## Issues Identified

### Issue 1: Incomplete Model Downloads
**Impact**: Immediate segfaults
**Solution**: Clean up with `huggingface-cli delete-cache --repos MODEL_NAME`
**Status**: ✅ Identified and documented

### Issue 2: PyTorch/Transformers Compatibility
**Impact**: Hangs/crashes even with complete models
**Suspected Causes**:
- PyTorch 2.4.x/2.9.x issues on macOS Apple Silicon
- MPS (Metal Performance Shaders) compatibility problems
- Memory pressure with large models (15GB+)
- Transformers library interaction with PyTorch on macOS

**Status**: ❌ Unresolved

### Issue 3: Environment Confusion
**Impact**: Different PyTorch versions in Poetry vs system
**Details**:
- Poetry venv: torch 2.4.1
- System Python: torch 2.9.1
- `pip install -e '.[all]'` overrides Poetry environment

**Recommendation**: Use `poetry run` for consistent environment

## Performance Optimizations Implemented ✅

1. **Removed startup cache scan** (model_picker_modal.__init__)
2. **Removed config cache scan** (get_current_model_config())
3. **Lazy loading** - only scan when clicking HuggingFace tab

**Result**: TUI startup is fast regardless of cache size

## Working Solutions

### ✅ Option 1: HuggingFace API Mode (Recommended)

```python
from consoul.config.models import HuggingFaceModelConfig
from consoul.ai.providers import get_chat_model

config = HuggingFaceModelConfig(
    model="meta-llama/Llama-3.1-8B-Instruct",
    local=False,  # Use API
)

# Requires HUGGINGFACEHUB_API_TOKEN
chat_model = get_chat_model(config)
```

**Setup**:
1. Get token: https://huggingface.co/settings/tokens
2. Export: `export HUGGINGFACEHUB_API_TOKEN=your_token`
3. Use in TUI or code

### ✅ Option 2: Ollama (Best for Local)

```bash
# Install and start
brew install ollama
ollama serve

# Pull model
ollama pull llama3.2

# Use in Consoul TUI
consoul tui  # Select Ollama provider
```

**Why Ollama**:
- ✅ Works perfectly on macOS
- ✅ No PyTorch/transformers issues
- ✅ Optimized for Apple Silicon
- ✅ Fast and reliable

### ❌ Option 3: Local HuggingFace (Not Working)

Status: Not recommended on macOS due to multiple compatibility issues.

## Cleanup Commands

Remove incomplete models:
```bash
huggingface-cli delete-cache --repos gpt2
huggingface-cli delete-cache --repos google/flan-t5-base
huggingface-cli delete-cache --repos google/medgemma-27b-text-it
```

Check cache:
```bash
python check_hf_models.py
```

## Test Scripts Created

1. `check_hf_models.py` - Analyze cache for complete vs incomplete models
2. `test_qwen3.py` - Test Qwen3-8B local execution (comprehensive)
3. `test_hf_comprehensive.py` - Full diagnostic suite
4. `test_startup_time.py` - Verify startup optimizations
5. Others: test_hf_*.py - Various diagnostic tests

## Recommendations

### For Users

1. **Use HuggingFace API mode** for HuggingFace models
2. **Use Ollama** for local execution needs
3. **Clean up incomplete models** to save space
4. **Don't select local HuggingFace models in TUI** on macOS

### For Development

1. **Document limitation** in README/docs
2. **Add clear error messages** when local mode fails
3. **Consider disabling** local HuggingFace option on macOS
4. **Test on Linux** - likely works there

## Files Modified

- `src/consoul/config/models.py` - Skip cache scan, default to API mode
- `src/consoul/tui/widgets/model_picker_modal.py` - Lazy load HF models
- `src/consoul/ai/providers.py` - Add macOS warning
- `pyproject.toml` - Pin torch to 2.4.x, add optional deps
- `HUGGINGFACE_LOCAL_ISSUES.md` - User-facing documentation

## Commits

- `cf2acf5` - Document and mitigate macOS PyTorch segfault issues
- `8fa6778` - Defer HuggingFace cache scan (startup performance)
- `55631f1` - Remove cache scan from get_current_model_config
- Others - Dependency validation, test scripts

## Conclusion

Local HuggingFace execution on macOS is **not reliable** due to:
1. Risk of incomplete downloads causing segfaults
2. PyTorch/transformers compatibility issues
3. Model loading hangs even with complete models

**Recommended approach**: Use HuggingFace API or Ollama instead.

---
Last Updated: 2025-11-16
Status: Investigation Complete, Issues Documented
