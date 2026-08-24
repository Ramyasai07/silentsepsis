import 'package:flutter/material.dart';
import '../models/alert.dart';
import '../models/patient.dart';
import '../repositories/alert_repository.dart';
import '../repositories/patient_repository.dart';
import '../services/api_config_service.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/risk_colors.dart';
import '../widgets/section_header.dart';

/// Ward analytics computed from real, already-available patient and
/// alert data (risk distribution, alert outcomes). If the backend's
/// `/analytics` endpoint is implemented, its fields are also shown
/// generically below — nothing on this screen is fabricated.
class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({
    super.key,
    required this.patientRepository,
    required this.alertRepository,
    required this.apiConfigService,
  });

  final PatientRepository patientRepository;
  final AlertRepository alertRepository;
  final ApiConfigService apiConfigService;

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  late Future<_AnalyticsData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_AnalyticsData> _load() async {
    final patients = await widget.patientRepository.getPatients();
    final alerts = await widget.alertRepository.getAlerts();
    Map<String, dynamic>? backendAnalytics;
    final api = ApiService(baseUrl: widget.apiConfigService.apiUrl);
    try {
      final raw = await api.getAnalytics();
      if (raw is Map<String, dynamic>) backendAnalytics = raw;
    } catch (_) {
      backendAnalytics = null;
    } finally {
      api.dispose();
    }
    return _AnalyticsData(
      patients: patients,
      alerts: alerts,
      backendAnalytics: backendAnalytics,
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
            const Text(
              'Analytics',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Aggregated from current patient and alert data',
              style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: FutureBuilder<_AnalyticsData>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        'Could not load analytics: ${snapshot.error}',
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textDim),
                      ),
                    );
                  }
                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final data = snapshot.data!;
                  return ListView(
                    children: [
                      const SectionHeader(title: 'Risk distribution'),
                      _RiskDistribution(patients: data.patients),
                      const SizedBox(height: 24),
                      const SectionHeader(title: 'Alert outcomes'),
                      _AlertOutcomes(alerts: data.alerts),
                      if (data.backendAnalytics != null &&
                          data.backendAnalytics!.isNotEmpty) ...[
                        const SizedBox(height: 24),
                        const SectionHeader(title: 'Model performance'),
                        _BackendAnalytics(fields: data.backendAnalytics!),
                      ],
                    ],
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

class _AnalyticsData {
  _AnalyticsData({
    required this.patients,
    required this.alerts,
    required this.backendAnalytics,
  });
  final List<Patient> patients;
  final List<Alert> alerts;
  final Map<String, dynamic>? backendAnalytics;
}

class _RiskDistribution extends StatelessWidget {
  const _RiskDistribution({required this.patients});

  final List<Patient> patients;

  @override
  Widget build(BuildContext context) {
    final total = patients.isEmpty ? 1 : patients.length;
    final counts = <RiskLevel, int>{
      for (final level in RiskLevel.values)
        level: patients
            .where((p) => RiskColors.levelForScore(p.risk) == level)
            .length,
    };

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              height: 8,
              child: Row(
                children: [
                  for (final level in RiskLevel.values)
                    if ((counts[level] ?? 0) > 0)
                      Expanded(
                        flex: counts[level]!,
                        child: Container(color: RiskColors.levelColor(level)),
                      ),
                  if (patients.isEmpty)
                    Expanded(child: Container(color: AppColors.line)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 20,
            runSpacing: 10,
            children: [
              for (final level in RiskLevel.values)
                _LegendItem(
                  color: RiskColors.levelColor(level),
                  label: RiskColors.levelLabel(level),
                  count: counts[level] ?? 0,
                  total: total,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({
    required this.color,
    required this.label,
    required this.count,
    required this.total,
  });

  final Color color;
  final String label;
  final int count;
  final int total;

  @override
  Widget build(BuildContext context) {
    final pct = ((count / total) * 100).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
            Text(label,
                style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary)),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          '$count · $pct%',
          style: const TextStyle(
              fontSize: 13.5, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
        ),
      ],
    );
  }
}

class _AlertOutcomes extends StatelessWidget {
  const _AlertOutcomes({required this.alerts});

  final List<Alert> alerts;

  @override
  Widget build(BuildContext context) {
    const statuses = AlertStatus.values;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: alerts.isEmpty
          ? const Text(
              'No alerts recorded yet.',
              style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
            )
          : Wrap(
              spacing: 24,
              runSpacing: 12,
              children: [
                for (final status in statuses)
                  _LegendItem(
                    color: status.isOpen ? AppColors.watch : AppColors.stable,
                    label: status.label,
                    count: alerts.where((a) => a.status == status).length,
                    total: alerts.length,
                  ),
              ],
            ),
    );
  }
}

class _BackendAnalytics extends StatelessWidget {
  const _BackendAnalytics({required this.fields});

  final Map<String, dynamic> fields;

  @override
  Widget build(BuildContext context) {
    final entries = fields.entries.toList();
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        children: [
          for (var i = 0; i < entries.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
              decoration: BoxDecoration(
                border: i == entries.length - 1
                    ? null
                    : const Border(bottom: BorderSide(color: AppColors.line)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    entries[i].key,
                    style: const TextStyle(
                        fontSize: 12.5, color: AppColors.textSecondary),
                  ),
                  Text(
                    entries[i].value.toString(),
                    style: const TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}



