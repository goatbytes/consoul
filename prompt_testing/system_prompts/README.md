# System Prompts

Pre-configured system prompts for customizing AI behavior in test_prompts.py.

## Available Prompts

### 🎯 concise_expert.txt
**Purpose:** Short, direct answers without fluff
**Best for:** Quick references, API documentation, fact-checking
**Response style:** 2-3 sentences, code examples when relevant

**Example usage:**
```bash
python ../test_prompts.py \
  --system-prompt-file system_prompts/concise_expert.txt \
  --preset high-value
```

---

### 👨‍🏫 beginner_friendly.txt
**Purpose:** Patient, detailed explanations for learners
**Best for:** Tutorials, teaching materials, documentation for newcomers
**Response style:** Step-by-step, analogies, detailed comments in code

**Example usage:**
```bash
python ../test_prompts.py \
  --system-prompt-file system_prompts/beginner_friendly.txt \
  --prompts-file learning_prompts.json
```

---

### 🔍 code_reviewer.txt
**Purpose:** Critical analysis focused on quality and best practices
**Best for:** Code review, optimization tasks, identifying bugs
**Response style:** Constructive criticism, improved examples, explains reasoning

**Example usage:**
```bash
python ../test_prompts.py \
  --system-prompt-file system_prompts/code_reviewer.txt \
  --preset default
```

---

### 👔 senior_engineer.txt
**Purpose:** Production-ready advice with real-world considerations
**Best for:** Architecture decisions, system design, trade-off analysis
**Response style:** Pragmatic, considers scale/maintenance, acknowledges context

**Example usage:**
```bash
python ../test_prompts.py \
  --system-prompt-file system_prompts/senior_engineer.txt \
  --model gpt-4o
```

---

### 🐍 python_expert.txt
**Purpose:** Modern, idiomatic Python code
**Best for:** Python-specific tasks, code examples, best practices
**Response style:** Type hints, comprehensions, standard library focus

**Example usage:**
```bash
python ../test_prompts.py \
  --system-prompt-file system_prompts/python_expert.txt \
  --preset high-value
```

## Creating Custom System Prompts

### Template

```txt
You are a [ROLE] with expertise in [DOMAIN].

Your approach:
- [GUIDELINE 1]
- [GUIDELINE 2]
- [GUIDELINE 3]

When responding:
- [INSTRUCTION 1]
- [INSTRUCTION 2]
- [INSTRUCTION 3]

[ADDITIONAL CONTEXT]
```

### Example: Security Expert

```txt
You are a security-focused code reviewer with expertise in application security.

Your approach:
- Identify security vulnerabilities first
- Consider OWASP Top 10 risks
- Think like an attacker

When responding:
- Point out specific security issues
- Explain the risk and potential impact
- Provide secure code examples
- Reference security best practices

Focus on practical, actionable security improvements.
```

Save as `security_expert.txt` and use:
```bash
python ../test_prompts.py --system-prompt-file system_prompts/security_expert.txt
```

## Comparison Testing

Test the same prompts with different system prompts to compare responses:

```bash
#!/bin/bash

PROMPTS="example_prompts.json"

# Test with different personalities
for style in concise_expert beginner_friendly senior_engineer; do
  python test_prompts.py \
    --prompts-file $PROMPTS \
    --system-prompt-file "system_prompts/${style}.txt" \
    --output "results/${style}"
done

# Compare results
echo "Concise responses:"
cat results/concise_expert/response_01.json | jq -r '.response' | wc -w

echo "Beginner-friendly responses:"
cat results/beginner_friendly/response_01.json | jq -r '.response' | wc -w
```

## Tips

1. **Be specific**: Clearly define the role and expectations
2. **Use examples**: Show the desired response style
3. **Keep it focused**: One clear purpose per system prompt
4. **Test iteratively**: Try your prompt with a few examples first
5. **Version control**: Track changes to see what works best

## Use Cases by Prompt Type

| System Prompt | Technical Q&A | Code Gen | Debugging | Architecture | Teaching |
|---------------|---------------|----------|-----------|--------------|----------|
| concise_expert | ✅ Best | ✅ Good | ❌ Too brief | ⚠️ OK | ❌ Too terse |
| beginner_friendly | ✅ Good | ✅ Best | ✅ Best | ⚠️ OK | ✅ Best |
| code_reviewer | ⚠️ OK | ✅ Best | ✅ Best | ✅ Good | ⚠️ OK |
| senior_engineer | ✅ Best | ✅ Good | ✅ Good | ✅ Best | ⚠️ Advanced |
| python_expert | ⚠️ Python only | ✅ Best | ✅ Good | ⚠️ OK | ✅ Good |

## Best Practices

### ✅ Good System Prompts

- Clear role definition
- Specific guidelines
- Measurable criteria
- Examples of desired behavior

### ❌ Avoid

- Vague instructions ("be helpful")
- Contradictory guidelines
- Overly complex rules
- Personal opinions as facts

## Contributing

To add a new system prompt:

1. Create a `.txt` file in this directory
2. Follow the template structure
3. Test with various prompts
4. Document in this README
5. Add example usage

## License

Apache-2.0
