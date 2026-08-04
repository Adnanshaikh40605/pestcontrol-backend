from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Same hashed/compressed staticfiles behavior as WhiteNoise's default,
    but missing manifest entries fall back instead of raising 500s
    (e.g. Django admin templates referencing admin/css/base.css).
    """

    manifest_strict = False
