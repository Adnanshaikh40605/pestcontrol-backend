import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

abstract final class AppTypography {
  static TextTheme textTheme = TextTheme(
    displayLarge: GoogleFonts.manrope(
      fontSize: 40,
      fontWeight: FontWeight.w800,
      height: 1.0,
      letterSpacing: -0.015,
      color: AppColors.onPrimary,
    ),
    headlineLarge: GoogleFonts.manrope(
      fontSize: 32,
      fontWeight: FontWeight.w800,
      height: 1.25,
      letterSpacing: -0.015,
      color: AppColors.textPrimary,
    ),
    headlineMedium: GoogleFonts.manrope(
      fontSize: 24,
      fontWeight: FontWeight.w800,
      height: 32 / 24,
      color: AppColors.textPrimary,
    ),
    headlineSmall: GoogleFonts.manrope(
      fontSize: 18,
      fontWeight: FontWeight.w600,
      height: 24 / 18,
      color: AppColors.textPrimary,
    ),
    titleMedium: GoogleFonts.manrope(
      fontSize: 20,
      fontWeight: FontWeight.w700,
      height: 28 / 20,
      color: AppColors.textPrimary,
    ),
    bodyLarge: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w500,
      height: 24 / 16,
      color: AppColors.textPrimary,
    ),
    bodyMedium: GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: 20 / 14,
      color: AppColors.textPrimary,
    ),
    labelLarge: GoogleFonts.inter(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      height: 18 / 13,
      letterSpacing: 0.02,
      color: AppColors.textPrimary,
    ),
    labelSmall: GoogleFonts.inter(
      fontSize: 11,
      fontWeight: FontWeight.w700,
      height: 16 / 11,
      letterSpacing: 0.05,
      color: AppColors.textSecondary,
    ),
  );
}
