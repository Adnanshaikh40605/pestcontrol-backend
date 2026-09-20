import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../providers/booking_flow_provider.dart';
import '../services/places_service.dart';

/// Website-style address field: Google Places suggestions + inline GPS locate.
/// Uses the backend Places proxy (`/api/customer/places/…`) — same as ServiceAddressSection.
class BookingAddressField extends StatefulWidget {
  const BookingAddressField({
    super.key,
    required this.controller,
    required this.height,
    required this.decoration,
    this.errorText,
  });

  final TextEditingController controller;
  final double height;
  final InputDecoration decoration;
  final String? errorText;

  @override
  State<BookingAddressField> createState() => _BookingAddressFieldState();
}

class _BookingAddressFieldState extends State<BookingAddressField> {
  final _focus = FocusNode();
  final _debouncer = Debouncer(milliseconds: 300);
  PlacesService? _places;

  List<PlaceSuggestion> _suggestions = [];
  bool _loadingSuggestions = false;
  bool _locating = false;
  String? _placesHint;

  @override
  void initState() {
    super.initState();
    _places = PlacesService(context.read<ApiClient>());
    widget.controller.addListener(_onTextChanged);
    _focus.addListener(() {
      if (!_focus.hasFocus) {
        Future<void>.delayed(const Duration(milliseconds: 180), () {
          if (!mounted || _focus.hasFocus) return;
          setState(() => _suggestions = []);
        });
      }
    });
  }

  @override
  void dispose() {
    _debouncer.dispose();
    widget.controller.removeListener(_onTextChanged);
    _focus.dispose();
    super.dispose();
  }

  void _onTextChanged() {
    final flow = context.read<BookingFlowProvider>();
    final text = widget.controller.text;
    // Avoid notifyListeners during parent rebuild sync when texts already match.
    if (flow.streetAddress != text) {
      flow.setStreetAddress(text);
    }
    _debouncer.run(_fetchSuggestions);
  }

  Future<void> _fetchSuggestions() async {
    final places = _places;
    if (places == null) return;
    final query = widget.controller.text.trim();
    // Match website MIN_SEARCH_LENGTH (3).
    if (query.length < 3) {
      if (!mounted) return;
      setState(() {
        _suggestions = [];
        _loadingSuggestions = false;
        _placesHint = query.isEmpty ? null : 'Type at least 3 characters to search';
      });
      return;
    }
    setState(() {
      _loadingSuggestions = true;
      _placesHint = null;
    });
    try {
      final suggestions = await places.autocomplete(query);
      if (!mounted) return;
      if (widget.controller.text.trim() != query) return;
      setState(() {
        _suggestions = suggestions;
        _loadingSuggestions = false;
        if (suggestions.isEmpty) {
          _placesHint = 'No matching addresses. Try a fuller street or landmark.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _suggestions = [];
        _loadingSuggestions = false;
        _placesHint = '$e';
      });
    }
  }

  Future<void> _selectSuggestion(PlaceSuggestion suggestion) async {
    final places = _places;
    if (places == null) return;
    setState(() {
      _suggestions = [];
      _locating = true;
      _placesHint = null;
    });
    _focus.unfocus();
    try {
      final place = await places.resolvePlace(suggestion.placeId);
      if (!mounted) return;
      _applyPlace(place, placeId: suggestion.placeId);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not load address: $e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _useCurrentLocation() async {
    final places = _places;
    if (places == null) return;
    setState(() {
      _suggestions = [];
      _locating = true;
      _placesHint = null;
    });
    _focus.unfocus();
    try {
      final place = await places.currentLocation();
      if (!mounted) return;
      _applyPlace(place);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e'), backgroundColor: AppColors.danger),
      );
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _applyPlace(ResolvedPlace place, {String placeId = ''}) {
    final address = place.formattedAddress.isNotEmpty
        ? place.formattedAddress
        : (place.streetLine.isNotEmpty ? place.streetLine : place.formattedAddress);
    widget.controller.removeListener(_onTextChanged);
    widget.controller.text = address;
    widget.controller.addListener(_onTextChanged);

    final city = place.locality.isNotEmpty
        ? place.locality
        : (place.cityHint.isNotEmpty ? place.cityHint : '');
    context.read<BookingFlowProvider>().setServiceAddress(
          address: address,
          fullAddress: place.formattedAddress,
          placeId: placeId,
          city: city,
          area: place.sublocality,
          latitude: place.latitude,
          longitude: place.longitude,
          clearLocationIds: true,
        );
  }

  @override
  Widget build(BuildContext context) {
    final deco = widget.decoration.copyWith(
      // Room for the GPS button on the right.
      contentPadding: const EdgeInsets.fromLTRB(10, 0, 44, 0),
      suffixIcon: null,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          height: widget.height,
          child: Stack(
            alignment: Alignment.centerRight,
            children: [
              TextField(
                controller: widget.controller,
                focusNode: _focus,
                textInputAction: TextInputAction.search,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1B2A22),
                ),
                decoration: deco,
              ),
              Positioned(
                right: 4,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _locating ? null : _useCurrentLocation,
                    borderRadius: BorderRadius.circular(8),
                    child: SizedBox(
                      width: 36,
                      height: 36,
                      child: Center(
                        child: _locating
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Color(0xFF087B3D),
                                ),
                              )
                            : const Icon(
                                Icons.my_location_rounded,
                                size: 18,
                                color: Color(0xFF087B3D),
                              ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        if (_loadingSuggestions)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Row(
              children: [
                SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF087B3D)),
                ),
                SizedBox(width: 6),
                Text(
                  'Searching addresses…',
                  style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
        if (widget.errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text(
              widget.errorText!,
              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.red),
            ),
          ),
        if (_placesHint != null && _suggestions.isEmpty && !_loadingSuggestions && widget.errorText == null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              _placesHint!,
              style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
            ),
          ),
        if (_suggestions.isNotEmpty) ...[
          const SizedBox(height: 6),
          Container(
            constraints: const BoxConstraints(maxHeight: 200),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFDBE8DF)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.06),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: ListView.separated(
              shrinkWrap: true,
              padding: const EdgeInsets.symmetric(vertical: 2),
              itemCount: _suggestions.length,
              separatorBuilder: (_, _) => const Divider(height: 1, color: Color(0xFFEFF4F0)),
              itemBuilder: (context, index) {
                final item = _suggestions[index];
                return InkWell(
                  onTap: () => _selectSuggestion(item),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    child: Row(
                      children: [
                        const Icon(Icons.place_rounded, size: 16, color: Color(0xFF087B3D)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.mainText,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF1B2A22),
                                ),
                              ),
                              Text(
                                item.description,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 10.5, color: AppColors.textSecondary),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 4, left: 2),
            child: Text(
              'Powered by Google',
              style: TextStyle(fontSize: 9, color: AppColors.textMuted),
            ),
          ),
        ],
      ],
    );
  }
}
