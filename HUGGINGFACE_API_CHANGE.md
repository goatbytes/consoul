# HuggingFace API Endpoint Change (2024)

## ✅ IMPORTANT: HuggingFace Inference is STILL FREE!

**TL;DR**: The API endpoint changed but the free tier still exists. Update your packages to fix 410 errors.

## What Actually Happened

### Endpoint Migration ✅

**Old Endpoint (Deprecated)**:
- URL: `https://api-inference.huggingface.co`
- Status: Returns 410 "Gone" errors
- Client: `InferenceApi` class (deprecated)

**New Endpoint (Active)**:
- URL: `https://router.huggingface.co`
- Status: **STILL FREE!** (with rate limits)
- Client: `InferenceClient` (current)

### What's Free vs Paid?

| Feature | Cost | Details |
|---------|------|---------|
| **Serverless Inference** | FREE | ~few hundred requests/hour |
| **PRO Tier** | $9/month | 20× more credits, higher priority |
| **Inference Endpoints** | $0.033+/hour | Dedicated servers (optional) |

## Impact on Consoul

### If You're Seeing 410 Errors:

**Cause**: Outdated `langchain-huggingface` package using old endpoint

**Fix**:
```bash
# Update packages
pip install --upgrade langchain-huggingface huggingface-hub

# Or with poetry
poetry install --sync
```

### After Updating:

✅ HuggingFace models work with **FREE tier**
✅ Same rate limits as before (~few hundred/hour)
✅ No payment required
✅ Optional PRO upgrade for more quota

## Migration Guide

### Step 1: Update Packages

```bash
# Check current versions
pip list | grep huggingface

# Update to latest
pip install --upgrade langchain-huggingface huggingface-hub

# Verify (should be 0.1.0+ for langchain-huggingface)
pip list | grep huggingface
```

### Step 2: Test Connection

```bash
# Run diagnostic script
poetry run python test_huggingface.py

# Or test manually in Python
python -c "from huggingface_hub import InferenceClient; print('✓ Working!')"
```

### Step 3: Use in Consoul

```bash
# Set your token (if not already set)
export HUGGINGFACEHUB_API_TOKEN='hf_...'

# Launch Consoul and select HuggingFace provider
# Press Ctrl+M → Select "HuggingFace"
```

## What Changed in the Code?

### Python Package Changes

**Old Way (Deprecated)**:
```python
from huggingface_hub import InferenceApi
client = InferenceApi(repo_id="model", token="...")
```

**New Way (Current)**:
```python
from huggingface_hub import InferenceClient
client = InferenceClient(model="model", token="...")
```

### LangChain Integration

**Consoul uses** `langchain_huggingface.HuggingFaceEndpoint` which:
- Automatically uses new endpoint (if package is updated)
- Falls back gracefully with helpful error messages
- Works with free tier out of the box

## Free Tier Details

### What You Get FREE:

✅ **Serverless Inference**
- Rate limit: ~few hundred requests per hour
- Access to hundreds of models
- Automatic model loading (may take ~20 seconds first time)

✅ **Model Downloads**
- Download any public model for local use
- No rate limits on downloads

✅ **Gated Models**
- Request access to Llama, Mistral, etc.
- Free after approval

### What Requires Payment:

💰 **PRO Subscription** ($9/month)
- 20× more inference credits
- Higher priority in queue
- Faster model loading

💰 **Inference Endpoints** (Dedicated)
- Starts at $0.033/hour
- Dedicated hardware (CPU/GPU)
- No cold starts
- Production-grade SLA

## Alternative Free Options

If you want more free quota or different models:

### 1. Groq (FREE - Fastest)
```bash
# Get key: https://console.groq.com
export GROQ_API_KEY='gsk_...'
# Models: Llama 3.1, Mixtral, Gemma
```

### 2. Ollama (FREE - Unlimited)
```bash
# Install: https://ollama.com
ollama pull llama3.1:8b
# Run locally, no internet needed
```

### 3. MLX (FREE - Apple Silicon)
```bash
# Already in Consoul
# Press Ctrl+M → Select "MLX"
# Fast on M-series Macs
```

## FAQ

### Q: Do I need to pay now?
**A**: NO! Free tier still exists with same limits as before.

### Q: Why the 410 error?
**A**: Your `langchain-huggingface` package is using the old deprecated endpoint. Update it!

### Q: Will my existing code break?
**A**: Only if packages are outdated. Update and it works the same.

### Q: Is the new endpoint faster/slower?
**A**: Similar performance. May have better routing to available servers.

### Q: Can I still use gated models like Llama?
**A**: YES! Request access on HuggingFace, then use for free via API.

### Q: What if I hit rate limits?
**A**: Options:
1. Wait ~1 hour for quota reset (free)
2. Upgrade to PRO $9/month (20× more)
3. Use Ollama locally (unlimited)
4. Use Groq (different free tier)

## Testing Your Setup

Run the diagnostic script:

```bash
poetry run python test_huggingface.py
```

Expected output:
```
✓ HuggingFace token found
✓ Serverless Inference API: FREE tier available
✓ Package versions up to date
```

## For Consoul Developers

### What Changed in Consoul:

1. **Better Error Messages**
   - Detects 410 errors
   - Suggests package update
   - Explains free tier still works

2. **Documentation**
   - Updated HUGGINGFACE_SETUP.md
   - Created this change notice
   - Added diagnostic script

3. **Code Compatibility**
   - Works with old and new endpoints
   - Graceful degradation
   - No breaking changes for users

### Files Modified:

- `src/consoul/ai/providers.py` - Enhanced error handling
- `HUGGINGFACE_SETUP.md` - Complete setup guide
- `HUGGINGFACE_API_CHANGE.md` - This file
- `test_huggingface.py` - Diagnostic script

## Summary

**The Bottom Line**:

1. ✅ HuggingFace Serverless Inference is **STILL FREE**
2. ✅ Just need to update `langchain-huggingface` package
3. ✅ Same functionality, new endpoint
4. ✅ No payment required for basic use

**Update command**:
```bash
pip install --upgrade langchain-huggingface huggingface-hub
```

That's it! Your HuggingFace models will work again with the free tier.

## Resources

- **HuggingFace Docs**: https://huggingface.co/docs/api-inference
- **Migration Guide**: https://huggingface.co/docs/huggingface_hub/main/en/guides/inference
- **Pricing**: https://huggingface.co/pricing (note the FREE tier!)
- **Test Script**: `poetry run python test_huggingface.py`
