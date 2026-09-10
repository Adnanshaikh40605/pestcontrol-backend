"""City-aware pricing — DB-backed with legacy fallback."""

from .aliases import (
    alias_candidates,
    resolve_service_package,
)
from .db import (
    build_pricing_config_payload,
    get_area_options,
    get_pricing_data,
    get_service_types,
    normalize_city_name,
    pricing_region_for_city,
    resolve_pricing_region_slug,
)

__all__ = [
    'alias_candidates',
    'build_pricing_config_payload',
    'get_area_options',
    'get_pricing_data',
    'get_service_types',
    'normalize_city_name',
    'pricing_region_for_city',
    'resolve_pricing_region_slug',
    'resolve_service_package',
]
