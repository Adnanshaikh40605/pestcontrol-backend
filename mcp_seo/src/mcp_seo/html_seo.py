"""Parse HTML into SEO-relevant fields."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def _meta_content(soup: BeautifulSoup, *, name: str | None = None, prop: str | None = None) -> str | None:
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _abs(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def parse_json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            items.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                items.extend(x for x in data["@graph"] if isinstance(x, dict))
            else:
                items.append(data)
    return items


def extract_text_content(soup: BeautifulSoup, *, max_chars: int = 8000) -> str:
    clone = BeautifulSoup(str(soup), "lxml")
    for tag in clone(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", clone.get_text(" ", strip=True)).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def parse_page(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    description = _meta_content(soup, name="description")
    robots = _meta_content(soup, name="robots")
    viewport = _meta_content(soup, name="viewport")
    canonical_tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in str(v).lower()})
    canonical = canonical_tag.get("href").strip() if canonical_tag and canonical_tag.get("href") else None
    if canonical:
        canonical = _abs(page_url, canonical)

    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]

    base_host = (urlparse(page_url).hostname or "").lower()
    internal_links: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = _abs(page_url, href)
        parsed = urlparse(abs_url)
        if (parsed.hostname or "").lower() != base_host:
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)
        internal_links.append({
            "url": abs_url,
            "text": a.get_text(" ", strip=True)[:200],
        })

    images: list[dict[str, Any]] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        alt = img.get("alt")
        images.append({
            "src": _abs(page_url, str(src)),
            "alt": None if alt is None else str(alt),
            "missing_alt": alt is None or str(alt).strip() == "",
        })

    json_ld = parse_json_ld(soup)
    return {
        "url": page_url,
        "title": title,
        "description": description,
        "canonical_url": canonical,
        "robots": robots,
        "viewport": viewport,
        "h1": h1,
        "h2": h2,
        "og_title": _meta_content(soup, prop="og:title"),
        "og_description": _meta_content(soup, prop="og:description"),
        "og_url": _meta_content(soup, prop="og:url"),
        "twitter_card": _meta_content(soup, name="twitter:card"),
        "internal_links": internal_links,
        "images": images,
        "structured_data": json_ld,
        "text_excerpt": extract_text_content(soup),
    }


def parse_sitemap_urls(xml_text: str) -> list[str]:
    soup = BeautifulSoup(xml_text, "lxml-xml")
    urls: list[str] = []
    for loc in soup.find_all("loc"):
        value = loc.get_text(strip=True)
        if value:
            urls.append(value)
    return urls


def schema_types(item: dict[str, Any]) -> list[str]:
    raw = item.get("@type")
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if raw is None:
        return []
    return [str(raw)]


def filter_structured_data(items: list[dict[str, Any]], type_name: str) -> list[dict[str, Any]]:
    wanted = type_name.lower()
    return [item for item in items if any(t.lower() == wanted for t in schema_types(item))]


def validate_schema(item: dict[str, Any], type_name: str) -> dict[str, Any]:
    required_by_type = {
        "Organization": ["name", "url"],
        "LocalBusiness": ["name", "address"],
        "Service": ["name", "provider"],
        "Product": ["name"],
        "BreadcrumbList": ["itemListElement"],
        "FAQPage": ["mainEntity"],
    }
    required = required_by_type.get(type_name, ["name"])
    present = [field for field in required if item.get(field) not in (None, "", [], {})]
    missing = [field for field in required if field not in present]
    return {
        "type": type_name,
        "present_fields": present,
        "missing_fields": missing,
        "is_valid": len(missing) == 0,
        "item": item,
    }
