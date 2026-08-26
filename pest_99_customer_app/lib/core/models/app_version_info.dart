class AppVersionInfo {
  const AppVersionInfo({
    required this.latestVersion,
    required this.minimumSupportedVersion,
    required this.forceUpdate,
    required this.updateTitle,
    required this.updateMessage,
    required this.storeUrl,
  });

  final String latestVersion;
  final String minimumSupportedVersion;
  final bool forceUpdate;
  final String updateTitle;
  final String updateMessage;
  final String storeUrl;

  static const defaultStoreUrl =
      'https://play.google.com/store/apps/details?id=com.pestcontrol99.pest_99_customer_app';

  factory AppVersionInfo.fromJson(Map<String, dynamic> json) {
    final store = json['store_url']?.toString().trim();
    return AppVersionInfo(
      latestVersion: json['latest_version']?.toString() ?? '0.0.0',
      minimumSupportedVersion:
          json['minimum_supported_version']?.toString() ?? '0.0.0',
      forceUpdate: json['force_update'] == true,
      updateTitle: json['update_title']?.toString() ?? 'Update required',
      updateMessage: json['update_message']?.toString() ??
          'A newer version is required to continue.',
      storeUrl: (store != null && store.isNotEmpty) ? store : defaultStoreUrl,
    );
  }
}
