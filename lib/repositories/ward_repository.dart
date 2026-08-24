import '../models/ward_summary.dart';
import '../services/api_service.dart';

class WardRepository {
  WardRepository(this._api);

  final ApiService _api;

  Future<List<dynamic>> getWards() async {
    return _api.getWards();
  }

  Future<WardSummary?> getSummary(String wardId) async {
    try {
      final raw = await _api.getWardSummary(wardId);
      return WardSummary.fromJson(raw);
    } catch (_) {
      return null;
    }
  }
}
