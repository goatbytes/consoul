# Tokenizer Discovery Strategy for Ollama Models

## Current Approach: Static Mapping

**Pros:**
- Fast (no I/O)
- Reliable (verified mappings)
- Works offline
- No subprocess overhead

**Cons:**
- Requires manual updates
- Doesn't handle custom models
- Limited to mapped models

## Proposed Enhancement: Hybrid Approach

### Tier 1: Static Mapping (Primary)
```python
HUGGINGFACE_MODEL_MAP = {
    "granite4:3b": "ibm-granite/granite-4.0-micro",
    # ... 27+ verified mappings
}
```
**Use for:** Common models (95% of usage)

### Tier 2: Manifest Discovery (Fallback)
```python
def discover_tokenizer_from_manifest(model_name: str) -> str | None:
    """
    Read Ollama manifest to find source HuggingFace model.

    Ollama stores manifests at:
    ~/.ollama/models/manifests/registry.ollama.ai/library/{model}/latest
    """
    import json
    from pathlib import Path

    manifest_path = (
        Path.home() / ".ollama" / "models" / "manifests"
        / "registry.ollama.ai" / "library" / model_name.split(":")[0] / "latest"
    )

    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Look for source info in manifest annotations
        for layer in manifest.get("layers", []):
            annotations = layer.get("annotations", {})

            # Check for HF source
            if "org.opencontainers.image.source" in annotations:
                source = annotations["org.opencontainers.image.source"]
                if "huggingface.co" in source:
                    # Extract model ID from URL
                    # https://huggingface.co/ibm-granite/granite-4.0-micro
                    parts = source.rstrip("/").split("/")
                    return f"{parts[-2]}/{parts[-1]}"

    except Exception as e:
        logger.debug(f"Could not parse manifest for {model_name}: {e}")

    return None
```

### Tier 3: GGUF Metadata (Future)
```python
def extract_tokenizer_from_gguf(model_name: str) -> str | None:
    """
    Extract tokenizer metadata from GGUF blob.

    Requires: gguf-py library
    """
    # TODO: Implement if needed for custom models
    # This would parse the GGUF header to find tokenizer type
    pass
```

### Tier 4: Character Approximation (Ultimate Fallback)
```python
# Existing fallback - always works
return _create_approximate_counter()
```

## Recommended Implementation

```python
def _create_huggingface_counter(model_name: str) -> Callable:
    """Create HF tokenizer with multi-tier discovery."""

    # Tier 1: Check static mapping (fast path)
    hf_model_id = HUGGINGFACE_MODEL_MAP.get(model_name)

    # Tier 2: Try manifest discovery
    if not hf_model_id:
        hf_model_id = discover_tokenizer_from_manifest(model_name)

    # Tier 3: Try GGUF parsing (future)
    # if not hf_model_id:
    #     hf_model_id = extract_tokenizer_from_gguf(model_name)

    if not hf_model_id:
        raise ValueError(f"Model {model_name} not found")

    try:
        from consoul.ai.tokenizers import HuggingFaceTokenCounter
        counter = HuggingFaceTokenCounter(model_name, hf_model_id)
        return counter.count_tokens
    except Exception as e:
        logger.warning(f"HF tokenizer failed for {model_name}: {e}")
        raise
```

## Why Not Go Fully Automatic?

### Performance
- Static mapping: 0ms overhead
- Manifest parsing: ~5-10ms overhead
- GGUF parsing: ~50-100ms overhead + dependencies

### Reliability
- Static mapping: 100% reliable (tested)
- Manifest parsing: ~90% reliable (Ollama may not include source)
- GGUF parsing: Complex, model-dependent

### Dependencies
- Static mapping: None
- Manifest parsing: None (uses stdlib)
- GGUF parsing: Requires `gguf-py` (~50MB)

## Recommendation

**Phase 1 (Now):** Keep static mapping
- Covers 95% of use cases
- Zero overhead
- Battle-tested

**Phase 2 (Future):** Add manifest discovery
- Handles custom models
- Minimal overhead
- No new dependencies

**Phase 3 (Optional):** Add GGUF parsing
- Only if users request it
- Requires new dependency

## Testing Strategy

```python
def test_tokenizer_discovery():
    """Test discovery tiers in order."""

    # Common model - should use static mapping
    assert get_hf_model_id("granite4:3b") == "ibm-granite/granite-4.0-micro"

    # Custom model - should use manifest discovery
    # (requires test setup with custom Ollama model)

    # Unmapped model - should raise ValueError
    with pytest.raises(ValueError):
        get_hf_model_id("unknown-model:1b")
```

## Conclusion

**Best approach:** Hybrid strategy with static mapping as primary, dynamic discovery as fallback.

This balances:
- ✅ Performance (fast path for common models)
- ✅ Coverage (handles custom models)
- ✅ Reliability (tested mappings)
- ✅ Maintainability (clear fallback chain)
