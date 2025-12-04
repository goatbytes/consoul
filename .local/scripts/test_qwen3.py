#!/usr/bin/env python3
"""Test local HuggingFace execution with Qwen3-8B (complete model)."""

import sys


def test_qwen3_transformers_direct():
    """Test 1: Direct transformers usage."""
    print("\n" + "=" * 80)
    print("TEST 1: Direct Transformers - Qwen3-8B")
    print("=" * 80)

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_name = "Qwen/Qwen3-8B"

        print(f"Loading tokenizer for {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        print("✓ Tokenizer loaded")

        print(f"Loading model for {model_name}...")
        print("  (This may take 30-60 seconds for a 15GB model...)")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",  # Automatically use best device (MPS/CPU)
            low_cpu_mem_usage=True,  # Optimize memory
        )
        print("✓ Model loaded successfully!")

        print("\nGenerating text...")
        prompt = "Hello! What is AI?"
        inputs = tokenizer(prompt, return_tensors="pt")
        if hasattr(inputs, "to") and hasattr(model, "device"):
            inputs = inputs.to(model.device)

        outputs = model.generate(
            **inputs, max_new_tokens=50, pad_token_id=tokenizer.eos_token_id
        )
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print(f"\nPrompt: {prompt}")
        print(f"Response: {result}")
        print("\n✅ TEST 1 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qwen3_langchain():
    """Test 2: LangChain HuggingFacePipeline."""
    print("\n" + "=" * 80)
    print("TEST 2: LangChain HuggingFacePipeline - Qwen3-8B")
    print("=" * 80)

    try:
        from langchain_huggingface import HuggingFacePipeline

        model_name = "Qwen/Qwen3-8B"

        print(f"Creating HuggingFacePipeline for {model_name}...")
        print("  (This may take 30-60 seconds...)")

        llm = HuggingFacePipeline.from_model_id(
            model_id=model_name,
            task="text-generation",
            device_map="auto",
            pipeline_kwargs={
                "max_new_tokens": 50,
                "temperature": 0.7,
            },
            model_kwargs={
                "low_cpu_mem_usage": True,
            },
        )

        print("✓ Pipeline created!")

        print("\nTesting generation...")
        prompt = "What are the three laws of robotics?"
        result = llm.invoke(prompt)

        print(f"\nPrompt: {prompt}")
        print(f"Response: {result}")
        print("\n✅ TEST 2 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qwen3_chat_wrapper():
    """Test 3: ChatHuggingFace wrapper."""
    print("\n" + "=" * 80)
    print("TEST 3: ChatHuggingFace Wrapper - Qwen3-8B")
    print("=" * 80)

    try:
        from langchain_core.messages import HumanMessage
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

        model_name = "Qwen/Qwen3-8B"

        print(f"Creating pipeline for {model_name}...")
        print("  (This may take 30-60 seconds...)")

        llm = HuggingFacePipeline.from_model_id(
            model_id=model_name,
            task="text-generation",
            device_map="auto",
            pipeline_kwargs={"max_new_tokens": 50},
            model_kwargs={"low_cpu_mem_usage": True},
        )

        print("✓ Pipeline created!")

        print("Wrapping in ChatHuggingFace...")
        chat = ChatHuggingFace(llm=llm)
        print("✓ Chat wrapper created!")

        print("\nTesting chat...")
        messages = [HumanMessage(content="Hi! Tell me a fun fact about Python.")]
        response = chat.invoke(messages)

        print(f"\nPrompt: {messages[0].content}")
        print(f"Response: {response.content}")
        print("\n✅ TEST 3 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qwen3_consoul():
    """Test 4: Full Consoul integration."""
    print("\n" + "=" * 80)
    print("TEST 4: Consoul Integration - Qwen3-8B")
    print("=" * 80)

    try:
        from langchain_core.messages import HumanMessage

        from consoul.ai.providers import get_chat_model
        from consoul.config.models import HuggingFaceModelConfig

        model_name = "Qwen/Qwen3-8B"

        print(f"Creating HuggingFaceModelConfig for {model_name}...")
        config = HuggingFaceModelConfig(
            model=model_name,
            local=True,
            max_tokens=50,
            temperature=0.7,
        )
        print(f"✓ Config created: local={config.local}")

        print("\nInitializing via get_chat_model()...")
        print("  (This may take 30-60 seconds...)")

        chat = get_chat_model(config)
        print("✓ Chat model initialized!")

        print("\nTesting chat...")
        messages = [HumanMessage(content="What is the capital of France?")]
        response = chat.invoke(messages)

        print(f"\nPrompt: {messages[0].content}")
        print(f"Response: {response.content}")
        print("\n✅ TEST 4 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("QWEN3-8B LOCAL EXECUTION TEST")
    print("=" * 80)
    print("\nNOTE: Each test loads a 15GB model and may take 30-60 seconds.")
    print("      Be patient and wait for output...")
    print("      Press Ctrl+C to cancel if needed.")

    results = {}

    # Test 1: Direct transformers (most basic test)
    results["transformers_direct"] = test_qwen3_transformers_direct()

    if not results["transformers_direct"]:
        print("\n⚠️  Skipping remaining tests due to transformers failure")
        print("=" * 80)
        sys.exit(1)

    # Test 2: LangChain pipeline
    results["langchain_pipeline"] = test_qwen3_langchain()

    # Test 3: Chat wrapper
    if results["langchain_pipeline"]:
        results["chat_wrapper"] = test_qwen3_chat_wrapper()

    # Test 4: Consoul integration
    if results.get("chat_wrapper", False):
        results["consoul_integration"] = test_qwen3_consoul()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test:25s}: {status}")

    all_passed = all(results.values())
    print("=" * 80)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nLocal HuggingFace execution works correctly with complete models!")
        print("The previous segfaults were due to incomplete model downloads.")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("See error details above.")

    print("=" * 80)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
        sys.exit(130)
