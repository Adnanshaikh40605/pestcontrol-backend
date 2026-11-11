"""Read-only SEO operations used by MCP tools and resources."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from mcp_seo.config import SiteConfig, Settings, get_settings
from mcp_seo.html_seo import (
    filter_structured_data,
    parse_page,
    parse_sitemap_urls,
    validate_schema,
)
from mcp_seo.http_client import (
    HttpSafetyError,
    fetch_json,
    fetch_text,
    resolve_api_url,
    resolve_site_url,
)
from mcp_seo.sites import deepcleaning as deep_site
from mcp_seo.sites import pestcontrol as pest_site


def _paginate(items: list[Any], page: int = 1, page_size: int = 20, max_size: int = 50) -> dict[str, Any]:
    page = max(1, int(page or 1))
    page_size = min(max_size, max(1, int(page_size or 20)))
    start = (page - 1) * page_size
    end = start + page_size
    slice_items = items[start:end]
    return {
        "page": page,
        "page_size": page_size,
        "total": len(items),
        "results": slice_items,
    }


def _classify(site: SiteConfig, url: str) -> str:
    if site.key == "pestcontrol":
        return pest_site.classify_url(url, site)
    return deep_site.classify_url(url, site)


def _contact(site: SiteConfig) -> dict[str, Any]:
    if site.key == "pestcontrol":
        return pest_site.PUBLIC_CONTACT
    return deep_site.PUBLIC_CONTACT


class SeoService:
    def __init__(self, site_key: str, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.site = self.settings.site(site_key)

    async def _get_page(self, path_or_url: str = "/") -> dict[str, Any]:
        url = resolve_site_url(self.site, path_or_url)
        result = await fetch_text(
            url,
            site=self.site,
            settings=self.settings,
            cache_ttl=self.settings.page_cache_ttl,
        )
        parsed = parse_page(result["text"], result["url"])
        return {
            "http_status": result["status_code"],
            "content_type": result["content_type"],
            "last_modified": result["last_modified"],
            **parsed,
        }

    async def get_website_info(self) -> dict[str, Any]:
        home = await self._get_page("/")
        return {
            "site_key": self.site.key,
            "name": self.site.name,
            "base_url": self.site.site_base,
            "contact": _contact(self.site),
            "home_title": home.get("title"),
            "home_description": home.get("description"),
            "home_status": home.get("http_status"),
        }

    async def get_robots_txt(self) -> dict[str, Any]:
        url = self.site.absolute("/robots.txt")
        result = await fetch_text(
            url,
            site=self.site,
            settings=self.settings,
            cache_ttl=self.settings.robots_cache_ttl,
        )
        return {
            "url": result["url"],
            "status_code": result["status_code"],
            "content": result["text"],
        }

    async def get_sitemap(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        url = self.site.absolute("/sitemap.xml")
        result = await fetch_text(
            url,
            site=self.site,
            settings=self.settings,
            cache_ttl=self.settings.sitemap_cache_ttl,
        )
        urls = parse_sitemap_urls(result["text"])
        paged = _paginate(urls, page=page, page_size=page_size, max_size=self.settings.max_page_size)
        return {
            "sitemap_url": result["url"],
            "status_code": result["status_code"],
            **paged,
        }

    async def list_pages(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        url = self.site.absolute("/sitemap.xml")
        result = await fetch_text(
            url,
            site=self.site,
            settings=self.settings,
            cache_ttl=self.settings.sitemap_cache_ttl,
        )
        urls = parse_sitemap_urls(result["text"])
        rows = [
            {"url": u, "path": urlparse(u).path or "/", "category": _classify(self.site, u)}
            for u in urls
        ]
        return _paginate(rows, page=page, page_size=page_size, max_size=self.settings.max_page_size)

    async def get_page_metadata(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        return {
            "url": page["url"],
            "http_status": page["http_status"],
            "title": page.get("title"),
            "description": page.get("description"),
            "canonical_url": page.get("canonical_url"),
            "robots": page.get("robots"),
            "h1": page.get("h1"),
            "h2": page.get("h2"),
            "viewport": page.get("viewport"),
            "og_title": page.get("og_title"),
            "og_description": page.get("og_description"),
            "og_url": page.get("og_url"),
            "last_modified": page.get("last_modified"),
            "structured_data_count": len(page.get("structured_data") or []),
        }

    async def get_page_title(self, path_or_url: str = "/") -> dict[str, Any]:
        meta = await self.get_page_metadata(path_or_url)
        return {"url": meta["url"], "title": meta["title"], "http_status": meta["http_status"]}

    async def get_page_description(self, path_or_url: str = "/") -> dict[str, Any]:
        meta = await self.get_page_metadata(path_or_url)
        return {
            "url": meta["url"],
            "description": meta["description"],
            "http_status": meta["http_status"],
        }

    async def get_canonical_url(self, path_or_url: str = "/") -> dict[str, Any]:
        meta = await self.get_page_metadata(path_or_url)
        return {
            "url": meta["url"],
            "canonical_url": meta["canonical_url"],
            "http_status": meta["http_status"],
        }

    async def get_page_content(self, path_or_url: str = "/", max_chars: int = 8000) -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        text = page.get("text_excerpt") or ""
        if max_chars and len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        return {
            "url": page["url"],
            "http_status": page["http_status"],
            "title": page.get("title"),
            "text": text,
        }

    async def get_internal_links(self, path_or_url: str = "/", page: int = 1, page_size: int = 50) -> dict[str, Any]:
        parsed = await self._get_page(path_or_url)
        links = parsed.get("internal_links") or []
        paged = _paginate(links, page=page, page_size=page_size, max_size=self.settings.max_page_size)
        return {"url": parsed["url"], "http_status": parsed["http_status"], **paged}

    async def check_page_status(self, path_or_url: str = "/") -> dict[str, Any]:
        url = resolve_site_url(self.site, path_or_url)
        result = await fetch_text(url, site=self.site, settings=self.settings, cache_ttl=60)
        return {
            "url": result["url"],
            "status_code": result["status_code"],
            "ok": 200 <= result["status_code"] < 400,
            "content_type": result["content_type"],
        }

    async def check_broken_links(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        links = (page.get("internal_links") or [])[: self.settings.broken_link_limit]
        broken: list[dict[str, Any]] = []
        checked: list[dict[str, Any]] = []
        for link in links:
            try:
                status = await self.check_page_status(link["url"])
                row = {"url": link["url"], "status_code": status["status_code"], "ok": status["ok"]}
                checked.append(row)
                if not status["ok"]:
                    broken.append(row)
            except HttpSafetyError as exc:
                row = {"url": link["url"], "status_code": None, "ok": False, "error": str(exc)}
                checked.append(row)
                broken.append(row)
        return {
            "url": page["url"],
            "checked": len(checked),
            "broken_count": len(broken),
            "broken": broken,
            "results": checked,
        }

    async def _sample_pages(self, limit: int = 30) -> list[dict[str, Any]]:
        sitemap = await self.get_sitemap(page=1, page_size=limit)
        pages: list[dict[str, Any]] = []
        for url in sitemap["results"]:
            try:
                pages.append(await self.get_page_metadata(url))
            except Exception as exc:  # noqa: BLE001
                pages.append({"url": url, "error": str(exc)})
        return pages

    async def check_missing_metadata(self, limit: int = 30) -> dict[str, Any]:
        pages = await self._sample_pages(limit=limit)
        missing = []
        for page in pages:
            if page.get("error"):
                missing.append(page)
                continue
            issues = []
            if not page.get("title"):
                issues.append("title")
            if not page.get("description"):
                issues.append("description")
            if not page.get("canonical_url"):
                issues.append("canonical")
            if issues:
                missing.append({"url": page["url"], "missing": issues})
        return {"scanned": len(pages), "issues": missing}

    async def check_duplicate_titles(self, limit: int = 40) -> dict[str, Any]:
        pages = await self._sample_pages(limit=limit)
        buckets: dict[str, list[str]] = {}
        for page in pages:
            title = (page.get("title") or "").strip().lower()
            if not title:
                continue
            buckets.setdefault(title, []).append(page["url"])
        dupes = [
            {"title": title, "urls": urls, "count": len(urls)}
            for title, urls in buckets.items()
            if len(urls) > 1
        ]
        return {"scanned": len(pages), "duplicates": dupes}

    async def check_duplicate_descriptions(self, limit: int = 40) -> dict[str, Any]:
        pages = await self._sample_pages(limit=limit)
        buckets: dict[str, list[str]] = {}
        for page in pages:
            desc = (page.get("description") or "").strip().lower()
            if not desc:
                continue
            buckets.setdefault(desc, []).append(page["url"])
        dupes = [
            {"description": desc, "urls": urls, "count": len(urls)}
            for desc, urls in buckets.items()
            if len(urls) > 1
        ]
        return {"scanned": len(pages), "duplicates": dupes}

    async def check_image_alt_text(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        images = page.get("images") or []
        missing = [img for img in images if img.get("missing_alt")]
        return {
            "url": page["url"],
            "image_count": len(images),
            "missing_alt_count": len(missing),
            "missing_alt": missing[:50],
        }

    async def check_canonical_tags(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self.get_page_metadata(path_or_url)
        canonical = page.get("canonical_url")
        return {
            "url": page["url"],
            "canonical_url": canonical,
            "has_canonical": bool(canonical),
            "matches_request": bool(canonical and canonical.rstrip("/") == page["url"].rstrip("/")),
        }

    async def check_robots_indexability(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self.get_page_metadata(path_or_url)
        robots = (page.get("robots") or "").lower()
        robots_txt = await self.get_robots_txt()
        path = urlparse(page["url"]).path or "/"
        disallowed = False
        for line in robots_txt["content"].splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:"):
                rule = line.split(":", 1)[1].strip()
                if rule and path.startswith(rule):
                    disallowed = True
        return {
            "url": page["url"],
            "meta_robots": page.get("robots"),
            "meta_noindex": "noindex" in robots,
            "robots_txt_disallowed": disallowed,
            "indexable": ("noindex" not in robots) and (not disallowed),
        }

    async def check_structured_data(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        items = page.get("structured_data") or []
        types: list[str] = []
        for item in items:
            raw = item.get("@type")
            if isinstance(raw, list):
                types.extend(str(x) for x in raw)
            elif raw:
                types.append(str(raw))
        return {
            "url": page["url"],
            "count": len(items),
            "types": sorted(set(types)),
            "items": items,
        }

    async def check_heading_structure(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        h1 = page.get("h1") or []
        h2 = page.get("h2") or []
        return {
            "url": page["url"],
            "h1_count": len(h1),
            "h2_count": len(h2),
            "h1": h1,
            "h2": h2,
            "has_single_h1": len(h1) == 1,
        }

    async def check_mobile_metadata(self, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        viewport = page.get("viewport")
        return {
            "url": page["url"],
            "viewport": viewport,
            "has_viewport": bool(viewport),
            "looks_mobile_friendly": bool(viewport and "width" in viewport.lower()),
        }

    async def get_schema_by_type(self, type_name: str, path_or_url: str = "/") -> dict[str, Any]:
        page = await self._get_page(path_or_url)
        items = filter_structured_data(page.get("structured_data") or [], type_name)
        validations = [validate_schema(item, type_name) for item in items]
        return {
            "url": page["url"],
            "type": type_name,
            "count": len(items),
            "items": items,
            "validation": validations,
        }

    async def _filter_sitemap(self, predicate, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        url = self.site.absolute("/sitemap.xml")
        result = await fetch_text(
            url,
            site=self.site,
            settings=self.settings,
            cache_ttl=self.settings.sitemap_cache_ttl,
        )
        urls = [u for u in parse_sitemap_urls(result["text"]) if predicate(u)]
        return _paginate(
            [{"url": u, "path": urlparse(u).path or "/", "category": _classify(self.site, u)} for u in urls],
            page=page,
            page_size=page_size,
            max_size=self.settings.max_page_size,
        )

    async def get_service_pages(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        return await self._filter_sitemap(
            lambda u: _classify(self.site, u) == "service",
            page=page,
            page_size=page_size,
        )

    async def get_location_pages(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        return await self._filter_sitemap(
            lambda u: _classify(self.site, u) == "location",
            page=page,
            page_size=page_size,
        )

    async def get_faq_content(self, path_or_url: str | None = None) -> dict[str, Any]:
        if path_or_url:
            target = path_or_url
        elif self.site.faq_paths:
            target = self.site.faq_paths[0]
        else:
            # PestControl FAQs are often embedded on service/area pages.
            target = "/"
        page = await self._get_page(target)
        faq_schema = filter_structured_data(page.get("structured_data") or [], "FAQPage")
        text = page.get("text_excerpt") or ""
        # Lightweight FAQ extraction from common patterns
        qa_pairs = []
        for match in re.finditer(r"(?:Q[:.]?\s*)?(.{10,120}\?)\s+(.{20,400})", text):
            qa_pairs.append({"question": match.group(1).strip(), "answer": match.group(2).strip()[:400]})
            if len(qa_pairs) >= 20:
                break
        return {
            "url": page["url"],
            "http_status": page["http_status"],
            "faq_schema": faq_schema,
            "extracted_qa": qa_pairs,
            "text_excerpt": text[:2000],
        }

    async def get_blog_posts(self, page: int = 1, page_size: int = 20, query: str = "") -> dict[str, Any]:
        if self.site.key == "pestcontrol":
            from urllib.parse import quote

            path = "/api/public/blogs/"
            resolve_api_url(self.settings, path)
            api_url = (
                f"{self.settings.public_api_base}{path}"
                f"?page={max(1, page)}"
                f"&page_size={min(self.settings.max_page_size, max(1, page_size))}"
            )
            if query:
                api_url += f"&search={quote(query)}"
            payload = await fetch_json(api_url, site=self.site, settings=self.settings, cache_ttl=300)
            data = payload["data"]
            if isinstance(data, dict):
                results = data.get("results") or data.get("data") or []
                total = data.get("count", len(results))
            else:
                results = data if isinstance(data, list) else []
                total = len(results)
            return {
                "source": "api",
                "page": page,
                "page_size": page_size,
                "total": total,
                "results": results,
            }
        guides = await self._filter_sitemap(
            lambda u: _classify(self.site, u) == "blog",
            page=page,
            page_size=page_size,
        )
        return {"source": "sitemap", **guides}

    async def get_blog_categories(self) -> dict[str, Any]:
        if self.site.key != "pestcontrol":
            guides = await self._filter_sitemap(lambda u: _classify(self.site, u) == "blog", page=1, page_size=50)
            return {"source": "sitemap", "categories": [{"name": "Guides", "pages": guides["results"]}]}
        api_url = f"{self.settings.public_api_base}/api/public/categories/"
        payload = await fetch_json(api_url, site=self.site, settings=self.settings, cache_ttl=300)
        return {"source": "api", "categories": payload["data"]}

    async def get_public_pricing(self) -> dict[str, Any]:
        if self.site.key == "pestcontrol":
            api_url = f"{self.settings.public_api_base}/api/customer/catalog/"
            payload = await fetch_json(api_url, site=self.site, settings=self.settings, cache_ttl=300)
            brochure = await self.get_page_metadata("/brochure/")
            return {
                "source": "api+brochure",
                "catalog": payload["data"],
                "brochure_page": brochure,
            }
        api_url = f"{self.settings.public_api_base}/api/v1/deepcleaning-rates/catalog/"
        payload = await fetch_json(api_url, site=self.site, settings=self.settings, cache_ttl=300)
        prices_page = await self.get_page_metadata("/prices/")
        return {
            "source": "api+prices_page",
            "catalog": payload["data"],
            "prices_page": prices_page,
        }

    async def get_public_business_info(self) -> dict[str, Any]:
        home = await self.check_structured_data("/")
        return {
            "contact": _contact(self.site),
            "organization_schema": filter_structured_data(home.get("items") or [], "Organization"),
            "local_business_schema": filter_structured_data(home.get("items") or [], "LocalBusiness"),
        }

    async def search_website_content(self, query: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        q = (query or "").strip().lower()
        if not q:
            raise HttpSafetyError("query is required")
        matches: list[dict[str, Any]] = []
        if self.site.key == "pestcontrol":
            blogs = await self.get_blog_posts(page=1, page_size=20, query=query)
            for item in blogs.get("results") or []:
                if isinstance(item, dict):
                    matches.append({
                        "type": "blog",
                        "title": item.get("title") or item.get("meta_title"),
                        "url": item.get("canonical_url") or item.get("slug"),
                        "excerpt": item.get("excerpt") or item.get("meta_description"),
                    })
        sitemap = await self.get_sitemap(page=1, page_size=500)
        for url in sitemap["results"]:
            path = (urlparse(url).path or "").lower()
            if q in path or q in url.lower():
                matches.append({"type": "sitemap", "url": url, "path": path})
        # Sample metadata titles for a small subset
        for url in sitemap["results"][:15]:
            try:
                meta = await self.get_page_metadata(url)
            except Exception:  # noqa: BLE001
                continue
            hay = f"{meta.get('title') or ''} {meta.get('description') or ''}".lower()
            if q in hay:
                matches.append({
                    "type": "page_meta",
                    "url": meta["url"],
                    "title": meta.get("title"),
                    "description": meta.get("description"),
                })
        # Dedupe by url
        seen = set()
        unique = []
        for row in matches:
            key = str(row.get("url"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return _paginate(unique, page=page, page_size=page_size, max_size=self.settings.max_page_size)
