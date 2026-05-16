from rest_framework import serializers
from django.utils.text import slugify

from .models import Blog, Category, Tag, BlogStatus
from .fields import AbsoluteImageField
from .utils import sanitize_html, calculate_reading_time, validate_image_size


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    blog_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "meta_title", "meta_description",
            "is_active", "blog_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_blog_count(self, obj):
        return obj.blogs.filter(status=BlogStatus.PUBLISHED).count()


class CategoryLiteSerializer(serializers.ModelSerializer):
    """Minimal serializer for embedding inside Blog responses."""
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagSerializer(serializers.ModelSerializer):
    blog_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "blog_count", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_blog_count(self, obj):
        return obj.blogs.filter(status=BlogStatus.PUBLISHED).count()


class TagLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


# ---------------------------------------------------------------------------
# Blog — Admin (full write access)
# ---------------------------------------------------------------------------

class BlogAdminSerializer(serializers.ModelSerializer):
    featured_image = AbsoluteImageField(required=False, allow_null=True)
    image_thumbnail = AbsoluteImageField(read_only=True)
    image_medium = AbsoluteImageField(read_only=True)

    # Read-only nested representations (SerializerMethodField avoids source conflicts)
    category_detail = serializers.SerializerMethodField()
    tags_detail = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    # Write-only relations
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
        source="category",
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Blog
        fields = [
            # Basic
            "id", "title", "slug", "content", "excerpt",
            # Images
            "featured_image", "featured_image_alt", "featured_image_title",
            "image_thumbnail", "image_medium",
            # SEO
            "meta_title", "meta_description", "target_keywords",
            "canonical_url", "schema_type",
            "og_title", "og_description",
            # Status
            "status", "publish_date",
            # Relations (read)
            "author", "author_name",
            "category_detail", "tags_detail",
            # Relations (write)
            "category_id", "tag_ids",
            # Computed
            "reading_time", "views_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "reading_time", "views_count",
            "image_thumbnail", "image_medium",
            "author", "author_name", "category_detail", "tags_detail",
            "created_at", "updated_at",
        ]

    def get_category_detail(self, obj):
        if obj.category:
            return CategoryLiteSerializer(obj.category).data
        return None

    def get_tags_detail(self, obj):
        return TagLiteSerializer(obj.tags.all(), many=True).data

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None

    def validate_content(self, value):
        return sanitize_html(value)

    def validate_featured_image(self, value):
        if value:
            try:
                validate_image_size(value)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
        return value

    def validate_slug(self, value):
        if value:
            qs = Blog.objects.filter(slug=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A blog with this slug already exists.")
            return slugify(value)
        return value

    def validate(self, attrs):
        if not attrs.get("og_title"):
            attrs["og_title"] = attrs.get("meta_title") or attrs.get("title", "")
        if not attrs.get("og_description"):
            attrs["og_description"] = attrs.get("meta_description") or attrs.get("excerpt", "")
        return attrs

    def create(self, validated_data):
        tag_ids = validated_data.pop("tag_ids", [])
        blog = super().create(validated_data)
        if tag_ids:
            blog.tags.set(tag_ids)
        return blog

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop("tag_ids", None)
        blog = super().update(instance, validated_data)
        if tag_ids is not None:
            blog.tags.set(tag_ids)
        return blog


# ---------------------------------------------------------------------------
# Blog — Admin List (lighter payload for list views)
# ---------------------------------------------------------------------------

class BlogAdminListSerializer(serializers.ModelSerializer):
    featured_image = AbsoluteImageField(read_only=True)
    image_thumbnail = AbsoluteImageField(read_only=True)

    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "status", "publish_date",
            "category_name", "author_name",
            "reading_time", "views_count",
            "featured_image", "image_thumbnail",
            "created_at", "updated_at",
        ]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None


# ---------------------------------------------------------------------------
# Blog — Public (read-only, only published blogs)
# ---------------------------------------------------------------------------

class BlogPublicSerializer(serializers.ModelSerializer):
    featured_image = AbsoluteImageField(read_only=True)
    image_thumbnail = AbsoluteImageField(read_only=True)
    image_medium = AbsoluteImageField(read_only=True)

    category = CategoryLiteSerializer(read_only=True)
    tags = TagLiteSerializer(many=True, read_only=True)
    author_name = serializers.SerializerMethodField()
    keywords_list = serializers.ReadOnlyField()

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "content", "excerpt",
            "featured_image", "featured_image_alt", "featured_image_title",
            "image_thumbnail", "image_medium",
            "meta_title", "meta_description", "target_keywords", "keywords_list",
            "canonical_url", "schema_type",
            "og_title", "og_description",
            "status", "publish_date",
            "author_name",
            "category", "tags",
            "reading_time", "views_count",
            "created_at", "updated_at",
        ]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None


class BlogPublicListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for public blog listing pages."""
    featured_image = AbsoluteImageField(read_only=True)
    image_thumbnail = AbsoluteImageField(read_only=True)

    category = CategoryLiteSerializer(read_only=True)
    tags = TagLiteSerializer(many=True, read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "excerpt",
            "featured_image", "image_thumbnail",
            "featured_image_alt",
            "meta_title", "meta_description",
            "publish_date", "reading_time", "views_count",
            "author_name", "category", "tags",
        ]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None


# ---------------------------------------------------------------------------
# Image Upload
# ---------------------------------------------------------------------------

class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    alt_text = serializers.CharField(max_length=300, required=False, allow_blank=True)
    title = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_image(self, value):
        try:
            validate_image_size(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return value


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class BlogViewTrackSerializer(serializers.Serializer):
    slug = serializers.SlugField()


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

class BlogDashboardSerializer(serializers.Serializer):
    total_blogs = serializers.IntegerField()
    published = serializers.IntegerField()
    drafts = serializers.IntegerField()
    total_views = serializers.IntegerField()
    top_blogs = BlogPublicListSerializer(many=True)
