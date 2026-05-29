/// Semantic version comparison (e.g. 2.0.0 vs 0.1.0+1).
int compareVersions(String left, String right) {
  final a = _parseParts(left);
  final b = _parseParts(right);
  for (var i = 0; i < 3; i++) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return 0;
}

bool isVersionBelow(String current, String minimum) {
  return compareVersions(current, minimum) < 0;
}

String normalizeVersion(String version) {
  var v = version.trim();
  if (v.contains('+')) {
    v = v.split('+').first;
  }
  return v.isEmpty ? '0.0.0' : v;
}

List<int> _parseParts(String version) {
  final normalized = normalizeVersion(version);
  final parts = normalized.split('.').map((segment) {
    final digits = StringBuffer();
    for (final ch in segment.trim().split('')) {
      if (ch.codeUnitAt(0) >= 48 && ch.codeUnitAt(0) <= 57) {
        digits.write(ch);
      } else {
        break;
      }
    }
    return int.tryParse(digits.toString()) ?? 0;
  }).toList();
  while (parts.length < 3) {
    parts.add(0);
  }
  return parts.take(3).toList();
}
