import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/models/customer_models.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';

void main() {
  group('BookingFlowProvider service lock', () {
    test('beginWithService locks and shows only that service', () {
      final flow = BookingFlowProvider();
      flow.beginWithService('rodent');

      expect(flow.isServiceLocked, isTrue);
      expect(flow.lockedServiceId, 'rodent');
      expect(flow.selectedServiceIds, {'rodent'});
      expect(flow.visibleCatalog.length, 1);
      expect(flow.visibleCatalog.first.id, 'rodent');
      expect(flow.visibleCatalog.first.name, contains('Rodent'));
    });

    test('unlockServiceSelection clears lock and selection', () {
      final flow = BookingFlowProvider();
      flow.beginWithService('termite');
      flow.unlockServiceSelection();

      expect(flow.isServiceLocked, isFalse);
      expect(flow.selectedServiceIds, isEmpty);
      expect(flow.visibleCatalog.length, BookingFlowProvider.catalog.length);
    });

    test('resetFlow clears service lock', () {
      final flow = BookingFlowProvider();
      flow.beginWithService('mosquito');
      flow.resetFlow();

      expect(flow.lockedServiceId, isNull);
      expect(flow.selectedServiceIds, isEmpty);
    });

    test('visibleCatalog filters by backend rates when unlocked', () {
      final flow = BookingFlowProvider();
      flow.setRates([
        CatalogRate(
          id: 1,
          servicePackage: 'Rodent',
          planType: 'One Time Service',
          areaKey: '2 BHK',
          amount: '1500',
          standardAmount: '1500',
          premiumAmount: '1725',
        ),
        CatalogRate(
          id: 2,
          servicePackage: 'Cockroach / Ants',
          planType: 'One Time Service',
          areaKey: '2 BHK',
          amount: '1500',
          standardAmount: '1500',
          premiumAmount: '1725',
        ),
      ]);

      expect(flow.visibleCatalog.map((s) => s.id), containsAll(['rodent', 'cockroach']));
      expect(flow.visibleCatalog.map((s) => s.id), isNot(contains('bee')));
    });

    test('matchRateForService uses selected service and property size', () {
      final flow = BookingFlowProvider();
      flow.beginWithService('rodent');
      flow.selectHomeBhk('2 BHK');
      flow.setRates([
        CatalogRate(
          id: 10,
          servicePackage: 'Rodent',
          planType: 'One Time Service',
          areaKey: '2 BHK',
          amount: '2000',
          standardAmount: '2000',
          premiumAmount: '2300',
          propertyCategory: 'residential',
        ),
        CatalogRate(
          id: 11,
          servicePackage: 'Cockroach / Ants',
          planType: 'One Time Service',
          areaKey: '2 BHK',
          amount: '1500',
          standardAmount: '1500',
          premiumAmount: '1725',
          propertyCategory: 'residential',
        ),
      ]);

      final rate = flow.matchRateForService('rodent', isAmc: false);
      expect(rate?.id, 10);
      expect(flow.priceLabelForService('rodent'), '₹2,000');
    });
  });
}
