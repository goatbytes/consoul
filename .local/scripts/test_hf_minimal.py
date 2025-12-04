"""Minimal HuggingFace test - no LangChain."""

from transformers import AutoModelForCausalLM, AutoTokenizer

print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("gpt2")
model = AutoModelForCausalLM.from_pretrained("gpt2")

print("Generating text...")
inputs = tokenizer("Hello, how are you?", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=20)
result = tokenizer.decode(outputs[0])

print(f"Result: {result}")
print("SUCCESS!")
