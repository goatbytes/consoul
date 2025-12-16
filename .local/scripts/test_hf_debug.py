#!/usr/bin/env python3
"""Debug test to find where HuggingFace initialization hangs."""

import sys

print("Step 1: Testing HuggingFacePipeline import...", flush=True)
try:
    from langchain_huggingface import HuggingFacePipeline

    print("✓ HuggingFacePipeline imported", flush=True)
except Exception as e:
    print(f"✗ Import failed: {e}", flush=True)
    sys.exit(1)

print("\nStep 2: Testing direct HuggingFacePipeline creation...", flush=True)
try:
    print("   Creating pipeline with gpt2...", flush=True)

    pipeline_params = {
        "model_id": "gpt2",
        "task": "text-generation",
        "pipeline_kwargs": {
            "max_new_tokens": 50,
            "temperature": 0.7,
        },
    }

    print(f"   Pipeline params: {pipeline_params}", flush=True)
    print("   Calling HuggingFacePipeline.from_model_id()...", flush=True)

    llm = HuggingFacePipeline.from_model_id(**pipeline_params)

    print(f"✓ Pipeline created: {type(llm).__name__}", flush=True)

except Exception as e:
    print(f"✗ Pipeline creation failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Testing ChatHuggingFace wrapper...", flush=True)
try:
    from langchain_huggingface import ChatHuggingFace

    print("   Wrapping pipeline in ChatHuggingFace...", flush=True)
    chat_model = ChatHuggingFace(llm=llm)

    print(f"✓ Chat model created: {type(chat_model).__name__}", flush=True)

except Exception as e:
    print(f"✗ Chat wrapper failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Testing chat interaction...", flush=True)
try:
    from langchain_core.messages import HumanMessage

    messages = [HumanMessage(content="Hi")]
    print("   Invoking chat model...", flush=True)

    response = chat_model.invoke(messages)

    print(f"✓ Response: {response.content}", flush=True)
    print("\n✅ ALL TESTS PASSED!", flush=True)

except Exception as e:
    print(f"✗ Chat failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)
