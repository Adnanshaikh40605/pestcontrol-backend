import 'dart:async';

import 'package:geolocator/geolocator.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';

class PlaceSuggestion {
  const PlaceSuggestion({
    required this.placeId,
    required this.description,
    required this.mainText,
  });

  final String placeId;
  final String description;
  final String mainText;
}

class ResolvedPlace {
  const ResolvedPlace({
    required this.formattedAddress,
    required this.streetLine,
    required this.latitude,
    required this.longitude,
    this.locality = '',
    this.sublocality = '',
    this.cityHint = '',
  });

  final String formattedAddress;
  final String streetLine;
  final double latitude;
  final double longitude;
  final String locality;
  final String sublocality;
  final String cityHint;

  factory ResolvedPlace.fromJson(Map<String, dynamic> json) {
    return ResolvedPlace(
      formattedAddress: (json['formatted_address'] as String?) ?? '',
      streetLine: (json['street_line'] as String?) ?? '',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0,
      locality: (json['locality'] as String?) ?? '',
      sublocality: (json['sublocality'] as String?) ?? '',
      cityHint: (json['city_hint'] as String?) ?? '',
    );
  }
}

class PlacesService {
  PlacesService(this._api);

  final ApiClient _api;

  bool get isAvailable => true;

  Future<List<PlaceSuggestion>> autocomplete(String input) async {
    final query = input.trim();
    if (query.length < 2) return [];
    try {
      final data = await _api.get(
        '${ApiConfig.placesAutocomplete}?input=${Uri.encodeQueryComponent(query)}',
        auth: false,
      );
      if (data['error'] != null) {
        throw Exception(data['error'].toString());
      }
      final raw = data['results'];
      if (raw is! List) return [];
      return raw
          .whereType<Map<String, dynamic>>()
          .map(
            (row) => PlaceSuggestion(
              placeId: (row['place_id'] as String?) ?? '',
              description: (row['description'] as String?) ?? '',
              mainText: (row['main_text'] as String?) ?? (row['description'] as String?) ?? '',
            ),
          )
          .where((s) => s.placeId.isNotEmpty)
          .toList();
    } catch (e) {
      rethrow;
    }
  }

  Future<ResolvedPlace> resolvePlace(String placeId) async {
    final data = await _api.get(
      '${ApiConfig.placesDetails}?place_id=${Uri.encodeQueryComponent(placeId)}',
      auth: false,
    );
    return ResolvedPlace.fromJson(data);
  }

  Future<ResolvedPlace> reverseGeocode(double latitude, double longitude) async {
    final data = await _api.get(
      '${ApiConfig.placesReverse}?latitude=$latitude&longitude=$longitude',
      auth: false,
    );
    return ResolvedPlace.fromJson(data);
  }

  Future<ResolvedPlace> currentLocation() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      final opened = await Geolocator.openLocationSettings();
      if (!opened) {
        throw Exception('Turn on GPS/location services, then tap the location button again.');
      }
      throw Exception('GPS was off. Enable location services and try again.');
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.deniedForever) {
      await Geolocator.openAppSettings();
      throw Exception('Location permission is blocked. Allow it in app settings and try again.');
    }
    if (permission == LocationPermission.denied) {
      throw Exception('Location permission is required to use current location.');
    }
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    return reverseGeocode(position.latitude, position.longitude);
  }
}

class Debouncer {
  Debouncer({this.milliseconds = 350});

  final int milliseconds;
  Timer? _timer;

  void run(void Function() action) {
    _timer?.cancel();
    _timer = Timer(Duration(milliseconds: milliseconds), action);
  }

  void dispose() => _timer?.cancel();
}
