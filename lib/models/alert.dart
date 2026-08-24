/// Lifecycle status of an alert, ported from the SilentSepsis
/// alert history table (src/pages/Alerts.jsx).
enum AlertStatus {
  active,
  watching,
  confirmed,
  dismissed,
  resolved;

  static AlertStatus fromString(String? value) {
    switch (value) {
      case 'watching':
        return AlertStatus.watching;
      case 'confirmed':
        return AlertStatus.confirmed;
      case 'dismissed':
        return AlertStatus.dismissed;
      case 'resolved':
        return AlertStatus.resolved;
      case 'active':
      default:
        return AlertStatus.active;
    }
  }

  String get label {
    switch (this) {
      case AlertStatus.active:
        return 'Active';
      case AlertStatus.watching:
        return 'Watching';
      case AlertStatus.confirmed:
        return 'Confirmed';
      case AlertStatus.dismissed:
        return 'Dismissed';
      case AlertStatus.resolved:
        return 'Resolved';
    }
  }

  /// Whether this alert still needs clinical review.
  bool get isOpen => this == AlertStatus.active || this == AlertStatus.watching;
}

/// A single ward alert tied to a patient.
class Alert {
  final String id;
  final String patientId;
  final String patientName;
  final String bed;
  final String reason;
  final String time;
  final String actor;
  AlertStatus status;

  Alert({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.bed,
    required this.reason,
    required this.time,
    required this.actor,
    required this.status,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      id: json['id'] as String? ?? '',
      patientId: json['patientId'] as String? ?? '',
      patientName: json['patient'] as String? ?? '',
      bed: json['bed'] as String? ?? '',
      reason: json['reason'] as String? ?? '',
      time: json['time'] as String? ?? '',
      actor: json['actor'] as String? ?? '—',
      status: AlertStatus.fromString(json['status'] as String?),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'patientId': patientId,
        'patient': patientName,
        'bed': bed,
        'reason': reason,
        'time': time,
        'actor': actor,
        'status': status.name,
      };
}

