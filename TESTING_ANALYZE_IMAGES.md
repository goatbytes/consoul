# Testing the analyze_images Tool

This guide shows you how to test the newly implemented `analyze_images` tool locally.

## Quick Start

### Option 1: Automated Demo Script

Run the comprehensive demo that tests all features:

```bash
python3 test_analyze_images_demo.py
```

This will run 9 different test scenarios:
1. ✅ Single PNG image analysis
2. ✅ Multiple images (PNG, JPG, WebP)
3. ✅ Error handling - Non-existent file
4. ✅ Error handling - Too many images
5. ✅ Security - Blocked path
6. ✅ Security - Path traversal
7. ✅ Validation - Invalid extension
8. ✅ Custom configuration
9. ✅ Base64 encoding verification

### Option 2: Interactive Testing

Test with your own images interactively:

```bash
python3 test_analyze_images_interactive.py
```

Or pass image paths directly:

```bash
python3 test_analyze_images_interactive.py tests/fixtures/test_image.png
```

Multiple images:

```bash
python3 test_analyze_images_interactive.py \
    tests/fixtures/test_image.png \
    tests/fixtures/test_photo.jpg \
    tests/fixtures/test_diagram.webp
```

### Option 3: Unit Tests

Run the comprehensive test suite (38 tests):

```bash
# Run all tests
python3 -m pytest tests/ai/tools/implementations/test_analyze_images.py -v

# Run specific test class
python3 -m pytest tests/ai/tools/implementations/test_analyze_images.py::TestAnalyzeImagesTool -v

# Run with coverage
python3 -m pytest tests/ai/tools/implementations/test_analyze_images.py --cov=src/consoul/ai/tools/implementations/analyze_images
```

## Python API Usage

```python
from consoul.ai.tools.implementations.analyze_images import (
    analyze_images,
    set_analyze_images_config,
)
from consoul.config.models import ImageAnalysisToolConfig

# Set up configuration
config = ImageAnalysisToolConfig(
    max_image_size_mb=5,
    max_images_per_query=5,
    allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
)
set_analyze_images_config(config)

# Analyze a single image
result = analyze_images.invoke({
    "query": "What's in this image?",
    "image_paths": ["path/to/image.png"]
})

# Parse the JSON result
import json
data = json.loads(result)

print(f"Query: {data['query']}")
print(f"Images: {len(data['images'])}")
for img in data['images']:
    print(f"  - {img['path']}: {img['mime_type']}")
    print(f"    Base64 data length: {len(img['data'])}")
```

## Configuration Options

```python
config = ImageAnalysisToolConfig(
    enabled=True,                    # Enable/disable the tool
    max_image_size_mb=5,             # Max file size per image (1-20 MB)
    max_images_per_query=5,          # Max images per request (1-10)
    allowed_extensions=[             # Allowed file types
        ".png", ".jpg", ".jpeg",
        ".gif", ".webp", ".bmp"
    ],
    blocked_paths=[                  # Security: blocked directories
        "/etc", "/proc", "/dev", "/sys",
        "~/.ssh", "~/.aws", "~/.config"
    ]
)
```

## Security Features

The tool includes robust security validation:

1. **Path Traversal Protection**: Blocks `..` in paths
2. **Blocked Paths**: Prevents access to sensitive directories
3. **Extension Validation**: Only allows image file extensions
4. **Magic Byte Verification**: Uses PIL to verify actual file type
5. **Size Limits**: Prevents uploading huge files
6. **Query Limits**: Restricts number of images per request

## Test Fixtures

Small test images are available in `tests/fixtures/`:
- `test_image.png` - 287 bytes, 100x100 blue square
- `test_photo.jpg` - 825 bytes, 100x100 red square
- `test_diagram.webp` - 102 bytes, 100x100 green square

## Output Format

The tool returns JSON with this structure:

```json
{
  "query": "What's in this image?",
  "images": [
    {
      "path": "/full/path/to/image.png",
      "data": "iVBORw0KGgoAAAANSUhEUgAA...",  // Base64 encoded
      "mime_type": "image/png"
    }
  ]
}
```

## Next Steps

After SOUL-113 (✅ Complete), the following tickets will add full vision support:

1. **SOUL-114**: Multimodal message formatting
   - Anthropic Claude format: Content blocks with base64 image sources
   - OpenAI GPT-4V format: HumanMessage with image_url data URIs
   - Google Gemini format: Content array with image objects
   - **Ollama qwen3-vl** format: LangChain Ollama multimodal support

2. **SOUL-115**: ToolRegistry integration
   - Auto-registration for vision-capable models
   - RiskLevel.CAUTION approval workflow
   - Audit logging for image analysis

3. **SOUL-118**: Vision capability detection
   - Detect Claude 3+, GPT-4V, Gemini 2.0
   - **Detect Ollama qwen3-vl, llava, bakllava**
   - Auto-enable/disable based on model

## Ollama qwen3-vl Support

Your system has **qwen3-vl:latest** (6.1 GB) installed! ✅

This will be fully supported in SOUL-114 when implementing the Ollama multimodal message formatting. The qwen3-vl model is a powerful vision-language model that will work seamlessly with this tool.

## Troubleshooting

### Import Error
```bash
# Make sure you're in the project root
cd /Users/jaredrummler/Development/github/goatbytes/consoul

# Install dependencies if needed
poetry install
```

### PIL/Pillow Not Found
Magic byte validation will be skipped if PIL is not available. Install with:
```bash
pip install Pillow
# or
poetry add Pillow
```

### Test Fixtures Missing
Generate test images:
```python
from PIL import Image
img = Image.new('RGB', (100, 100), color='blue')
img.save('tests/fixtures/test_image.png')
```

## Questions?

- **Implementation**: `src/consoul/ai/tools/implementations/analyze_images.py`
- **Tests**: `tests/ai/tools/implementations/test_analyze_images.py`
- **Config**: `src/consoul/config/models.py` (ImageAnalysisToolConfig)
- **Gira Ticket**: SOUL-113 (✅ Done)
