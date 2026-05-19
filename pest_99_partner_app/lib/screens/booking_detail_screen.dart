import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/booking.dart';
import '../providers/bookings_provider.dart';
import '../services/booking_service.dart';
import '../core/api_client.dart';
import '../theme/app_theme.dart';

class BookingDetailScreen extends StatefulWidget {
  const BookingDetailScreen({super.key, required this.bookingId, this.initial});

  final int bookingId;
  final PartnerBooking? initial;

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  PartnerBooking? _booking;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _booking = widget.initial;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = BookingService(ApiClient());
      _booking = await service.getDetail(widget.bookingId);
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _startJob() async {
    final picker = ImagePicker();
    final file = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (file == null || !mounted) return;

    final result = await context.read<BookingsProvider>().startJob(widget.bookingId, file.path);
    if (!mounted) return;
    if (result.success) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Job started')));
      await _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.read<BookingsProvider>().error ?? 'Could not start job'),
          backgroundColor: AppColors.danger,
        ),
      );
    }
  }

  Future<void> _endService() async {
    final mode = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(title: const Text('Cash'), onTap: () => Navigator.pop(ctx, 'Cash')),
            ListTile(title: const Text('Online'), onTap: () => Navigator.pop(ctx, 'Online')),
          ],
        ),
      ),
    );
    if (mode == null || !mounted) return;
    final result = await context.read<BookingsProvider>().completeJob(widget.bookingId, mode);
    if (!mounted) return;
    if (result.success) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Service completed')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = _booking;
    return Scaffold(
      appBar: AppBar(title: Text('Booking #${widget.bookingId}')),
      body: _loading && b == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : b == null
                  ? const Center(child: Text('Not found'))
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        _section('Customer', [
                          _row('Name', b.clientName),
                          if (b.canViewClientPhone) _row('Mobile', b.clientMobile),
                          _row('Address', b.locationDisplay ?? b.clientAddress),
                        ]),
                        _section('Service', [
                          _row('Type', b.serviceType),
                          _row('Category', b.serviceCategory),
                          _row('Amount', b.priceDisplay ?? b.price),
                        ]),
                        _section('Schedule', [
                          _row('Date', b.scheduleDatetime),
                          _row('Time', b.timeSlot),
                        ]),
                        if (b.canViewClientPhone && b.clientMobile != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: OutlinedButton.icon(
                              onPressed: () => launchUrl(Uri.parse('tel:${b.clientMobile}')),
                              icon: const Icon(Icons.phone),
                              label: const Text('Call customer'),
                            ),
                          ),
                        if (b.canStartJob)
                          ElevatedButton(onPressed: _startJob, child: const Text('Start job (selfie)')),
                        if (b.canCompleteJob)
                          ElevatedButton(onPressed: _endService, child: const Text('End service')),
                      ],
                    ),
    );
  }

  Widget _section(String title, List<Widget> children) => Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              const SizedBox(height: 8),
              ...children,
            ],
          ),
        ),
      );

  Widget _row(String label, String? value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 100, child: Text(label, style: const TextStyle(color: Colors.grey))),
            Expanded(child: Text(value ?? '—')),
          ],
        ),
      );
}
