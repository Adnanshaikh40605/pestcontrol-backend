import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

enum BookingType {
  booking('One-Time', AppColors.primary),
  oneTime('One-Time', AppColors.primary),
  serviceCall('Service Call', AppColors.tagPurple),
  complaintCall('Complaint Call', AppColors.danger),
  followUp('Follow-up', AppColors.infoBlue),
  amcVisit('AMC', AppColors.tagOrange);

  const BookingType(this.label, this.color);

  final String label;
  final Color color;
}

enum BookingPriority { standard, high }

enum AcceptedJobState { pending, inService, completed }

enum PaymentStatus { unpaid, paid, pending }

enum PaymentMode { cash, online }
