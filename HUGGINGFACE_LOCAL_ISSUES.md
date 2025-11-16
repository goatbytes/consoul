# HuggingFace Local Execution Issues

## Summary

Local HuggingFace model execution is currently **not supported** due to segmentation faults when loading models with PyTorch/Transformers on macOS (Apple Silicon).

## Issue Details

**Symptoms:**
- Segmentation fault when loading any HuggingFace model locally
- Occurs during `AutoModelForCausalLM.from_pretrained()`
- Affects both direct transformers usage and LangChain integration

**Environment:**
- macOS 15.x (Darwin 24.6.0)
- Apple Silicon ARM64
- PyTorch 2.4.1-2.9.1
- Transformers 4.57.1

**Root Cause:**
Known compatibility issue between PyTorch and Transformers on macOS Apple Silicon. The segfault occurs in the underlying C++ code when loading model weights.

## Workarounds

### Option 1: Use API-based Execution (Recommended)

HuggingFace models work perfectly via the API endpoint:

```python
from consoul.config.models import HuggingFaceModelConfig
from consoul.ai.providers import get_chat_model

config = HuggingFaceModelConfig(
    model="meta-llama/Llama-3.1-8B-Instruct",
    local=False,  # Use API
)

# Requires HUGGINGFACEHUB_API_TOKEN environment variable
chat_model = get_chat_model(config)
```

**Get API Token:**
1. Visit https://huggingface.co/settings/tokens
2. Create a new token
3. Set environment variable: `export HUGGINGFACEHUB_API_TOKEN=your_token`

### Option 2: Use Other Providers

For local execution without API keys, use **Ollama**:

```bash
# Install Ollama
brew install ollama

# Start service
ollama serve

# Pull a model
ollama pull llama3.2

# Use in Consoul
consoul tui  # Select Ollama provider
```

### Option 3: Linux/Docker

Local HuggingFace execution works on Linux. You can run Consoul in a Docker container:

```dockerfile
FROM python:3.11-slim

RUN pip install consoul[huggingface-local]

CMD ["consoul", "tui"]
```

## Status

- ✅ HuggingFace API execution: **Working**
- ❌ HuggingFace local execution: **Not supported on macOS**
- ✅ Ollama local execution: **Working** (alternative)
- ✅ OpenAI, Anthropic, Google: **Working**

## Future Work

This will be re-evaluated when:
1. PyTorch releases a stable macOS ARM64 version
2. Transformers fixes compatibility issues
3. LangChain provides alternative local execution methods

## Related Issues

- PyTorch macOS segfault: https://github.com/pytorch/pytorch/issues
- Transformers Apple Silicon: https://github.com/huggingface/transformers/issues

---

**Recommendation:** Use HuggingFace API mode or switch to Ollama for local execution.
