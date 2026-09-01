"""Server-side Google Places / Geocoding proxy for the customer app."""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PLACES_BASE = 'https://maps.googleapis.com/maps/api'


class PlacesProxyError(Exception):
    def __init__(self, message: str, *, code: str = 'places_error', status: int = 400):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


def _api_key() -> str:
    key = (getattr(settings, 'GOOGLE_MAPS_API_KEY', '') or '').strip()
    if not key or key.startswith('your-'):
        raise PlacesProxyError(
            'Address search is temporarily unavailable.',
            code='maps_not_configured',
            status=503,
        )
    return key


def _google_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, 'key': _api_key()}
    try:
        response = requests.get(f'{PLACES_BASE}/{path}', params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.exception('Google Places request failed: %s', exc)
        raise PlacesProxyError('Could not reach address search service.', status=502) from exc
    except ValueError as exc:
        raise PlacesProxyError('Invalid response from address search service.', status=502) from exc

    status = payload.get('status') or ''
    if status in ('OK', 'ZERO_RESULTS'):
        return payload
    error_message = payload.get('error_message') or f'Google Places error ({status})'
    raise PlacesProxyError(error_message, status=400)


def _parse_address_components(components: list[dict[str, Any]]) -> dict[str, str]:
    sublocality = ''
    locality = ''
    city_hint = ''
    route = ''
    street_number = ''

    for raw in components:
        types = raw.get('types') or []
        long_name = (raw.get('long_name') or '').strip()
        if not long_name:
            continue
        if 'sublocality_level_1' in types or 'sublocality' in types:
            sublocality = long_name
        elif 'locality' in types:
            locality = long_name
        elif 'administrative_area_level_2' in types and not city_hint:
            city_hint = long_name
        elif 'route' in types:
            route = long_name
        elif 'street_number' in types:
            street_number = long_name

    street_parts = [part for part in (street_number, route) if part]
    street_line = ' '.join(street_parts).strip()
    return {
        'sublocality': sublocality,
        'locality': locality,
        'city_hint': city_hint or locality,
        'street_line': street_line,
    }


def _resolved_place_from_result(result: dict[str, Any]) -> dict[str, Any]:
    geometry = result.get('geometry') or {}
    location = geometry.get('location') or {}
    lat = location.get('lat')
    lng = location.get('lng')
    if lat is None or lng is None:
        raise PlacesProxyError('Place coordinates missing.', status=400)

    parsed = _parse_address_components(result.get('address_components') or [])
    formatted = (result.get('formatted_address') or '').strip()
    street_line = parsed['street_line']
    if not street_line:
        street_line = (result.get('name') or formatted.split(',')[0]).strip()

    return {
        'formatted_address': formatted,
        'street_line': street_line,
        'latitude': lat,
        'longitude': lng,
        'locality': parsed['locality'],
        'sublocality': parsed['sublocality'],
        'city_hint': parsed['city_hint'],
    }


def places_autocomplete(input_text: str) -> list[dict[str, str]]:
    query = (input_text or '').strip()
    if len(query) < 3:
        return []
    payload = _google_get(
        'place/autocomplete/json',
        {'input': query, 'components': 'country:in', 'language': 'en'},
    )
    results: list[dict[str, str]] = []
    for row in payload.get('predictions') or []:
        if not isinstance(row, dict):
            continue
        place_id = (row.get('place_id') or '').strip()
        if not place_id:
            continue
        structured = row.get('structured_formatting') or {}
        results.append({
            'place_id': place_id,
            'description': (row.get('description') or '').strip(),
            'main_text': (structured.get('main_text') or row.get('description') or '').strip(),
        })
    return results


def places_details(place_id: str) -> dict[str, Any]:
    pid = (place_id or '').strip()
    if not pid:
        raise PlacesProxyError('place_id is required.')
    payload = _google_get(
        'place/details/json',
        {
            'place_id': pid,
            'fields': 'formatted_address,geometry,address_components,name',
            'language': 'en',
        },
    )
    result = payload.get('result')
    if not isinstance(result, dict):
        raise PlacesProxyError('Place details missing.', status=404)
    return _resolved_place_from_result(result)


def places_reverse_geocode(latitude: float, longitude: float) -> dict[str, Any]:
    payload = _google_get(
        'geocode/json',
        {'latlng': f'{latitude},{longitude}', 'language': 'en'},
    )
    results = payload.get('results') or []
    if not results:
        raise PlacesProxyError('No address found for this location.', status=404)
    first = results[0]
    if not isinstance(first, dict):
        raise PlacesProxyError('No address found for this location.', status=404)
    place_id = (first.get('place_id') or '').strip()
    if place_id:
        return places_details(place_id)
    return _resolved_place_from_result(first)
