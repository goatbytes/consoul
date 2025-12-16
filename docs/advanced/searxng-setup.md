# SearxNG Setup Guide for Consoul

This guide walks you through setting up SearxNG as a self-hosted search backend for Consoul's `web_search` tool.

## Why SearxNG?

**SearxNG** is a free, privacy-respecting metasearch engine that aggregates results from 135+ search engines without tracking users.

### Benefits for Consoul:
- ✅ **No Rate Limits**: Self-hosted, unlimited searches
- ✅ **Engine Selection**: Choose from Google, GitHub, Stack Overflow, arXiv, and 130+ more
- ✅ **Categories**: Filter by general, IT, news, academic, images, etc.
- ✅ **Privacy**: Complete control over data, no external tracking
- ✅ **Free**: No API costs or subscription fees
- ✅ **Production-Grade**: Used by Perplexica (17k stars) and other LLM projects

## Quick Start (5 Minutes)

### Option 1: Docker (Recommended)

```bash
# Pull and run SearxNG container
docker run -d \
  --name searxng \
  -p 8888:8080 \
  -e BASE_URL=http://localhost:8888 \
  searxng/searxng:latest

# Verify it's running
curl http://localhost:8888/healthz
```

### Option 2: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "8888:8080"
    environment:
      - BASE_URL=http://localhost:8888
    volumes:
      - ./searxng:/etc/searxng  # Optional: persist config
    restart: unless-stopped
```

Start:
```bash
docker-compose up -d
```

### Option 3: Perplexica Bundle (SearxNG + AI Interface)

If you want a reference implementation with SearxNG already configured:

```bash
git clone https://github.com/ItzCrazyKns/Perplexica.git
cd Perplexica
docker-compose up -d
```

This includes SearxNG pre-configured for AI agents at `http://localhost:4000`.

## Configure Consoul

Once SearxNG is running, update your Consoul profile config:

```yaml
# ~/.consoul/profiles/default/config.yaml
tools:
  enabled: true
  web_search:
    # Common settings
    max_results: 5
    timeout: 10

    # SearxNG settings
    searxng_url: "http://localhost:8888"  # Your SearxNG instance
    searxng_engines:
      - google          # General web search
      - duckduckgo      # Privacy-focused search
      - bing            # Microsoft search
      - github          # Code repositories
      - stackoverflow   # Programming Q&A
      - arxiv           # Academic papers
      - wikipedia       # Encyclopedia
    enable_engine_selection: true
    enable_categories: true

    # DuckDuckGo fallback settings
    region: "wt-wt"
    safesearch: "moderate"
```

## Test the Integration

```python
from consoul.ai.tools import web_search

# Basic search (will use SearxNG)
result = web_search.invoke({
    "query": "Python programming",
    "max_results": 3
})
print(result)

# Engine-specific search
result = web_search.invoke({
    "query": "machine learning papers",
    "engines": ["arxiv", "google"],
    "max_results": 5
})
print(result)

# Category search
result = web_search.invoke({
    "query": "cybersecurity breach",
    "categories": ["news", "it"],
    "max_results": 5
})
print(result)
```

## Available Engines

SearxNG supports 135+ engines. Here are the most useful for development:

### Code & Development
- `github` - Code repositories
- `gitlab` - GitLab repositories
- `stackoverflow` - Programming Q&A
- `stackexchange` - Stack Exchange network
- `searchcode` - Source code search
- `dockerhub` - Docker images

### Documentation & Learning
- `wikipedia` - Encyclopedia
- `wikidata` - Structured data
- `devdocs` - Developer documentation
- `mdn` - Mozilla Developer Network

### Academic & Research
- `arxiv` - Scientific papers
- `google scholar` - Academic search
- `pubmed` - Medical research
- `semantic scholar` - AI-powered research

### General Web
- `google` - Google search
- `bing` - Microsoft search
- `duckduckgo` - Privacy search
- `brave` - Brave search

### News & Social
- `reddit` - Reddit posts
- `hackernews` - Hacker News
- `google news` - News articles

### Package Managers
- `npm` - Node.js packages
- `pypi` - Python packages
- `crates` - Rust packages
- `rubygems` - Ruby gems

## Available Categories

Categories let you filter searches by topic:

- `general` - General web search (default)
- `it` - Information technology
- `news` - News articles
- `images` - Image search
- `videos` - Video search
- `music` - Music search
- `files` - File search
- `science` - Scientific content
- `social media` - Social platforms
- `map` - Maps and locations

## Advanced Configuration

### Custom SearxNG Settings

To customize SearxNG behavior, mount a config file:

```yaml
# docker-compose.yml
services:
  searxng:
    image: searxng/searxng:latest
    volumes:
      - ./searxng/settings.yml:/etc/searxng/settings.yml:ro
```

Create `searxng/settings.yml`:

```yaml
# Minimal custom config
use_default_settings: true

server:
  secret_key: "your-secret-key-here"  # Generate with: openssl rand -hex 32
  base_url: "http://localhost:8888"

search:
  default_lang: "en"
  max_request_timeout: 10.0
  formats:
    - html
    - json

engines:
  - name: google
    engine: google
    shortcut: go
    weight: 1.0
    disabled: false

  - name: github
    engine: github
    shortcut: gh
    disabled: false

  # Add more engines...
```

### Enable JSON API

SearxNG's JSON API is automatically available:

```bash
# Test JSON endpoint
curl "http://localhost:8888/search?q=python&format=json"
```

Consoul uses this endpoint via LangChain's `SearxSearchWrapper`.

## Production Deployment

### Environment Variables

```bash
# docker-compose.yml
environment:
  - BASE_URL=https://search.yourdomain.com
  - INSTANCE_NAME=My SearxNG
  - AUTOCOMPLETE=google
  - UWSGI_WORKERS=4
  - UWSGI_THREADS=2
```

### Behind Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name search.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Update Consoul config:
```yaml
web_search:
  searxng_url: "https://search.yourdomain.com"
```

### Behind Reverse Proxy (Traefik)

```yaml
# docker-compose.yml
services:
  searxng:
    image: searxng/searxng:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.searxng.rule=Host(`search.yourdomain.com`)"
      - "traefik.http.routers.searxng.entrypoints=websecure"
      - "traefik.http.routers.searxng.tls.certresolver=letsencrypt"
```

## Troubleshooting

### SearxNG Not Responding

```bash
# Check container status
docker ps | grep searxng

# View logs
docker logs searxng

# Restart container
docker restart searxng
```

### Connection Refused

Verify SearxNG is listening:
```bash
curl http://localhost:8888/healthz
```

If this fails, check:
1. Port mapping: `-p 8888:8080` maps container port 8080 to host 8888
2. Firewall rules allow port 8888
3. Container is running: `docker ps`

### Engine Not Working

Some engines may be disabled by default. Enable in `settings.yml`:

```yaml
engines:
  - name: github
    disabled: false  # Change from true
```

Restart container after changes.

### Fallback to DuckDuckGo

Consoul automatically falls back to DuckDuckGo if SearxNG is unavailable. Check logs:

```python
import logging
logging.basicConfig(level=logging.INFO)

# This will log which backend is used
web_search.invoke({"query": "test"})
```

## Performance Tuning

### Increase Workers

```yaml
# docker-compose.yml
environment:
  - UWSGI_WORKERS=8    # Default: 4
  - UWSGI_THREADS=4    # Default: 2
```

### Add Redis Cache

```yaml
services:
  redis:
    image: redis:alpine
    restart: unless-stopped

  searxng:
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

### Limit Engines

For faster results, disable slow engines:

```yaml
engines:
  - name: wikipedia
    disabled: true  # Disable if not needed
```

## References

- **SearxNG Docs**: https://docs.searxng.org/
- **Docker Hub**: https://hub.docker.com/r/searxng/searxng
- **GitHub**: https://github.com/searxng/searxng
- **Perplexica** (Reference Implementation): https://github.com/ItzCrazyKns/Perplexica
- **LangChain Integration**: https://python.langchain.com/docs/integrations/tools/searx_search

## Next Steps

1. **Test Different Engines**: Experiment with GitHub, Stack Overflow, arXiv for specialized searches
2. **Configure Categories**: Try filtering by `it`, `news`, or `science`
3. **Monitor Performance**: Check Docker stats with `docker stats searxng`
4. **Customize Settings**: Add/remove engines based on your needs
5. **Set Up Monitoring**: Use Prometheus/Grafana for production deployments

---

**Need Help?**

- Consoul Issues: https://github.com/goatbytes/consoul/issues
- SearxNG Issues: https://github.com/searxng/searxng/issues
