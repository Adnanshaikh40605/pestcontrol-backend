import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_partner_app/features/force_update/force_update_screen.dart';

void main() {
  testWidgets('shows only Please update the app and Update button', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ForceUpdateScreen()),
    );

    expect(find.text('Please update the app.'), findsOneWidget);
    expect(find.text('Update'), findsOneWidget);
    expect(find.text('Cancel'), findsNothing);
    expect(find.text('Later'), findsNothing);
    expect(find.text('Skip'), findsNothing);
    expect(find.text('About'), findsNothing);
  });
}
