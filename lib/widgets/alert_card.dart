import 'package:flutter/material.dart';
import '../models/alert.dart';
import '../theme/app_colors.dart';

/// Maps an [AlertStatus] to a display color, consistent with the risk
/// color semantics used elsewhere: open/urgent = red, in-review = amber,
/// closed = green.
Color _statusColor(AlertStatus status) {
  switch (status) {
    case AlertStatus.active:
      return AppColors.critical;
    case AlertStatus.watching:
    case AlertStatus.confirmed:
      return AppColors.watch;
    case AlertStatus.dismissed:
    case AlertStatus.resolved:
      return AppColors.stable;
  }
}

/// A single alert row: patient, reason, status, timestamp, and an
/// optional acknowledge action for still-open alerts.
class AlertCard extends StatelessWidget {
  const AlertCard({
    super.key,
    required this.alert,
    this.onAcknowledge,
    this.onTap,
    this.dense = false,
  });

  final Alert alert;
  final VoidCallback? onAcknowledge;
  final VoidCallback? onTap;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(alert.status);
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        hoverColor: AppColors.surfaceHover,
        child: Padding(
          padding: EdgeInsets.all(dense ? 12 : 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.only(right: 8),
                    decoration:
                        BoxDecoration(color: color, shape: BoxShape.circle),
                  ),
                  Expanded(
                    child: Text(
                      '${alert.patientName} · ${alert.bed}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13.5,
                        color: AppColors.textPrimary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: color.withValues(alpha: 0.35)),
                    ),
                    child: Text(
                      alert.status.label,
                      style: TextStyle(
                        color: color,
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 7),
              Text(
                alert.reason,
                style: const TextStyle(
                    fontSize: 12.5, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 9),
              Row(
                children: [
                  const Icon(Icons.schedule, size: 12, color: AppColors.textDim),
                  const SizedBox(width: 4),
                  Text(
                    alert.time,
                    style: const TextStyle(fontSize: 11, color: AppColors.textDim),
                  ),
                  if (alert.actor != '—') ...[
                    const SizedBox(width: 10),
                    const Icon(Icons.person_outline,
                        size: 12, color: AppColors.textDim),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        alert.actor,
                        style: const TextStyle(
                            fontSize: 11, color: AppColors.textDim),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ] else
                    const Spacer(),
                  if (alert.status.isOpen && onAcknowledge != null)
                    SizedBox(
                      height: 26,
                      child: OutlinedButton(
                        onPressed: onAcknowledge,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.textPrimary,
                          side: const BorderSide(color: AppColors.lineStrong),
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        child: const Text(
                          'Acknowledge',
                          style:
                              TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

