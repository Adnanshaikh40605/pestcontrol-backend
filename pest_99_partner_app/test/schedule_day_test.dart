import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/core/constants/notification_channels.dart';
import 'package:pest_99_partner_app/core/mappers/booking_mapper.dart';
import 'package:pest_99_partner_app/core/notification_open_plan.dart';
import 'package:pest_99_partner_app/core/schedule_day.dart';
import 'package:pest_99_partner_app/models/booking.dart';
import 'package:pest_99_partner_app/shared/widgets/booking_day_sections.dart';

PartnerBooking _job(int id, String schedule) => PartnerBooking(
      id: id,
      serviceType: 'Cockroach',
      scheduleDatetime: schedule,
    );

void main() {
  // 27 Sep 2026 10:00 IST
  final morningIst = DateTime.utc(2026, 9, 27, 4, 30);
  // 27 Sep 2026 22:00 IST
  final lateIst = DateTime.utc(2026, 9, 27, 16, 30);

  group('ScheduleDay IST buckets', () {
    test('today afternoon IST stays on Today', () {
      expect(
        ScheduleDay.bucketFor('2026-09-27T16:30:00+05:30', now: morningIst),
        'today',
      );
      expect(
        ScheduleDay.bucketFor('2026-09-27T11:00:00Z', now: morningIst),
        'today',
      );
    });

    test('next IST calendar day is Tomorrow', () {
      expect(
        ScheduleDay.bucketFor('2026-09-28T09:00:00+05:30', now: morningIst),
        'tomorrow',
      );
    });

    test('IST midnight stored as the previous UTC instant is Tomorrow, not missed', () {
      // 28 Sep 2026 00:00 IST == 27 Sep 2026 18:30 UTC.
      // A UTC or US-local calendar date is the 27th, so phone-local Today
      // and Tomorrow both skip it when "now" is the morning of the 27th in India.
      expect(
        ScheduleDay.bucketFor('2026-09-27T18:30:00Z', now: morningIst),
        'tomorrow',
      );
      expect(
        ScheduleDay.bucketFor('2026-09-28T00:00:00+05:30', now: morningIst),
        'tomorrow',
      );
    });

    test('late-night UTC is the next IST day and lands on Tomorrow', () {
      // 27 Sep 2026 20:00 UTC == 28 Sep 2026 01:30 IST.
      expect(
        ScheduleDay.bucketFor('2026-09-27T20:00:00Z', now: lateIst),
        'tomorrow',
      );
    });

    test('late-night UTC now does not drop IST tomorrow off both tabs', () {
      // Now is 28 Sep 2026 02:00 IST (still 27 Sep 20:30 UTC).
      // IST tomorrow 10:00 is 29 Sep 04:30 UTC — two UTC calendar days
      // later, so a UTC date bucket misses both Today and Tomorrow.
      final lateUtc = DateTime.utc(2026, 9, 27, 20, 30);
      expect(
        ScheduleDay.bucketFor('2026-09-28T04:30:00Z', now: lateUtc),
        'today',
      );
      expect(
        ScheduleDay.bucketFor('2026-09-29T04:30:00Z', now: lateUtc),
        'tomorrow',
      );
    });

    test('a morning IST job is Today even when UTC still says yesterday', () {
      // 27 Sep 2026 00:30 IST == 26 Sep 2026 19:00 UTC.
      expect(
        ScheduleDay.bucketFor('2026-09-26T19:00:00Z', now: morningIst),
        'today',
      );
    });

    test('same-evening IST job stays on Today', () {
      expect(
        ScheduleDay.bucketFor('2026-09-27T23:30:00+05:30', now: lateIst),
        'today',
      );
    });

    test('a zone-less schedule string is an IST wall clock, not the phone clock', () {
      expect(
        ScheduleDay.bucketFor('2026-09-28T08:00:00', now: lateIst),
        'tomorrow',
      );
    });

    test('beyond tomorrow is Later, and parse failure is not a day tab', () {
      expect(
        ScheduleDay.bucketFor('2026-09-30T10:00:00+05:30', now: morningIst),
        'later',
      );
      expect(ScheduleDay.bucketFor('not-a-date', now: morningIst), isNull);
    });

    test('job 3860 on 28 Sep 15:28 IST is Later, not a shifted today', () {
      // Screenshot time. Stored instant is 2026-09-30T07:30:00Z == 30 Sep 13:00 IST.
      // Created the same afternoon (28 Sep 12:56 IST) with time_slot 01:00 PM,
      // so the calendar date is Wednesday, two days out — the Later section.
      final screenshotIst = DateTime.utc(2026, 9, 28, 9, 58);
      expect(
        ScheduleDay.bucketFor('2026-09-30T07:30:00+00:00', now: screenshotIst),
        'later',
      );
      expect(
        ScheduleDay.bucketFor('2026-09-30T13:00:00+05:30', now: screenshotIst),
        'later',
      );
      final booking = BookingMapper.fromPartner(
        _job(3860, '2026-09-30T07:30:00+00:00'),
        now: screenshotIst,
      );
      expect(booking.dayBucket, 'later');
      expect(booking.dateLabel, 'Wed, 30 Sep');
      expect(booking.timeLabel, '1:00 PM');
    });
  });

  group('New Bookings day sections', () {
    test('morning IST job, midnight edge, and late UTC split into Today and Tomorrow', () {
      final sections = BookingDaySections.from(
        [
          _job(1, '2026-09-26T19:00:00Z'), // 00:30 IST 27 Sep — today
          _job(2, '2026-09-27T18:30:00Z'), // 00:00 IST 28 Sep — tomorrow
          _job(3, '2026-09-27T20:00:00Z'), // 01:30 IST 28 Sep — tomorrow
          _job(4, '2026-09-30T10:00:00+05:30'),
        ],
        now: morningIst,
      );

      expect(sections.today.map((b) => b.id), [1]);
      expect(sections.tomorrow.map((b) => b.id), [2, 3]);
      expect(sections.later.map((b) => b.id), [4]);
    });

    test('mapper label matches the IST bucket', () {
      final booking = BookingMapper.fromPartner(
        _job(9, '2026-09-27T20:00:00Z'),
        now: lateIst,
      );
      expect(booking.dayBucket, 'tomorrow');
      expect(booking.dateLabel, 'Tomorrow');
      expect(booking.timeLabel, '1:30 AM');
    });
  });

  group('notification tap payload', () {
    test('reads booking id from a local notification JSON payload', () {
      final data = notificationDataFromPayload(
        '{"type":"new_booking","booking_id":"4821","schedule_datetime":"2026-09-27T18:30:00Z"}',
      );
      expect(bookingIdFromNotificationData(data), 4821);
      expect(isNewBookingPush(data!), isTrue);
      expect(
        ScheduleDay.bucketFor(data['schedule_datetime']?.toString(), now: morningIst),
        'tomorrow',
      );
    });

    test('ignores a payload with no booking id', () {
      expect(notificationDataFromPayload('not-json'), isNull);
      expect(
        bookingIdFromNotificationData({'type': 'new_booking'}),
        isNull,
      );
    });

    test('3860 opens the booking page and scrolls Later instead of Today', () {
      final screenshotIst = DateTime.utc(2026, 9, 28, 9, 58);
      final plan = NotificationOpenPlan.fromNotificationData(
        {
          'type': 'new_booking',
          'booking_id': '3860',
          'schedule_datetime': '2026-09-30T07:30:00+00:00',
        },
        now: screenshotIst,
      );
      expect(plan, isNotNull);
      expect(plan!.detailPath, '/booking/3860');
      expect(plan.dayTabIndex, isNull);
      expect(plan.scrollToCard, isTrue);
      expect(plan.bucket, 'later');
      expect(canPushBookingDetail('/bookings'), isTrue);
      expect(canPushBookingDetail('/splash'), isFalse);
    });

    test('a tomorrow payload selects the Tomorrow tab', () {
      final plan = NotificationOpenPlan.fromNotificationData(
        {
          'type': 'new_booking',
          'booking_id': '10',
          'schedule_datetime': '2026-09-28T09:00:00+05:30',
        },
        now: morningIst,
      );
      expect(plan!.dayTabIndex, 1);
      expect(plan.scrollToCard, isFalse);
      expect(plan.detailPath, '/booking/10');
    });
  });

  group('Today Tomorrow tab controller', () {
    test('Tomorrow tap stays selected after a consumed Today hint', () {
      final tabs = NewBookingDayTab();
      expect(tabs.applyHint(0, 1), isFalse);
      expect(tabs.index, 0);
      expect(tabs.select(1), isTrue);
      expect(tabs.applyHint(0, 1), isFalse);
      expect(tabs.index, 1);
    });

    test('a later notification does not force the Today tab', () {
      final tabs = NewBookingDayTab();
      expect(tabs.select(1), isTrue);
      expect(tabs.applyHint(null, 2), isFalse);
      expect(tabs.index, 1);
    });

    test('a newer notification serial selects that job\'s day tab', () {
      final tabs = NewBookingDayTab();
      tabs.applyHint(0, 1);
      tabs.select(1);
      expect(tabs.applyHint(0, 4), isTrue);
      expect(tabs.index, 0);
    });
  });
}
