import 'package:flutter/material.dart';
import '../models/alert.dart';
import '../models/patient.dart';
import '../repositories/alert_repository.dart';
import '../repositories/patient_repository.dart';
import '../theme/app_colors.dart';
import '../theme/risk_colors.dart';
import '../widgets/alert_card.dart';
import '../widgets/patient_table.dart';
import '../widgets/section_header.dart';
import '../widgets/sparkline.dart';
import '../widgets/stat_card.dart';
import 'patient_detail_screen.dart';

/// System overview: compact header, headline counts, the patient
/// monitoring table (top by risk), recent alerts, and a trend
/// visualization for the highest-priority patient. All values are
/// computed from real API data — nothing here is invented.
class OverviewScreen extends StatefulWidget {
  const OverviewScreen({
    super.key,
    required this.patientRepository,
    required this.alertRepository,
    this.onSeeAllAlerts,
    this.onSeeAllPatients,
  });

  final PatientRepository patientRepository;
  final AlertRepository alertRepository;
  final VoidCallback? onSeeAllAlerts;
  final VoidCallback? onSeeAllPatients;

  @override
  State<OverviewScreen> createState() => _OverviewScreenState();
}

class _OverviewScreenState extends State<OverviewScreen> {
  late Future<_OverviewData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_OverviewData> _load() async {
    final patients = await widget.patientRepository.getPatients();
    final alerts = await widget.alertRepository.getAlerts();
    return _OverviewData(patients: patients, alerts: alerts);
  }

  Future<void> _refresh() async {
    final data = await _load();
    if (!mounted) return;
    setState(() => _future = Future.value(data));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_OverviewData>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return _ErrorState(error: snapshot.error.toString(), onRetry: _refresh);
        }
        if (!snapshot.hasData) {
          return const Scaffold(
            backgroundColor: AppColors.background,
            body: Center(child: CircularProgressIndicator()),
          );
        }
        final data = snapshot.data!;
        final wardCount = data.patients.map((p) => p.ward).toSet().length;
        final activeAlerts = data.alerts.where((a) => a.status.isOpen).length;
        final priority = data.patients.where((p) {
          final level = RiskColors.levelForScore(p.risk);
          return level == RiskLevel.high || level == RiskLevel.critical;
        }).length;

        final sortedByRisk = [...data.patients]
          ..sort((a, b) => b.risk.compareTo(a.risk));
        final topPatients = sortedByRisk.take(8).toList();
        final focusPatient = sortedByRisk.isNotEmpty ? sortedByRisk.first : null;

        return Scaffold(
          backgroundColor: AppColors.background,
          body: RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(28, 24, 28, 40),
              children: [
                _Header(wardCount: wardCount, onRefresh: _refresh),
                const SizedBox(height: 20),
                LayoutBuilder(builder: (context, constraints) {
                  final narrow = constraints.maxWidth < 720;
                  final tiles = [
                    StatCard(
                      label: 'Patients monitored',
                      value: '${data.patients.length}',
                      accentColor: AppColors.accent,
                    ),
                    StatCard(
                      label: 'Active alerts',
                      value: '$activeAlerts',
                      accentColor: AppColors.critical,
                    ),
                    StatCard(
                      label: 'High / critical risk',
                      value: '$priority',
                      accentColor: AppColors.riskHigh,
                    ),
                    StatCard(
                      label: 'Wards represented',
                      value: '$wardCount',
                      accentColor: AppColors.stable,
                    ),
                  ];
                  if (narrow) {
                    return Column(
                      children: [
                        for (final t in tiles) ...[
                          t,
                          const SizedBox(height: 10),
                        ],
                      ],
                    );
                  }
                  return Row(
                    children: [
                      for (var i = 0; i < tiles.length; i++) ...[
                        Expanded(child: tiles[i]),
                        if (i != tiles.length - 1) const SizedBox(width: 12),
                      ],
                    ],
                  );
                }),
                const SizedBox(height: 28),
                LayoutBuilder(builder: (context, constraints) {
                  final stacked = constraints.maxWidth < 980;
                  final table = _PatientMonitoringSection(
                    patients: topPatients,
                    total: data.patients.length,
                    onTap: (p) => _openPatient(context, p),
                    onSeeAll: widget.onSeeAllPatients,
                  );
                  final side = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _RecentAlertsSection(
                        alerts: data.alerts.take(4).toList(),
                        onSeeAll: widget.onSeeAllAlerts,
                      ),
                      const SizedBox(height: 24),
                      if (focusPatient != null)
                        _TrendSection(patient: focusPatient),
                    ],
                  );
                  if (stacked) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [table, const SizedBox(height: 24), side],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 3, child: table),
                      const SizedBox(width: 24),
                      Expanded(flex: 2, child: side),
                    ],
                  );
                }),
              ],
            ),
          ),
        );
      },
    );
  }

  void _openPatient(BuildContext context, Patient patient) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PatientDetailScreen(
          patient: patient,
          patientRepository: widget.patientRepository,
          alertRepository: widget.alertRepository,
        ),
      ),
    );
  }
}

class _OverviewData {
  _OverviewData({required this.patients, required this.alerts});
  final List<Patient> patients;
  final List<Alert> alerts;
}

class _Header extends StatelessWidget {
  const _Header({required this.wardCount, required this.onRefresh});

  final int wardCount;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Overview',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              wardCount > 0
                  ? 'Monitoring across $wardCount ward${wardCount == 1 ? '' : 's'}'
                  : 'Ward monitoring',
              style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
            ),
          ],
        ),
        const Spacer(),
        OutlinedButton.icon(
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh, size: 15),
          label: const Text('Refresh'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.textSecondary,
            side: const BorderSide(color: AppColors.lineStrong),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            textStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _PatientMonitoringSection extends StatelessWidget {
  const _PatientMonitoringSection({
    required this.patients,
    required this.total,
    required this.onTap,
    this.onSeeAll,
  });

  final List<Patient> patients;
  final int total;
  final ValueChanged<Patient> onTap;
  final VoidCallback? onSeeAll;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Patient monitoring',
          trailing: total > patients.length
              ? TextButton(
                  onPressed: onSeeAll,
                  child: Text('View all $total'),
                )
              : null,
        ),
        PatientTable(patients: patients, onTap: onTap),
      ],
    );
  }
}

class _RecentAlertsSection extends StatelessWidget {
  const _RecentAlertsSection({required this.alerts, this.onSeeAll});

  final List<Alert> alerts;
  final VoidCallback? onSeeAll;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Recent alerts',
          trailing: TextButton(onPressed: onSeeAll, child: const Text('See all')),
        ),
        if (alerts.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppColors.line),
            ),
            child: const Text(
              'No alerts to review.',
              style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
            ),
          )
        else
          ...alerts.map(
            (a) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: AlertCard(alert: a, dense: true),
            ),
          ),
      ],
    );
  }
}

class _TrendSection extends StatelessWidget {
  const _TrendSection({required this.patient});

  final Patient patient;

  @override
  Widget build(BuildContext context) {
    final color = RiskColors.colorForScore(patient.risk);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Highest-priority trend'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: AppColors.line),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${patient.name.isEmpty ? 'Unnamed patient' : patient.name} · ${patient.bed}',
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Risk score ${patient.risk}',
                style: const TextStyle(fontSize: 11.5, color: AppColors.textDim),
              ),
              const SizedBox(height: 12),
              if (patient.trend.isNotEmpty)
                Sparkline(values: patient.trend, color: color, height: 56)
              else
                const Text(
                  'No trend data available from the API for this patient.',
                  style: TextStyle(fontSize: 12, color: AppColors.textDim),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});

  final String error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 32, color: AppColors.textDim),
              const SizedBox(height: 12),
              const Text(
                'Could not reach the backend',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                error,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: AppColors.textDim),
              ),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: onRetry,
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textPrimary,
                  side: const BorderSide(color: AppColors.lineStrong),
                ),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

