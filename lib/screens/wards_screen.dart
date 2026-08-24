import 'package:flutter/material.dart';
import '../models/patient.dart';
import '../repositories/patient_repository.dart';
import '../repositories/ward_repository.dart';
import '../theme/app_colors.dart';
import '../theme/risk_colors.dart';

/// Ward roster: lists wards as returned by the backend's `/wards`
/// endpoint, with patient counts and risk mix computed from the real,
/// already-fetched patient list (matched by the patient's `ward` field).
class WardsScreen extends StatefulWidget {
  const WardsScreen({
    super.key,
    required this.wardRepository,
    required this.patientRepository,
  });

  final WardRepository wardRepository;
  final PatientRepository patientRepository;

  @override
  State<WardsScreen> createState() => _WardsScreenState();
}

class _WardsScreenState extends State<WardsScreen> {
  late Future<_WardsData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_WardsData> _load() async {
    final patients = await widget.patientRepository.getPatients();
    List<dynamic> rawWards = const [];
    try {
      rawWards = await widget.wardRepository.getWards();
    } catch (_) {
      // /wards endpoint unavailable on this backend/build — fall back to
      // the distinct ward names already present on real patient records.
      rawWards = patients.map((p) => p.ward).toSet().toList();
    }
    return _WardsData(patients: patients, rawWards: rawWards);
  }

  String _wardName(dynamic raw) {
    if (raw is String) return raw;
    if (raw is Map) {
      return (raw['name'] ?? raw['ward'] ?? raw['id'] ?? '').toString();
    }
    return raw.toString();
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
              'Wards',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Patient distribution by ward',
              style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: FutureBuilder<_WardsData>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        'Could not load wards: ${snapshot.error}',
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textDim),
                      ),
                    );
                  }
                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final data = snapshot.data!;
                  final wardNames = data.rawWards
                      .map(_wardName)
                      .where((n) => n.isNotEmpty)
                      .toSet()
                      .toList()
                    ..sort();

                  if (wardNames.isEmpty) {
                    return const Center(
                      child: Text(
                        'No ward data available.',
                        style: TextStyle(fontSize: 12.5, color: AppColors.textDim),
                      ),
                    );
                  }

                  return GridView.builder(
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 320,
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: 1.5,
                    ),
                    itemCount: wardNames.length,
                    itemBuilder: (context, i) {
                      final ward = wardNames[i];
                      final wardPatients =
                          data.patients.where((p) => p.ward == ward).toList();
                      return _WardCard(name: ward, patients: wardPatients);
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

class _WardsData {
  _WardsData({required this.patients, required this.rawWards});
  final List<Patient> patients;
  final List<dynamic> rawWards;
}

class _WardCard extends StatelessWidget {
  const _WardCard({required this.name, required this.patients});

  final String name;
  final List<Patient> patients;

  @override
  Widget build(BuildContext context) {
    final critical = patients
        .where((p) => RiskColors.levelForScore(p.risk) == RiskLevel.critical)
        .length;
    final high = patients
        .where((p) => RiskColors.levelForScore(p.risk) == RiskLevel.high)
        .length;

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
              const Icon(Icons.local_hospital_outlined,
                  size: 15, color: AppColors.textDim),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  name,
                  style: const TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            '${patients.length}',
            style: const TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
              letterSpacing: -0.4,
            ),
          ),
          const Text(
            'patients',
            style: TextStyle(fontSize: 11.5, color: AppColors.textDim),
          ),
          const Spacer(),
          if (critical + high > 0)
            Row(
              children: [
                if (critical > 0) ...[
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                        color: AppColors.riskCritical, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 5),
                  Text('$critical critical',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textSecondary)),
                ],
                if (critical > 0 && high > 0) const SizedBox(width: 10),
                if (high > 0) ...[
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                        color: AppColors.riskHigh, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 5),
                  Text('$high high',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textSecondary)),
                ],
              ],
            )
          else
            const Text(
              'No elevated risk',
              style: TextStyle(fontSize: 11, color: AppColors.textDim),
            ),
        ],
      ),
    );
  }
}

