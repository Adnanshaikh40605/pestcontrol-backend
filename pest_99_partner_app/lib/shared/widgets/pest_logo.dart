import 'package:flutter/material.dart';

import '../../core/constants/app_assets.dart';

/// Official Pest Control 99 brand mark (matches Customer App).
class PestLogo extends StatelessWidget {
  const PestLogo({super.key, this.height = 32, this.width});

  final double height;
  final double? width;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      AppAssets.logo,
      height: height,
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (_, _, _) => Text(
        'PestControl99',
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          fontSize: height * 0.4,
        ),
      ),
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
      padding: const EdgeInsets.all(12),
      child: Image.asset(
        AppAssets.logo,
        fit: BoxFit.contain,
        filterQuality: FilterQuality.high,
      ),
    );
  }
}
