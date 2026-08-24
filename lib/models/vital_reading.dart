/// One point-in-time set of vitals for a patient.
/// `label` mirrors the demo data's relative-time markers (e.g. "-12h", "now")
/// so the UI can plot a short history without needing real timestamps.
class VitalReading {
  final String label;
  final double heartRate;
  final double respiratoryRate;
  final double bloodPressure;
  final double spo2;
  final double temperature;

  const VitalReading({
    required this.label,
    required this.heartRate,
    required this.respiratoryRate,
    required this.bloodPressure,
    required this.spo2,
    required this.temperature,
  });

  factory VitalReading.fromJson(Map<String, dynamic> json) {
    return VitalReading(
      label: json['t'] as String? ?? json['label'] as String? ?? '',
      heartRate: (json['hr'] as num?)?.toDouble() ?? 0.0,
      respiratoryRate: (json['rr'] as num?)?.toDouble() ?? 0.0,
      bloodPressure: (json['bp'] as num?)?.toDouble() ?? 0.0,
      spo2: (json['spo2'] as num?)?.toDouble() ?? 0.0,
      temperature: (json['temp'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        't': label,
        'hr': heartRate,
        'rr': respiratoryRate,
        'bp': bloodPressure,
        'spo2': spo2,
        'temp': temperature,
      };
}

