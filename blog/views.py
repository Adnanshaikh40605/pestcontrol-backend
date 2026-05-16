import logging
import uuid

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db.models import Sum, Q, F
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Blog, Category, Tag, BlogStatus
from .serializers import (
    BlogAdminSerializer,
    BlogAdminListSerializer,
    BlogPublicSerializer,
    BlogPublicListSerializer,
    CategorySerializer,
    TagSerializer,
    ImageUploadSerializer,
)
from .utils import convert_to_webp

logger = logging.getLogger(__name__)

BLOG_CACHE_TTL = 300       # 5 minutes for public endpoints
DASHBOARD_CACHE_TTL = 120  # 2 minutes for dashboard stats


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class BlogPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


# ---------------------------------------------------------------------------
# Admin Throttle (limit view-tracking abuse)
# ---------------------------------------------------------------------------

class ViewTrackThrottle(AnonRateThrottle):
    rate = "60/hour"
    scope = "blog_view_track"


# ===========================================================================
# ADMIN / CRM APIs  (require authentication)
# ===========================================================================

class BlogDashboardView(APIView):
    """GET /api/blogs/dashboard-stats/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "blog_dashboard_stats"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = Blog.objects.all()
        total_views = qs.aggregate(tv=Sum("views_count"))["tv"] or 0
        top_blogs = (
            Blog.objects.filter(status=BlogStatus.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
            .order_by("-views_count")[:5]
        )

        data = {
            "total_blogs": qs.count(),
            "published": qs.filter(status=BlogStatus.PUBLISHED).count(),
            "drafts": qs.filter(status=BlogStatus.DRAFT).count(),
            "total_views": total_views,
            "top_blogs": BlogPublicListSerializer(top_blogs, many=True, context={"request": request}).data,
        }
        cache.set(cache_key, data, DASHBOARD_CACHE_TTL)
        return Response(data)


class BlogListAdminView(APIView):
    """GET /api/blogs/ — CRM admin blog list with search/filter/pagination"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Blog.objects
            .select_related("category", "author")
            .prefetch_related("tags")
        )

        # Filters
        blog_status = request.query_params.get("status")
        if blog_status in (BlogStatus.DRAFT, BlogStatus.PUBLISHED):
            qs = qs.filter(status=blog_status)

        category_slug = request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        tag_slug = request.query_params.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)

        # Search
        search = request.query_params.get("search") or request.query_params.get("q")
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(excerpt__icontains=search)
                | Q(meta_description__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        allowed_orderings = {
            "created_at", "-created_at",
            "publish_date", "-publish_date",
            "views_count", "-views_count",
            "title", "-title",
        }
        if ordering not in allowed_orderings:
            ordering = "-created_at"
        qs = qs.order_by(ordering)

        paginator = BlogPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BlogAdminListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class BlogCreateView(APIView):
    """POST /api/blogs/create/"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = BlogAdminSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            blog = serializer.save(author=request.user)
            cache.delete("blog_dashboard_stats")
            _invalidate_public_cache()
            return Response(
                BlogAdminSerializer(blog, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BlogDetailAdminView(APIView):
    """GET/PUT/PATCH /api/blogs/{id}/"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_blog(self, pk):
        try:
            return Blog.objects.select_related("category", "author").prefetch_related("tags").get(pk=pk)
        except Blog.DoesNotExist:
            raise NotFound(detail="Blog not found.")

    def get(self, request, pk):
        blog = self._get_blog(pk)
        return Response(BlogAdminSerializer(blog, context={"request": request}).data)

    def put(self, request, pk):
        blog = self._get_blog(pk)
        serializer = BlogAdminSerializer(blog, data=request.data, context={"request": request})
        if serializer.is_valid():
            blog = serializer.save()
            cache.delete("blog_dashboard_stats")
            _invalidate_public_cache(blog.slug)
            return Response(BlogAdminSerializer(blog, context={"request": request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        blog = self._get_blog(pk)
        serializer = BlogAdminSerializer(blog, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            blog = serializer.save()
            cache.delete("blog_dashboard_stats")
            _invalidate_public_cache(blog.slug)
            return Response(BlogAdminSerializer(blog, context={"request": request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BlogDeleteView(APIView):
    """DELETE /api/blogs/{id}/delete/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            raise NotFound(detail="Blog not found.")
        slug = blog.slug
        blog.delete()
        cache.delete("blog_dashboard_stats")
        _invalidate_public_cache(slug)
        return Response({"message": "Blog deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class BlogPublishToggleView(APIView):
    """PATCH /api/blogs/{id}/toggle-publish/"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            raise NotFound(detail="Blog not found.")

        if blog.status == BlogStatus.PUBLISHED:
            blog.status = BlogStatus.DRAFT
        else:
            blog.status = BlogStatus.PUBLISHED
            if not blog.publish_date:
                blog.publish_date = timezone.now()

        blog.save(update_fields=["status", "publish_date"])
        cache.delete("blog_dashboard_stats")
        _invalidate_public_cache(blog.slug)
        return Response({"status": blog.status, "publish_date": blog.publish_date})


class ImageUploadView(APIView):
    """POST /api/blogs/upload-image/ — Upload a standalone image for the rich editor."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data["image"]
        alt_text = serializer.validated_data.get("alt_text", "")
        title = serializer.validated_data.get("title", "")

        try:
            webp_buffer = convert_to_webp(image_file, quality=88)
            filename = f"{uuid.uuid4().hex}.webp"
            content = ContentFile(webp_buffer.read(), name=filename)

            from django.core.files.storage import default_storage

            from .storage import storage_url

            path = f"blog/uploads/{timezone.now().year}/{timezone.now().month}/{filename}"
            saved_path = default_storage.save(path, content)
            url = storage_url(saved_path)
            if not url.startswith(("http://", "https://")):
                url = request.build_absolute_uri(url)

            return Response({
                "url": url,
                "path": saved_path,
                "alt_text": alt_text,
                "title": title,
                "filename": filename,
            }, status=status.HTTP_201_CREATED)

        except (ValueError, Exception) as exc:
            logger.error("Image upload failed: %s", exc)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# PUBLIC APIs (no auth required, cached)
# ===========================================================================

class PublicBlogListView(APIView):
    """GET /api/public/blogs/ — Public paginated blog list"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = (
            Blog.objects
            .filter(status=BlogStatus.PUBLISHED)
            .select_related("category", "author")
            .prefetch_related("tags")
            .order_by("-publish_date")
        )

        # Filters
        category_slug = request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        tag_slug = request.query_params.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)

        search = request.query_params.get("search") or request.query_params.get("q")
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(excerpt__icontains=search)
                | Q(content__icontains=search)
            )

        paginator = BlogPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BlogPublicListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class PublicBlogDetailView(APIView):
    """GET /api/public/blogs/{slug}/"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        cache_key = f"public_blog_{slug}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            blog = (
                Blog.objects
                .filter(status=BlogStatus.PUBLISHED)
                .select_related("category", "author")
                .prefetch_related("tags")
                .get(slug=slug)
            )
        except Blog.DoesNotExist:
            raise NotFound(detail="Blog not found.")

        data = BlogPublicSerializer(blog, context={"request": request}).data
        cache.set(cache_key, data, BLOG_CACHE_TTL)
        return Response(data)


class PublicCategoryListView(APIView):
    """GET /api/public/categories/"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        cache_key = "public_categories"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        categories = Category.objects.filter(is_active=True).order_by("name")
        data = CategorySerializer(categories, many=True, context={"request": request}).data
        cache.set(cache_key, data, BLOG_CACHE_TTL)
        return Response(data)


class PublicTagListView(APIView):
    """GET /api/public/tags/"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        cache_key = "public_tags"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        tags = Tag.objects.all().order_by("name")
        data = TagSerializer(tags, many=True, context={"request": request}).data
        cache.set(cache_key, data, BLOG_CACHE_TTL)
        return Response(data)


class PublicRelatedBlogsView(APIView):
    """GET /api/public/related-blogs/?slug=<slug>&limit=4"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        slug = request.query_params.get("slug")
        limit = min(int(request.query_params.get("limit", 4)), 10)

        if not slug:
            return Response({"error": "slug query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blog = Blog.objects.filter(status=BlogStatus.PUBLISHED).get(slug=slug)
        except Blog.DoesNotExist:
            raise NotFound(detail="Blog not found.")

        # Same category first, then same tags
        related = (
            Blog.objects
            .filter(status=BlogStatus.PUBLISHED)
            .exclude(pk=blog.pk)
            .select_related("category", "author")
            .prefetch_related("tags")
        )

        if blog.category:
            related = related.filter(category=blog.category)

        if related.count() < limit:
            tag_related = (
                Blog.objects
                .filter(status=BlogStatus.PUBLISHED, tags__in=blog.tags.all())
                .exclude(pk=blog.pk)
                .exclude(pk__in=related.values_list("pk", flat=True))
                .select_related("category", "author")
                .prefetch_related("tags")
                .distinct()
            )
            from itertools import chain
            combined = list(chain(related[:limit], tag_related[:limit - related.count()]))[:limit]
            data = BlogPublicListSerializer(combined, many=True, context={"request": request}).data
            return Response(data)

        data = BlogPublicListSerializer(related[:limit], many=True, context={"request": request}).data
        return Response(data)


# ===========================================================================
# Analytics
# ===========================================================================

class BlogViewTrackView(APIView):
    """POST /api/blogs/view/ — Increment view count for a blog."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ViewTrackThrottle]

    def post(self, request):
        slug = request.data.get("slug")
        if not slug:
            return Response({"error": "slug is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduplicate view tracking per session per slug using cache
        session_key = f"viewed_{request.META.get('REMOTE_ADDR', 'unknown')}_{slug}"
        if cache.get(session_key):
            return Response({"message": "View already counted."})

        updated = Blog.objects.filter(slug=slug, status=BlogStatus.PUBLISHED).update(
            views_count=F("views_count") + 1
        )
        if updated == 0:
            raise NotFound(detail="Blog not found.")

        # Mark as viewed for 1 hour (per IP per slug)
        cache.set(session_key, True, 3600)
        _invalidate_blog_detail_cache(slug)
        return Response({"message": "View counted."})


# ===========================================================================
# SEO — Sitemap & Robots
# ===========================================================================

class SitemapXMLView(APIView):
    """GET /sitemap.xml"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        cache_key = "blog_sitemap_xml"
        cached = cache.get(cache_key)
        if cached:
            return HttpResponse(cached, content_type="application/xml")

        base_url = _get_base_url(request)
        blogs = (
            Blog.objects
            .filter(status=BlogStatus.PUBLISHED)
            .values("slug", "updated_at", "publish_date")
            .order_by("-publish_date")
        )
        categories = Category.objects.filter(is_active=True).values("slug", "updated_at")

        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        ]

        # Homepage
        xml_parts.append(f"""  <url>
    <loc>{base_url}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

        # Blog listing
        xml_parts.append(f"""  <url>
    <loc>{base_url}/blog/</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")

        # Individual blogs
        for blog in blogs:
            lastmod = (blog["updated_at"] or blog["publish_date"] or timezone.now()).strftime("%Y-%m-%d")
            xml_parts.append(f"""  <url>
    <loc>{base_url}/blog/{blog["slug"]}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

        # Categories
        for cat in categories:
            lastmod = (cat["updated_at"] or timezone.now()).strftime("%Y-%m-%d")
            xml_parts.append(f"""  <url>
    <loc>{base_url}/blog/category/{cat["slug"]}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>""")

        xml_parts.append("</urlset>")
        xml_content = "\n".join(xml_parts)

        cache.set(cache_key, xml_content, 3600)  # Cache for 1 hour
        return HttpResponse(xml_content, content_type="application/xml")


class RobotsTxtView(APIView):
    """GET /robots.txt"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        base_url = _get_base_url(request)
        content = f"""User-agent: *
Allow: /

# Disallow admin and API endpoints
Disallow: /admin/
Disallow: /api/token/
Disallow: /api/schema/
Disallow: /api/docs/

# Allow blog content
Allow: /api/public/

# Sitemap
Sitemap: {base_url}/sitemap.xml
"""
        return HttpResponse(content, content_type="text/plain")


# ---------------------------------------------------------------------------
# Category & Tag Admin Views
# ---------------------------------------------------------------------------

class CategoryAdminView(APIView):
    """GET /api/blogs/categories/ — list, POST — create"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.all().order_by("name")
        return Response(CategorySerializer(categories, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete("public_categories")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryAdminDetailView(APIView):
    """GET/PUT/DELETE /api/blogs/categories/{pk}/"""
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            raise NotFound(detail="Category not found.")

    def get(self, request, pk):
        return Response(CategorySerializer(self._get(pk), context={"request": request}).data)

    def put(self, request, pk):
        cat = self._get(pk)
        serializer = CategorySerializer(cat, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete("public_categories")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self._get(pk).delete()
        cache.delete("public_categories")
        return Response({"message": "Category deleted."}, status=status.HTTP_204_NO_CONTENT)


class TagAdminView(APIView):
    """GET /api/blogs/tags/ — list, POST — create"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tags = Tag.objects.all().order_by("name")
        return Response(TagSerializer(tags, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = TagSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete("public_tags")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagAdminDetailView(APIView):
    """GET/PUT/DELETE /api/blogs/tags/{pk}/"""
    permission_classes = [IsAuthenticated]

    def _get(self, pk):
        try:
            return Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            raise NotFound(detail="Tag not found.")

    def get(self, request, pk):
        return Response(TagSerializer(self._get(pk), context={"request": request}).data)

    def put(self, request, pk):
        tag = self._get(pk)
        serializer = TagSerializer(tag, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete("public_tags")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self._get(pk).delete()
        cache.delete("public_tags")
        return Response({"message": "Tag deleted."}, status=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Helpers
# ===========================================================================

def _get_base_url(request) -> str:
    from django.conf import settings
    base = getattr(settings, "SITE_BASE_URL", None)
    if base:
        return base.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def _invalidate_public_cache(slug: str = None):
    if slug:
        cache.delete(f"public_blog_{slug}")
    cache.delete("public_categories")
    cache.delete("public_tags")
    cache.delete("blog_sitemap_xml")


def _invalidate_blog_detail_cache(slug: str):
    cache.delete(f"public_blog_{slug}")
