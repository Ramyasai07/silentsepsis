import 'package:flutter/material.dart';
import '../models/alert.dart';
import '../repositories/alert_repository.dart';
import '../theme/app_colors.dart';
import '../widgets/alert_card.dart';

/// Active alerts and alert history for the ward, with an acknowledge
/// action for anything still open.
class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key, required this.alertRepository});

  final AlertRepository alertRepository;

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  late Future<List<Alert>> _future;
  bool _activeOnly = true;

  @override
  void initState() {
    super.initState();
    _future = widget.alertRepository.getAlerts();
  }

  Future<void> _acknowledge(Alert alert) async {
    await widget.alertRepository.acknowledge(alert.id);
    if (!mounted) return;
    setState(() => _future = widget.alertRepository.getAlerts());
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Acknowledged alert for ${alert.patientName}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Padding(
        padding: const EdgeInsets.fromLTRB(28, 24, 28, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  'Alerts',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    letterSpacing: -0.3,
                  ),
                ),
                const Spacer(),
                _FilterChip(
                  label: 'Active',
                  selected: _activeOnly,
                  onTap: () => setState(() => _activeOnly = true),
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'All history',
                  selected: !_activeOnly,
                  onTap: () => setState(() => _activeOnly = false),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Expanded(
              child: FutureBuilder<List<Alert>>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        'Could not load alerts: ${snapshot.error}',
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textDim),
                      ),
                    );
                  }
                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final all = snapshot.data!;
                  final shown =
                      _activeOnly ? all.where((a) => a.status.isOpen).toList() : all;

                  if (shown.isEmpty) {
                    return const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.check_circle_outline,
                              size: 30, color: AppColors.stable),
                          SizedBox(height: 10),
                          Text('No active alerts',
                              style: TextStyle(
                                  fontSize: 12.5, color: AppColors.textSecondary)),
                        ],
                      ),
                    );
                  }

                  return ListView.separated(
                    itemCount: shown.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final alert = shown[i];
                      return AlertCard(
                        alert: alert,
                        onAcknowledge:
                            alert.status.isOpen ? () => _acknowledge(alert) : null,
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? AppColors.accentDim : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: selected ? AppColors.accent.withValues(alpha: 0.4) : AppColors.lineStrong,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
            color: selected ? AppColors.accentStrong : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}

