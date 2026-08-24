import 'package:flutter/material.dart';
import '../models/alert.dart';
import '../models/patient.dart';
import '../models/vital_reading.dart';
import '../repositories/alert_repository.dart';
import '../repositories/patient_repository.dart';
import '../theme/app_colors.dart';
import '../theme/risk_colors.dart';
import '../widgets/alert_card.dart';
import '../widgets/risk_badge.dart';
import '../widgets/section_header.dart';
import '../widgets/sparkline.dart';
import '../widgets/vital_tile.dart';

/// Full clinical picture for one patient: identity, current risk tier
/// and score, latest vitals, a risk trend visualization, recent vitals
/// history, contributing risk factors, and alert history — all sourced
/// from the real Patient/Alert models and the live backend. Fields the
/// API doesn't provide for a given patient are simply omitted, never
/// invented.
class PatientDetailScreen extends StatefulWidget {
  const PatientDetailScreen({
    super.key,
    required this.patient,
    this.patientRepository,
    this.alertRepository,
  });

  /// The patient as already known by the caller (e.g. from the table).
  /// Used immediately, then refreshed in the background if a repository
  /// is provided, since the detail endpoint may return richer data
  /// (e.g. full vitals history) than the list endpoint.
  final Patient patient;
  final PatientRepository? patientRepository;
  final AlertRepository? alertRepository;

  @override
  State<PatientDetailScreen> createState() => _PatientDetailScreenState();
}

class _PatientDetailScreenState extends State<PatientDetailScreen> {
  late Patient _patient;
  List<Alert> _alerts = const [];
  bool _loadingAlerts = false;

  @override
  void initState() {
    super.initState();
    _patient = widget.patient;
    _refreshPatient();
    _loadAlerts();
  }

  Future<void> _refreshPatient() async {
    final repo = widget.patientRepository;
    if (repo == null) return;
    try {
      final fresh = await repo.getPatient(_patient.id);
      if (fresh != null && mounted) setState(() => _patient = fresh);
    } catch (_) {
      // Keep showing the patient we already have.
    }
  }

  Future<void> _loadAlerts() async {
    final repo = widget.alertRepository;
    if (repo == null) return;
    setState(() => _loadingAlerts = true);
    try {
      final all = await repo.getAlerts();
      final related = all
          .where((a) =>
              a.patientId == _patient.id || a.patientName == _patient.name)
          .toList();
      if (mounted) setState(() => _alerts = related);
    } catch (_) {
      // Leave alert history empty rather than showing stale/fake data.
    } finally {
      if (mounted) setState(() => _loadingAlerts = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final patient = _patient;
    final vitals = patient.latestVitals;
    final fg = RiskColors.foreground(patient.tier);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(patient.name.isEmpty ? 'Patient' : patient.name),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 40),
            children: [
              _IdentityCard(patient: patient, fg: fg),
              if (patient.reason.isNotEmpty) ...[
                const SizedBox(height: 16),
                _ReasonCard(patient: patient, fg: fg),
              ],
              const SizedBox(height: 24),
              const SectionHeader(title: 'Current vitals'),
              if (vitals != null)
                _VitalsGrid(vitals: vitals)
              else
                const _EmptyCard(
                  message: 'No vitals available from the API for this patient.',
                ),
              const SizedBox(height: 24),
              const SectionHeader(title: 'Risk trend'),
              if (patient.trend.isNotEmpty)
                Container(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.line),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Sparkline(values: patient.trend, color: fg, height: 64),
                      const SizedBox(height: 8),
                      Text(
                        'Last ${patient.trend.length} readings',
                        style: const TextStyle(fontSize: 11, color: AppColors.textDim),
                      ),
                    ],
                  ),
                )
              else
                const _EmptyCard(
                  message: 'No historical trend data available from the API.',
                ),
              if (patient.vitalsHistory.isNotEmpty) ...[
                const SizedBox(height: 24),
                const SectionHeader(title: 'Recent vitals'),
                _VitalsHistoryTable(history: patient.vitalsHistory),
              ],
              if (patient.features.isNotEmpty) ...[
                const SizedBox(height: 24),
                const SectionHeader(title: 'Contributing risk factors'),
                _RiskFactors(patient: patient, fg: fg),
              ],
              const SizedBox(height: 24),
              const SectionHeader(title: 'Alert history'),
              if (_loadingAlerts)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(
                      child: SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2))),
                )
              else if (_alerts.isEmpty)
                const _EmptyCard(message: 'No alerts recorded for this patient.')
              else
                ..._alerts.map(
                  (a) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AlertCard(alert: a),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({required this.patient, required this.fg});

  final Patient patient;
  final Color fg;

  @override
  Widget build(BuildContext context) {
    final details = [
      if (patient.age > 0) '${patient.age} yo',
      if (patient.sex.isNotEmpty) patient.sex,
      if (patient.bed.isNotEmpty) patient.bed,
      if (patient.ward.isNotEmpty) patient.ward,
    ].join(' · ');

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 48,
            height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: RiskColors.background(patient.tier),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              patient.initials.isEmpty ? '—' : patient.initials,
              style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 16),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  patient.name.isEmpty ? 'Unnamed patient' : patient.name,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                if (details.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(details,
                      style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
                ],
                if (patient.note.isNotEmpty || patient.admitted.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(
                    [
                      if (patient.note.isNotEmpty) patient.note,
                      if (patient.admitted.isNotEmpty) 'Admitted ${patient.admitted}',
                    ].join(' · '),
                    style: const TextStyle(fontSize: 11.5, color: AppColors.textDim),
                  ),
                ],
                const SizedBox(height: 12),
                RiskBadge(score: patient.risk),
              ],
            ),
          ),
          RiskScoreDial(score: patient.risk, size: 56),
        ],
      ),
    );
  }
}

class _ReasonCard extends StatelessWidget {
  const _ReasonCard({required this.patient, required this.fg});

  final Patient patient;
  final Color fg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, size: 15, color: fg),
              const SizedBox(width: 6),
              const Text('Why this score',
                  style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: AppColors.textPrimary)),
            ],
          ),
          const SizedBox(height: 8),
          Text(patient.reason,
              style: const TextStyle(
                  fontSize: 12.5, color: AppColors.textSecondary, height: 1.4)),
          if (patient.trajectory.isNotEmpty || patient.confidenceIntervalMinutes > 0) ...[
            const SizedBox(height: 6),
            Text(
              [
                if (patient.trajectory.isNotEmpty) patient.trajectory,
                if (patient.confidenceIntervalMinutes > 0)
                  'confidence window ±${patient.confidenceIntervalMinutes} min',
              ].join(' · '),
              style: const TextStyle(fontSize: 11.5, color: AppColors.textDim),
            ),
          ],
        ],
      ),
    );
  }
}

class _VitalsGrid extends StatelessWidget {
  const _VitalsGrid({required this.vitals});

  final VitalReading vitals;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 1.55,
      children: [
        VitalTile(
          label: 'Heart rate',
          value: vitals.heartRate.toStringAsFixed(0),
          unit: 'bpm',
          icon: Icons.favorite_border,
          isAbnormal: vitals.heartRate > 100 || vitals.heartRate < 55,
        ),
        VitalTile(
          label: 'Respiratory rate',
          value: vitals.respiratoryRate.toStringAsFixed(0),
          unit: '/min',
          icon: Icons.air,
          isAbnormal: vitals.respiratoryRate > 20,
        ),
        VitalTile(
          label: 'SpO2',
          value: vitals.spo2.toStringAsFixed(0),
          unit: '%',
          icon: Icons.bubble_chart_outlined,
          isAbnormal: vitals.spo2 < 95,
        ),
        VitalTile(
          label: 'Temperature',
          value: vitals.temperature.toStringAsFixed(1),
          unit: '°C',
          icon: Icons.thermostat_outlined,
          isAbnormal: vitals.temperature > 37.8,
        ),
        VitalTile(
          label: 'Blood pressure',
          value: vitals.bloodPressure.toStringAsFixed(0),
          unit: 'mmHg',
          icon: Icons.monitor_heart_outlined,
          isAbnormal: vitals.bloodPressure < 100,
        ),
      ],
    );
  }
}

class _VitalsHistoryTable extends StatelessWidget {
  const _VitalsHistoryTable({required this.history});

  final List<VitalReading> history;

  @override
  Widget build(BuildContext context) {
    final rows = history.reversed.toList();
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        children: [
          for (var i = 0; i < rows.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                border: i == rows.length - 1
                    ? null
                    : const Border(bottom: BorderSide(color: AppColors.line)),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 44,
                    child: Text(
                      rows[i].label,
                      style: const TextStyle(
                          fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      'HR ${rows[i].heartRate.toStringAsFixed(0)} · '
                      'RR ${rows[i].respiratoryRate.toStringAsFixed(0)} · '
                      'BP ${rows[i].bloodPressure.toStringAsFixed(0)} · '
                      'SpO2 ${rows[i].spo2.toStringAsFixed(0)}% · '
                      '${rows[i].temperature.toStringAsFixed(1)}°',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
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

class _RiskFactors extends StatelessWidget {
  const _RiskFactors({required this.patient, required this.fg});

  final Patient patient;
  final Color fg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        children: patient.features.map((f) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(f.name,
                          style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary)),
                    ),
                    Text('${(f.weight * 100).round()}%',
                        style: const TextStyle(fontSize: 11.5, color: AppColors.textDim)),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: f.weight.clamp(0.0, 1.0),
                    minHeight: 5,
                    backgroundColor: AppColors.line,
                    valueColor: AlwaysStoppedAnimation(fg),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      child: Text(message,
          style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
    );
  }
}

