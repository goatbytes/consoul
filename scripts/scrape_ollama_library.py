"""Scrape Ollama Library - Extract comprehensive model details from ollama.com.

This script scrapes all available models from ollama.com and outputs detailed
JSON data including descriptions, tags, pull counts, and metadata.

Features:
- Scrapes library and community models
- Extracts model details from individual model pages
- Includes tags, quantization info, parameter counts
- Outputs structured JSON for use in model discovery
- Progress tracking for long-running scrapes

Usage:
    python scripts/scrape_ollama_library.py
    python scripts/scrape_ollama_library.py --output ollama_models.json
    python scripts/scrape_ollama_library.py --namespace library --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup


@dataclass
class OllamaModelTag:
    """Represents a specific tagged version of an Ollama model."""

    name: str  # e.g., "latest", "7b", "13b-q4_0"
    size: str = ""  # e.g., "4.1 GB"
    quantization: str = ""  # e.g., "Q4_0", "Q8_0", "fp16"
    parameters: str = ""  # e.g., "7B", "13B", "70B"
    updated: str = ""  # Last update timestamp


@dataclass
class OllamaModelDetails:
    """Comprehensive details for an Ollama model."""

    # Basic info
    name: str  # e.g., "llama3.2"
    full_name: str  # e.g., "Meta Llama 3.2"
    description: str
    url: str  # ollama.com URL

    # Metadata
    num_pulls: str = ""  # e.g., "100M+"
    num_tags: str = ""  # Number of available tags
    updated: str = ""  # Last update timestamp
    license: str = ""  # e.g., "Llama 3.2 Community License"

    # Tags (versions)
    tags: list[OllamaModelTag] = field(default_factory=list)

    # Capabilities
    supports_vision: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False

    # Additional metadata
    context_length: str = ""  # e.g., "128K", "8K"
    family: str = ""  # e.g., "llama", "mistral", "gemma"
    readme: str = ""  # Full README/description from model page


def scrape_library_page(
    namespace: str = "library",
    category: Literal["popular", "featured", "newest"] | None = None,
    timeout: int = 10,
) -> list[dict[str, str]]:
    """Scrape the Ollama library page for model listings.

    Args:
        namespace: Namespace to scrape (library or custom)
        category: Optional category filter (popular, featured, newest)
        timeout: Request timeout in seconds

    Returns:
        List of basic model info dicts with name, url, description, etc.
    """
    url_base = f"https://ollama.com/{namespace}"
    url = f"{url_base}?sort={category}" if category else url_base

    print(f"📥 Fetching library page: {url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OllamaLibraryScraper/1.0)"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")

        models = []
        # Find all model cards (adjust selector based on actual HTML structure)
        for card in soup.select("li"):
            # Extract model name from link
            link = card.find("a")
            if not link or not link.get("href"):
                continue

            href = link.get("href", "")
            if not href.startswith(f"/{namespace}/"):
                continue

            model_name = href.replace(f"/{namespace}/", "").split("/")[0]
            if not model_name:
                continue

            # Extract description
            desc_elem = card.find("p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extract metadata (pulls, tags, updated)
            metadata = {}
            for span in card.find_all("span"):
                text = span.get_text(strip=True)
                # Parse metadata like "100M pulls", "5 tags", "Updated 2 days ago"
                if "pull" in text.lower():
                    metadata["num_pulls"] = text.split()[0]
                elif "tag" in text.lower():
                    metadata["num_tags"] = text.split()[0]
                elif "updated" in text.lower():
                    metadata["updated"] = text

            models.append(
                {
                    "name": model_name,
                    "description": description,
                    "url": f"https://ollama.com/{namespace}/{model_name}",
                    "model_url": f"{url_base}/{model_name}",
                    **metadata,
                }
            )

        print(f"✅ Found {len(models)} models on library page")
        return models

    except requests.RequestException as e:
        print(f"❌ Failed to fetch library page: {e}")
        return []


def scrape_model_details(
    model_name: str,
    namespace: str = "library",
    timeout: int = 10,
) -> OllamaModelDetails | None:
    """Scrape detailed information for a specific model.

    Args:
        model_name: Name of the model (e.g., "llama3.2")
        namespace: Namespace (library or custom)
        timeout: Request timeout in seconds

    Returns:
        OllamaModelDetails object or None if scraping failed
    """
    url = f"https://ollama.com/{namespace}/{model_name}"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OllamaLibraryScraper/1.0)"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")

        # Extract full name (usually in h1 or title)
        title_elem = soup.find("h1")
        full_name = title_elem.get_text(strip=True) if title_elem else model_name

        # Extract description (usually in meta description or first paragraph)
        description = ""
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc.get("content", "")
        else:
            # Fallback to first paragraph
            first_p = soup.find("p")
            if first_p:
                description = first_p.get_text(strip=True)

        # Extract tags/versions
        tags = []
        tag_section = soup.find("select", {"id": "tags"}) or soup.find(
            "div", class_="tags"
        )
        if tag_section:
            for option in (
                tag_section.find_all("option")
                if tag_section.name == "select"
                else tag_section.find_all("div")
            ):
                tag_name = option.get("value", "") or option.get_text(strip=True)
                if tag_name:
                    # Try to extract size/quantization info
                    tag_text = option.get_text(strip=True)
                    size = ""
                    quant = ""
                    params = ""

                    # Parse tag text like "7b-q4_0 (4.1 GB)"
                    if "GB" in tag_text or "MB" in tag_text:
                        parts = tag_text.split("(")
                        if len(parts) > 1:
                            size = parts[1].replace(")", "").strip()

                    # Detect quantization
                    tag_lower = tag_name.lower()
                    if "q4" in tag_lower:
                        quant = "Q4_0"
                    elif "q8" in tag_lower:
                        quant = "Q8_0"
                    elif "fp16" in tag_lower:
                        quant = "FP16"

                    # Detect parameters
                    if "70b" in tag_lower:
                        params = "70B"
                    elif "13b" in tag_lower:
                        params = "13B"
                    elif "7b" in tag_lower:
                        params = "7B"
                    elif "3b" in tag_lower:
                        params = "3B"
                    elif "1b" in tag_lower:
                        params = "1B"

                    tags.append(
                        OllamaModelTag(
                            name=tag_name,
                            size=size,
                            quantization=quant,
                            parameters=params,
                        )
                    )

        # Extract README/documentation
        readme = ""
        readme_section = soup.find("div", class_="readme") or soup.find("article")
        if readme_section:
            readme = readme_section.get_text(strip=True)[:1000]  # First 1000 chars

        # Extract capability badges from HTML
        # Ollama.com shows badges like: <span class="...text-indigo-600...">vision</span>
        capability_badges = soup.find_all(
            "span", class_=lambda x: x and "text-indigo-600" in x
        )
        badge_texts = [
            badge.get_text(strip=True).lower() for badge in capability_badges
        ]

        supports_vision = "vision" in badge_texts
        supports_tools = "tools" in badge_texts
        supports_reasoning = "thinking" in badge_texts

        # Fallback: Detect from description/readme if no badges found
        if not (supports_vision or supports_tools or supports_reasoning):
            combined_text = f"{description} {readme}".lower()
            supports_vision = any(
                kw in combined_text
                for kw in ["vision", "image", "multimodal", "visual"]
            )
            supports_tools = any(
                kw in combined_text for kw in ["function calling", "tool use", "tools"]
            )
            supports_reasoning = any(
                kw in combined_text
                for kw in ["reasoning", "thinking", "chain-of-thought"]
            )

        # Extract metadata
        num_pulls = ""
        num_tags = str(len(tags)) if tags else ""
        updated = ""
        license_text = ""

        # Look for metadata in various places
        for meta in soup.find_all("span"):
            text = meta.get_text(strip=True)
            if "pull" in text.lower():
                num_pulls = text.split()[0]
            elif "updated" in text.lower():
                updated = text

        # Look for license
        license_elem = soup.find("a", href=lambda h: h and "license" in h.lower())
        if license_elem:
            license_text = license_elem.get_text(strip=True)

        return OllamaModelDetails(
            name=model_name,
            full_name=full_name,
            description=description,
            url=url,
            num_pulls=num_pulls,
            num_tags=num_tags,
            updated=updated,
            license=license_text,
            tags=tags,
            supports_vision=supports_vision,
            supports_tools=supports_tools,
            supports_reasoning=supports_reasoning,
            readme=readme,
        )

    except requests.RequestException as e:
        print(f"❌ Failed to scrape {model_name}: {e}")
        return None


def scrape_all_models(
    namespace: str = "library",
    limit: int | None = None,
    delay: float = 1.0,
    detailed: bool = True,
) -> list[OllamaModelDetails]:
    """Scrape all models from Ollama library with full details.

    Args:
        namespace: Namespace to scrape (library or custom)
        limit: Maximum number of models to scrape (None for all)
        delay: Delay between requests in seconds (be nice to servers!)
        detailed: If True, scrape individual model pages for full details

    Returns:
        List of OllamaModelDetails objects
    """
    # Get initial listing
    basic_models = scrape_library_page(namespace=namespace)

    if limit:
        basic_models = basic_models[:limit]

    if not detailed:
        # Convert basic models to OllamaModelDetails
        return [
            OllamaModelDetails(
                name=m["name"],
                full_name=m["name"],
                description=m.get("description", ""),
                url=m.get("url", ""),
                num_pulls=m.get("num_pulls", ""),
                num_tags=m.get("num_tags", ""),
                updated=m.get("updated", ""),
            )
            for m in basic_models
        ]

    # Scrape detailed info for each model
    detailed_models = []
    total = len(basic_models)

    print(f"\n🔍 Scraping detailed info for {total} models...")
    print("⏱️  This may take a while. Be patient!\n")

    for i, basic_model in enumerate(basic_models, 1):
        model_name = basic_model["name"]
        print(f"[{i}/{total}] Scraping {model_name}...", end=" ")

        details = scrape_model_details(model_name, namespace=namespace)
        if details:
            # Merge basic info with detailed info
            if not details.num_pulls:
                details.num_pulls = basic_model.get("num_pulls", "")
            if not details.updated:
                details.updated = basic_model.get("updated", "")

            detailed_models.append(details)
            print("✅")
        else:
            print("❌")

        # Be nice to the server
        if i < total:
            time.sleep(delay)

    print(f"\n✅ Successfully scraped {len(detailed_models)}/{total} models")
    return detailed_models


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape Ollama library and output comprehensive model data as JSON"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="ollama_library_full.json",
        help="Output JSON file path (default: ollama_library_full.json)",
    )
    parser.add_argument(
        "--namespace",
        "-n",
        type=str,
        default="library",
        help="Namespace to scrape (default: library)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        help="Limit number of models to scrape (default: all)",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Only scrape basic info (faster, less detail)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    print("🚀 Ollama Library Scraper\n")
    print(f"📂 Namespace: {args.namespace}")
    print(f"📊 Limit: {args.limit or 'all'}")
    print(f"⏱️  Delay: {args.delay}s")
    print(f"📝 Detail level: {'basic' if args.basic else 'full'}")
    print()

    # Scrape models
    models = scrape_all_models(
        namespace=args.namespace,
        limit=args.limit,
        delay=args.delay,
        detailed=not args.basic,
    )

    if not models:
        print("❌ No models found!")
        sys.exit(1)

    # Convert to JSON-serializable format
    models_data = [asdict(model) for model in models]

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        if args.pretty:
            json.dump(models_data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(models_data, f, ensure_ascii=False)

    print(f"\n✅ Wrote {len(models)} models to {output_path}")

    # Print summary
    print("\n📊 Summary:")
    print(f"  Total models: {len(models)}")
    print(f"  With vision: {sum(1 for m in models if m.supports_vision)}")
    print(f"  With tools: {sum(1 for m in models if m.supports_tools)}")
    print(f"  With reasoning: {sum(1 for m in models if m.supports_reasoning)}")
    total_tags = sum(len(m.tags) for m in models)
    print(f"  Total tags: {total_tags}")
    print()

    # Show first few models
    print("🔍 Sample models:")
    for model in models[:5]:
        print(f"  • {model.name}: {model.description[:80]}...")


if __name__ == "__main__":
    main()
