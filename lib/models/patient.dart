import 'risk_factor.dart';
import 'vital_reading.dart';

/// Three-tier risk classification used throughout the app.
enum RiskTier {
  stable,
  watch,
  critical;

  static RiskTier fromString(String? value) {
    switch (value) {
      case 'critical':
        return RiskTier.critical;
      case 'watch':
        return RiskTier.watch;
      case 'stable':
      default:
        return RiskTier.stable;
    }
  }

  String get label {
    switch (this) {
      case RiskTier.critical:
        return 'Critical';
      case RiskTier.watch:
        return 'Watch';
      case RiskTier.stable:
        return 'Stable';
    }
  }
}

/// A ward patient, ported from the SilentSepsis demo dataset
/// (src/data/mockData.js) into a strongly typed Dart model.
class Patient {
  final String id;
  final String name;
  final String initials;
  final String bed;
  final String ward;
  final int age;
  final String sex;
  final String admitted;
  final String note;
  final int risk;
  final RiskTier tier;
  final int confidenceIntervalMinutes;
  final String reason;
  final String trajectory;
  final String lastVitals;
  final List<int> trend;
  final List<RiskFactor> features;
  final List<VitalReading> vitalsHistory;

  const Patient({
    required this.id,
    required this.name,
    required this.initials,
    required this.bed,
    required this.ward,
    required this.age,
    required this.sex,
    required this.admitted,
    required this.note,
    required this.risk,
    required this.tier,
    required this.confidenceIntervalMinutes,
    required this.reason,
    required this.trajectory,
    required this.lastVitals,
    required this.trend,
    required this.features,
    required this.vitalsHistory,
  });

  /// Most recent vitals reading, if any history is available.
  VitalReading? get latestVitals =>
      vitalsHistory.isNotEmpty ? vitalsHistory.last : null;

  factory Patient.fromJson(Map<String, dynamic> json) {
    return Patient(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      initials: json['initials'] as String? ?? '',
      bed: json['bed'] as String? ?? '',
      ward: json['ward'] as String? ?? '',
      age: (json['age'] as num?)?.toInt() ?? 0,
      sex: json['sex'] as String? ?? '',
      admitted: json['admitted'] as String? ?? '',
      note: json['note'] as String? ?? '',
      risk: (json['risk'] as num?)?.toInt() ?? 0,
      tier: RiskTier.fromString(json['tier'] as String?),
      confidenceIntervalMinutes: (json['ci'] as num?)?.toInt() ?? 0,
      reason: json['reason'] as String? ?? '',
      trajectory: json['trajectory'] as String? ?? '',
      lastVitals: json['lastVitals'] as String? ?? '',
      trend: (json['trend'] as List<dynamic>? ?? [])
          .map((e) => (e as num).toInt())
          .toList(),
      features: (json['features'] as List<dynamic>? ?? [])
          .map((e) => RiskFactor.fromJson(e as Map<String, dynamic>))
          .toList(),
      vitalsHistory: (json['vitalsHistory'] as List<dynamic>? ?? [])
          .map((e) => VitalReading.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

