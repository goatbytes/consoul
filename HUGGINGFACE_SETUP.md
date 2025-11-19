# HuggingFace Setup Guide for Consoul

## ✅ Good News: HuggingFace Inference is Still FREE!

**TL;DR**: HuggingFace Serverless Inference API is FREE with rate limits. If you're seeing errors, you likely need to update packages.

## Current Status (2025)

### What Works for FREE

✅ **Serverless Inference API** - FREE tier available!
- Endpoint: `https://router.huggingface.co` (new)
- Rate limits: ~few hundred requests/hour for free users
- Access to hundreds of models
- No payment required!

✅ **PRO Tier** - $9/month (optional)
- 20× more inference credits
- Higher rate limits
- Priority queue
- Still uses same free API, just more quota

## What Changed in 2024?

### Old Endpoint Deprecated ❌

- **Old URL**: `https://api-inference.huggingface.co`
- **Status**: Returns 410 "Gone" errors
- **Old Client**: `InferenceApi` class deprecated

### New Endpoint Active ✅

- **New URL**: `https://router.huggingface.co`
- **New Client**: `InferenceClient` (use this!)
- **Status**: FREE tier + paid options
- **Compatibility**: Automatically used by updated packages

## Setup Guide

### Option 1: HuggingFace Serverless (FREE!)

**Step 1: Get API Token**
```bash
# Visit https://huggingface.co/settings/tokens
# Create a new token (read access is enough)
export HUGGINGFACEHUB_API_TOKEN='hf_...'
```

**Step 2: Update Packages** (Important!)
```bash
# Make sure you have latest versions
pip install --upgrade langchain-huggingface huggingface-hub

# Or with poetry:
poetry install --sync
```

**Step 3: Use in Consoul**
```bash
# Press Ctrl+M in Consoul
# Select "HuggingFace" provider
# Choose model (e.g., meta-llama/Llama-3.1-8B-Instruct)
```

**That's it!** Free tier gives you:
- Few hundred requests per hour
- Access to all serverless models
- No payment required

### Option 2: HuggingFace PRO ($9/month)

Get 20× more credits:
1. Subscribe at https://huggingface.co/pricing
2. Same setup as free tier
3. Higher rate limits automatically

### Option 3: Local HuggingFace Models (FREE!)

Run models locally without API:

```bash
# Install dependencies
pip install 'consoul[huggingface-local]'

# In Consoul config, set local=True for HuggingFace models
# This downloads and runs models on your machine
```

**Pros**: No rate limits, fully private
**Cons**: Requires GPU/RAM, slower on CPU

## Alternative FREE Options

If HuggingFace doesn't work or you want alternatives:

### Groq (Recommended - Fastest)

```bash
# Get free API key: https://console.groq.com
export GROQ_API_KEY='gsk_...'

# In Consoul: Press Ctrl+M → Select "Groq"
# Models: Llama 3.1, Mixtral, Gemma (all free!)
```

### Ollama (Best for Privacy)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# In Consoul: Press Ctrl+M → Select "Ollama"
```

### MLX (Apple Silicon Only)

```bash
# Already integrated in Consoul
# Press Ctrl+M → Select "MLX"
# Choose from mlx-community models
```

## Troubleshooting

### Error: "410 Gone" or "no longer supported"

**Cause**: Using outdated `langchain-huggingface` package

**Fix**:
```bash
pip install --upgrade langchain-huggingface huggingface-hub
# Or: poetry install --sync
```

### Error: "Authentication failed"

**Cause**: Missing or invalid API token

**Fix**:
```bash
# Get token from: https://huggingface.co/settings/tokens
export HUGGINGFACEHUB_API_TOKEN='hf_your_token_here'
```

### Error: "Rate limit exceeded"

**Cause**: Hit free tier limits

**Solutions**:
1. Wait an hour for quota reset
2. Upgrade to PRO ($9/month) for 20× more credits
3. Use Ollama locally (unlimited)
4. Use Groq (different rate limits)

## Pricing Comparison

| Service | Cost | Rate Limits | Speed |
|---------|------|-------------|-------|
| **HuggingFace Free** | FREE | ~few hundred/hour | Medium |
| **HuggingFace PRO** | $9/month | 20× more | Medium |
| **Groq** | FREE | Generous | Very Fast |
| **Ollama** | FREE | Unlimited | Medium (local) |
| **MLX** | FREE | Unlimited | Fast (M-series) |
| **OpenAI GPT-4** | ~$10/million tokens | High | Fast |
| **Anthropic Claude** | ~$3/million tokens | High | Fast |

## What Your HuggingFace Token Gets You

### Always FREE:
✅ Model downloads (for local use)
✅ Dataset access
✅ Gated model access (Llama, etc. after approval)
✅ Serverless inference (with rate limits)
✅ Spaces (host apps)

### Paid Only:
💰 Inference Endpoints (dedicated servers, starts $0.033/hour)
💰 Higher rate limits (PRO subscription $9/month)

## Testing Your Setup

Run our diagnostic script:

```bash
poetry run python test_huggingface.py
```

This checks:
- ✓ HuggingFace token validity
- ✓ Package versions
- ✓ Groq availability
- ✓ Ollama installation
- ✓ MLX support

## Best Practices

### For Free Usage:
1. **Use HuggingFace Free Tier** - Good for experimentation
2. **Add Groq as backup** - Fast and generous free tier
3. **Install Ollama for heavy use** - No limits, runs locally

### For Production:
1. **HuggingFace PRO** - $9/month, good value
2. **Groq** - Still free, very fast
3. **Anthropic/OpenAI** - Best quality, paid per use

## FAQ

### Q: Is HuggingFace Inference still free?
**A**: YES! Free tier with rate limits. The API endpoint changed but it's still free.

### Q: Do I need to pay for HuggingFace?
**A**: NO for basic use. Free tier is sufficient for most personal projects.

### Q: What's the difference between free and PRO?
**A**: PRO ($9/month) gives 20× more inference credits and higher priority.

### Q: Why am I getting 410 errors?
**A**: Your `langchain-huggingface` package is outdated. Update it!

### Q: What's the best free option?
**A**:
- **Groq** - If you want cloud API (fast)
- **Ollama** - If you want local/private (unlimited)
- **HuggingFace** - If you want variety of models (good middle ground)

### Q: Can I use Llama models for free?
**A**: YES! Via:
- HuggingFace Serverless (free tier)
- Groq (free API)
- Ollama (local, unlimited)

## Resources

- **HuggingFace Docs**: https://huggingface.co/docs/api-inference
- **Groq Console**: https://console.groq.com
- **Ollama**: https://ollama.com
- **Pricing**: https://huggingface.co/pricing
- **Test Script**: `poetry run python test_huggingface.py`

## Need Help?

1. Run diagnostic: `poetry run python test_huggingface.py`
2. Check package versions: `pip list | grep huggingface`
3. Update packages: `pip install --upgrade langchain-huggingface huggingface-hub`
4. Open issue: https://github.com/goatbytes/consoul/issues

---

**Bottom Line**: HuggingFace Serverless Inference is FREE! Just update your packages if you're seeing errors.
