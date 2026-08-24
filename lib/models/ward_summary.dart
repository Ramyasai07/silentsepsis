/// Ward-level roll-up stats, ported from mockData.js `wardSummary`.
class WardSummary {
  final String ward;
  final int activeAlerts;
  final int trendingUp;
  final int stable;
  final int avgConfirmMinutes;
  final int riskLoad;
  final int totalPatients;

  const WardSummary({
    required this.ward,
    required this.activeAlerts,
    required this.trendingUp,
    required this.stable,
    required this.avgConfirmMinutes,
    required this.riskLoad,
    required this.totalPatients,
  });

  factory WardSummary.fromJson(Map<String, dynamic> json) {
    return WardSummary(
      ward: json['ward'] as String? ?? '',
      activeAlerts: (json['activeAlerts'] as num?)?.toInt() ?? 0,
      trendingUp: (json['trendingUp'] as num?)?.toInt() ?? 0,
      stable: (json['stable'] as num?)?.toInt() ?? 0,
      avgConfirmMinutes: (json['avgConfirmMinutes'] as num?)?.toInt() ?? 0,
      riskLoad: (json['riskLoad'] as num?)?.toInt() ?? 0,
      totalPatients: (json['totalPatients'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'ward': ward,
        'activeAlerts': activeAlerts,
        'trendingUp': trendingUp,
        'stable': stable,
        'avgConfirmMinutes': avgConfirmMinutes,
        'riskLoad': riskLoad,
        'totalPatients': totalPatients,
      };
}

