import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/app_colors.dart';

/// Official PestControl99 logo (original spray-can brand mark).
class Pc99Logo extends StatelessWidget {
  const Pc99Logo({
    super.key,
    this.height = 32,
    this.width,
  });

  final double height;
  final double? width;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/images/pc99_logo.png',
      height: height,
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (_, _, _) => Text(
        'PestControl99',
        style: TextStyle(
          color: AppColors.primary,
          fontWeight: FontWeight.w800,
          fontSize: height * 0.45,
        ),
      ),
    );
  }
}

class Pc99Scaffold extends StatelessWidget {
  const Pc99Scaffold({
    super.key,
    required this.child,
    this.title,
    this.brandTitle = false,
    this.onBack,
    this.showClose = false,
    this.greenHeader = false,
    this.floatingBottom,
    this.padding,
  });

  final Widget child;
  final String? title;
  final bool brandTitle;
  final VoidCallback? onBack;
  final bool showClose;
  final bool greenHeader;
  final Widget? floatingBottom;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final fg = greenHeader ? Colors.white : AppColors.textPrimary;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: floatingBottom == null,
        child: Column(
          children: [
            Container(
              color: greenHeader ? AppColors.primary : AppColors.surface,
              padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
              child: Row(
                children: [
                  if (onBack != null || showClose)
                    IconButton(
                      onPressed: onBack,
                      icon: Icon(
                        showClose ? Icons.close_rounded : Icons.arrow_back_ios_new_rounded,
                        size: showClose ? 22 : 18,
                        color: greenHeader ? Colors.white : AppColors.primary,
                      ),
                    )
                  else
                    const SizedBox(width: 48),
                  Expanded(
                    child: brandTitle
                        ? Center(
                            child: Pc99Logo(
                              height: greenHeader ? 30 : 34,
                            ),
                          )
                        : Text(
                            title ?? '',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: fg,
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                            ),
                          ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            if (!greenHeader) const Divider(height: 1, color: AppColors.divider),
            Expanded(
              child: Padding(
                padding: padding ?? EdgeInsets.zero,
                child: child,
              ),
            ),
            if (floatingBottom != null)
              SafeArea(
                top: false,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
                  decoration: const BoxDecoration(
                    color: AppColors.surface,
                    border: Border(top: BorderSide(color: AppColors.divider)),
                  ),
                  child: floatingBottom,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class Pc99PrimaryButton extends StatelessWidget {
  const Pc99PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        onPressed: busy ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.border,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
        child: busy
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Text(label),
      ),
    );
  }
}

class Pc99OutlineButton extends StatelessWidget {
  const Pc99OutlineButton({
    super.key,
    required this.label,
    required this.onPressed,
  });

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary, width: 1.4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
        child: Text(label),
      ),
    );
  }
}

class Pc99Card extends StatelessWidget {
  const Pc99Card({
    super.key,
    required this.child,
    this.onTap,
    this.padding = const EdgeInsets.all(14),
    this.selected = false,
    this.color,
  });

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry padding;
  final bool selected;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color ?? (selected ? AppColors.planSelectedBg : AppColors.surface),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: padding,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? AppColors.primary : AppColors.border,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}

class Pc99SectionTitle extends StatelessWidget {
  const Pc99SectionTitle(this.text, {super.key, this.action, this.onAction});

  final String text;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
        ),
        if (action != null)
          TextButton(
            onPressed: onAction,
            style: TextButton.styleFrom(
              foregroundColor: AppColors.primary,
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: Text(action!, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          ),
      ],
    );
  }
}

class Pc99StatusPill extends StatelessWidget {
  const Pc99StatusPill(this.label, {super.key, this.success = true});

  final String label;
  final bool success;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: success ? AppColors.successBg : const Color(0xFFFFEBEE),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: success ? AppColors.primary : AppColors.danger,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

IconData pc99PropertyIcon(String key) {
  switch (key) {
    case 'office':
      return Icons.apartment_rounded;
    case 'family':
      return Icons.favorite_outline_rounded;
    default:
      return Icons.home_outlined;
  }
}

IconData pc99ServiceIcon(String key) {
  switch (key) {
    case 'ant':
      return Icons.bug_report_outlined;
    case 'mosquito':
      return Icons.coronavirus_outlined;
    case 'termite':
      return Icons.carpenter_outlined;
    case 'fly':
      return Icons.bug_report_rounded;
    case 'lizard':
      return Icons.pets_outlined;
    case 'spider':
      return Icons.hub_outlined;
    case 'woodborer':
      return Icons.forest_outlined;
    case 'bee':
      return Icons.emoji_nature_outlined;
    case 'general':
      return Icons.grid_view_rounded;
    case 'bedbug':
      return Icons.bed_outlined;
    case 'rodent':
      return Icons.pest_control_rodent_outlined;
    default:
      return Icons.pest_control_outlined;
  }
}

class Pc99IconBubble extends StatelessWidget {
  const Pc99IconBubble({
    super.key,
    required this.icon,
    this.size = 42,
    this.iconSize = 22,
    this.filled = false,
  });

  final IconData icon;
  final double size;
  final double iconSize;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: filled ? AppColors.primary : AppColors.successSoft,
        borderRadius: BorderRadius.circular(size * 0.28),
      ),
      child: Icon(icon, size: iconSize, color: filled ? Colors.white : AppColors.primary),
    );
  }
}

class Pc99Radio extends StatelessWidget {
  const Pc99Radio({super.key, required this.selected, this.blue = false});

  final bool selected;
  final bool blue;

  @override
  Widget build(BuildContext context) {
    final color = blue ? AppColors.infoBlue : AppColors.primary;
    return Icon(
      selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
      color: selected ? color : AppColors.border,
      size: 22,
    );
  }
}

class Pc99CheckBox extends StatelessWidget {
  const Pc99CheckBox({super.key, required this.selected});

  final bool selected;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 140),
      width: 22,
      height: 22,
      decoration: BoxDecoration(
        color: selected ? AppColors.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: selected ? AppColors.primary : AppColors.border, width: 1.5),
      ),
      child: selected ? const Icon(Icons.check, size: 15, color: Colors.white) : null,
    );
  }
}

/// Centered empty-state prompt that attracts first-time users to book.
class Pc99EmptyBookPrompt extends StatelessWidget {
  const Pc99EmptyBookPrompt({
    super.key,
    required this.title,
    required this.subtitle,
    required this.onBook,
    this.buttonLabel = 'Book a Service',
  });

  final String title;
  final String subtitle;
  final VoidCallback onBook;
  final String buttonLabel;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: AppColors.successBg,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
              ),
              child: const Icon(Icons.calendar_month_rounded, size: 42, color: AppColors.primary),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13.5, color: AppColors.textMuted, height: 1.35),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: onBook,
                icon: const Icon(Icons.add_rounded, size: 22),
                label: Text(buttonLabel, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> pc99Copy(BuildContext context, String text, {String label = 'Copied'}) async {
  await Clipboard.setData(ClipboardData(text: text));
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(label), backgroundColor: AppColors.primary),
  );
}
