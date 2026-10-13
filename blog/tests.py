from django.test import TestCase

from blog.serializers import BlogAdminSerializer
from blog.views import _blog_validation_response


class BlogCanonicalUrlTests(TestCase):
    def test_path_without_scheme_is_accepted(self):
        serializer = BlogAdminSerializer(data={
            "title": "Navratri home tips",
            "content": "<p>Check the kitchen corners.</p>",
            "canonical_url": "pestcontrol99.com/blog/navratri-home-tips/",
            "status": "published",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["canonical_url"],
            "https://pestcontrol99.com/blog/navratri-home-tips/",
        )

    def test_blank_canonical_stays_blank(self):
        serializer = BlogAdminSerializer(data={
            "title": "Navratri home tips",
            "content": "<p>Check the kitchen corners.</p>",
            "canonical_url": "   ",
            "status": "published",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["canonical_url"], "")

    def test_validation_response_includes_detail_for_the_crm_banner(self):
        serializer = BlogAdminSerializer(data={"status": "published"})
        self.assertFalse(serializer.is_valid())
        response = _blog_validation_response(serializer.errors)
        self.assertEqual(response.status_code, 400)
        self.assertIn("content", response.data["detail"])
        self.assertIn("title", response.data["detail"])
