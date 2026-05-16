from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    # ── Admin / CRM APIs (authentication required) ──────────────────────────

    # Dashboard
    path("blogs/dashboard-stats/", views.BlogDashboardView.as_view(), name="blog-dashboard"),

    # Blog CRUD
    path("blogs/", views.BlogListAdminView.as_view(), name="blog-list-admin"),
    path("blogs/create/", views.BlogCreateView.as_view(), name="blog-create"),
    path("blogs/<int:pk>/", views.BlogDetailAdminView.as_view(), name="blog-detail-admin"),
    path("blogs/<int:pk>/update/", views.BlogDetailAdminView.as_view(), name="blog-update"),
    path("blogs/<int:pk>/delete/", views.BlogDeleteView.as_view(), name="blog-delete"),
    path("blogs/<int:pk>/toggle-publish/", views.BlogPublishToggleView.as_view(), name="blog-toggle-publish"),

    # Image upload
    path("blogs/upload-image/", views.ImageUploadView.as_view(), name="blog-upload-image"),

    # Analytics
    path("blogs/view/", views.BlogViewTrackView.as_view(), name="blog-view-track"),

    # Categories (admin)
    path("blogs/categories/", views.CategoryAdminView.as_view(), name="category-list-admin"),
    path("blogs/categories/<int:pk>/", views.CategoryAdminDetailView.as_view(), name="category-detail-admin"),

    # Tags (admin)
    path("blogs/tags/", views.TagAdminView.as_view(), name="tag-list-admin"),
    path("blogs/tags/<int:pk>/", views.TagAdminDetailView.as_view(), name="tag-detail-admin"),


    # ── Public APIs (no auth, cached) ────────────────────────────────────────

    path("public/blogs/", views.PublicBlogListView.as_view(), name="public-blog-list"),
    path("public/blogs/<slug:slug>/", views.PublicBlogDetailView.as_view(), name="public-blog-detail"),
    path("public/categories/", views.PublicCategoryListView.as_view(), name="public-category-list"),
    path("public/tags/", views.PublicTagListView.as_view(), name="public-tag-list"),
    path("public/related-blogs/", views.PublicRelatedBlogsView.as_view(), name="public-related-blogs"),
]
