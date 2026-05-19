class PartnerNotificationItem {
  PartnerNotificationItem({
    required this.id,
    required this.notificationType,
    required this.title,
    required this.body,
    this.bookingId,
    required this.isRead,
    required this.createdAt,
  });

  final int id;
  final String notificationType;
  final String title;
  final String body;
  final int? bookingId;
  final bool isRead;
  final DateTime? createdAt;

  factory PartnerNotificationItem.fromJson(Map<String, dynamic> json) {
    final bookingRaw = json['booking'];
    int? bookingId;
    if (bookingRaw is int) {
      bookingId = bookingRaw;
    } else if (json['booking_id'] is int) {
      bookingId = json['booking_id'] as int;
    }
    return PartnerNotificationItem(
      id: json['id'] as int,
      notificationType: json['notification_type'] as String? ?? 'general',
      title: json['title'] as String? ?? '',
      body: json['body'] as String? ?? '',
      bookingId: bookingId,
      isRead: json['is_read'] == true,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'] as String) : null,
    );
  }
}

class PartnerNotificationListResponse {
  PartnerNotificationListResponse({
    required this.unreadCount,
    required this.results,
  });

  final int unreadCount;
  final List<PartnerNotificationItem> results;

  factory PartnerNotificationListResponse.fromJson(Map<String, dynamic> json) {
    final list = json['results'];
    return PartnerNotificationListResponse(
      unreadCount: json['unread_count'] as int? ?? 0,
      results: list is List
          ? list.map((e) => PartnerNotificationItem.fromJson(e as Map<String, dynamic>)).toList()
          : [],
    );
  }
}
