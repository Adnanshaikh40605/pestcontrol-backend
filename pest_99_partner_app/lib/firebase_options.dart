import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Firebase config for Pest 99 Partner (`pest-99-partner-app`).
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError('Web is not configured for Pest 99 Partner.');
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError('Platform not supported.');
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyBg0cUpE0FgpbNXAGhICeQM5zZ09NpmRko',
    appId: '1:1081130965061:android:7b27fabd53de34fd8cab2c',
    messagingSenderId: '1081130965061',
    projectId: 'pest-99-partner-app',
    storageBucket: 'pest-99-partner-app.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyBg0cUpE0FgpbNXAGhICeQM5zZ09NpmRko',
    appId: '1:1081130965061:android:7b27fabd53de34fd8cab2c',
    messagingSenderId: '1081130965061',
    projectId: 'pest-99-partner-app',
    storageBucket: 'pest-99-partner-app.firebasestorage.app',
    iosBundleId: 'com.example.pest99PartnerApp',
  );
}
