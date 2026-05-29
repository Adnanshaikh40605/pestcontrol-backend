class AppVersionInfo {
  const AppVersionInfo({
    required this.latestVersion,
    required this.minimumSupportedVersion,
    required this.forceUpdate,
    required this.updateTitle,
    required this.updateMessage,
  });

  final String latestVersion;
  final String minimumSupportedVersion;
  final bool forceUpdate;
  final String updateTitle;
  final String updateMessage;

  factory AppVersionInfo.fromJson(Map<String, dynamic> json) {
    return AppVersionInfo(
      latestVersion: json['latest_version']?.toString() ?? '0.0.0',
      minimumSupportedVersion:
          json['minimum_supported_version']?.toString() ?? '0.0.0',
      forceUpdate: json['force_update'] == true,
      updateTitle: json['update_title']?.toString() ?? 'New Update Available',
      updateMessage: json['update_message']?.toString() ?? '',
    );
  }
}
