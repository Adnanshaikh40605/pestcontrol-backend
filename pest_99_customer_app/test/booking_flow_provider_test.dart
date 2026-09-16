import 'package:flutter_test/flutter_test.dart';
import 'package:pest_99_customer_app/models/customer_models.dart';
import 'package:pest_99_customer_app/providers/booking_flow_provider.dart';
import 'package:pest_99_customer_app/utils/catalog_pricing.dart';

void main() {
  group('BookingFlowProvider website form', () {
    test('defaults to residential + cockroach-ants', () {
      final flow = BookingFlowProvider();
      expect(flow.premiseType, 'residential');
      expect(flow.pestTypes, ['cockroach-ants']);
      expect(flow.preferredDate, isNotEmpty);
      expect(flow.preferredTime, isNotEmpty);
    });

    test('beginWithService maps legacy ids to website pest slugs', () {
      final flow = BookingFlowProvider();
      flow.beginWithService('rodent');
      expect(flow.pestTypes, ['rodent']);
      flow.beginWithService('cockroach');
      expect(flow.pestTypes, ['cockroach-ants']);
      flow.beginWithService('bedbug');
      expect(flow.pestTypes, ['bedbugs']);
    });

    test('amc only for cockroach-ants', () {
      final flow = BookingFlowProvider();
      expect(flow.amcAvailable, isTrue);
      flow.setServiceType('amc');
      expect(flow.serviceType, 'amc');
      flow.setPestTypes(['termite']);
      expect(flow.amcAvailable, isFalse);
      expect(flow.serviceType, isEmpty);
    });

    test('commercial clears residential-only fields', () {
      final flow = BookingFlowProvider();
      flow.setPremiseSize('2bhk');
      flow.setTreatmentQuality('premium');
      flow.setServiceType('one-time');
      flow.setPremiseType('commercial');
      expect(flow.premiseSize, isEmpty);
      expect(flow.treatmentQuality, isEmpty);
      expect(flow.serviceType, isEmpty);
      expect(flow.isInspectionQuote, isTrue);
    });

    test('validate requires name, mobile, address, schedule', () {
      final flow = BookingFlowProvider();
      flow.setPremiseSize('1bhk');
      flow.setTreatmentQuality('standard');
      flow.setServiceType('one-time');
      final errors = flow.validate();
      expect(errors.containsKey('streetAddress'), isTrue);
      expect(errors.containsKey('name'), isTrue);
      expect(errors.containsKey('phone'), isTrue);

      flow.setStreetAddress('Baner Road, Pune');
      flow.setFullName('Adnan Shaikh');
      flow.setMobile('9876543210');
      expect(flow.validate(), isEmpty);
    });

    test('catalog quote prices excl-GST base with promo list', () {
      final flow = BookingFlowProvider();
      flow.setPremiseSize('1bhk');
      flow.setTreatmentQuality('standard');
      flow.setServiceType('one-time');
      flow.setRates([
        CatalogRate(
          id: 5,
          servicePackage: 'Cockroach Standard',
          planType: 'One Time Service',
          areaKey: '1 BHK',
          amount: '1250',
          baseAmount: '1250',
          standardAmount: '1475',
          premiumAmount: '1696',
          propertyCategory: 'residential',
          priceIncludesGst: false,
        ),
      ]);
      final q = flow.quote;
      expect(q.pricePending, isFalse);
      expect(q.offerPrice, 1250);
      expect(q.listPrice, greaterThan(q.offerPrice));
      expect(q.discountPercent, 30);
      expect(q.pricingRateId, 5);
    });

    test('other premise size flags custom quote path', () {
      final flow = BookingFlowProvider();
      flow.setPremiseSize('other');
      flow.setTreatmentQuality('standard');
      flow.setServiceType('one-time');
      expect(flow.isOtherPremiseSize, isTrue);
      expect(flow.selectionsComplete, isTrue);
      expect(flow.priceSummaryLabel, contains('Custom quote'));
    });
  });

  group('catalog_pricing matchers', () {
    test('packageTokenMatches uses word boundaries', () {
      expect(packageTokenMatches(['rat'], 'Integrated IPM'), isFalse);
      expect(packageTokenMatches(['rat'], 'Regular Rodent / Rat'), isTrue);
      expect(packageTokenMatches(['fly'], 'Butterfly'), isFalse);
    });

    test('excludes hospital/addon from home pricing', () {
      final hospital = CatalogRate(
        id: 1,
        servicePackage: 'Integrated IPM',
        planType: 'One Time Service',
        areaKey: 'Large',
        amount: '24000',
        standardAmount: '24000',
        premiumAmount: '27600',
        propertyCategory: 'hospital',
      );
      expect(isHomeExcludedRate(hospital), isTrue);
    });

    test('premise size options include 1 RK through 6 BHK + Other', () {
      expect(
        BookingFlowProvider.premiseSizeOptions.map((e) => e.value).toList(),
        ['1rk', '1bhk', '2bhk', '3bhk', '4bhk', '5bhk', '6bhk', 'other'],
      );
      expect(areaKeyForForm('residential', '1rk'), '1 RK');
      expect(areaKeyForForm('commercial', null), 'Commercial');
    });
  });
}
