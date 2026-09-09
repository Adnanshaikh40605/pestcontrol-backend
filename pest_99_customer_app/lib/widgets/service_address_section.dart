import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../models/customer_models.dart';
import '../providers/booking_flow_provider.dart';
import '../services/customer_services.dart';
import '../services/places_service.dart';

int? matchMasterCityId(String? hint, List<MasterCity> cities) {
  final raw = (hint ?? '').trim().toLowerCase();
  if (raw.isEmpty) return null;

  String normalize(String value) => value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'\s+'), ' ');

  final aliases = <String, String>{
    'bombay': 'mumbai',
    'new mumbai': 'navi mumbai',
    'navimumbai': 'navi mumbai',
    'lonavala': 'lonavla',
    'lonawala': 'lonavla',
    'mumbai suburban': 'mumbai',
    'mumbai city': 'mumbai',
    'greater mumbai': 'mumbai',
    'thane city': 'thane',
    'pimpri chinchwad': 'pune',
    'pcmc': 'pune',
  };

  var target = aliases[raw] ?? raw;
  target = aliases[target] ?? target;

  for (final city in cities) {
    final name = normalize(city.name);
    if (name == target || name == raw) return city.id;
  }
  for (final city in cities) {
    final name = normalize(city.name);
    if (target.contains(name) || name.contains(target)) return city.id;
  }
  return null;
}

/// Resolve master city from Google place fields (locality preferred).
int? resolveCityIdFromPlace(ResolvedPlace place, List<MasterCity> cities) {
  final candidates = <String>[
    place.locality,
    place.cityHint,
    place.sublocality,
    place.formattedAddress,
  ];
  for (final candidate in candidates) {
    final id = matchMasterCityId(candidate, cities);
    if (id != null) return id;
  }
  // Token-scan formatted address against known city names.
  final hay = place.formattedAddress.toLowerCase();
  for (final city in cities) {
    final name = city.name.trim().toLowerCase();
    if (name.isNotEmpty && hay.contains(name)) return city.id;
  }
  return null;
}

class ServiceAddressSection extends StatefulWidget {
  const ServiceAddressSection({super.key});

  @override
  State<ServiceAddressSection> createState() => _ServiceAddressSectionState();
}

class _ServiceAddressSectionState extends State<ServiceAddressSection> {
  final _addressController = TextEditingController();
  final _addressFocus = FocusNode();
  PlacesService? _places;
  final _debouncer = Debouncer();

  List<MasterCity> _cities = [];
  List<MasterLocation> _locations = [];
  List<PlaceSuggestion> _suggestions = [];

  bool _loadingCities = true;
  bool _loadingLocations = false;
  bool _loadingLocation = false;
  bool _loadingSuggestions = false;
  String? _loadError;
  String? _placesError;

  @override
  void initState() {
    super.initState();
    _places = PlacesService(context.read<ApiClient>());
    final flow = context.read<BookingFlowProvider>();
    _addressController.text = flow.serviceAddress;
    _addressController.addListener(_onAddressChanged);
    _addressFocus.addListener(() {
      if (!_addressFocus.hasFocus) {
        // Keep suggestions briefly so taps on a row still register.
        Future<void>.delayed(const Duration(milliseconds: 180), () {
          if (!mounted || _addressFocus.hasFocus) return;
          setState(() => _suggestions = []);
        });
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadCities());
  }

  @override
  void dispose() {
    _debouncer.dispose();
    _addressController.removeListener(_onAddressChanged);
    _addressController.dispose();
    _addressFocus.dispose();
    super.dispose();
  }

  Future<void> _loadCities() async {
    setState(() {
      _loadingCities = true;
      _loadError = null;
    });
    try {
      final cities = await MasterDataService(context.read<ApiClient>()).listCities();
      if (!mounted) return;
      setState(() {
        _cities = cities;
        _loadingCities = false;
      });
      final flow = context.read<BookingFlowProvider>();
      if (flow.masterCityId != null) {
        await _loadLocations(flow.masterCityId!, preserveSelection: true);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingCities = false;
        _loadError = '$e';
      });
    }
  }

  Future<void> _loadLocations(int cityId, {bool preserveSelection = false}) async {
    setState(() {
      _loadingLocations = true;
      _loadError = null;
    });
    try {
      final locations = await MasterDataService(context.read<ApiClient>()).listLocations(cityId);
      if (!mounted) return;
      final flow = context.read<BookingFlowProvider>();
      int? selectedLocationId;
      if (preserveSelection) {
        selectedLocationId = flow.masterLocationId;
        if (selectedLocationId != null &&
            !locations.any((location) => location.id == selectedLocationId)) {
          selectedLocationId = null;
        }
      }
      final cityName = _cities
          .firstWhere((c) => c.id == cityId, orElse: () => const MasterCity(id: 0, name: ''))
          .name;
      flow.setServiceAddress(
        masterCityId: cityId,
        city: cityName,
        area: '',
      );
      flow.clearMasterLocation();
      if (selectedLocationId != null) {
        final location = locations.firstWhere((l) => l.id == selectedLocationId);
        flow.setServiceAddress(
          masterLocationId: selectedLocationId,
          area: location.name,
        );
      }
      setState(() {
        _locations = locations;
        _loadingLocations = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingLocations = false;
        _loadError = '$e';
      });
    }
  }

  void _onAddressChanged() {
    final flow = context.read<BookingFlowProvider>();
    flow.setServiceAddress(address: _addressController.text);
    _debouncer.run(_fetchSuggestions);
  }

  Future<void> _fetchSuggestions() async {
    final places = _places;
    if (places == null) return;
    final query = _addressController.text.trim();
    if (query.length < 2) {
      setState(() {
        _suggestions = [];
        _loadingSuggestions = false;
        _placesError = query.isEmpty ? null : 'Type at least 2 characters to search';
      });
      return;
    }
    setState(() {
      _loadingSuggestions = true;
      _placesError = null;
    });
    try {
      final suggestions = await places.autocomplete(query);
      if (!mounted) return;
      // Ignore stale responses if the user kept typing.
      if (_addressController.text.trim() != query) return;
      setState(() {
        _suggestions = suggestions;
        _loadingSuggestions = false;
        if (suggestions.isEmpty) {
          _placesError = 'No matching addresses. Try a fuller street or landmark.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _suggestions = [];
        _loadingSuggestions = false;
        _placesError = 'Address search failed. Check internet and try again.';
      });
    }
  }

  Future<void> _selectSuggestion(PlaceSuggestion suggestion) async {
    final places = _places;
    if (places == null) return;
    setState(() {
      _suggestions = [];
      _loadingLocation = true;
      _placesError = null;
    });
    _addressFocus.unfocus();
    try {
      final place = await places.resolvePlace(suggestion.placeId);
      if (!mounted) return;
      await _applyResolvedPlace(place, placeId: suggestion.placeId);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not load address: $e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _loadingLocation = false);
    }
  }

  Future<void> _useCurrentLocation() async {
    final places = _places;
    if (places == null) return;
    setState(() {
      _suggestions = [];
      _loadingLocation = true;
      _placesError = null;
    });
    _addressFocus.unfocus();
    try {
      final place = await places.currentLocation();
      if (!mounted) return;
      await _applyResolvedPlace(place);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _loadingLocation = false);
    }
  }

  Future<void> _applyResolvedPlace(ResolvedPlace place, {String placeId = ''}) async {
    if (_cities.isEmpty) {
      await _loadCities();
    }
    if (!mounted) return;
    final cityId = resolveCityIdFromPlace(place, _cities);
    _addressController.removeListener(_onAddressChanged);
    _addressController.text = place.streetLine.isNotEmpty ? place.streetLine : place.formattedAddress;
    _addressController.addListener(_onAddressChanged);

    final flow = context.read<BookingFlowProvider>();
    flow.setServiceAddress(
      address: _addressController.text,
      fullAddress: place.formattedAddress,
      latitude: place.latitude,
      longitude: place.longitude,
      placeId: placeId,
      clearLocationIds: true,
    );
    if (cityId != null) {
      await _loadLocations(cityId);
      if (!mounted) return;
      // Best-effort area match from Google sublocality / locality.
      final areaHint = (place.sublocality.isNotEmpty ? place.sublocality : place.locality)
          .trim()
          .toLowerCase();
      if (areaHint.isNotEmpty && _locations.isNotEmpty) {
        MasterLocation? match;
        for (final location in _locations) {
          final name = location.name.trim().toLowerCase();
          if (name == areaHint || name.contains(areaHint) || areaHint.contains(name)) {
            match = location;
            break;
          }
        }
        if (match != null) {
          flow.setServiceAddress(masterLocationId: match.id, area: match.name);
        }
      }
      if (flow.masterLocationId == null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('City set to ${flow.serviceCity}. Please confirm your area.'),
            backgroundColor: AppColors.warning,
          ),
        );
      }
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Address found — please select your city and area.'),
          backgroundColor: AppColors.warning,
        ),
      );
    }
  }

  Future<void> _openCityPicker() async {
    if (_loadingCities || _cities.isEmpty) return;
    final flow = context.read<BookingFlowProvider>();
    final selected = await showModalBottomSheet<MasterCity>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _LocationPickerSheet(
        title: 'Select city',
        subtitle: 'Service cities available for booking',
        icon: Icons.location_city_rounded,
        items: _cities
            .map((c) => _PickerItem(id: c.id, title: c.name, raw: c))
            .toList(),
        selectedId: flow.masterCityId,
        searchHint: 'Search city…',
      ),
    );
    if (selected == null || !mounted) return;
    flow.clearMasterLocation();
    await _loadLocations(selected.id);
  }

  Future<void> _openAreaPicker() async {
    final flow = context.read<BookingFlowProvider>();
    if (flow.masterCityId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Select a city first.'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }
    if (_loadingLocations) return;
    if (_locations.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No areas found for this city.'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }
    final selected = await showModalBottomSheet<MasterLocation>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _LocationPickerSheet(
        title: 'Select area',
        subtitle: flow.serviceCity.isEmpty ? 'Choose your service area' : 'Areas in ${flow.serviceCity}',
        icon: Icons.place_rounded,
        items: _locations
            .map((l) => _PickerItem(id: l.id, title: l.name, raw: l))
            .toList(),
        selectedId: flow.masterLocationId,
        searchHint: 'Search area…',
      ),
    );
    if (selected == null || !mounted) return;
    flow.setServiceAddress(masterLocationId: selected.id, area: selected.name);
  }

  @override
  Widget build(BuildContext context) {
    final flow = context.watch<BookingFlowProvider>();
    final selectedCity = _cities.where((c) => c.id == flow.masterCityId).toList();
    final cityLabel = flow.masterCityId == null
        ? 'Select city'
        : (selectedCity.isNotEmpty
            ? selectedCity.first.name
            : (flow.serviceCity.isEmpty ? 'Select city' : flow.serviceCity));
    final selectedArea = _locations.where((l) => l.id == flow.masterLocationId).toList();
    final areaLabel = flow.masterLocationId == null
        ? (flow.masterCityId == null ? 'Select city first' : 'Select area')
        : (selectedArea.isNotEmpty
            ? selectedArea.first.name
            : (flow.serviceArea.isEmpty ? 'Select area' : flow.serviceArea));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Search address',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 6),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: TextFormField(
                controller: _addressController,
                focusNode: _addressFocus,
                maxLines: 1,
                textInputAction: TextInputAction.search,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                decoration: InputDecoration(
                  isDense: true,
                  filled: true,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  prefixIcon: const Icon(Icons.search_rounded, size: 20, color: AppColors.primary),
                  hintText: 'Type 2+ letters to search Google…',
                  hintStyle: const TextStyle(fontSize: 13, color: AppColors.textHint),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: Colors.grey.shade300),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Material(
              color: AppColors.successBg,
              borderRadius: BorderRadius.circular(12),
              child: InkWell(
                onTap: _loadingLocation ? null : _useCurrentLocation,
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(
                  width: 48,
                  height: 48,
                  child: Center(
                    child: _loadingLocation
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                          )
                        : const Icon(Icons.my_location_rounded, color: AppColors.primary, size: 22),
                  ),
                ),
              ),
            ),
          ],
        ),
        if (_loadingSuggestions)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Row(
              children: [
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                ),
                SizedBox(width: 8),
                Text(
                  'Searching Google Maps…',
                  style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
        if (_placesError != null && _suggestions.isEmpty && !_loadingSuggestions)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              _placesError!,
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
          ),
        if (_suggestions.isNotEmpty) ...[
          const SizedBox(height: 8),
          Container(
            constraints: const BoxConstraints(maxHeight: 220),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade200),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.06),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ListView.separated(
              shrinkWrap: true,
              padding: const EdgeInsets.symmetric(vertical: 4),
              itemCount: _suggestions.length,
              separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
              itemBuilder: (context, index) {
                final item = _suggestions[index];
                return ListTile(
                  dense: true,
                  leading: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.successBg,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.place_rounded, color: AppColors.primary, size: 18),
                  ),
                  title: Text(
                    item.mainText,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    item.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                  ),
                  onTap: () => _selectSuggestion(item),
                );
              },
            ),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 6, left: 2),
            child: Text(
              'Powered by Google',
              style: TextStyle(fontSize: 10, color: AppColors.textMuted),
            ),
          ),
        ],
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: _PickerField(
                label: 'City',
                value: cityLabel,
                icon: Icons.location_city_rounded,
                loading: _loadingCities,
                enabled: !_loadingCities && _cities.isNotEmpty,
                onTap: _openCityPicker,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _PickerField(
                label: 'Area',
                value: areaLabel,
                icon: Icons.place_outlined,
                loading: _loadingLocations,
                enabled: !_loadingLocations && flow.masterCityId != null,
                onTap: _openAreaPicker,
              ),
            ),
          ],
        ),
        if (_loadError != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_loadError!, style: const TextStyle(fontSize: 11, color: AppColors.danger)),
          ),
      ],
    );
  }
}

class _PickerField extends StatelessWidget {
  const _PickerField({
    required this.label,
    required this.value,
    required this.icon,
    required this.onTap,
    this.loading = false,
    this.enabled = true,
  });

  final String label;
  final String value;
  final IconData icon;
  final VoidCallback onTap;
  final bool loading;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 6),
        Material(
          color: enabled ? Colors.white : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            onTap: enabled && !loading ? onTap : null,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              height: 48,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: Row(
                children: [
                  Icon(icon, size: 18, color: enabled ? AppColors.primary : AppColors.textMuted),
                  const SizedBox(width: 8),
                  Expanded(
                    child: loading
                        ? const Text(
                            'Loading…',
                            style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                          )
                        : Text(
                            value,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: enabled ? AppColors.textPrimary : AppColors.textMuted,
                            ),
                          ),
                  ),
                  Icon(
                    Icons.keyboard_arrow_down_rounded,
                    color: enabled ? AppColors.textSecondary : AppColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _PickerItem<T> {
  const _PickerItem({required this.id, required this.title, required this.raw});

  final int id;
  final String title;
  final T raw;
}

class _LocationPickerSheet<T> extends StatefulWidget {
  const _LocationPickerSheet({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.items,
    required this.searchHint,
    this.selectedId,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final List<_PickerItem<T>> items;
  final String searchHint;
  final int? selectedId;

  @override
  State<_LocationPickerSheet<T>> createState() => _LocationPickerSheetState<T>();
}

class _LocationPickerSheetState<T> extends State<_LocationPickerSheet<T>> {
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = widget.items.where((item) {
      if (_query.isEmpty) return true;
      return item.title.toLowerCase().contains(_query);
    }).toList();

    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.78,
        ),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 10),
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 12, 8),
              child: Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: AppColors.successBg,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(widget.icon, color: AppColors.primary, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.title,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          widget.subtitle,
                          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
              child: TextField(
                controller: _searchController,
                onChanged: (value) => setState(() => _query = value.trim().toLowerCase()),
                decoration: InputDecoration(
                  isDense: true,
                  filled: true,
                  fillColor: AppColors.surfaceMuted,
                  hintText: widget.searchHint,
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
            Expanded(
              child: filtered.isEmpty
                  ? const Center(
                      child: Text(
                        'No matches',
                        style: TextStyle(color: AppColors.textMuted),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(8, 0, 8, 24),
                      itemCount: filtered.length,
                      separatorBuilder: (_, __) => Divider(
                        height: 1,
                        indent: 62,
                        color: Colors.grey.shade100,
                      ),
                      itemBuilder: (context, index) {
                        final item = filtered[index];
                        final selected = item.id == widget.selectedId;
                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                          leading: Container(
                            width: 38,
                            height: 38,
                            decoration: BoxDecoration(
                              color: selected ? AppColors.primary : AppColors.successBg,
                              borderRadius: BorderRadius.circular(11),
                            ),
                            child: Icon(
                              Icons.place_rounded,
                              size: 18,
                              color: selected ? Colors.white : AppColors.primary,
                            ),
                          ),
                          title: Text(
                            item.title,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          trailing: selected
                              ? const Icon(Icons.check_circle_rounded, color: AppColors.primary)
                              : const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
                          onTap: () => Navigator.pop(context, item.raw),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
