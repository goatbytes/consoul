# Performance Testing Scripts

This directory contains several standalone scripts for measuring Consoul's streaming performance and identifying bottlenecks.

## Available Scripts

### 1. `test_ollama_streaming.py` - Minimal Baseline

Tests raw Ollama streaming performance without any Consoul overhead.

**Usage:**
```bash
python test_ollama_streaming.py [model_name]
python test_ollama_streaming.py granite4:1b
```

**Measures:**
- Time to first token
- Total duration
- Token chunks received
- Tokens per second
- Response length

### 2. `compare_streaming_performance.py` - Consoul vs Baseline

Compares minimal Ollama streaming against Consoul's full stack.

**Usage:**
```bash
python compare_streaming_performance.py [model_name]
python compare_streaming_performance.py granite4:1b
```

**Compares:**
- Minimal Ollama (baseline)
- Consoul Stack (with ConversationHistory, token counting, context management)
- Calculates overhead percentage for each metric
- Includes warmup runs to ensure fair comparison

### 3. `compare_tools_performance.py` - Tool Call Overhead

Measures the overhead of tool calling infrastructure.

**Usage:**
```bash
python compare_tools_performance.py [model_name]
python compare_tools_performance.py qwen2.5-coder:7b
```

**Compares:**
- No tools (baseline)
- Tools available but not called (binding overhead)
- Tools called and executed (full overhead)

**Example Results:**
```
┌─────────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Metric                      │ No Tools     │ Tools Avail  │ Tools Called │
├─────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Time to first token         │    0.114s    │    0.181s    │    0.444s    │
│ Total duration              │    0.738s    │    0.767s    │    0.700s    │
│ Tokens/second               │    65.07     │    57.39     │     5.71     │
│ Tool calls made             │        0     │        0     │        2     │
└─────────────────────────────┴──────────────┴──────────────┴──────────────┘

Tools Available Overhead: +3.9%
  ✓ Tool binding has minimal overhead (<5%)
```

### 4. `compare_consoul_overhead.py` - Comprehensive Overhead Analysis

Layer-by-layer analysis of Consoul's overhead.

**Usage:**
```bash
python compare_consoul_overhead.py [model_name]
python compare_consoul_overhead.py granite4:1b
```

**Layers Tested:**
1. **Minimal Baseline** - Direct ChatOllama streaming
2. **+ ConversationHistory** - Message management (no DB, no token counting)
3. **+ Database** - SQLite persistence
4. **+ Token Counting** - tiktoken/transformers token counting

**Example Results:**
```
┌─────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Metric              │ Baseline │ +History │  +DB     │ +Tokens  │ Overhead │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ TTFT                │  0.075s  │  0.112s  │  0.110s  │  0.109s  │   46.5%  │
│ Stream duration     │  0.582s  │  0.619s  │  0.630s  │  0.626s  │    8.3%  │
│ Token count time    │      N/A │      N/A │      N/A │  0.000s  │      N/A │
│ Tokens/sec          │  67.06   │  62.98   │  61.89   │  62.33   │      N/A │
└─────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

OVERHEAD BREAKDOWN:
  1. ConversationHistory overhead: +6.5% (+0.038s)
  2. Database persistence overhead: +1.8% (+0.011s)
  3. Token counting time: 0.000s (happens after streaming)
  4. Total overhead: +8.3% (+0.049s)
```

## Key Findings

### Streaming Performance
- **Consoul overhead: ~8%** - Moderate but acceptable for the features provided
- **Token counting: <100ms** - Fast and doesn't affect perceived responsiveness
- **Database persistence: ~2%** - Minimal overhead

### Tool Infrastructure
- **Tool binding overhead: ~4%** - Very minimal when tools are available but not called
- **Time to first token increases** when tools are bound (model needs to process tool schemas)

### Optimization Opportunities

1. **Time to First Token (TTFT)** shows the most overhead (~46%)
   - This is likely due to ConversationHistory initialization and message formatting
   - Consider lazy initialization or caching

2. **Streaming Duration** overhead is minimal (~8%)
   - Most overhead comes from ConversationHistory message management (~6.5%)
   - Database persistence adds minimal overhead (~1.8%)

3. **Token Counting** happens after streaming
   - Currently very fast (<100ms)
   - Uses transformers tokenizer for granite models
   - Could be optimized further with caching

## Usage Notes

- All scripts use `temperature=0.0` in comprehensive tests for consistent results
- Scripts include warmup runs to load models into memory
- Use `2>/dev/null` to suppress stderr output (tokenizer downloads, etc.)
- Results may vary based on system performance and model size

## Testing Recommendations

1. **For general performance testing**: Use `compare_consoul_overhead.py`
2. **For tool-heavy workloads**: Use `compare_tools_performance.py`
3. **For baseline establishment**: Use `test_ollama_streaming.py`
4. **For quick checks**: Use `compare_streaming_performance.py`

## Example Workflow

```bash
# 1. Test minimal baseline
python test_ollama_streaming.py granite4:1b

# 2. Run comprehensive overhead analysis
python compare_consoul_overhead.py granite4:1b 2>/dev/null

# 3. Test tool overhead (if using tools)
python compare_tools_performance.py qwen2.5-coder:7b 2>/dev/null
```

## Interpreting Results

### Overhead Thresholds
- **<5%**: Minimal overhead ✓
- **5-15%**: Moderate overhead ⚠
- **>15%**: Significant overhead ✗

### What's Acceptable?
- Streaming overhead <10% is excellent
- Token counting <200ms is good
- TTFT overhead <100ms is ideal

### Red Flags
- Streaming overhead >20%
- Token counting >500ms
- TTFT >1s for small models
