/// Google Maps / Places API key (optional client-side).
///
/// Address autocomplete in the customer app uses the backend Places proxy
/// (`/api/customer/places/…` → `GOOGLE_MAPS_API_KEY` on the server).
/// A client key is not required for autocomplete/GPS reverse-geocode.
///
/// If you later call Maps SDKs directly, pass:
/// `flutter build apk --dart-define=GOOGLE_MAPS_API_KEY=your_key`
class MapsConfig {
  static const String apiKey = String.fromEnvironment(
    'GOOGLE_MAPS_API_KEY',
    defaultValue: '',
  );

  static bool get isConfigured => apiKey.trim().isNotEmpty;
}
