import 'package:flutter/material.dart';
import '../theme/risk_colors.dart';

/// A small pill showing a clinical priority label derived from a numeric
/// 0-100 risk score, e.g. "Critical". Colors are reserved for this one
/// purpose across the app.
class RiskBadge extends StatelessWidget {
  const RiskBadge({super.key, required this.score, this.dense = false});

  final int score;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final level = RiskColors.levelForScore(score);
    final fg = RiskColors.levelColor(level);
    final bg = RiskColors.levelBackground(level);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 7 : 9,
        vertical: dense ? 2.5 : 4,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: fg.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
          ),
          const SizedBox(width: 5),
          Text(
            RiskColors.levelLabel(level),
            style: TextStyle(
              color: fg,
              fontSize: dense ? 10.5 : 11.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// A compact circular readout of a 0-100 risk score, tinted by its
/// clinical priority band.
class RiskScoreDial extends StatelessWidget {
  const RiskScoreDial({super.key, required this.score, this.size = 44});

  final int score;
  final double size;

  @override
  Widget build(BuildContext context) {
    final level = RiskColors.levelForScore(score);
    final fg = RiskColors.levelColor(level);
    final bg = RiskColors.levelBackground(level);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: bg,
        shape: BoxShape.circle,
        border: Border.all(color: fg.withValues(alpha: 0.45), width: 1.4),
      ),
      alignment: Alignment.center,
      child: Text(
        '$score',
        style: TextStyle(
          color: fg,
          fontSize: size * 0.34,
          fontWeight: FontWeight.w700,
          height: 1,
        ),
      ),
    );
  }
}

/// A small filled dot used as a minimal status indicator, colored by
/// clinical priority band.
class RiskDot extends StatelessWidget {
  const RiskDot({super.key, required this.score, this.size = 7});

  final int score;
  final double size;

  @override
  Widget build(BuildContext context) {
    final color = RiskColors.colorForScore(score);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

