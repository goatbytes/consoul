# Consoul Examples

This directory contains example scripts demonstrating Consoul's AI provider capabilities and SDK integration patterns.

## Available Examples

### FastAPI WebSocket Server (`fastapi_websocket_server.py`) 🆕

**Real-time AI chat server with WebSocket support** - Proof-of-concept validating that Consoul SDK works independently without TUI/CLI dependencies.

**Features:**
- WebSocket-based real-time chat
- Token-by-token streaming responses
- Tool execution with WebSocket approval
- Multi-user concurrent support
- Clean REST API architecture
- No TUI/CLI dependencies (pure SDK usage)

**Installation:**
```bash
pip install consoul fastapi uvicorn websockets
```

**Usage:**
```bash
# Start server
python examples/fastapi_websocket_server.py

# Connect with test client
python examples/fastapi_websocket_client.py

# Or use wscat (add ?api_key=YOUR_KEY if authentication is enabled)
npm install -g wscat
wscat -c ws://localhost:8000/ws/chat
```

**Server Endpoints:**
- `ws://localhost:8000/ws/chat` - WebSocket chat endpoint
- `http://localhost:8000/health` - Health check

**WebSocket Protocol:**

Client → Server:
```json
{"type": "message", "content": "What is 2+2?"}
{"type": "tool_approval", "id": "call_123", "approved": true}
```

Server → Client:
```json
{"type": "token", "content": "AI response chunk", "cost": 0.0001}
{"type": "tool_request", "id": "call_123", "name": "bash_execute", "arguments": {...}, "risk_level": "caution"}
{"type": "done"}
{"type": "error", "message": "error details"}
```

**Architecture:**
- `ConversationService` - Core AI chat logic (from SDK)
- `WebSocketApprovalProvider` - Custom tool approval via WebSocket
- Per-connection isolated conversation state
- Concurrent message receiver task (prevents approval deadlock)
- Message queue for processing user messages
- Demonstrates SDK-first architecture

**What This Proves:**
✅ SDK works without TUI/CLI dependencies
✅ Service layer provides clean integration
✅ Streaming works over WebSocket
✅ Tool execution works with custom approval
✅ Multi-user scenarios are possible

---

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

## Security Considerations

### Development vs Production

⚠️ **IMPORTANT**: All examples in this directory are configured for **development convenience**, not production security.

Before deploying to production, you MUST address these security requirements:

### 1. API Authentication

✅ **Production Best Practices:**
- Store API keys in environment variables or secret management systems (AWS Secrets Manager, HashiCorp Vault)
- Use different keys per environment (dev/staging/prod)
- Rotate keys regularly (at least quarterly)
- Implement rate limiting per API key
- Monitor and audit API key usage
- Use strong, randomly generated keys (minimum 32 characters)

❌ **Never Do This:**
- Hardcode API keys in source code
- Commit API keys to version control
- Share API keys between services
- Use development keys in production
- Reuse API keys across environments

**Example - Development (NOT for production):**
```python
# ❌ BAD: Hardcoded fallback for development
api_keys = os.getenv("CONSOUL_API_KEYS", "dev-key-1,dev-key-2").split(",")
```

**Example - Production:**
```python
# ✅ GOOD: Require environment variable
api_keys = os.getenv("CONSOUL_API_KEYS")
if not api_keys:
    raise ValueError(
        "CONSOUL_API_KEYS environment variable is required. "
        "Never hardcode API keys in source code."
    )
api_keys = api_keys.split(",")
```

### 2. CORS Configuration

✅ **Production Best Practices:**
- Specify exact allowed origins (no wildcards)
- Use HTTPS for all origins
- Restrict methods and headers to minimum required
- Set appropriate cache times with `max_age`
- Never combine `allow_origins=["*"]` with `allow_credentials=True`

❌ **Never Do This:**
- Use wildcard origins (`["*"]`) in production
- Allow all methods and headers unless necessary
- Enable credentials with wildcard origins (browsers block this anyway)

**Example - Development (NOT for production):**
```python
# ⚠️  DEVELOPMENT ONLY - INSECURE for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Any website can access your API!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Example - Production:**
```python
# ✅ PRODUCTION-SAFE
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.yourdomain.com",
        "https://admin.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=3600,
)
```

**Security Risks of Wildcard CORS:**
- Any website can make requests to your API
- Potential for CSRF (Cross-Site Request Forgery) attacks
- No origin-based access control
- Credentials could be exposed to malicious sites
- Data leakage to untrusted origins

**References:**
- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [OWASP CORS Guide](https://owasp.org/www-community/attacks/csrf)

### 3. Rate Limiting

✅ **Production Best Practices:**
- Enable rate limiting on all endpoints (except health checks)
- Use Redis for distributed rate limiting (multiple server instances)
- Set appropriate limits per endpoint type
- Implement per-API-key rate limiting
- Monitor rate limit violations
- Use multiple time windows (e.g., `["10/minute", "100/hour", "1000/day"]`)

❌ **Never Do This:**
- Disable rate limiting in production
- Use in-memory rate limiting with multiple server instances
- Set overly permissive rate limits
- Forget to exempt health check endpoints

**Example - Production Configuration:**
```python
from consoul.server import RateLimiter

# Use Redis for distributed rate limiting
limiter = RateLimiter(
    default_limits=["100/minute", "1000/hour", "10000/day"],
    storage_url=os.getenv("REDIS_URL"),  # Required for production
    key_func=lambda request: request.headers.get("X-API-Key", request.client.host),
)

# Apply stricter limits to expensive endpoints
@app.post("/chat")
@limiter.limit("10/minute")  # Override default
async def chat(...):
    ...

# Always exempt health checks
@app.get("/health")
@limiter.exempt
async def health(...):
    ...
```

### 4. HTTPS/TLS

✅ **Production Best Practices:**
- Use HTTPS for all production endpoints
- Configure TLS 1.2 or higher (TLS 1.3 recommended)
- Use valid SSL certificates (Let's Encrypt, commercial CA)
- Enable HSTS (HTTP Strict Transport Security) headers
- Redirect HTTP to HTTPS
- Configure via reverse proxy (nginx, Caddy, Traefik)

❌ **Never Do This:**
- Use HTTP in production
- Accept self-signed certificates in production
- Disable certificate verification
- Allow mixed content (HTTP resources on HTTPS pages)

**Example - nginx reverse proxy configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # TLS configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 5. Input Validation

✅ **Production Best Practices:**
- Use Pydantic models for request validation
- Set maximum body sizes
- Validate all user input
- Sanitize data before logging
- Use parameterized queries for databases
- Set field constraints (min/max length, regex patterns)

❌ **Never Do This:**
- Trust user input
- Log sensitive data (API keys, passwords, PII)
- Disable validation in production
- Use user input directly in commands or queries

**Example - Proper Input Validation:**
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, regex="^[a-zA-Z0-9-]+$")
    message: str = Field(..., min_length=1, max_length=10000)

    @validator("message")
    def sanitize_message(cls, v):
        # Remove potentially dangerous characters
        return v.strip()

# Configure maximum request body size
from consoul.server import RequestValidator

validator = RequestValidator(
    max_body_size=1024 * 100  # 100KB limit
)
```

### 6. Session Management

✅ **Production Best Practices:**
- Use Redis or database for session storage (not in-memory)
- Generate secure session IDs (UUID v4, cryptographically random)
- Set appropriate session TTL
- Implement session invalidation
- Never accept user-provided session IDs
- Clear sessions on logout

❌ **Never Do This:**
- Use in-memory session storage in production (not distributed)
- Accept user-provided session IDs directly
- Store sensitive data in sessions without encryption
- Use predictable session IDs

**Example - Secure Session Management:**
```python
import uuid
from consoul.sdk.session_store import RedisSessionStore

# Use Redis for distributed session storage
session_store = RedisSessionStore(
    redis_url=os.getenv("REDIS_URL"),
    ttl=3600,  # 1 hour
    key_prefix="app:session:"
)

# Generate secure session IDs server-side
def create_session(user_id: str):
    session_id = str(uuid.uuid4())  # Cryptographically random
    # Never use user-provided IDs or predictable patterns
    return session_id
```

### 7. Error Handling

✅ **Production Best Practices:**
- Return generic error messages to clients
- Log detailed errors server-side only
- Never expose stack traces to users
- Don't leak internal implementation details
- Use proper HTTP status codes

❌ **Never Do This:**
- Return stack traces or internal errors to clients
- Include file paths or code snippets in error responses
- Expose database schema or query details

**Example - Secure Error Handling:**
```python
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Process request
        result = process_chat(request)
        return result
    except Exception as e:
        # ✅ Log detailed error server-side
        logger.error(f"Chat processing failed: {e}", exc_info=True)

        # ✅ Return generic error to client (don't expose internals)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request"
        )
```

### Production Deployment Checklist

Before deploying any example to production:

**Security:**
- [ ] Replace wildcard CORS with specific origins
- [ ] Move all API keys to environment variables
- [ ] Enable rate limiting with Redis backend
- [ ] Configure HTTPS/TLS properly
- [ ] Add security headers (HSTS, X-Frame-Options, CSP)
- [ ] Implement proper authentication (not just API keys)
- [ ] Add authorization checks for sensitive operations
- [ ] Enable request validation with size limits
- [ ] Configure proper error handling (no stack traces)
- [ ] Use secure session IDs (UUID v4, not user-provided)

**Monitoring & Logging:**
- [ ] Set up logging (without sensitive data)
- [ ] Add monitoring and alerting
- [ ] Implement health check endpoints
- [ ] Track API usage metrics
- [ ] Monitor rate limit violations
- [ ] Set up error tracking (Sentry, Rollbar)

**Infrastructure:**
- [ ] Use Redis for distributed caching/sessions
- [ ] Configure load balancer with SSL termination
- [ ] Set up auto-scaling
- [ ] Implement backup and disaster recovery
- [ ] Configure proper timeouts
- [ ] Set resource limits (CPU, memory)

**Testing:**
- [ ] Test authentication flows
- [ ] Verify CORS configuration with browser
- [ ] Load test rate limiting
- [ ] Security scan (OWASP ZAP, Burp Suite)
- [ ] Penetration testing
- [ ] Review dependencies for vulnerabilities

### Reference Examples

- **Development-Friendly:** `examples/server/basic_server.py`, `examples/backend/fastapi_sessions.py`
  - Good for learning and local development
  - ⚠️  NOT production-ready without modifications

- **Security Best Practices:** `examples/server/security_middleware.py`
  - ✅ Shows proper security patterns (no wildcards, required env vars, no hardcoded secrets)
  - ✅ Demonstrates correct CORS configuration with specific origins
  - ⚠️  Still requires customization: Update CORS origins for your domains before deployment
  - Use as a reference template for security middleware configuration

### Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [Consoul Server Documentation](https://docs.consoul.com/server/)

---

## Next Steps

- Explore the main documentation for advanced features
- Create custom profiles for your workflows
- Try different models to find what works best for your use case
- Integrate Consoul into your own applications using the library API
- Review security considerations before deploying to production
