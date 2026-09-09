/// Google Maps / Places API key for address autocomplete and geocoding.
///
/// Pass at build time:
/// `flutter build apk --dart-define=GOOGLE_MAPS_API_KEY=your_key`
class MapsConfig {
  static const String apiKey = String.fromEnvironment(
    'GOOGLE_MAPS_API_KEY',
    defaultValue: '',
  );

  static bool get isConfigured => apiKey.trim().isNotEmpty;
}
