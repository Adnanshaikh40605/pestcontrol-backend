import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/booking.dart';
import '../providers/auth_provider.dart';
import '../providers/bookings_provider.dart';
import '../theme/app_theme.dart';
import 'booking_detail_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<BookingsProvider>().refreshAll();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bookings = context.watch<BookingsProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pest 99 Partner'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: bookings.loading ? null : () => bookings.refreshAll(),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthProvider>().logout(),
          ),
        ],
      ),
      body: bookings.loading && bookings.available.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: bookings.refreshAll,
              child: _buildList(bookings),
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          NavigationDestination(
            icon: Badge(label: Text('${bookings.counts.available}'), child: const Icon(Icons.inbox)),
            label: 'Bookings',
          ),
          NavigationDestination(
            icon: Badge(label: Text('${bookings.counts.accepted}'), child: const Icon(Icons.check_circle_outline)),
            label: 'Accepted',
          ),
          NavigationDestination(
            icon: Badge(label: Text('${bookings.counts.completed}'), child: const Icon(Icons.task_alt)),
            label: 'Done',
          ),
        ],
      ),
    );
  }

  Widget _buildList(BookingsProvider bookings) {
    if (bookings.error != null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(bookings.error!, style: const TextStyle(color: AppColors.danger)),
          ),
        ],
      );
    }
    final List<PartnerBooking> list;
    final bool showAcceptReject;
    switch (_tab) {
      case 1:
        list = bookings.accepted;
        showAcceptReject = false;
        break;
      case 2:
        list = bookings.completed;
        showAcceptReject = false;
        break;
      default:
        list = bookings.available;
        showAcceptReject = true;
    }
    if (list.isEmpty) {
      return ListView(children: const [SizedBox(height: 120), Center(child: Text('No bookings'))]);
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: list.length,
      itemBuilder: (context, i) => _BookingCard(
        booking: list[i],
        showAcceptReject: showAcceptReject,
        onOpen: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => BookingDetailScreen(bookingId: list[i].id, initial: list[i]),
          ),
        ),
      ),
    );
  }
}

class _BookingCard extends StatelessWidget {
  const _BookingCard({
    required this.booking,
    required this.showAcceptReject,
    required this.onOpen,
  });

  final PartnerBooking booking;
  final bool showAcceptReject;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final bookings = context.read<BookingsProvider>();
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onOpen,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.primaryLight,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text('#${booking.id}', style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.primary)),
                  ),
                  const SizedBox(width: 8),
                  if (booking.bookingTag != null)
                    Text(booking.bookingTag!, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 8),
              Text(booking.serviceType, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              Text(booking.locationDisplay ?? '', style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 12),
              if (showAcceptReject)
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () async {
                          final result = await bookings.reject(booking.id);
                          if (context.mounted && !result.success) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text(bookings.error ?? 'Reject failed'), backgroundColor: AppColors.danger),
                            );
                          }
                        },
                        child: const Text('Reject'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () async {
                          final result = await bookings.accept(booking.id);
                          if (context.mounted) {
                            if (result.success) {
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Accepted')));
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(bookings.error ?? 'Accept failed'), backgroundColor: AppColors.danger),
                              );
                            }
                          }
                        },
                        child: const Text('Accept'),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
