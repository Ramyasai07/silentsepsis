/// A single contributing factor behind a patient's risk score,
/// e.g. "Respiratory rate trend" with a relative weight from 0-1.
class RiskFactor {
  final String name;
  final double weight;

  const RiskFactor({required this.name, required this.weight});

  factory RiskFactor.fromJson(Map<String, dynamic> json) {
    return RiskFactor(
      name: json['name'] as String? ?? '',
      weight: (json['weight'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {'name': name, 'weight': weight};
}

