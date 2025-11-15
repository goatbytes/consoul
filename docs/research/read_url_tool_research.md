# read_url Tool Research

**Date**: 2025-11-14
**Researcher**: Claude (via user request)
**Purpose**: Research and design a `read_url` tool for Consoul AI to convert web URLs into LLM-readable content

---

## Executive Summary

After comprehensive research, **Jina AI Reader** emerges as the best solution for a `read_url` tool due to:
- ✅ **Zero configuration** (no API key needed for basic usage)
- ✅ **Fast response times** (~2s)
- ✅ **Clean markdown output** optimized for LLMs
- ✅ **Generous free tier** (20 RPM no-auth, 500 RPM with free API key)
- ✅ **Proven reliability** (used by major AI products)

**Recommended Implementation**: Jina Reader as primary, with optional trafilatura fallback for privacy-sensitive use cases.

---

## Research Findings

### 1. Jina AI Reader

**URL**: `https://r.jina.ai/{target_url}`

#### Capabilities
- Converts any URL to clean, LLM-optimized markdown
- Supports HTML pages, PDFs, and complex web structures
- Image captioning for webpage images
- Extracts structured content with metadata
- Supports 29 languages
- Returns clean markdown with proper formatting

#### Rate Limits & Pricing
| Tier | Rate Limit | Price | Tokens |
|------|------------|-------|--------|
| No Auth | 20 RPM | Free | N/A |
| Free API Key | 500 RPM | Free | 10M tokens |
| Premium | 5,000 RPM | Paid | Token-based |

#### Performance
- **Response Time**: ~2 seconds average
- **Output Size**: Typically 100-500 lines for standard pages
- **Quality**: Excellent - removes nav, ads, footers automatically

#### Limitations
- Cannot access login-protected content
- No content translation
- Publicly accessible URLs only
- Token limits on free tier

#### Test Results

**GoatBytes.IO homepage** (186 lines, 2.2s):
```markdown
Title: GoatBytes.IO

URL Source: https://goatbytes.io/

Markdown Content:
GoatBytes.IO
===============

Secure software solutions for a changing world
==============================================
...
```

**GitHub profile** (clean extraction, nav removed):
```markdown
Title: GoatBytes.IO

URL Source: https://github.com/goatbytes

Our mission is to develop secure software solutions that empower
businesses to transform the world.

Popular repositories Loading
----------------------------
...
```

**Academic paper (arXiv)**: Successfully extracted paper title, abstract, and metadata.

---

### 2. Trafilatura

**Installation**: `pip install trafilatura`

#### Capabilities
- Python library for web scraping and text extraction
- Supports markdown, XML, JSON, TXT output
- Language-aware extraction
- Sitemap and RSS feed discovery
- Link extraction and filtering
- Used by HuggingFace, IBM, Microsoft Research

#### Pricing
- **Free** (open source)
- **No rate limits** (runs locally)
- **No API dependencies**

#### Performance
- **Response Time**: Varies (depends on page complexity)
- **Quality**: Good for news/articles, struggles with modern JS-heavy sites
- **Privacy**: Excellent (all local processing)

#### Test Results

**Wikipedia**: ✅ **Success** - Clean extraction
```markdown
# Python (programming language)

**Python** is a high-level, general-purpose programming language.
Its design philosophy emphasizes code readability with the use of
significant indentation...
```

**GoatBytes.IO**: ❌ **Failed** - Returned None (likely JS-rendered content)

**Conclusion**: Trafilatura works well for static content (news, Wikipedia, blogs) but fails on modern JS-heavy sites.

---

### 3. Markdownify

**Installation**: Already installed in Consoul

#### Capabilities
- Python library for HTML-to-Markdown conversion
- Works with requests/BeautifulSoup
- Highly customizable conversion rules

#### Pricing
- **Free** (open source)
- **No dependencies** on external services

#### Performance
- **Fast** (local processing)
- **Quality**: Raw - includes all HTML (nav, ads, scripts)

#### Test Results

**GoatBytes.IO**: ⚠️ **Partial success** - Converted but included navigation, footers, etc.

**Conclusion**: Good for simple HTML conversion but lacks intelligent content extraction.

---

### 4. Firecrawl

**URL**: `https://api.firecrawl.dev`

#### Capabilities
- "Web Data API for AI" - LLM-optimized scraping
- JavaScript rendering support
- Recursive crawling
- Structured data extraction
- Python SDK available

#### Pricing
| Tier | Credits | Price |
|------|---------|-------|
| Free | 500 pages | $0 |
| Hobby | 3,000 pages | $16/mo |
| Standard | 100,000 pages | $83/mo |
| Growth | 500,000 pages | $333/mo |

#### Conclusion
- **Excellent quality** but requires API key
- **Limited free tier** (500 pages total, not per month)
- **Not ideal** for Consoul's "zero-config" philosophy

---

### 5. Other Solutions Evaluated

#### BeautifulSoup + Readability
- **Pros**: Full control, local processing
- **Cons**: Requires complex extraction logic, maintenance burden

#### newspaper3k
- **Pros**: Article extraction, metadata parsing
- **Cons**: Unmaintained (last update 2020), Python 3.7 only

#### Scrapy
- **Pros**: Powerful, scalable
- **Cons**: Overkill for single-URL fetching, steep learning curve

#### Playwright/Selenium + html2text
- **Pros**: Handles JavaScript rendering
- **Cons**: Heavy dependencies (browser), slow, complex setup

---

## Comparison Matrix

| Solution | Setup | Free | Speed | Quality | JS Sites | Privacy |
|----------|-------|------|-------|---------|----------|---------|
| **Jina Reader** | None | ✅ 20 RPM | ⚡ 2s | ⭐⭐⭐⭐⭐ | ✅ | ⚠️ External |
| **Trafilatura** | pip | ✅ Unlimited | ⚡ Fast | ⭐⭐⭐⭐ | ❌ | ✅ Local |
| **Markdownify** | pip | ✅ Unlimited | ⚡⚡ Instant | ⭐⭐ | ❌ | ✅ Local |
| **Firecrawl** | API key | ⚠️ 500 total | ⚡ 2-5s | ⭐⭐⭐⭐⭐ | ✅ | ⚠️ External |

---

## Recommended Implementation

### Primary: Jina AI Reader

**Why Jina?**
1. **Zero friction** - Works immediately, no setup
2. **Best quality** - Purpose-built for LLMs
3. **Generous free tier** - 20 RPM is enough for most use cases
4. **Proven track record** - Used by production AI applications
5. **Handles modern web** - JS rendering, complex layouts

**Configuration**:
```python
class ReadUrlToolConfig(BaseModel):
    """Configuration for read_url tool."""

    # Jina Reader settings
    jina_api_key: str | None = Field(
        default=None,
        description="Optional Jina AI API key for higher rate limits (500 RPM)",
    )
    timeout: int = Field(
        default=10,
        gt=0,
        le=30,
        description="Request timeout in seconds",
    )

    # Fallback settings
    enable_fallback: bool = Field(
        default=True,
        description="Enable trafilatura fallback if Jina fails",
    )

    # Output settings
    include_images: bool = Field(
        default=True,
        description="Include image captions in output",
    )
    max_length: int = Field(
        default=50000,
        description="Maximum output length in characters",
    )
```

**Tool Signature**:
```python
@tool
def read_url(
    url: str,
    use_fallback: bool | None = None,
) -> str:
    """Read and convert a web page to LLM-ready markdown.

    Uses Jina AI Reader for best results, with optional trafilatura fallback.

    Args:
        url: URL to read (must be publicly accessible)
        use_fallback: Force fallback to trafilatura (default: auto)

    Returns:
        Markdown-formatted content from the URL
    """
```

---

## Implementation Plan

### Phase 1: Core Implementation (2-3 hours)

1. **Create ReadUrlToolConfig** in `config/models.py`
   - Jina API key (optional)
   - Timeout settings
   - Fallback configuration
   - Output preferences

2. **Implement read_url.py** in `ai/tools/implementations/`
   - `_read_with_jina()` - Primary method
   - `_read_with_trafilatura()` - Fallback method
   - `read_url()` - Main tool function with auto-fallback
   - Error handling and logging

3. **Export and register** in tool registry
   - Add to `__init__.py` exports
   - Register with `RiskLevel.SAFE`
   - Tags: `["web", "readonly", "content"]`

### Phase 2: TUI Integration (30 min)

1. Import and configure in `tui/app.py`
2. Set config from profile settings
3. Register with tool registry

### Phase 3: Documentation (1 hour)

1. Update `docs/tools.md` with:
   - read_url capabilities
   - Configuration examples
   - Use cases and examples
   - Jina vs trafilatura comparison

2. Add to README features list

### Phase 4: Testing (1 hour)

1. Test with various URL types:
   - Corporate websites (goatbytes.io)
   - GitHub profiles/repos
   - Documentation pages
   - Academic papers (arXiv)
   - News articles
   - Blog posts

2. Test fallback behavior
3. Test rate limiting
4. Test error handling

**Total Estimated Time**: 4.5-5.5 hours

---

## Use Cases

### 1. Enhanced Web Search Workflow

Current (limited):
```
User: "Find information about GoatBytes.IO"
→ web_search returns URLs
→ User sees titles/snippets only
```

With read_url:
```
User: "Find and read information about GoatBytes.IO"
→ web_search finds URLs
→ read_url fetches full content from top result
→ User gets complete, formatted content
```

### 2. Documentation Reading

```python
# Find and read LangChain docs
web_search("LangChain tool calling documentation")
→ Returns: https://python.langchain.com/docs/concepts/tools

read_url("https://python.langchain.com/docs/concepts/tools")
→ Returns: Full markdown documentation
```

### 3. Competitive Analysis

```python
# Read competitor websites
read_url("https://competitor.com/features")
→ Clean markdown of features page
```

### 4. Academic Research

```python
# Read arXiv papers
read_url("https://arxiv.org/abs/2301.00234")
→ Paper abstract and metadata
```

---

## Security Considerations

### Risks

1. **SSRF (Server-Side Request Forgery)**
   - Risk: LLM could try to access internal URLs (localhost, 192.168.x.x)
   - Mitigation: Validate URLs, block private IP ranges

2. **Rate Limiting**
   - Risk: Excessive requests to Jina or target sites
   - Mitigation: Respect rate limits, implement caching

3. **Malicious Content**
   - Risk: Fetching malicious pages, XSS in markdown
   - Mitigation: Jina sanitizes content, markdown is safe

4. **Privacy**
   - Risk: Sending private URLs to external service (Jina)
   - Mitigation: Offer trafilatura fallback, document privacy implications

### Recommended Protections

```python
def _validate_url(url: str) -> bool:
    """Validate URL is safe to fetch."""
    parsed = urlparse(url)

    # Must be HTTP(S)
    if parsed.scheme not in ('http', 'https'):
        raise ToolExecutionError("Only HTTP(S) URLs are supported")

    # Block private IPs
    hostname = parsed.hostname
    if hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
        raise ToolExecutionError("Cannot fetch localhost URLs")

    if hostname.startswith('192.168.') or hostname.startswith('10.'):
        raise ToolExecutionError("Cannot fetch private network URLs")

    return True
```

---

## Future Enhancements

### Short-term (Next 6 months)

1. **Caching** - Cache fetched URLs to reduce API calls
2. **PDF Support** - Use Jina's PDF reading capabilities
3. **Batch Reading** - Read multiple URLs in one call
4. **Content Summarization** - Optional LLM summarization of long content

### Medium-term (6-12 months)

1. **Custom Extraction Rules** - CSS selectors for specific content
2. **Screenshot Capture** - Return page screenshots
3. **Archive Support** - Read from web.archive.org
4. **Diff Detection** - Track changes over time

### Long-term (12+ months)

1. **Site Crawling** - Recursive site reading (like Firecrawl)
2. **JavaScript Execution** - Full browser rendering (Playwright integration)
3. **Authentication** - Read login-protected pages
4. **Custom Parsers** - Plugin system for site-specific extraction

---

## Alternatives Considered But Rejected

### Why not BeautifulSoup + Custom Logic?
- **Maintenance burden** - Need to handle edge cases
- **Quality issues** - Hard to extract clean content from modern sites
- **Time investment** - Reinventing what Jina already does well

### Why not Firecrawl?
- **API key required** - Breaks zero-config philosophy
- **Limited free tier** - 500 pages total (not monthly)
- **Overkill** - Too many features for simple URL reading

### Why not Playwright/Selenium?
- **Heavy dependencies** - Requires browser installation
- **Slow** - 5-10s per page vs 2s for Jina
- **Complex** - Harder to maintain and debug

---

## Conclusion

**Recommended Approach**: Implement `read_url` with:
1. **Jina AI Reader** as primary (zero-config, best quality)
2. **Trafilatura** as optional fallback (privacy, offline use)
3. **URL validation** for security
4. **RiskLevel.SAFE** (read-only, no system modification)

**Expected Benefits**:
- Complements `web_search` tool perfectly
- Enables complete web research workflows
- Zero-config for immediate use
- Optional API key for power users (500 RPM)
- Privacy-conscious fallback available

**Next Steps**:
1. Create SOUL-XXX ticket for implementation
2. Implement Phase 1 (core functionality)
3. Test with real use cases
4. Document and deploy

---

## References

- Jina AI Reader: https://jina.ai/reader
- Trafilatura: https://github.com/adbar/trafilatura
- Firecrawl: https://www.firecrawl.dev/
- LangChain Tools: https://python.langchain.com/docs/concepts/tools
- SOUL-91: Advanced search tools research (web_search implementation)
