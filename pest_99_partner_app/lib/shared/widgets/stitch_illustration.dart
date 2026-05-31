import 'package:flutter/material.dart';

/// Stitch design-system hero illustration used on auth and empty states.
class StitchIllustration extends StatelessWidget {
  const StitchIllustration({
    super.key,
    required this.asset,
    this.height = 220,
    this.fit = BoxFit.contain,
    this.semanticLabel,
  });

  final String asset;
  final double height;
  final BoxFit fit;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel,
      child: Image.asset(
        asset,
        height: height,
        width: double.infinity,
        fit: fit,
        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
      ),
    );
  }
}
