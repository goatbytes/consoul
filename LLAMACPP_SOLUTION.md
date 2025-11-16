# LLama.cpp Solution for Local HuggingFace Models

## Problem

HuggingFace's transformers library with PyTorch has compatibility issues on macOS Apple Silicon, causing:
- Segfaults with incomplete models
- Hangs/crashes even with complete safetensors models
- Memory pressure with large models

## Solution: Use llama.cpp + GGUF Format

**Key Insight from LM Studio**: LM Studio uses llama.cpp under the hood to run models efficiently on macOS, using the GGUF format instead of safetensors/PyTorch.

### Why llama.cpp Works Better

1. **Native C++ implementation** - No PyTorch/Python overhead
2. **Optimized for Apple Silicon** - Uses Metal Performance Shaders (MPS)
3. **Quantized models** - GGUF format supports 4-bit, 5-bit, 8-bit quantization
4. **Lower memory usage** - Much more efficient than loading full fp16/fp32 models
5. **Proven on macOS** - Powers Ollama, LM Studio, and other tools

## Your GGUF Models

You already have GGUF models downloaded!

**DavidAU/OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf** (269GB total):
- `OpenAI-20B-NEO-CODEPlus-Uncensored-IQ4_NL.gguf` - 11GB (4-bit)
- `OpenAI-20B-NEO-CODE-DI-Uncensored-Q5_1.gguf` - 15GB (5-bit)
- `OpenAI-20B-NEO-CODE-DI-Uncensored-Q8_0.gguf` - ~20GB (8-bit)
- Plus many more variants

## Implementation Plan

### Step 1: Add llama-cpp-python Dependency

```toml
# In pyproject.toml [tool.poetry.dependencies]
llama-cpp-python = {version = "^0.3.0", optional = true}

# Update extras
[tool.poetry.extras]
huggingface-local = ["llama-cpp-python"]  # Replace transformers/torch
```

### Step 2: Add LlamaCpp Provider Support

Create new provider enum value and config:

```python
# In src/consoul/config/models.py
class Provider(str, Enum):
    # ... existing providers
    LLAMACPP = "llamacpp"

class LlamaCppModelConfig(BaseModelConfig):
    """Llama.cpp-specific model configuration."""
    provider: Literal[Provider.LLAMACPP] = Provider.LLAMACPP
    model_path: str  # Path to .gguf file
    n_ctx: int = Field(default=4096, description="Context window size")
    n_gpu_layers: int = Field(default=-1, description="-1 = all layers on GPU")
    n_batch: int = Field(default=512, description="Batch size for prompt processing")
    n_threads: int | None = Field(default=None, description="CPU threads")
    use_mlock: bool = Field(default=False, description="Keep model in RAM")
    use_mmap: bool = Field(default=True, description="Use memory mapping")
```

### Step 3: Implement get_chat_model() Support

```python
# In src/consoul/ai/providers.py
def get_chat_model(model_config, ...):
    # ... existing code

    elif provider == Provider.LLAMACPP:
        from langchain_community.chat_models import ChatLlamaCpp
        import multiprocessing

        # Get model path
        if hasattr(model_config, 'model_path'):
            model_path = model_config.model_path
        else:
            # Auto-detect GGUF in HF cache
            model_path = find_gguf_in_cache(model_config.model)

        # Build params
        llama_params = {
            "model_path": model_path,
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 512),
            "n_ctx": getattr(model_config, "n_ctx", 4096),
            "n_gpu_layers": getattr(model_config, "n_gpu_layers", -1),
            "n_batch": getattr(model_config, "n_batch", 512),
            "n_threads": getattr(model_config, "n_threads", multiprocessing.cpu_count() - 1),
            "verbose": False,
        }

        return ChatLlamaCpp(**llama_params)
```

### Step 4: Auto-Detect GGUF Models

```python
def find_gguf_in_cache(model_name: str) -> str | None:
    """Find GGUF file in HuggingFace cache for a model."""
    from pathlib import Path
    import re

    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

    # Convert model name to cache format
    # "DavidAU/OpenAi-GPT-oss-20b" -> "models--DavidAU--OpenAi-GPT-oss-20b"
    cache_name = f"models--{model_name.replace('/', '--')}"

    model_dir = cache_dir / cache_name
    if not model_dir.exists():
        return None

    # Find GGUF files
    gguf_files = list(model_dir.rglob("*.gguf"))

    if not gguf_files:
        return None

    # Prefer smaller quantized versions (Q4, Q5)
    # Sort by: Q4 > Q5 > Q8 > others
    def sort_key(path):
        name = path.name.lower()
        if 'q4' in name or 'iq4' in name:
            return 0
        elif 'q5' in name:
            return 1
        elif 'q8' in name:
            return 2
        else:
            return 3

    gguf_files.sort(key=sort_key)

    return str(gguf_files[0])
```

### Step 5: Update TUI Model Picker

```python
# In model_picker_modal.py, add LlamaCpp to providers
providers = ["openai", "anthropic", "google", "llamacpp"]

# When loading models for llamacpp provider
elif provider_value == "llamacpp":
    gguf_models = get_gguf_models_from_cache()
    for model_info in gguf_models:
        provider_models[model_info["name"]] = {
            "provider": "llamacpp",
            "context": f"{model_info['n_ctx']}",
            "cost": "free",
            "description": f"GGUF {model_info['quant']} ({model_info['size_gb']:.1f}GB)",
        }
```

## Testing Plan

### Test 1: Direct llama-cpp-python

```python
from langchain_community.chat_models import ChatLlamaCpp

llm = ChatLlamaCpp(
    model_path="~/.cache/huggingface/hub/.../OpenAI-20B-NEO-CODEPlus-Uncensored-IQ4_NL.gguf",
    n_ctx=4096,
    n_gpu_layers=-1,  # Use Metal on macOS
    temperature=0.7,
)

response = llm.invoke("What is Python?")
print(response.content)
```

### Test 2: Consoul Integration

```python
from consoul.config.models import LlamaCppModelConfig
from consoul.ai.providers import get_chat_model

config = LlamaCppModelConfig(
    model="DavidAU/OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf",
    model_path="auto",  # Auto-detect
)

chat = get_chat_model(config)
response = chat.invoke("Hello!")
```

## Converting Existing Models to GGUF

For your safetensors models (Qwen3-8B), you can convert them:

```bash
# Clone llama.cpp
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# Install requirements
pip install -r requirements.txt

# Convert Qwen3-8B to GGUF
python convert_hf_to_gguf.py ~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/XXX/ \
    --outfile qwen3-8b-fp16.gguf

# Quantize to 4-bit (optional, reduces size)
./llama-quantize qwen3-8b-fp16.gguf qwen3-8b-q4.gguf Q4_K_M
```

## Benefits

1. **Works on macOS** ✅ - No PyTorch segfaults
2. **Lower memory** ✅ - 4-bit models use 1/4 the RAM
3. **Faster inference** ✅ - Optimized C++ code
4. **LangChain compatible** ✅ - ChatLlamaCpp implements BaseChatModel
5. **Already have models** ✅ - 269GB of GGUF files ready

## Migration Path

### Phase 1: Add Parallel Support
- Keep existing HuggingFace transformers support
- Add LlamaCpp as separate provider
- Let users choose

### Phase 2: Deprecate Transformers
- Mark transformers-based local HF as deprecated on macOS
- Recommend llama.cpp alternative

### Phase 3: Full Migration
- Remove transformers dependency from local execution
- Use llama.cpp exclusively for GGUF models

## Dependencies

**Add to pyproject.toml**:
```toml
# Required
llama-cpp-python = {version = "^0.3.0", optional = true}

# Optional extras
[tool.poetry.extras]
llamacpp = ["llama-cpp-python"]
llamacpp-metal = ["llama-cpp-python"]  # With Metal support for macOS
```

**Installation**:
```bash
# Basic (CPU only)
poetry install --extras llamacpp

# macOS with Metal GPU acceleration
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python
```

## Expected Results

With llama.cpp and your existing 11GB Q4 GGUF model:

- ✅ Loads in ~5-10 seconds (vs hanging forever)
- ✅ Uses ~11GB RAM (vs 30GB+ for fp16)
- ✅ Fast inference with Metal acceleration
- ✅ Stable, no segfaults
- ✅ Same LangChain interface

## Next Steps

1. Install llama-cpp-python: `CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python`
2. Test with existing GGUF: `python test_llamacpp.py`
3. Add to Consoul if successful
4. Update documentation

---

**This is the solution LM Studio and Ollama use - proven to work on macOS!**
