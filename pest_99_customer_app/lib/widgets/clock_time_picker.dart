import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Website-style 12-hour clock. One ring of hours, then one ring of minutes.
/// AM and PM stay as two buttons. There is no 24-hour inner ring and no keyboard.
Future<(int, int)?> showClockTimePicker(
  BuildContext context, {
  required int hour24,
  required int minute,
}) {
  return showDialog<(int, int)>(
    context: context,
    barrierColor: const Color(0x61092456),
    builder: (context) => ClockTimePickerDialog(hour24: hour24, minute: minute),
  );
}

class ClockTimePickerDialog extends StatefulWidget {
  const ClockTimePickerDialog({
    super.key,
    required this.hour24,
    required this.minute,
  });

  final int hour24;
  final int minute;

  @override
  State<ClockTimePickerDialog> createState() => _ClockTimePickerDialogState();
}

class _ClockTimePickerDialogState extends State<ClockTimePickerDialog> {
  static const _green = Color(0xFF087B3D);
  static const _navy = Color(0xFF092456);
  static const _face = Color(0xFFE8F5EE);
  static const _sheet = Color(0xFFF7FBF8);
  static const _hours = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
  static const _minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

  late int _hour12;
  late int _minute;
  late bool _pm;
  bool _pickingHour = true;
  int _hourPick = 0;

  @override
  void initState() {
    super.initState();
    final hour = widget.hour24.clamp(0, 23);
    _pm = hour >= 12;
    final display = hour % 12;
    _hour12 = display == 0 ? 12 : display;
    _minute = _snapMinute(widget.minute);
  }

  int _snapMinute(int minute) {
    final stepped = ((minute / 5).round() * 5).clamp(0, 55);
    return stepped.toInt();
  }

  int get _hour24 {
    if (_pm) return _hour12 == 12 ? 12 : _hour12 + 12;
    return _hour12 == 12 ? 0 : _hour12;
  }

  void _pickHour(int hour) {
    final pick = ++_hourPick;
    setState(() => _hour12 = hour);
    Future<void>.delayed(const Duration(milliseconds: 160), () {
      if (!mounted || pick != _hourPick || !_pickingHour) return;
      setState(() => _pickingHour = false);
    });
  }

  void _showHours() {
    _hourPick++;
    setState(() => _pickingHour = true);
  }

  void _showMinutes() {
    _hourPick++;
    setState(() => _pickingHour = false);
  }

  void _pickMinute(int minute) {
    Navigator.of(context).pop((_hour24, minute));
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 300),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final face = math.min(248.0, math.max(160.0, constraints.maxWidth - 16));
            return SingleChildScrollView(child: _dialogBody(face));
          },
        ),
      ),
    );
  }

  Widget _dialogBody(double face) {
    final items = _pickingHour ? _hours : _minutes;
    final selected = _pickingHour ? _hour12 : _minute;
    return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _Digit(
                        label: _hour12.toString().padLeft(2, '0'),
                        active: _pickingHour,
                        onTap: _showHours,
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 2),
                        child: Text(
                          ':',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.w900,
                            color: Color(0x59092456),
                            height: 1,
                          ),
                        ),
                      ),
                      _Digit(
                        label: _minute.toString().padLeft(2, '0'),
                        active: !_pickingHour,
                        onTap: _showMinutes,
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _PeriodButton(
                        label: 'AM',
                        selected: !_pm,
                        onTap: () => setState(() => _pm = false),
                      ),
                      const SizedBox(width: 8),
                      _PeriodButton(
                        label: 'PM',
                        selected: _pm,
                        onTap: () => setState(() => _pm = true),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            ColoredBox(
              color: _sheet,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(8, 10, 8, 8),
                child: Column(
                  children: [
                    _ClockFace(
                      size: face,
                      items: items,
                      selected: selected,
                      minutes: !_pickingHour,
                      faceColor: _face,
                      selectedColor: _green,
                      labelColor: _navy,
                      onPick: _pickingHour ? _pickHour : _pickMinute,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _pickingHour ? 'Tap an hour, then the minutes' : 'Minutes are in steps of 5',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
              child: Row(
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text(
                      'CANCEL',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (!_pickingHour)
                    TextButton(
                      onPressed: _showHours,
                      child: const Text(
                        '← HOUR',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: _green,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        );
  }
}

class _Digit extends StatelessWidget {
  const _Digit({required this.label, required this.active, required this.onTap});

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 36,
            fontWeight: FontWeight.w900,
            height: 1,
            letterSpacing: -0.5,
            color: active ? const Color(0xFF087B3D) : const Color(0x66092456),
          ),
        ),
      ),
    );
  }
}

class _PeriodButton extends StatelessWidget {
  const _PeriodButton({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFF087B3D) : Colors.transparent,
      shape: StadiumBorder(
        side: BorderSide(color: selected ? const Color(0xFF087B3D) : const Color(0xFFDBE8DF), width: 1.5),
      ),
      child: InkWell(
        key: Key('clock-ampm-$label'),
        onTap: onTap,
        customBorder: const StadiumBorder(),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
              color: selected ? Colors.white : const Color(0xFF092456),
            ),
          ),
        ),
      ),
    );
  }
}

class _ClockFace extends StatelessWidget {
  const _ClockFace({
    required this.size,
    required this.items,
    required this.selected,
    required this.minutes,
    required this.faceColor,
    required this.selectedColor,
    required this.labelColor,
    required this.onPick,
  });

  final double size;
  final List<int> items;
  final int selected;
  final bool minutes;
  final Color faceColor;
  final Color selectedColor;
  final Color labelColor;
  final ValueChanged<int> onPick;

  @override
  Widget build(BuildContext context) {
    final center = size / 2;
    final radius = size * (92 / 248);
    final selectedIndex = items.indexOf(selected);
    final disc = size * (216 / 248);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: disc,
            height: disc,
            decoration: BoxDecoration(color: faceColor, shape: BoxShape.circle),
          ),
          if (selectedIndex >= 0)
            CustomPaint(
              size: Size(size, size),
              painter: _HandPainter(
                index: selectedIndex,
                count: items.length,
                radius: radius,
                color: selectedColor,
              ),
            ),
          for (var i = 0; i < items.length; i++)
            _ClockNumber(
              index: i,
              count: items.length,
              value: items[i],
              minutes: minutes,
              selected: items[i] == selected,
              center: center,
              radius: radius,
              hit: math.min(44.0, radius * 0.46),
              selectedColor: selectedColor,
              labelColor: labelColor,
              onPick: onPick,
            ),
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: labelColor, shape: BoxShape.circle),
          ),
        ],
      ),
    );
  }
}

class _ClockNumber extends StatelessWidget {
  const _ClockNumber({
    required this.index,
    required this.count,
    required this.value,
    required this.minutes,
    required this.selected,
    required this.center,
    required this.radius,
    required this.hit,
    required this.selectedColor,
    required this.labelColor,
    required this.onPick,
  });

  final int index;
  final int count;
  final int value;
  final bool minutes;
  final bool selected;
  final double center;
  final double radius;
  final double hit;
  final Color selectedColor;
  final Color labelColor;
  final ValueChanged<int> onPick;

  @override
  Widget build(BuildContext context) {
    final angle = ((index / count) * 360 - 90) * math.pi / 180;
    final dx = math.cos(angle) * radius;
    final dy = math.sin(angle) * radius;
    final label = minutes ? value.toString().padLeft(2, '0') : '$value';
    return Positioned(
      left: center + dx - hit / 2,
      top: center + dy - hit / 2,
      width: hit,
      height: hit,
      child: Material(
        color: selected ? selectedColor : Colors.transparent,
        shape: const CircleBorder(),
        child: InkWell(
          key: Key(minutes ? 'clock-min-$value' : 'clock-hour-$value'),
          customBorder: const CircleBorder(),
          onTap: () => onPick(value),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: minutes ? 12 : 16,
                fontWeight: FontWeight.w800,
                color: selected ? Colors.white : labelColor,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HandPainter extends CustomPainter {
  const _HandPainter({
    required this.index,
    required this.count,
    required this.radius,
    required this.color,
  });

  final int index;
  final int count;
  final double radius;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final angle = ((index / count) * 360 - 90) * math.pi / 180;
    final center = Offset(size.width / 2, size.height / 2);
    final end = center + Offset(math.cos(angle) * radius, math.sin(angle) * radius);
    canvas.drawLine(
      center,
      end,
      Paint()
        ..color = color
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant _HandPainter oldDelegate) =>
      oldDelegate.index != index || oldDelegate.color != color;
}
