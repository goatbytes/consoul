"""Ollama Library - Discover and browse models from ollama.com."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup


@dataclass
class OllamaLibraryModel:
    """Represents a model from the Ollama library."""

    name: str
    description: str
    model_url: str
    url: str
    num_pulls: str = ""
    num_tags: str = ""
    updated: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class OllamaLibraryData:
    """Container for library models with cache metadata."""

    models: list[OllamaLibraryModel]
    last_update: datetime


def get_cache_dir() -> Path:
    """Get the cache directory path."""
    cache_dir = Path.home() / ".consoul" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def fetch_library_models(
    namespace: str = "library",
    category: Literal["popular", "featured", "newest"] | None = None,
    force_refresh: bool = False,
    timeout: int = 10,
) -> list[OllamaLibraryModel]:
    """
    Fetch available models from ollama.com.

    Args:
        namespace: The namespace to fetch models from (default: "library")
        category: Optional category filter ("popular", "featured", "newest")
        force_refresh: Force refresh even if cache is valid
        timeout: Request timeout in seconds

    Returns:
        List of OllamaLibraryModel objects

    Raises:
        requests.RequestException: If the request fails
    """
    # Sanitize namespace
    if not namespace:
        namespace = "library"
    namespace = os.path.basename(namespace)

    # Check cache first
    cache_file = get_cache_dir() / f"ollama_library_{namespace}.json"
    if not force_refresh and cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            cache_data = OllamaLibraryData(
                models=[OllamaLibraryModel(**m) for m in data["models"]],
                last_update=datetime.fromisoformat(data["last_update"]),
            )
            # Check if cache is less than 24 hours old
            age = datetime.now(timezone.utc) - cache_data.last_update.replace(
                tzinfo=timezone.utc
            )
            if age.total_seconds() < 86400:  # 24 hours
                return cache_data.models
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid cache, will refresh
            pass

    # Fetch from ollama.com
    url_base = f"https://ollama.com/{namespace}"
    categories = [category] if category else ["popular", "featured", "newest"]
    models: list[OllamaLibraryModel] = []
    seen_names: set[str] = set()

    for cat in categories:
        url = url_base
        if namespace == "models":
            url += f"?sort={cat}"

        response = requests.get(
            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")

        for card in soup.find_all("li", class_="items-baseline"):
            # Extract basic info
            h2 = card.find("h2")
            p = card.find("p")
            a = card.find("a")

            if not h2 or not p or not a:
                continue

            name = h2.text.strip()
            if name in seen_names:
                continue
            seen_names.add(name)

            meta_data = {
                "name": name,
                "description": p.text.strip(),
                "model_url": a["href"],
                "url": f"{url}{a['href']}",
                "num_pulls": "",
                "num_tags": "",
                "updated": "",
                "tags": [],
            }

            # Extract metadata spans
            spans = card.find_all(
                "span", class_=["flex", "items-center"], recursive=True
            )
            span_texts = [s.text.strip() for s in spans if s.text.strip()]

            for text in span_texts:
                if "Pulls" in text:
                    meta_data["num_pulls"] = text.split("\n")[0].strip()
                elif "Tags" in text:
                    meta_data["num_tags"] = text.split("\xa0")[0].strip()
                elif "Updated" in text:
                    meta_data["updated"] = text.split("\xa0")[-1].strip()

            # Extract tags
            tag_spans = card.find_all("span", class_=["text-blue-600"], recursive=True)
            tags = [t.text.strip() for t in tag_spans if t.text.strip()]
            meta_data["tags"] = tags

            models.append(OllamaLibraryModel(**meta_data))

        # For library namespace, only fetch once (not per category)
        if namespace != "models":
            break

    # Save to cache
    if models:
        cache_data = OllamaLibraryData(
            models=models, last_update=datetime.now(timezone.utc)
        )
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "models": [
                        {
                            "name": m.name,
                            "description": m.description,
                            "model_url": m.model_url,
                            "url": m.url,
                            "num_pulls": m.num_pulls,
                            "num_tags": m.num_tags,
                            "updated": m.updated,
                            "tags": m.tags,
                        }
                        for m in cache_data.models
                    ],
                    "last_update": cache_data.last_update.isoformat(),
                },
                f,
                indent=2,
            )

    return models
