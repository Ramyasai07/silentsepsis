import 'package:flutter/material.dart';

/// Central color palette for the SilentSepsis clinical dashboard.
///
/// Dark, restrained "operations console" tone rather than an AI-startup
/// look: near-black surfaces, a single muted slate-blue accent, and
/// desaturated risk colors that are reserved for genuine clinical
/// priority signaling rather than decoration.
class AppColors {
  AppColors._();

  // Backgrounds / surfaces — layered near-black, not pure black.
  static const Color background = Color(0xFF0B0D10);
  static const Color surface = Color(0xFF13161B);
  static const Color surfaceRaised = Color(0xFF181C22);
  static const Color surfaceSunken = Color(0xFF0E1013);
  static const Color surfaceHover = Color(0xFF1E232B);

  // Borders — subtle 1px hairlines, never heavy.
  static const Color line = Color(0xFF232830);
  static const Color lineStrong = Color(0xFF313841);

  // Text.
  static const Color textPrimary = Color(0xFFE9EBEE);
  static const Color textSecondary = Color(0xFF9AA1AC);
  static const Color textDim = Color(0xFF666E7A);

  // Accent — muted slate blue, used sparingly for interactive elements.
  static const Color accent = Color(0xFF6E8FC9);
  static const Color accentDim = Color(0xFF1C2531);
  static const Color accentStrong = Color(0xFF88A6D9);

  // Risk tiers (3-state model, matches RiskTier on the Patient model).
  static const Color stable = Color(0xFF5FA37B);
  static const Color stableDim = Color(0xFF16241C);
  static const Color watch = Color(0xFFD1A13F);
  static const Color watchDim = Color(0xFF2A2216);
  static const Color critical = Color(0xFFD9614C);
  static const Color criticalDim = Color(0xFF2C1815);

  // Four-band clinical priority colors (derived from numeric risk score).
  static const Color riskLow = Color(0xFF5FA37B);
  static const Color riskLowDim = Color(0xFF16241C);
  static const Color riskModerate = Color(0xFFD1A13F);
  static const Color riskModerateDim = Color(0xFF2A2216);
  static const Color riskHigh = Color(0xFFE08A3C);
  static const Color riskHighDim = Color(0xFF2B2013);
  static const Color riskCritical = Color(0xFFDC5B4C);
  static const Color riskCriticalDim = Color(0xFF2C1815);
}

