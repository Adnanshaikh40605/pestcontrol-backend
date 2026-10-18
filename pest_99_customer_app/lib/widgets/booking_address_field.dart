import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme/app_colors.dart';
import '../providers/booking_flow_provider.dart';
import '../services/places_service.dart';

/// Website-style address field: Google Places suggestions + inline GPS locate.
/// Uses the backend Places proxy (`/api/customer/places/…`) — same as ServiceAddressSection.
///
/// Height/chrome match `.booking-address-input` + `.booking-gps-btn` in globals.css:
/// fixed height, 1.5px `#dbe8df` border, 8px radius, 28×28 soft-green locate button.
class BookingAddressField extends StatefulWidget {
  const BookingAddressField({
    super.key,
    required this.controller,
    required this.height,
    required this.decoration,
    this.errorText,
    this.errorBorder = false,
    this.scrollPadding = const EdgeInsets.all(20),
  });

  final TextEditingController controller;
  final double height;
  final InputDecoration decoration;
  final String? errorText;
  final bool errorBorder;
  final EdgeInsets scrollPadding;

  @override
  State<BookingAddressField> createState() => _BookingAddressFieldState();
}

class _BookingAddressFieldState extends State<BookingAddressField> {
  static const _green = Color(0xFF078B4F);
  static const _line = Color(0xFFE4E9F0);
  static const _navy = Color(0xFF102E68);

  final _focus = FocusNode();
  final _debouncer = Debouncer(milliseconds: 700);
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
    const gpsSize = 22.0;
    final deco = widget.decoration.copyWith(
      contentPadding: const EdgeInsets.fromLTRB(26, 0, gpsSize + 8, 0),
      suffixIcon: null,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: widget.height,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: widget.errorBorder ? const Color(0xFFE23B3B) : _line,
            ),
          ),
          child: Stack(
            alignment: Alignment.centerRight,
            children: [
              TextField(
                controller: widget.controller,
                focusNode: _focus,
                textInputAction: TextInputAction.search,
                textAlignVertical: TextAlignVertical.center,
                scrollPadding: widget.scrollPadding,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  height: 1.2,
                  color: _navy,
                ),
                decoration: deco,
              ),
              const Positioned(
                left: 8,
                child: Icon(Icons.location_on_outlined, size: 16, color: _green),
              ),
              Positioned(
                right: 2,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _locating ? null : _useCurrentLocation,
                    customBorder: const CircleBorder(),
                    child: SizedBox(
                      width: gpsSize,
                      height: gpsSize,
                      child: Center(
                        child: _locating
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: _green,
                                ),
                              )
                            : const _LocateGlyph(),
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
                  child: CircularProgressIndicator(strokeWidth: 2, color: _green),
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
        if (_placesHint != null &&
            _suggestions.isEmpty &&
            !_loadingSuggestions &&
            widget.errorText == null)
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
              border: Border.all(color: _line),
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
                        const Icon(Icons.place_rounded, size: 16, color: _green),
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

/// Website locate mark: outer ring, inner ring, and four ticks.
class _LocateGlyph extends StatelessWidget {
  const _LocateGlyph();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(16, 16),
      painter: _LocateGlyphPainter(),
    );
  }
}

class _LocateGlyphPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF078B4F)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..strokeCap = StrokeCap.round;
    final c = Offset(size.width / 2, size.height / 2);
    canvas.drawCircle(c, 2.1, paint);
    canvas.drawCircle(c, 4.8, paint);
    canvas.drawLine(Offset(c.dx, 0.6), Offset(c.dx, 2.4), paint);
    canvas.drawLine(Offset(c.dx, size.height - 2.4), Offset(c.dx, size.height - 0.6), paint);
    canvas.drawLine(Offset(0.6, c.dy), Offset(2.4, c.dy), paint);
    canvas.drawLine(Offset(size.width - 2.4, c.dy), Offset(size.width - 0.6, c.dy), paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
