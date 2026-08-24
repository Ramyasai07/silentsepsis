import '../models/alert.dart';
import '../services/api_service.dart';

class AlertRepository {
  AlertRepository(this._api);

  final ApiService _api;

  Future<List<Alert>> getAlerts() async {
    final raw = await _api.getAlerts();

    return raw
        .map((e) => Alert.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> acknowledge(String alertId) async {
    await _api.acknowledgeAlert(alertId);
  }

  Future<void> resolve(String alertId) async {
    await _api.resolveAlert(alertId);
  }

  Future<void> dismiss(String alertId) async {
    await _api.dismissAlert(alertId);
  }
}
