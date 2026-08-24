import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// One vital sign readout, e.g. "Heart rate", used in the patient detail
/// vitals grid.
class VitalTile extends StatelessWidget {
  const VitalTile({
    super.key,
    required this.label,
    required this.value,
    required this.unit,
    required this.icon,
    this.isAbnormal = false,
  });

  final String label;
  final String value;
  final String unit;
  final IconData icon;
  final bool isAbnormal;

  @override
  Widget build(BuildContext context) {
    final tint = isAbnormal ? AppColors.watch : AppColors.textDim;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: isAbnormal ? AppColors.watch.withValues(alpha: 0.4) : AppColors.line,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: tint),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (isAbnormal)
                const Icon(Icons.priority_high_rounded,
                    size: 13, color: AppColors.watch),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                value,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(width: 3),
              Text(
                unit,
                style: const TextStyle(fontSize: 11.5, color: AppColors.textDim),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

