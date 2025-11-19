# HuggingFace Setup Guide for Consoul

## ⚠️ Important Update (2024)

**HuggingFace has changed their API structure significantly:**

1. **Old Free Inference API** (`api-inference.huggingface.co`) → **DEPRECATED** (returns 410)
2. **New Inference Endpoints** (`router.huggingface.co/hf-inference`) → **PAID ONLY**
3. **Free Options** → Use dedicated providers or local models

## Current HuggingFace Options

### Option 1: Paid Inference Endpoints (Recommended for Production)

- **Cost**: Pay-per-use pricing
- **Endpoint**: `https://router.huggingface.co/hf-inference`
- **Models**: Access to all HuggingFace models
- **Setup**:
  1. Create account at https://huggingface.co
  2. Add payment method at https://huggingface.co/settings/billing
  3. Create API token at https://huggingface.co/settings/tokens
  4. Set environment variable: `export HUGGINGFACE_API_KEY='hf_...'`

**Pricing**: ~$0.001-$0.01 per 1K tokens (varies by model)

### Option 2: Free Third-Party Providers (Current Workaround)

HuggingFace models are available through other providers for FREE:

#### A. **Groq** (Recommended - Fast & Free)
- **Models**: Llama 3.1, Mixtral, Gemma
- **Speed**: Very fast inference
- **Setup**:
  ```bash
  # Get free API key: https://console.groq.com
  export GROQ_API_KEY='gsk_...'
  ```
- **In Consoul**: Select "Groq" provider, choose model

#### B. **Together AI** (Free Tier Available)
- **Models**: Llama, Mistral, Qwen, etc.
- **Free Tier**: $25 free credits
- **Setup**:
  ```bash
  # Get key: https://api.together.xyz/settings/api-keys
  export TOGETHER_API_KEY='...'
  ```

#### C. **Replicate** (Pay-per-use)
- **Models**: Many HuggingFace models
- **Setup**:
  ```bash
  # Get key: https://replicate.com/account/api-tokens
  export REPLICATE_API_TOKEN='r8_...'
  ```

### Option 3: Local Models (Completely Free)

Run models locally using **Ollama** or **MLX** (for Apple Silicon):

#### A. **Ollama** (Easiest for local)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# In Consoul: Select "Ollama" provider
```

**Pros**: Free, private, no API limits
**Cons**: Requires local compute, slower on non-GPU machines

#### B. **MLX** (Apple Silicon only)
```bash
# Already integrated in Consoul
# Select "MLX" provider in Consoul
# Choose from mlx-community models
```

**Pros**: Fast on M-series Macs, free
**Cons**: Apple Silicon only

## Why Did HuggingFace Change?

1. **Free Inference API** was expensive to operate at scale
2. **Serverless** model allows HF to monetize infrastructure
3. **Third-party providers** now fill the free tier gap

## What Works with Free HuggingFace Token?

Your free HuggingFace token **STILL WORKS** for:

✅ **Model Downloads** - Download models to run locally
✅ **Dataset Access** - Access HuggingFace datasets
✅ **Gated Models** - Request access to restricted models (Llama, etc.)
✅ **Spaces** - Deploy and run Gradio/Streamlit apps

❌ **Inference API** - NO LONGER FREE (requires payment)

## Recommended Setup for Consoul

**For Free Usage:**
1. Use **Groq** for fast inference (free)
2. Use **Ollama** for local/private models (free)
3. Use **MLX** if you have Apple Silicon (free)

**For Production/Scale:**
1. Use **Anthropic** (Claude) - Best quality
2. Use **OpenAI** (GPT-4) - Good balance
3. Use **HuggingFace Inference** - If you need specific HF models

## Testing Your Setup

Run the test script:
```bash
poetry run python test_huggingface.py
```

This will tell you:
- If your HF token is valid
- Which providers are working
- What options you have

## Getting Started

### Quick Start (Free):

1. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.1:8b
   ```

2. **Configure Consoul**:
   - Press `Ctrl+M` in Consoul
   - Select "Ollama"
   - Choose "llama3.1:8b"

3. **Start chatting!**

### Alternative (Groq - Free API):

1. **Get Groq API Key**:
   - Visit https://console.groq.com
   - Create free account
   - Copy API key

2. **Set Environment Variable**:
   ```bash
   export GROQ_API_KEY='gsk_your_key_here'
   ```

3. **Configure Consoul**:
   - Press `Ctrl+M`
   - Select "Groq"
   - Choose a model (llama-3.1-8b-instant recommended)

## FAQ

### Q: Do I need to pay for HuggingFace?
**A**: No! Use Groq, Ollama, or MLX instead. They're free and work great.

### Q: What happened to the free Inference API?
**A**: HuggingFace deprecated it in 2024. It now returns 410 errors.

### Q: Can I still use Llama models for free?
**A**: Yes! Via Groq (API) or Ollama (local).

### Q: Is the new HuggingFace API expensive?
**A**: Moderate - around $0.001-$0.01 per 1K tokens, cheaper than OpenAI.

### Q: What's the best free option?
**A**: **Groq** for speed, **Ollama** for privacy, **MLX** for M-series Macs.

## Support

If you're still having issues:

1. Check token: https://huggingface.co/settings/tokens
2. Run test: `poetry run python test_huggingface.py`
3. Try Groq instead: https://console.groq.com
4. Open issue: https://github.com/goatbytes/consoul/issues

## Resources

- **HuggingFace Pricing**: https://huggingface.co/pricing
- **Groq (Free)**: https://console.groq.com
- **Ollama (Local)**: https://ollama.com
- **Together AI**: https://www.together.ai
- **Replicate**: https://replicate.com
