# Consoul Examples

This directory contains example scripts demonstrating Consoul's AI provider capabilities.

## Available Examples

### 1. Interactive Chat (`interactive_chat.py`)

General-purpose interactive chat supporting all AI providers (OpenAI, Anthropic, Google, Ollama).

**Features:**
- Multi-provider support with auto-detection
- Profile-based configuration
- Conversation history
- Temperature and parameter overrides

**Usage:**
```bash
# Use default profile
python examples/interactive_chat.py

# Use specific model with auto-detection
python examples/interactive_chat.py --model gpt-4o
python examples/interactive_chat.py --model claude-3-5-sonnet-20241022
python examples/interactive_chat.py --model llama3

# Use specific profile
python examples/interactive_chat.py --profile creative

# Override temperature
python examples/interactive_chat.py --model gpt-4o --temperature 0.9
```

**Available Commands:**
- `exit`, `quit` - End the chat session
- `help` - Show available commands
- `clear` - Clear conversation history
- `config` - Show current configuration

---

### 2. Ollama Chat (`ollama_chat.py`)

Dedicated example for local Ollama models with offline capabilities.

**Features:**
- Local AI models (no API keys required)
- Offline operation (works without internet)
- Ollama service status checking
- Model availability detection
- Helpful error messages and setup guidance

**Usage:**
```bash
# Use default model (llama3)
python examples/ollama_chat.py

# Use specific model
python examples/ollama_chat.py --model mistral
python examples/ollama_chat.py --model codellama
python examples/ollama_chat.py --model phi

# Adjust temperature
python examples/ollama_chat.py --model llama3 --temperature 0.9

# Check Ollama status
python examples/ollama_chat.py --check-status

# List popular models
python examples/ollama_chat.py --list-models
```

**Available Commands:**
- `exit`, `quit` - End the chat session
- `help` - Show available commands
- `clear` - Clear conversation history
- `models` - Show popular Ollama models
- `status` - Check Ollama service status

**Prerequisites:**
1. Install Ollama: https://ollama.com
2. Start service: `ollama serve`
3. Pull a model: `ollama pull llama3`

**Popular Ollama Models:**
- `llama3` - Meta's Llama 3 (general purpose)
- `mistral` - Mistral 7B (fast and efficient)
- `codellama` - Code Llama (coding assistance)
- `phi` - Microsoft Phi-2 (compact)
- `qwen` - Alibaba Qwen (multilingual)
- `gemma` - Google Gemma (lightweight)

---

## Provider Setup

### OpenAI
Set your API key:
```bash
export OPENAI_API_KEY=your-key-here
```
Or add to `.env` file in project root or `~/.consoul/`

### Anthropic Claude
Set your API key:
```bash
export ANTHROPIC_API_KEY=your-key-here
```
Or add to `.env` file in project root or `~/.consoul/`

**Getting an API key:**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and set it as shown above

**Supported models:**
- `claude-sonnet-4-5-20250929` - Latest Claude 4 Sonnet (most capable)
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet (highly capable)
- `claude-3-opus-20240229` - Claude 3 Opus (best for complex tasks)
- `claude-3-sonnet-20240229` - Claude 3 Sonnet (balanced performance)
- `claude-3-haiku-20240307` - Claude 3 Haiku (fast and efficient)

**Example usage:**
```bash
# Use latest Claude model
python examples/interactive_chat.py --model claude-sonnet-4-5-20250929

# Use Claude 3.5 Sonnet with higher temperature
python examples/interactive_chat.py --model claude-3-5-sonnet-20241022 --temperature 0.9
```

**Anthropic-specific configuration:**

Claude supports advanced features like extended thinking, experimental beta features, and metadata tracking. Configure these in your YAML profile:

```yaml
profiles:
  thinking_mode:
    model:
      provider: anthropic
      model: claude-sonnet-4-5-20250929
      temperature: 0.7
      max_tokens: 4096
      thinking:
        type: enabled
        budget_tokens: 2000

  experimental_features:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
      temperature: 0.8
      betas:
        - files-api-2025-04-14
        - token-efficient-tools-2025-02-19

  tracked_session:
    model:
      provider: anthropic
      model: claude-3-opus-20240229
      temperature: 0.9
      metadata:
        user_id: user-123
        session_id: session-abc
```

**Advanced Features:**

**Extended Thinking:**
- Enables Claude to show its step-by-step reasoning process
- `budget_tokens`: Controls how many tokens can be used for thinking
- Useful for complex problem-solving and transparent reasoning

**Beta Features:**
- `files-api-2025-04-14`: Enhanced file handling capabilities
- `token-efficient-tools-2025-02-19`: Optimized tool usage
- `context-management-2025-06-27`: Advanced context window management

**Metadata:**
- Add custom metadata for run tracing and analytics
- Track user sessions, request origins, or custom identifiers
- Useful for debugging and monitoring

### Google Gemini
Set your API key:
```bash
export GOOGLE_API_KEY=your-key-here
```
Or add to `.env` file in project root or `~/.consoul/`

**Getting an API key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and set it as shown above

**Supported models:**
- `gemini-2.5-pro` - Latest and most capable
- `gemini-1.5-pro` - High quality general purpose
- `gemini-1.5-flash` - Fast and efficient

**Example usage:**
```bash
# Use latest Gemini model
python examples/interactive_chat.py --model gemini-2.5-pro

# Use fast model with higher temperature
python examples/interactive_chat.py --model gemini-1.5-flash --temperature 0.9
```

**Google-specific configuration:**

Google Gemini supports additional parameters for content safety and generation control. Configure these in your YAML profile:

```yaml
profiles:
  safe_chat:
    model:
      provider: google
      model: gemini-2.5-pro
      temperature: 0.7
      candidate_count: 1
      safety_settings:
        HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_ONLY_HIGH
        HARM_CATEGORY_HARASSMENT: BLOCK_MEDIUM_AND_ABOVE
        HARM_CATEGORY_HATE_SPEECH: BLOCK_MEDIUM_AND_ABOVE
        HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_MEDIUM_AND_ABOVE

  multimodal_chat:
    model:
      provider: google
      model: gemini-2.5-pro
      temperature: 0.8
      generation_config:
        response_modalities: ["TEXT", "IMAGE"]
        candidate_count: 2
```

**Safety Settings Options:**
- `BLOCK_NONE` - No filtering
- `BLOCK_ONLY_HIGH` - Block only high-probability harmful content
- `BLOCK_MEDIUM_AND_ABOVE` - Block medium and high-probability harmful content
- `BLOCK_LOW_AND_ABOVE` - Block low, medium, and high-probability harmful content

**Harm Categories:**
- `HARM_CATEGORY_DANGEROUS_CONTENT`
- `HARM_CATEGORY_HARASSMENT`
- `HARM_CATEGORY_HATE_SPEECH`
- `HARM_CATEGORY_SEXUALLY_EXPLICIT`

### Ollama
No API key required! Just install and run:
```bash
# Install from https://ollama.com
ollama serve

# Pull a model
ollama pull llama3

# Run the example
python examples/ollama_chat.py
```

**Using a remote Ollama instance:**
```bash
# Set custom endpoint
export OLLAMA_API_BASE=http://your-server:11434

# Or add to .env file
echo "OLLAMA_API_BASE=http://your-server:11434" >> .env

# Then run normally
python examples/ollama_chat.py
```

---

## Configuration

Consoul uses a YAML-based configuration system with profiles. See the main documentation for details on creating custom profiles.

Default configuration locations:
- Global: `~/.consoul/config.yaml`
- Project: `./consoul.yaml`
- Environment: `.env` files

---

## Tips

1. **Use Ollama for development/testing** - No API costs, runs offline
2. **Use profiles for different tasks** - Create profiles for code review, creative writing, etc.
3. **Adjust temperature for creativity** - Lower (0.3) for factual, higher (0.9) for creative
4. **Clear history for new topics** - Use the `clear` command to start fresh

---

## Troubleshooting

### "Missing API key" error
Make sure you've set the appropriate environment variable or `.env` file for your provider.

### "Ollama service is not running"
Start Ollama with `ollama serve` in a separate terminal.

### "Model not found" (Ollama)
Pull the model first: `ollama pull <model-name>`

### Model responses are slow
- For cloud providers: Check your internet connection
- For Ollama: Smaller models are faster (try `phi` or `mistral`)

---

## Next Steps

- Explore the main documentation for advanced features
- Create custom profiles for your workflows
- Try different models to find what works best for your use case
- Integrate Consoul into your own applications using the library API
