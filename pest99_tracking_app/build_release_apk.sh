#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"

API_URL="${API_BASE_URL:-https://api.vacationbna.site}"

echo "Building Pest99 Tracking release APK (API: $API_URL)..."
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL="$API_URL"

APK="build/app/outputs/flutter-apk/app-release.apk"
if [[ -f "$APK" ]]; then
  echo ""
  echo "APK ready:"
  echo "  $(pwd)/$APK"
  ls -lh "$APK"
fi
