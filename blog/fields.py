from rest_framework import serializers


class AbsoluteImageField(serializers.ImageField):
    """
    Returns a full URL for image fields.
    - S3: storage.url() is already absolute
    - Local dev: prefixes request host when needed
    """

    def to_representation(self, value):
        if not value:
            return None
        try:
            url = value.url
        except Exception:
            return None
        if url.startswith(("http://", "https://")):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url
