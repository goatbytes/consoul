# Updating Model Pricing Data

This guide shows how to keep `src/consoul/pricing.py` up-to-date with official provider pricing.

## Why Update Pricing?

- Provider pricing changes regularly
- LangChain's pricing data can be outdated
- Accurate cost estimates are critical for users

## Quick Update Methods

### Method 1: Copy Page Feature (Recommended)

1. Visit the official pricing page:
   - OpenAI: https://openai.com/api/pricing/
   - Anthropic: https://docs.anthropic.com/en/docs/about-claude/pricing
   - Google: https://ai.google.dev/gemini-api/docs/pricing

2. Use browser's "Copy page" feature or copy the pricing table

3. Save to a markdown file (e.g., `openai_pricing.md`)

4. Run the script:
   ```bash
   python scripts/update_pricing.py --from-markdown openai_pricing.md --format python
   ```

5. Copy the output into `src/consoul/pricing.py`

### Method 2: Interactive Paste

```bash
# Start interactive mode
python scripts/update_pricing.py --provider openai --format python

# Paste the pricing table markdown
# Press Ctrl+D when done

# Output will be formatted Python dict ready to paste
```

### Method 3: Manual Scraping

For providers with complex pricing or anti-bot protection:

1. Manually copy pricing data from official page
2. Format as markdown table:
   ```markdown
   | Model | Input | Output |
   |-------|-------|--------|
   | gpt-4o | $5.00 / 1M tokens | $20.00 / 1M tokens |
   | gpt-4o-mini | $0.15 / 1M tokens | $0.60 / 1M tokens |
   ```

3. Save to file and use Method 1

## Example: Update OpenAI Pricing

```bash
# 1. Visit https://openai.com/api/pricing/
# 2. Select pricing table, copy
# 3. Save to openai_pricing.md
# 4. Run script

$ python scripts/update_pricing.py --from-markdown openai_pricing.md --format python

# OpenAI pricing (updated 2024-11-29)
OPENAI_PRICING = {
    "gpt-4o": {
        "input": 5.00,  # $5.00 per MTok
        "output": 20.00,  # $20.00 per MTok
    },
    "gpt-4o-mini": {
        "input": 0.15,  # $0.15 per MTok
        "output": 0.60,  # $0.60 per MTok
    },
    # ... more models
}

# Found 4 openai models
#   - gpt-4o
#   - gpt-4o-mini
#   - o1
#   - o1-mini
```

## Verifying Updates

After updating pricing, always:

1. **Run unit tests:**
   ```bash
   pytest tests/unit/test_pricing.py -v
   ```

2. **Test with real API call:**
   ```python
   from consoul import Consoul

   console = Consoul(model="gpt-4o-mini")
   console.chat("Hello")
   cost = console.last_cost

   # Verify pricing matches official rates
   # For 1M input + 500K output tokens:
   # Expected: (1M * $0.15) + (500K * $0.60) = $0.45
   ```

3. **Compare with LangChain:**
   ```python
   from consoul.pricing import calculate_cost
   from langchain_community.callbacks.openai_info import get_openai_token_cost_for_model, TokenType

   # Our pricing
   ours = calculate_cost("gpt-4o", 1_000_000, 500_000)

   # LangChain pricing (if available)
   langchain_input = get_openai_token_cost_for_model("gpt-4o", 1_000_000, token_type=TokenType.PROMPT)
   langchain_output = get_openai_token_cost_for_model("gpt-4o", 500_000, token_type=TokenType.COMPLETION)

   print(f"Consoul: ${ours['total_cost']:.2f}")
   print(f"LangChain: ${langchain_input + langchain_output:.2f}")
   ```

## Update Frequency

Recommended update schedule:

- **Monthly**: Check all providers for pricing changes
- **After major releases**: When providers announce new models
- **When users report discrepancies**: If cost estimates seem wrong

## Adding New Providers

To add a new provider:

1. Create parser function in `update_pricing.py`:
   ```python
   def parse_newprovider_markdown(markdown: str) -> dict[str, dict[str, float]]:
       # Parse markdown format specific to provider
       pass
   ```

2. Add to provider choices and logic

3. Update `src/consoul/pricing.py` with new dict

4. Add tests in `tests/unit/test_pricing.py`

## Common Issues

### Issue: Script finds no models
**Solution**: Check markdown format. Provider may use different table structure.

### Issue: Prices seem wrong
**Solution**: Verify units - some providers show per 1K tokens, others per 1M tokens.

### Issue: Missing cache pricing
**Solution**: Some providers don't expose cache pricing publicly. Use 50% of input cost as estimate.

## Resources

- OpenAI Pricing: https://openai.com/api/pricing/
- Anthropic Pricing: https://docs.anthropic.com/en/docs/about-claude/pricing
- Google Gemini Pricing: https://ai.google.dev/gemini-api/docs/pricing
- LangChain Pricing Data: https://github.com/langchain-ai/langchain/blob/master/libs/community/langchain_community/callbacks/openai_info.py
