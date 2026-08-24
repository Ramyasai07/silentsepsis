import 'package:flutter/material.dart';
import '../models/patient.dart';
import '../repositories/alert_repository.dart';
import '../repositories/patient_repository.dart';
import '../theme/app_colors.dart';
import '../widgets/patient_table.dart';
import 'patient_detail_screen.dart';

/// Full, searchable roster of ward patients, shown as a dense table.
class PatientsScreen extends StatefulWidget {
  const PatientsScreen({
    super.key,
    required this.patientRepository,
    this.alertRepository,
  });

  final PatientRepository patientRepository;
  final AlertRepository? alertRepository;

  @override
  State<PatientsScreen> createState() => _PatientsScreenState();
}

class _PatientsScreenState extends State<PatientsScreen> {
  late Future<List<Patient>> _future;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _future = widget.patientRepository.getPatients();
  }

  Future<void> _refresh() async {
    final future = widget.patientRepository.getPatients();
    setState(() => _future = future);
    await future;
  }

  List<Patient> _filter(List<Patient> patients) {
    if (_query.trim().isEmpty) return patients;
    final q = _query.toLowerCase();
    return patients.where((p) {
      return p.name.toLowerCase().contains(q) ||
          p.bed.toLowerCase().contains(q) ||
          p.ward.toLowerCase().contains(q) ||
          p.note.toLowerCase().contains(q);
    }).toList();
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
                  'Patients',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    letterSpacing: -0.3,
                  ),
                ),
                const Spacer(),
                SizedBox(
                  width: 280,
                  height: 36,
                  child: TextField(
                    onChanged: (v) => setState(() => _query = v),
                    style: const TextStyle(fontSize: 13),
                    decoration: const InputDecoration(
                      isDense: true,
                      hintText: 'Search by name, bed, or ward…',
                      prefixIcon: Icon(Icons.search, size: 17),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                OutlinedButton.icon(
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh, size: 15),
                  label: const Text('Refresh'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.textSecondary,
                    side: const BorderSide(color: AppColors.lineStrong),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    shape:
                        RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    textStyle:
                        const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Expanded(
              child: FutureBuilder<List<Patient>>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        'Could not load patients: ${snapshot.error}',
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textDim),
                      ),
                    );
                  }
                  if (!snapshot.hasData) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final filtered = _filter(snapshot.data!);
                  return SingleChildScrollView(
                    child: PatientTable(
                      patients: filtered,
                      onTap: (p) => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PatientDetailScreen(
                            patient: p,
                            patientRepository: widget.patientRepository,
                            alertRepository: widget.alertRepository,
                          ),
                        ),
                      ),
                    ),
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

