import 'package:flutter/material.dart';
import '../models/patient.dart';
import 'app_colors.dart';

/// Four-band clinical priority used for display purposes wherever a
/// numeric 0-100 risk score is available. This sits alongside (and is
/// derived from) the three-state [RiskTier] on the Patient model — it
/// does not replace it, since the model itself is not modified here.
enum RiskLevel { low, moderate, high, critical }

/// Maps risk tiers and numeric risk scores to color/label, kept in one
/// place so risk semantics stay consistent across every screen.
class RiskColors {
  RiskColors._();

  // --- Three-tier (RiskTier) helpers, used where only the tier is known ---

  static Color foreground(RiskTier tier) {
    switch (tier) {
      case RiskTier.critical:
        return AppColors.critical;
      case RiskTier.watch:
        return AppColors.watch;
      case RiskTier.stable:
        return AppColors.stable;
    }
  }

  static Color background(RiskTier tier) {
    switch (tier) {
      case RiskTier.critical:
        return AppColors.criticalDim;
      case RiskTier.watch:
        return AppColors.watchDim;
      case RiskTier.stable:
        return AppColors.stableDim;
    }
  }

  /// Risk tier derived from a raw 0-100 score.
  static RiskTier tierForScore(int score) {
    if (score >= 75) return RiskTier.critical;
    if (score >= 30) return RiskTier.watch;
    return RiskTier.stable;
  }

  // --- Four-band (RiskLevel) helpers, used for the compact priority ---
  // --- indicators the dashboard/table/detail views are built around.  ---

  /// Clinical priority band derived from a raw 0-100 risk score.
  /// Thresholds are consistent with [tierForScore]: everything below the
  /// "watch" tier is Low, everything at or above the "critical" tier is
  /// Critical, and the watch band is split into Moderate/High.
  static RiskLevel levelForScore(int score) {
    if (score >= 75) return RiskLevel.critical;
    if (score >= 50) return RiskLevel.high;
    if (score >= 30) return RiskLevel.moderate;
    return RiskLevel.low;
  }

  static Color levelColor(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return AppColors.riskLow;
      case RiskLevel.moderate:
        return AppColors.riskModerate;
      case RiskLevel.high:
        return AppColors.riskHigh;
      case RiskLevel.critical:
        return AppColors.riskCritical;
    }
  }

  static Color levelBackground(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return AppColors.riskLowDim;
      case RiskLevel.moderate:
        return AppColors.riskModerateDim;
      case RiskLevel.high:
        return AppColors.riskHighDim;
      case RiskLevel.critical:
        return AppColors.riskCriticalDim;
    }
  }

  static String levelLabel(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return 'Low';
      case RiskLevel.moderate:
        return 'Moderate';
      case RiskLevel.high:
        return 'High';
      case RiskLevel.critical:
        return 'Critical';
    }
  }

  /// Convenience: color for a patient's numeric risk score.
  static Color colorForScore(int score) => levelColor(levelForScore(score));
}

