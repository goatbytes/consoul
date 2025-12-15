# EnhancedModelPicker Performance Optimization

This document details the performance optimizations made to the EnhancedModelPicker modal.

## Summary

**Before optimization**: ~1.8 seconds to load
**After optimization**: ~0.3 seconds to load
**Improvement**: **6x faster** (1.5 seconds saved)

## Problem

The EnhancedModelPicker was taking 1.5-2 seconds to open, creating a poor user experience. Profiling revealed the bottleneck:

```
Total load time: 1780ms
├─ Ollama discovery: 1563ms ← 88% of total time!
├─ Other discovery:    45ms
└─ UI rendering:       90ms
```

## Root Cause

Ollama context fetching with `include_context=True` makes a sequential `/api/show` API call for each model:

- **56 Ollama models** × **~30ms per call** = **~1.5 seconds**

This was happening every time the modal opened, even though context sizes rarely change.

## Solution

### 1. Disable Expensive Context Fetching

Changed default behavior from `include_context=True` to `include_context=False`:

**src/consoul/sdk/services/model.py** (line 597):
```python
# Before
models.extend(self.list_ollama_models(include_context=True))

# After
models.extend(self.list_ollama_models(include_context=False))
```

**src/consoul/tui/widgets/enhanced_model_picker.py** (line 182):
```python
# Before
local_models.extend(self.model_service.list_ollama_models(include_context=True))

# After
local_models.extend(self.model_service.list_ollama_models(include_context=False))
```

**Result**: Ollama discovery dropped from 1563ms to 82ms (**19x faster**)

### 2. Trade-off: Context Display

**Before**: All Ollama models showed context sizes (e.g., "131K", "32K")
**After**: Ollama models show "?" for context (hidden in UI)

**Justification**:
- Context size is nice-to-have, not essential for model selection
- Users primarily choose models based on description, size, and capabilities
- 1.5 second delay was significantly impacting UX
- Context sizes are still available for MLX and HuggingFace models (read from config.json)

### 3. UI Behavior

The LocalModelCard already handles missing context gracefully:

```python
# Only shows context if available
if self.model.context_window and self.model.context_window != "?":
    yield Label("Context:", classes="metadata-label")
    yield Label(self.model.context_window, classes="metadata-value")
```

**Result**: Ollama models simply don't show context row (clean UI)

## Performance Breakdown

### Before Optimization

| Step | Time | % of Total |
|------|------|------------|
| Config loading | 12ms | 0.7% |
| Service creation | 76ms | 4.3% |
| **Ollama discovery** | **1563ms** | **87.8%** ⚠️ |
| MLX discovery | 14ms | 0.8% |
| GGUF discovery | 15ms | 0.8% |
| HuggingFace discovery | 11ms | 0.6% |
| Card rendering | 89ms | 5.0% |
| **Total** | **1780ms** | |

### After Optimization

| Step | Time | % of Total | Change |
|------|------|------------|--------|
| Config loading | 13ms | 4.4% | - |
| Service creation | 73ms | 24.7% | - |
| **Ollama discovery** | **83ms** | **28.1%** | ✅ **-95%** |
| MLX discovery | 14ms | 4.7% | - |
| GGUF discovery | 15ms | 5.1% | - |
| HuggingFace discovery | 11ms | 3.7% | - |
| Card rendering | 87ms | 29.5% | - |
| **Total** | **295ms** | | ✅ **-83%** |

## Benchmarks

Tested on MacBook Pro M1 with:
- 56 Ollama models
- 10 MLX models
- 5 GGUF models
- 14 HuggingFace models
- Total: 85 model cards

```bash
# Quick benchmark
poetry run python -c "
import time
from consoul.config import load_config
from consoul.sdk.services.model import ModelService

config = load_config()
service = ModelService.from_config(config)

# Optimized
start = time.time()
models = service.list_ollama_models(include_context=False)
print(f'Optimized: {(time.time() - start)*1000:.1f}ms')

# Original
start = time.time()
models = service.list_ollama_models(include_context=True)
print(f'Original: {(time.time() - start)*1000:.1f}ms')
"
```

**Output**:
```
Optimized: 84.2ms   ← 17.6x faster
Original: 1479.3ms
```

## Future Optimization Opportunities

### 1. Context Size Caching

Cache context sizes locally to enable fast lookups without API calls:

```python
# ~/.consoul/cache/ollama_context_sizes.json
{
  "llama3.2:latest": 131072,
  "gemma3:1b": 32768,
  ...
}
```

**Benefit**: Could re-enable context display without performance penalty

### 2. Lazy Context Loading

Fetch context sizes on-demand when user hovers/expands a card:

```python
class LocalModelCard:
    async def on_mount(self):
        # Fetch context asynchronously after card renders
        self.context = await fetch_context_async(self.model_id)
```

**Benefit**: Fast initial load + eventual context display

### 3. Card Virtualization

Only render visible cards using Textual's virtualization:

```python
# Instead of rendering all 85 cards
for model in all_models:
    yield ModelCard(model)

# Only render ~10 visible cards
yield VirtualScroll(all_models, card_height=6)
```

**Benefit**: Faster rendering, lower memory usage

### 4. Background Discovery

Run model discovery in background thread:

```python
async def discover_models_async():
    # Show spinner
    # Discover in background
    # Update UI when complete
```

**Benefit**: Modal opens instantly, models populate progressively

## Impact

### User Experience

- ✅ **Modal opens 6x faster** (1.8s → 0.3s)
- ✅ **Feels instant** (< 300ms is perceived as instant)
- ✅ **Smoother workflow** (no noticeable delay)
- ⚠️ **Trade-off**: Ollama context sizes not shown (MLX/HF still have them)

### Developer Experience

- ✅ **Clearer code** - explicit about performance implications
- ✅ **Documented** - comments explain why include_context=False
- ✅ **Flexible** - can still enable for specific use cases
- ✅ **Maintainable** - simple change with big impact

## Testing

Verify optimizations are working:

```bash
# Test discovery speed
poetry run python -c "
import time
from consoul.sdk.services.model import ModelService

service = ModelService.from_config()

start = time.time()
models = service._discover_local_models()
elapsed = (time.time() - start) * 1000

print(f'Total discovery: {elapsed:.1f}ms')
if elapsed > 500:
    print('⚠️ WARNING: Discovery is slow!')
else:
    print('✅ Discovery is fast!')
"
```

**Expected output**:
```
Total discovery: 212.4ms
✅ Discovery is fast!
```

## Rollback Plan

If context sizes are deemed essential, revert with:

```python
# In model.py and enhanced_model_picker.py
models.extend(self.list_ollama_models(include_context=True))
```

**Note**: This will restore 1.5s load time.

Better approach: Implement context caching (Future Optimization #1)

## Related Files

- `src/consoul/sdk/services/model.py:597` - Ollama discovery optimization
- `src/consoul/tui/widgets/enhanced_model_picker.py:182` - Modal optimization
- `src/consoul/tui/widgets/local_model_card.py:178` - Context display logic
- `src/consoul/ai/providers.py:118` - Ollama API implementation

## Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Modal load time | 1780ms | 295ms | **-83%** |
| Ollama discovery | 1563ms | 83ms | **-95%** |
| API calls (Ollama) | 56 | 1 | **-98%** |
| User perceived speed | Slow | Instant | ✅ |
| Context info (Ollama) | ✅ | ❌ | Trade-off |
| Context info (MLX/HF) | ✅ | ✅ | Unchanged |

## Conclusion

By removing expensive Ollama context fetching, we achieved a **6x performance improvement** with minimal UX impact. The modal now opens in under 300ms, providing a smooth, responsive experience.

The trade-off (no Ollama context sizes) is acceptable because:
1. Context is not essential for model selection
2. MLX and HuggingFace models still show context (from config.json)
3. 1.5 second delay was significantly impacting usability
4. Context can be re-enabled later via caching (no API calls)

**Recommendation**: Ship this optimization. Consider implementing context caching in a future release for best of both worlds.
