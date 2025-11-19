# HuggingFace API Change Notice

## ⚠️ Important: Free Inference API Deprecated (2024)

**TL;DR**: The free HuggingFace Inference API no longer works. Use free alternatives (Groq, Ollama, MLX) or pay for HuggingFace Inference Endpoints.

## What Happened?

In 2024, HuggingFace deprecated their free Inference API:

- **Old Endpoint**: `https://api-inference.huggingface.co` → ❌ Returns 410 "Gone"
- **New Endpoint**: `https://router.huggingface.co/hf-inference` → 💰 Paid only

## Impact on Consoul

If you try to use HuggingFace models in Consoul, you'll see:

```
HuggingFace Inference API has been deprecated.
The free Inference API is no longer available.
```

## Solutions

### ✅ Recommended: Use Free Alternatives

**1. Groq (Easiest)**
- Fast, free API for Llama 3.1, Mixtral, Gemma models
- Get free key: https://console.groq.com
- Set environment: `export GROQ_API_KEY='gsk_...'`
- In Consoul: Press `Ctrl+M` → Select "Groq" provider

**2. Ollama (Most Private)**
- Run models completely locally (no internet, no API keys)
- Install: `curl -fsSL https://ollama.com/install.sh | sh`
- Pull model: `ollama pull llama3.1:8b`
- In Consoul: Press `Ctrl+M` → Select "Ollama" provider

**3. MLX (Apple Silicon)**
- Optimized for M-series Macs
- Already integrated in Consoul
- In Consoul: Press `Ctrl+M` → Select "MLX" provider

### 💰 Paid Option: HuggingFace Inference Endpoints

If you specifically need HuggingFace models via API:

1. Add payment method at https://huggingface.co/settings/billing
2. Create API token at https://huggingface.co/settings/tokens
3. Set environment: `export HUGGINGFACEHUB_API_TOKEN='hf_...'`
4. In Consoul: Use HuggingFace provider as normal

**Pricing**: ~$0.001-$0.01 per 1K tokens (cheaper than OpenAI, but not free)

## What Still Works for Free?

Your HuggingFace token **still works** for:

✅ **Model Downloads** - Download models to run locally
✅ **Dataset Access** - Access HuggingFace datasets
✅ **Gated Models** - Request access to Llama, etc.
✅ **Spaces** - Deploy Gradio/Streamlit apps

❌ **Inference API** - NO LONGER FREE

## Testing Your Setup

Run the test script to see what's working:

```bash
poetry run python test_huggingface.py
```

This will check:
- HuggingFace token status
- Groq API availability
- Ollama installation & models
- MLX support (Apple Silicon)

## For Consoul Users Who Want HuggingFace to Work

**Consoul code is already compatible** with both old and new HuggingFace APIs! The code uses `langchain_huggingface.HuggingFaceEndpoint` which works with paid inference.

You just need to decide:

- **Free**: Switch to Groq/Ollama/MLX (recommended)
- **Paid**: Add payment method to your HuggingFace account

The app will detect the 410 error and show helpful alternatives.

## Documentation

See these files for complete guides:

- **HUGGINGFACE_SETUP.md** - Complete setup guide with all options
- **test_huggingface.py** - Diagnostic script for all providers
- **HUGGINGFACE_LOCAL_ISSUES.md** - Local model execution guide

## Summary for Developers

**What changed in Consoul:**

1. Added better error detection for 410 errors in `src/consoul/ai/providers.py` (lines 1375-1392)
2. Error message now recommends free alternatives (Groq, Ollama, MLX)
3. Created comprehensive setup guide (HUGGINGFACE_SETUP.md)
4. Created diagnostic test script (test_huggingface.py)

**No code changes required for users who want to pay** - it already works with the new paid API!

## Need Help?

1. Run diagnostic: `poetry run python test_huggingface.py`
2. Read setup guide: `HUGGINGFACE_SETUP.md`
3. Try Groq (easiest free alternative): https://console.groq.com
4. Open issue: https://github.com/goatbytes/consoul/issues
