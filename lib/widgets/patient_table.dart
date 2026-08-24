import 'package:flutter/material.dart';
import '../models/patient.dart';
import '../theme/app_colors.dart';
import '../theme/risk_colors.dart';
import 'risk_badge.dart';

/// A dense, professional patient monitoring table — used in place of
/// large patient cards. Columns: Patient, Ward, Bed, Risk, Risk score,
/// Status. All values come directly from the [Patient] model; nothing is
/// invented for patients missing data (empty fields render as "—").
class PatientTable extends StatelessWidget {
  const PatientTable({
    super.key,
    required this.patients,
    required this.onTap,
  });

  final List<Patient> patients;
  final ValueChanged<Patient> onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const _TableHeaderRow(),
          const Divider(height: 1),
          if (patients.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(
                child: Text(
                  'No patients found',
                  style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                ),
              ),
            )
          else
            ...List.generate(patients.length, (i) {
              final patient = patients[i];
              return _PatientRow(
                patient: patient,
                isLast: i == patients.length - 1,
                onTap: () => onTap(patient),
              );
            }),
        ],
      ),
    );
  }
}

const _colPatient = 3;
const _colWard = 2;
const _colBed = 1;
const _colRisk = 2;
const _colScore = 1;
const _colStatus = 2;

class _TableHeaderRow extends StatelessWidget {
  const _TableHeaderRow();

  @override
  Widget build(BuildContext context) {
    const style = TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w600,
      color: AppColors.textDim,
      letterSpacing: 0.4,
    );
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: AppColors.surfaceRaised,
      child: const Row(
        children: [
          Expanded(flex: _colPatient, child: Text('PATIENT', style: style)),
          Expanded(flex: _colWard, child: Text('WARD', style: style)),
          Expanded(flex: _colBed, child: Text('BED', style: style)),
          Expanded(flex: _colRisk, child: Text('RISK', style: style)),
          Expanded(
              flex: _colScore,
              child: Text('SCORE', style: style, textAlign: TextAlign.right)),
          Expanded(flex: _colStatus, child: Text('STATUS', style: style)),
        ],
      ),
    );
  }
}

class _PatientRow extends StatefulWidget {
  const _PatientRow({
    required this.patient,
    required this.isLast,
    required this.onTap,
  });

  final Patient patient;
  final bool isLast;
  final VoidCallback onTap;

  @override
  State<_PatientRow> createState() => _PatientRowState();
}

class _PatientRowState extends State<_PatientRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final patient = widget.patient;
    final level = RiskColors.levelForScore(patient.risk);
    final fg = RiskColors.foreground(patient.tier);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: InkWell(
        onTap: widget.onTap,
        child: Container(
          decoration: BoxDecoration(
            color: _hovered ? AppColors.surfaceHover : Colors.transparent,
            border: widget.isLast
                ? null
                : const Border(bottom: BorderSide(color: AppColors.line)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
          child: Row(
            children: [
              Expanded(
                flex: _colPatient,
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: RiskColors.background(patient.tier),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        patient.initials.isEmpty ? '—' : patient.initials,
                        style: TextStyle(
                          color: fg,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            patient.name.isEmpty ? '—' : patient.name,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (patient.age > 0 || patient.sex.isNotEmpty)
                            Text(
                              [
                                if (patient.age > 0) '${patient.age}y',
                                if (patient.sex.isNotEmpty) patient.sex,
                              ].join(' · '),
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.textDim,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: _colWard,
                child: Text(
                  patient.ward.isEmpty ? '—' : patient.ward,
                  style: const TextStyle(
                      fontSize: 12.5, color: AppColors.textSecondary),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Expanded(
                flex: _colBed,
                child: Text(
                  patient.bed.isEmpty ? '—' : patient.bed,
                  style: const TextStyle(
                      fontSize: 12.5, color: AppColors.textSecondary),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Expanded(
                flex: _colRisk,
                child: RiskBadge(score: patient.risk, dense: true),
              ),
              Expanded(
                flex: _colScore,
                child: Text(
                  '${patient.risk}',
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: RiskColors.levelColor(level),
                  ),
                ),
              ),
              Expanded(
                flex: _colStatus,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      patient.tier.label,
                      style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

