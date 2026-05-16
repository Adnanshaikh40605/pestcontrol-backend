from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Blog, Category, Tag, BlogStatus


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "blog_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    def blog_count(self, obj):
        return obj.blogs.filter(status=BlogStatus.PUBLISHED).count()
    blog_count.short_description = "Published Blogs"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "blog_count", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    def blog_count(self, obj):
        return obj.blogs.filter(status=BlogStatus.PUBLISHED).count()
    blog_count.short_description = "Published Blogs"


class TagInline(admin.TabularInline):
    model = Blog.tags.through
    extra = 0
    verbose_name = "Tag"
    verbose_name_plural = "Tags"


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = [
        "title", "status_badge", "category", "author",
        "publish_date", "views_count", "reading_time", "created_at",
    ]
    list_filter = ["status", "category", "publish_date", "schema_type"]
    search_fields = ["title", "slug", "meta_title", "meta_description"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = [
        "slug", "reading_time", "views_count",
        "image_thumbnail", "image_medium",
        "created_at", "updated_at",
        "thumbnail_preview",
    ]
    filter_horizontal = ["tags"]
    date_hierarchy = "publish_date"

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "title", "slug", "excerpt", "content",
            )
        }),
        ("Featured Image", {
            "fields": (
                "featured_image", "featured_image_alt", "featured_image_title",
                "thumbnail_preview", "image_thumbnail", "image_medium",
            )
        }),
        ("SEO", {
            "fields": (
                "meta_title", "meta_description", "target_keywords",
                "canonical_url", "schema_type",
                "og_title", "og_description",
            ),
            "classes": ("collapse",),
        }),
        ("Status & Publishing", {
            "fields": ("status", "publish_date", "author", "category", "tags"),
        }),
        ("Analytics", {
            "fields": ("reading_time", "views_count"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def status_badge(self, obj):
        color = "green" if obj.status == BlogStatus.PUBLISHED else "orange"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def thumbnail_preview(self, obj):
        if obj.image_thumbnail:
            return format_html(
                '<img src="{}" width="200" style="border-radius:4px;" />',
                obj.image_thumbnail.url,
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Thumbnail Preview"

    actions = ["publish_blogs", "unpublish_blogs"]

    def publish_blogs(self, request, queryset):
        count = queryset.update(status=BlogStatus.PUBLISHED, publish_date=timezone.now())
        self.message_user(request, f"{count} blog(s) published.")
    publish_blogs.short_description = "Publish selected blogs"

    def unpublish_blogs(self, request, queryset):
        count = queryset.update(status=BlogStatus.DRAFT)
        self.message_user(request, f"{count} blog(s) moved to draft.")
    unpublish_blogs.short_description = "Move selected blogs to Draft"
