import 'package:flutter/material.dart';

import '../../core/constants/app_assets.dart';

class PestLogo extends StatelessWidget {
  const PestLogo({super.key, this.height = 32});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      AppAssets.logo,
      height: height,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => const Icon(Icons.shield, color: Colors.white),
    );
  }
}

class PestLogoCard extends StatelessWidget {
  const PestLogoCard({super.key, this.size = 112});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE4E7EC)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(8),
      child: Image.asset(AppAssets.logo, fit: BoxFit.contain),
    );
  }
}
