import 'package:url_launcher/url_launcher.dart';

/// Call customer / open maps for a booking address.
class BookingContactActions {
  BookingContactActions._();

  static Future<bool> callPhone(String? phone) async {
    final digits = _digitsOnly(phone);
    if (digits.length < 10) return false;
    final uri = Uri(scheme: 'tel', path: digits);
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  static Future<bool> openMaps(String? address) async {
    final query = address?.trim();
    if (query == null || query.isEmpty) return false;
    final encoded = Uri.encodeComponent(query);
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$encoded');
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  static String _digitsOnly(String? raw) {
    if (raw == null) return '';
    return raw.replaceAll(RegExp(r'\D'), '');
  }
}
