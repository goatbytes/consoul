Here are focused, drop-in updates that (1) refresh the token limits, and
(2) make matching more robust without changing your public API.

### 1) Update `MODEL_TOKEN_LIMITS`

```python
# Model token limits (context window sizes)
MODEL_TOKEN_LIMITS: dict[str, int] = {
    # OpenAI models
    "gpt-4.1": 1_000_000,           # 1M ctx (Apr 2025)
    "gpt-4.1-mini": 1_000_000,      # 1M ctx
    "gpt-4o": 128_000,              # 128K ctx
    "gpt-4o-mini": 128_000,         # 128K ctx
    "gpt-4-turbo": 128_000,         # 128K ctx (legacy, still seen in wild)
    "gpt-4": 8_192,                 # 8K ctx (legacy)
    "gpt-3.5-turbo": 16_385,        # 16K ctx (legacy)
    "o1-preview": 128_000,          # 128K ctx
    "o1-mini": 128_000,             # 128K ctx

    # Anthropic models
    # Default 200K; Sonnet 4 / 4.5 preview tiers enable 1M with flags
    "claude-sonnet-4-5": 200_000,
    "claude-sonnet-4": 1_000_000,   # 1M ctx (preview/expanded)
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,

    # Google models
    "gemini-2.5-pro": 1_000_000,    # 1M ctx (2M announced/rolling out)
    "gemini-2.5-flash": 128_000,    # docs list 128K for 2.5 Flash
    "gemini-1.5-pro": 2_000_000,    # 2M ctx
    "gemini-1.5-flash": 1_000_000,  # ~1M ctx
    "gemini-pro": 32_000,           # 32K ctx (legacy)

    # Ollama / common OSS defaults (model-specific variants may differ)
    "llama3": 8_192,
    "llama3.1": 128_000,
    "mistral": 32_000,
    "phi": 4_096,
    "qwen": 32_000,
    "codellama": 16_000,
}
```

### 2) Harden model-name matching (tolerant, case-insensitive)

```python
def get_model_token_limit(model_name: str) -> int:
    """Return max context window size for a model (tokens)."""
    key = (model_name or "").strip().lower()
    # Normalize separators some providers use (':', '/', '_')
    key = key.replace(":", "-").replace("/", "-").replace("_", "-")

    # Exact match first
    if key in MODEL_TOKEN_LIMITS:
        return MODEL_TOKEN_LIMITS[key]

    # Prefix match (e.g., "gpt-4o-2024-08-06" → "gpt-4o")
    for known, limit in MODEL_TOKEN_LIMITS.items():
        if key.startswith(known):
            return limit

    return DEFAULT_TOKEN_LIMIT
```

### 3) Broaden OpenAI detection (keeps your current behavior)

```python
def _is_openai_model(model_name: str) -> bool:
    """Heuristic: OpenAI chat/reasoning families that use tiktoken best."""
    key = (model_name or "").lower()
    return key.startswith(("gpt-", "o1-", "o2-", "o3-", "o4-", "text-davinci"))
```

### 4) Tighten docstring note (optional)

```python
"""
Notes:
- OpenAI GPT-4.1/4.1-mini support ~1M token context; GPT-4o remains 128K.
- Anthropic Claude defaults to 200K; Sonnet 4/4.5 can reach ~1M with flags.
- Gemini 1.5 Pro allows ~2M; 2.5 Pro is ~1M (2M announced); 2.5 Flash is 128K.
"""
```

---

**Sources (context window sizes):**
OpenAI GPT-4.1 (1M): ([OpenAI][1])
OpenAI o1 preview/mini (128K): ([OpenAI Developer Community][2])
Anthropic defaults 200K; Sonnet 4/4.5 1M preview: ([Amazon Web Services, Inc.][3])
Gemini 1.5 Pro (2M): ([Google Developers Blog][4])
Gemini 2.5 Pro (1M, 2M “coming soon”): ([blog.google][5])
Gemini 2.5 Flash (128K): ([Google Cloud Documentation][6])
Gemini 1.5 Flash (~1M): ([Google AI for Developers][7])
Llama 3.1 (128K): ([Ollama][8])

If you want, I can also add an **env-override hook** (e.g.,
`MODEL_TOKEN_LIMITS_OVERRIDES='{"gpt-4.1": 500000}'`) so ops can hot-fix limits
without a deploy.

[1]: https://openai.com/index/gpt-4-1/?utm_source=chatgpt.com "Introducing GPT-4.1 in the API"
[2]: https://community.openai.com/t/what-is-the-token-context-window-size-of-the-gpt-4-o1-preview-model/954321?utm_source=chatgpt.com "What is the token context window size of the GPT-4 o1- ..."
[3]: https://aws.amazon.com/bedrock/anthropic/?utm_source=chatgpt.com "Claude by Anthropic - Models in Amazon Bedrock"
[4]: https://developers.googleblog.com/en/new-features-for-the-gemini-api-and-google-ai-studio/?utm_source=chatgpt.com "Gemini 1.5 Pro 2M context window, code execution ..."
[5]: https://blog.google/technology/google-deepmind/gemini-model-thinking-updates-march-2025/?utm_source=chatgpt.com "Gemini 2.5: Our most intelligent AI model"
[6]: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash?utm_source=chatgpt.com "Gemini 2.5 Flash | Generative AI on Vertex AI"
[7]: https://ai.google.dev/gemini-api/docs/tokens?utm_source=chatgpt.com "Understand and count tokens | Gemini API"
[8]: https://ollama.com/library/llama3.1?utm_source=chatgpt.com "llama3.1"

---



Here’s a **revised and updated** `MODEL_TOKEN_LIMITS` dictionary reflecting the latest publicly-announced context window sizes. Some values remain conservative where clarity is incomplete. I recommend using this as a strong starting point, and you may still want to override via config if your deployment experiences differ.

```python
MODEL_TOKEN_LIMITS: dict[str, int] = {
    # OpenAI models
    "gpt-5":                400_000,    # API spec: 400K token context window. :contentReference[oaicite:0]{index=0}
    "gpt-5-mini":           400_000,    # same family as above
    "gpt-5-nano":           400_000,    # same
    "gpt-4.1":              1_000_000,  # full API version supports ≈1M tokens. :contentReference[oaicite:1]{index=1}
    "gpt-4.1-mini":         1_000_000,  # same family
    "gpt-4.1-nano":         1_000_000,  # same family
    "gpt-4o":               128_000,    # earlier OpenAI model still in many lists
    "gpt-4o-mini":          128_000,
    "gpt-4":                8_192,      # legacy
    "gpt-3.5-turbo":        16_385,     # legacy
    "o1-preview":           128_000,
    "o1-mini":              128_000,

    # Anthropic models
    "claude-sonnet-4":      1_000_000,  # Sonnet 4 now supports up to 1M tokens (beta/enterprise) :contentReference[oaicite:2]{index=2}
    "claude-sonnet-4-5":    200_000,    # default earlier; upgrade to 1M may apply in limited tiers :contentReference[oaicite:3]{index=3}
    "claude-3-5-sonnet":    200_000,
    "claude-3-opus":        200_000,
    "claude-3-sonnet":      200_000,
    "claude-3-haiku":       200_000,

    # Google / Gemini (DeepMind)
    "gemini-2.5-pro":       1_000_000,  # 1M context window stated for 2.5 Pro. :contentReference[oaicite:4]{index=4}
    "gemini-2.5-flash":     1_048_576,  # API spec shows 1,048,576 (≈1M) for input limit. :contentReference[oaicite:5]{index=5}
    "gemini-1.5-pro":       2_000_000,  # reported 2M context for 1.5 Pro in some sources (estimate)
    "gemini-1.5-flash":     1_000_000,  # estimate
    "gemini-pro":           32_000,     # legacy smaller context

    # Open / local / Ollama / OSS models
    "llama3":               8_192,      # conservative legacy default
    "llama3.1":             128_000,    # up to 128k tokens supported in the 3.1 family. :contentReference[oaicite:6]{index=6}
    "mistral":              32_000,    # rough estimate/common value
    "phi":                  4_096,     # small model default
    "qwen":                 32_000,    # estimate
    "codellama":            16_000,    # estimate
}
```

### Notes & caveats

* For models like `claude-sonnet-4`, the 1 000 000-token context window is currently **beta or enterprise only** (via specific header flags etc.). Use with caution. ([Claude Docs][1])
* For `gemini-1.5-pro` and `gemini-1.5-flash`, the values (2 000 000 and 1 000 000) are **estimates** based on press/rumor rather than fully transparent dev docs. You may want to treat these as upper bounds until verified.
* For `gpt-5`, the official OpenAI page says “400 K context length | 128 K max output tokens” for the “Text & vision” descriptor. ([OpenAI][2]) Other sources mention tier-based limits that are lower (e.g., 256K), so I picked 400K as the API cap. ([Cinco Días][3])
* For the open/OSS models (Ollama, CodeLlama, etc.), many context windows are flexible or user‐configurable, so the values shown are conservative or based on available documentation.
* Prefix matching logic in your `get_model_token_limit()` remains important because many models will come with version/variant suffixes (e.g., “gpt-5-thinking”, “gemini-2.5-flash-image”) which may not be listed exactly here.

### Suggested next step

* Review this list and mark any entries as **“estimate”** or **“beta”** so you know where margin of error exists.
* If you encounter a model with a context window **outside** these values (via your own logs or platform metadata), consider adding an override entry in `MODEL_TOKEN_LIMITS_OVERRIDES`.
* Maintain a **version metadata log** (e.g., date, source) for each model entry so you can revisit as providers publish updates.
* Optionally, in your logic you might treat “API full version” vs “UI/consumer version” context windows differently (since e.g., GPT-4.1 offers 1M in API but UI tiers may be smaller).

If you like, I can **generate a full CSV** of ~30+ models (with variants) including token windows, release dates and notes, so you can load that into your tooling for future updates. Would that be useful?

[1]: https://docs.anthropic.com/en/docs/build-with-claude/context-windows?utm_source=chatgpt.com "Context windows - Anthropic API"
[2]: https://openai.com/gpt-5/?utm_source=chatgpt.com "GPT-5 is here"
[3]: https://cincodias.elpais.com/smartlife/lifestyle/2025-08-11/gpt-5-openai-grandes-novedades.html?utm_source=chatgpt.com "GPT-5 de OpenAI: estas son sus grandes novedades para gobernar la IA en 2025"
