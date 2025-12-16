#!/usr/bin/env python3
"""Comprehensive HuggingFace diagnostics - run directly (not via timeout)."""


def test1_basic_imports():
    """Test 1: Basic imports."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Imports")
    print("=" * 60)

    try:
        import torch

        print(f"✓ PyTorch {torch.__version__}")
        print(f"  MPS available: {torch.backends.mps.is_available()}")
    except Exception as e:
        print(f"✗ PyTorch: {e}")
        return False

    try:
        import transformers

        print(f"✓ Transformers {transformers.__version__}")
    except Exception as e:
        print(f"✗ Transformers: {e}")
        return False

    try:
        print("✓ LangChain-HuggingFace")
    except Exception as e:
        print(f"✗ LangChain-HuggingFace: {e}")
        return False

    return True


def test2_direct_transformers():
    """Test 2: Direct transformers usage (no LangChain)."""
    print("\n" + "=" * 60)
    print("TEST 2: Direct Transformers (No LangChain)")
    print("=" * 60)

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Loading gpt2 tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        print("✓ Tokenizer loaded")

        print("Loading gpt2 model...")
        model = AutoModelForCausalLM.from_pretrained("gpt2")
        print("✓ Model loaded")

        print("Generating text...")
        inputs = tokenizer("Hello!", return_tensors="pt")
        outputs = model.generate(
            **inputs, max_new_tokens=10, pad_token_id=tokenizer.eos_token_id
        )
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print(f"✓ Generated: {result}")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test3_langchain_pipeline():
    """Test 3: LangChain HuggingFacePipeline."""
    print("\n" + "=" * 60)
    print("TEST 3: LangChain HuggingFacePipeline")
    print("=" * 60)

    try:
        print("Creating HuggingFacePipeline...")
        from langchain_huggingface import HuggingFacePipeline

        # NOTE: This is where it hangs in previous tests
        llm = HuggingFacePipeline.from_model_id(
            model_id="gpt2",
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": 10},
        )

        print("✓ Pipeline created")

        print("Testing invoke...")
        result = llm.invoke("Hello!")
        print(f"✓ Result: {result}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test4_chat_wrapper():
    """Test 4: ChatHuggingFace wrapper."""
    print("\n" + "=" * 60)
    print("TEST 4: ChatHuggingFace Wrapper")
    print("=" * 60)

    try:
        from langchain_core.messages import HumanMessage
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

        print("Creating pipeline...")
        llm = HuggingFacePipeline.from_model_id(
            model_id="gpt2",
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": 10},
        )

        print("Wrapping in ChatHuggingFace...")
        chat = ChatHuggingFace(llm=llm)

        print("Testing chat...")
        messages = [HumanMessage(content="Hi")]
        response = chat.invoke(messages)

        print(f"✓ Response: {response.content}")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test5_consoul_integration():
    """Test 5: Full Consoul integration."""
    print("\n" + "=" * 60)
    print("TEST 5: Consoul Integration")
    print("=" * 60)

    try:
        from langchain_core.messages import HumanMessage

        from consoul.ai.providers import get_chat_model
        from consoul.config.models import HuggingFaceModelConfig

        print("Creating config...")
        config = HuggingFaceModelConfig(
            model="gpt2",
            local=True,
            max_tokens=10,
        )

        print("Initializing model via get_chat_model...")
        chat = get_chat_model(config)

        print("Testing chat...")
        messages = [HumanMessage(content="Hi")]
        response = chat.invoke(messages)

        print(f"✓ Response: {response.content}")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("HUGGINGFACE COMPREHENSIVE DIAGNOSTIC")
    print("=" * 60)
    print("\nNOTE: Some tests may take time to load models.")
    print("      Be patient and wait for output...")

    results = {}

    results["imports"] = test1_basic_imports()

    if results["imports"]:
        results["transformers"] = test2_direct_transformers()
    else:
        print("\nSkipping remaining tests due to import failures")
        return

    if results["transformers"]:
        results["langchain_pipeline"] = test3_langchain_pipeline()
    else:
        print("\nSkipping LangChain tests due to transformers failure")
        return

    if results["langchain_pipeline"]:
        results["chat_wrapper"] = test4_chat_wrapper()
        results["consoul"] = test5_consoul_integration()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test:20s}: {status}")

    print("=" * 60)


if __name__ == "__main__":
    main()
