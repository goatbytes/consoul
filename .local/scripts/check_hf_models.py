#!/usr/bin/env python3
"""Check HuggingFace cache for complete vs incomplete models."""

from pathlib import Path


def check_model_completeness():
    """Check which models have actual weights vs just metadata."""
    from huggingface_hub import scan_cache_dir

    cache_info = scan_cache_dir()

    print("=" * 80)
    print("HUGGINGFACE MODEL CACHE ANALYSIS")
    print("=" * 80)

    complete_models = []
    incomplete_models = []

    for repo in cache_info.repos:
        if repo.repo_type != "model":
            continue

        # Get the snapshot directory
        for revision in repo.revisions:
            snapshot_path = Path(revision.snapshot_path)

            # Check for model weight files
            has_weights = any(
                snapshot_path.glob(pattern)
                for pattern in [
                    "*.safetensors",
                    "*.bin",
                    "pytorch_model*.bin",
                    "model*.safetensors",
                ]
            )

            size_gb = repo.size_on_disk / (1024**3)

            model_info = {
                "name": repo.repo_id,
                "size_gb": size_gb,
                "size": repo.size_on_disk,
                "has_weights": has_weights,
                "nb_files": repo.nb_files,
            }

            if has_weights and size_gb > 0.01:  # > 10MB
                complete_models.append(model_info)
            else:
                incomplete_models.append(model_info)

            break  # Only check first revision

    print(f"\n✅ COMPLETE MODELS ({len(complete_models)}):")
    print("-" * 80)
    for model in sorted(complete_models, key=lambda m: m["size"], reverse=True):
        print(f"  {model['name']:<50s} {model['size_gb']:>8.1f} GB")

    print(f"\n❌ INCOMPLETE/CORRUPT MODELS ({len(incomplete_models)}):")
    print("-" * 80)
    for model in sorted(incomplete_models, key=lambda m: m["name"]):
        size_str = (
            f"{model['size_gb']:.3f} GB"
            if model["size_gb"] > 0.001
            else f"{model['size'] / 1024:.1f} KB"
        )
        print(f"  {model['name']:<50s} {size_str:>12s} (missing weights)")

    total_size = sum(m["size"] for m in complete_models + incomplete_models)
    incomplete_size = sum(m["size"] for m in incomplete_models)

    print("\n" + "=" * 80)
    print(f"Total cache size: {total_size / (1024**3):.1f} GB")
    print(f"Wasted space (incomplete): {incomplete_size / (1024**2):.1f} MB")
    print("=" * 80)

    if incomplete_models:
        print("\nRECOMMENDATION:")
        print("Delete incomplete models to save space:")
        print("\n  huggingface-cli delete-cache")
        print("\nOr manually remove specific models:")
        for model in incomplete_models:
            print(f"  huggingface-cli delete-cache --repos {model['name']}")


if __name__ == "__main__":
    check_model_completeness()
