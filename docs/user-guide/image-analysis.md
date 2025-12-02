# Image Analysis (Vision)

Show the AI what you see—analyze screenshots, debug errors visually, review designs, and extract information from images.

## Introduction

Ever wanted to just *show* the AI what's on your screen instead of describing it? With Consoul's image analysis, you can attach screenshots, mockups, diagrams, or any image and ask questions about them.

**Quick example:**
```bash
$ consoul chat "What's wrong with this error?" --attach error-screenshot.png
```

The AI sees the screenshot, reads the error message, examines the stack trace, and helps you debug—all from the visual context.

**Related Tools:**

- [Code Search](code-search.md) - Find code referenced in screenshots
- [File Editing](file-editing.md) - Fix issues found in images

## Overview

The image analysis feature allows you to:

- 📸 **Analyze screenshots** - Debug errors, understand UI states
- 🎨 **Review designs** - Get feedback on mockups and interfaces
- 📊 **Interpret diagrams** - Understand flowcharts, architecture diagrams
- 🔍 **Compare visuals** - Side-by-side analysis of multiple images
- 💻 **Code from screenshots** - Extract code from terminal or IDE screenshots

## Quick Start

### 1. Enable Image Analysis

Image analysis is enabled by default. You can customize settings in `~/.config/consoul/config.yaml`:

```yaml
tools:
  image_analysis:
    enabled: true
    auto_detect_in_messages: true  # Detect image paths in messages
    max_images_per_query: 5
    max_image_size_mb: 5.0
    allowed_extensions: [".png", ".jpg", ".jpeg", ".gif", ".webp"]
```

### 2. Use a Vision-Capable Model

Configure a model that supports vision in your profile:

```yaml
active_profile: vision

profiles:
  vision:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
```

**Vision-Capable Models:**

| Provider | Recommended Models |
|----------|-------------------|
| Anthropic | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307` |
| OpenAI | `gpt-4o`, `gpt-4o-mini` |
| Google | `gemini-2.0-flash`, `gemini-1.5-pro` |
| Ollama | `llava:latest`, `bakllava:latest` |

### 3. Analyze Images in the TUI

There are two ways to include images in your messages:

**Method 1: Attach files using the 📎 button**

1. Click the 📎 attachment button in the input area
2. Select one or more image files
3. Type your question
4. Press Enter

**Method 2: Reference image paths in your message**

Simply type the image path in your message:

```
Explain the error in screenshot.png
```

Consoul will automatically detect the image path and include it in your message.

## Usage Examples

### Debugging Terminal Errors

```
> What's wrong in this error? terminal_error.png

[The AI will analyze the screenshot and explain the error]
```

### UI/UX Review

```
> Is this interface accessible? Review ui_mockup.png and suggest improvements.

[The AI analyzes the design for accessibility issues]
```

### Comparing Designs

```
> Compare design_v1.png and design_v2.png. Which is better for mobile users?

[The AI compares both designs and provides recommendations]
```

### Code Review from Screenshot

```
> What does this function do? code_screenshot.png

[The AI reads the code from the screenshot and explains it]
```

### Diagram Analysis

```
> Explain this architecture diagram: system_architecture.png

[The AI interprets the diagram and explains the system design]
```

## Supported Image Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PNG | `.png` | Best for screenshots, diagrams |
| JPEG | `.jpg`, `.jpeg` | Good for photos, compressed images |
| GIF | `.gif` | Supported (static only) |
| WebP | `.webp` | Modern format, smaller file sizes |

**File Size Limits:**

- Default maximum: 5 MB per image
- Configurable via `max_image_size_mb`
- Total limit: 5 images per query (configurable via `max_images_per_query`)

## Security & Privacy

### What Data is Sent?

When you analyze an image:
1. The image file is read from your local filesystem
2. Encoded as base64
3. Sent to your configured AI provider's API
4. Processed by the vision model
5. Response returned to you

**Important:** Images are sent to external AI provider APIs (Anthropic, OpenAI, Google, etc.).

### Security Features

**Path Blocking:**
Sensitive directories are blocked by default:

```yaml
tools:
  image_analysis:
    blocked_paths:
      - "~/.ssh"
      - "/etc"
      - "~/.aws"
      - "~/.config/consoul"  # Prevent leaking API keys
```

**File Validation:**

- Extension checking (prevent non-images)
- Magic byte validation (prevent extension spoofing)
- Size limits (prevent large uploads)
- Path traversal prevention (block `../` attacks)

### Privacy Best Practices

1. **Review before sending** - Check which files you're attaching
2. **Redact sensitive info** - Edit screenshots to remove passwords, tokens
3. **Use local models** - Consider Ollama with `llava` for fully local processing
4. **Check provider policies** - Review data retention policies for Claude, OpenAI, etc.

## Configuration Reference

### ImageAnalysisToolConfig

Full configuration options:

```yaml
tools:
  image_analysis:
    # Enable/disable the feature
    enabled: true

    # Automatically detect image paths in messages (e.g., "analyze screenshot.png")
    auto_detect_in_messages: true

    # Maximum file size per image (MB)
    max_image_size_mb: 5.0

    # Maximum number of images per query
    max_images_per_query: 5

    # Allowed file extensions
    allowed_extensions:
      - ".png"
      - ".jpg"
      - ".jpeg"
      - ".gif"
      - ".webp"

    # Blocked paths (security)
    blocked_paths:
      - "~/.ssh"
      - "/etc"
      - "~/.aws"
      - "~/.config/consoul"
      - "/System"  # macOS system files
      - "/Windows"  # Windows system files
```

### Provider-Specific Considerations

**Anthropic (Claude):**

- Best for detailed analysis and reasoning
- Supports up to 5 images per request
- Max image size: 5 MB (base64 encoded)

**OpenAI (GPT-4o):**

- Fast processing
- Good for general image understanding
- Supports multiple images

**Google (Gemini):**

- Strong for technical diagrams
- Supports large context windows
- Native image understanding

**Ollama (LLaVA):**

- Fully local, no data sent to cloud
- Requires more VRAM (8GB+)
- Slower than cloud models

## Troubleshooting

### "Model doesn't support vision"

**Problem:** Your current model doesn't have vision capabilities.

**Solution:** Switch to a vision-capable model:

```bash
# Using CLI
consoul --profile vision

# Or update config.yaml
active_profile: vision
```

Supported models:
- Claude: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- OpenAI: `gpt-4o`, `gpt-4o-mini`
- Google: `gemini-2.0-flash`, `gemini-1.5-pro`
- Ollama: `llava:latest`

### "File too large"

**Problem:** Image exceeds `max_image_size_mb` limit.

**Solutions:**
1. Compress the image using tools like ImageOptim, TinyPNG
2. Resize to a smaller resolution
3. Increase the limit in config (max 20 MB):

```yaml
tools:
  image_analysis:
    max_image_size_mb: 10.0
```

### "Invalid file extension"

**Problem:** File type not in `allowed_extensions`.

**Solution:** Ensure the file has a valid image extension:
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

If you have an unusual format, convert it:

```bash
# Convert WebP to PNG
ffmpeg -i image.webp image.png

# Convert HEIC to JPG (macOS)
sips -s format jpeg image.heic --out image.jpg
```

### "Blocked path"

**Problem:** Image is in a security-blocked directory.

**Solution:**
1. Copy the image to a safe location
2. Or remove the path from `blocked_paths` (not recommended for sensitive dirs)

### Images not detected automatically

**Problem:** Typing `screenshot.png` doesn't attach the image.

**Solutions:**
1. Enable auto-detection:
   ```yaml
   tools:
     image_analysis:
       auto_detect_in_messages: true
   ```

2. Use absolute or relative paths:
   ```
   ./screenshot.png
   ~/Desktop/screenshot.png
   /Users/you/Documents/screenshot.png
   ```

3. Use the 📎 attachment button instead

### "Image analysis failed"

**Problem:** Generic error during analysis.

**Debugging steps:**
1. Check the file exists: `ls -la screenshot.png`
2. Verify it's a valid image: `file screenshot.png`
3. Check file size: `du -h screenshot.png`
4. Check permissions: Ensure the file is readable
5. Try a different image format
6. Check logs for detailed error:
   ```bash
   tail -f ~/.local/state/consoul/logs/consoul.log
   ```

## Advanced Usage

### Batch Image Analysis

Analyze multiple images in one query:

```
Compare these UI states: login_before.png login_after.png homepage.png
```

Or using the attachment button:
1. Click 📎
2. Select multiple files (Cmd/Ctrl + Click)
3. Ask your question

### Mixing Images and Code

Attach images alongside code files:

```
Review the implementation in main.py compared to the mockup in design.png
```

### Custom File Size Limits

For high-resolution diagrams:

```yaml
tools:
  image_analysis:
    max_image_size_mb: 20.0  # Increase for large technical diagrams
    max_images_per_query: 3  # Reduce count to stay under API limits
```

### Programmatic Usage

Use image analysis in Python scripts:

```python
from consoul.sdk import Consoul

# Initialize with vision-capable model
consoul = Consoul(model="claude-3-5-sonnet-20241022")

# Analyze an image
response = consoul.chat(
    "What error is shown in this screenshot?",
    image_paths=["terminal_error.png"]
)

print(response)
```

See [docs/examples/image-analysis-example.py](../examples/image-analysis-example.py) for more examples.

## Best Practices

### 1. Use Descriptive Queries

❌ Bad: "What's this?"
✅ Good: "Analyze this error screenshot and suggest a fix"

### 2. Provide Context

❌ Bad: "Is this good?"
✅ Good: "Review this dashboard mockup for a healthcare app. Is it accessible?"

### 3. Use High-Quality Images

- Clear screenshots (avoid blurry photos of screens)
- Sufficient resolution (at least 800x600)
- Good contrast (readable text)

### 4. Organize by Use Case

Create dedicated directories:

```
~/screenshots/
  ├── errors/
  ├── designs/
  └── diagrams/
```

### 5. Combine with Other Tools

Image analysis works great with file editing:

```
1. Analyze design.png
2. Extract design requirements
3. Use file editing to implement the UI
```

## Examples by Use Case

### Software Development

**Debug Terminal Output:**
```
Analyze this pytest error: test_failure.png
```

**Code Review:**
```
Review the code quality in this screenshot: code_review.png
```

**Architecture Understanding:**
```
Explain this system diagram: architecture.png
```

### Design & UX

**Accessibility Audit:**
```
Check this interface for WCAG 2.1 compliance: login_screen.png
```

**Design Comparison:**
```
Compare these two button styles and recommend the best one: button_a.png button_b.png
```

**Responsive Design:**
```
Does this layout work well for mobile? mobile_view.png
```

### Documentation

**Diagram Documentation:**
```
Generate markdown documentation for this flowchart: user_flow.png
```

**Screenshot Annotation:**
```
Describe each numbered element in this annotated screenshot: ui_guide.png
```

## Related Documentation

- [Getting Started](getting-started.md) - Initial setup and configuration
- [Configuration Guide](configuration.md) - Detailed config options
- [File Editing](file-editing.md) - Combine vision with file operations
- [Tools Overview](../tools.md) - All available tools
- [SDK Tool Calling](../sdk/tool-calling-integration.md) - Programmatic usage

## FAQs

**Q: Does image analysis work offline?**
A: Only with local models like Ollama's LLaVA. Cloud providers (Claude, GPT-4o, Gemini) require internet.

**Q: Can I analyze videos?**
A: Not directly. Extract frames as images first using ffmpeg.

**Q: Are images cached or stored?**
A: No. Images are read, encoded, sent to the API, then discarded. Consoul doesn't cache images.

**Q: What about image generation (DALL-E, Midjourney)?**
A: Not currently supported. This feature is for analyzing existing images only.

**Q: Can I use custom vision models?**
A: Yes, if they're compatible with LangChain's multimodal message format. See the SDK documentation.

**Q: Is there a cost for image analysis?**
A: Cloud providers may charge more for vision API calls. Check pricing:
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [OpenAI Pricing](https://openai.com/pricing)
- [Google AI Pricing](https://ai.google.dev/pricing)

**Q: Can I disable image analysis?**
A: Yes, set `tools.image_analysis.enabled: false` in your config.

## See Also

**Other Tools:**

- [Code Search](code-search.md) - Find code referenced in images
- [File Editing](file-editing.md) - Fix issues discovered visually

**SDK & API:**

- [SDK Tools Overview](../api/tools.md) - Using image analysis programmatically
- [Tool Configuration](../sdk-tools.md) - Configuring vision tools in your code

**Configuration:**

- [Configuration Guide](configuration.md) - Enable/disable image analysis
- [Vision-Capable Models](configuration.md#models) - Supported AI models

## Feedback & Support

Having issues? Found a bug?

- 📖 [Documentation](https://github.com/goatbytes/consoul/tree/main/docs)
- 🐛 [Report Issues](https://github.com/goatbytes/consoul/issues)
- 💬 [Discussions](https://github.com/goatbytes/consoul/discussions)
