import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';
import 'package:pest_99_customer_app/widgets/clock_time_picker.dart';

void main() {
  Future<void> openPicker(
    WidgetTester tester,
    void Function((int, int)? value) onResult, {
    required int hour24,
    required int minute,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => TextButton(
            onPressed: () async {
              onResult(await showClockTimePicker(context, hour24: hour24, minute: minute));
            },
            child: const Text('open'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
  }

  testWidgets('uses one 12-hour ring and confirms on the minute', (tester) async {
    (int, int)? result;
    await openPicker(tester, (value) => result = value, hour24: 10, minute: 0);

    expect(find.text('14'), findsNothing);
    expect(find.text('23'), findsNothing);
    expect(find.byIcon(Icons.keyboard_outlined), findsNothing);
    expect(find.text('Tap an hour, then the minutes'), findsOneWidget);

    await tester.tap(find.byKey(const Key('clock-hour-2')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-ampm-PM')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-min-30')));
    await tester.pumpAndSettle();

    expect(result, (14, 30));
  });

  testWidgets('12 AM stays midnight and cancel leaves the time unchanged', (tester) async {
    (int, int)? result;
    await openPicker(tester, (value) => result = value, hour24: 0, minute: 5);

    await tester.tap(find.byKey(const Key('clock-hour-12')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-min-0')));
    await tester.pumpAndSettle();
    expect(result, (0, 0));

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('CANCEL'));
    await tester.pumpAndSettle();
    expect(result, isNull);
  });

  testWidgets('noon, 11 PM, and an existing 2:30 PM stay on the 24-hour booking clock', (tester) async {
    final flow = BookingFlowProvider();

    (int, int)? noon;
    await openPicker(tester, (value) => noon = value, hour24: 10, minute: 0);
    await tester.tap(find.byKey(const Key('clock-hour-12')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-ampm-PM')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-min-0')));
    await tester.pumpAndSettle();
    flow.setPreferredTime(noon!.$1, noon!.$2);
    expect(flow.preferredTime, '12:00 PM');
    expect(flow.bookingTime24, '12:00');
    expect(BookingFlowProvider.formatFriendlyTime(flow.preferredTime), '12:00 pm');

    (int, int)? night;
    await openPicker(tester, (value) => night = value, hour24: 10, minute: 0);
    await tester.tap(find.byKey(const Key('clock-hour-11')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-ampm-PM')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-min-55')));
    await tester.pumpAndSettle();
    flow.setPreferredTime(night!.$1, night!.$2);
    expect(flow.preferredTime, '11:55 PM');
    expect(flow.bookingTime24, '23:55');

    (int, int)? afternoon;
    await openPicker(tester, (value) => afternoon = value, hour24: 14, minute: 30);
    expect(find.text('14'), findsNothing);
    expect(find.text('02'), findsOneWidget);
    await tester.tap(find.text('30'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('clock-min-30')));
    await tester.pumpAndSettle();
    flow.setPreferredTime(afternoon!.$1, afternoon!.$2);
    expect(flow.bookingTime24, '14:30');
    expect(flow.preferredTime, '02:30 PM');
  });

  testWidgets('a second hour tap does not jump to the minutes early', (tester) async {
    (int, int)? result;
    await openPicker(tester, (value) => result = value, hour24: 10, minute: 0);
    await tester.tap(find.byKey(const Key('clock-hour-2')));
    await tester.pump(const Duration(milliseconds: 40));
    await tester.tap(find.byKey(const Key('clock-hour-5')));
    await tester.pump(const Duration(milliseconds: 130));
    expect(find.text('Tap an hour, then the minutes'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 80));
    await tester.pumpAndSettle();
    expect(find.text('Minutes are in steps of 5'), findsOneWidget);
    await tester.tap(find.byKey(const Key('clock-min-15')));
    await tester.pumpAndSettle();
    expect(result, (5, 15));
  });

  testWidgets('the clock fits a small phone', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 568));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openPicker(tester, (_) {}, hour24: 14, minute: 30);
    expect(tester.takeException(), isNull);
    await tester.tap(find.byKey(const Key('clock-hour-3')));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.text('Minutes are in steps of 5'), findsOneWidget);
  });
}
