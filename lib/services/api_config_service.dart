import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Holds the configured backend API base URL and the last known
/// connection status. This app only ever shows real API data — there is
/// no demo/offline mode — so this service exists purely to let the API
/// URL be configured and tested from Settings, the same way the previous
/// build's DemoModeService did for its "API URL" field.
class ApiConfigService extends ChangeNotifier {
  static const _apiUrlKey = 'silentsepsis_api_url';
  static const defaultApiUrl = 'http://localhost:8000';

  String _apiUrl = defaultApiUrl;
  ConnectionStatus _connectionStatus = ConnectionStatus.notChecked;

  String get apiUrl => _apiUrl;
  ConnectionStatus get connectionStatus => _connectionStatus;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _apiUrl = prefs.getString(_apiUrlKey) ?? defaultApiUrl;
    notifyListeners();
  }

  Future<void> setApiUrl(String value) async {
    _apiUrl = value.trim().isEmpty ? defaultApiUrl : value.trim();
    _connectionStatus = ConnectionStatus.notChecked;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_apiUrlKey, _apiUrl);
    notifyListeners();
  }

  void setConnectionStatus(ConnectionStatus status) {
    _connectionStatus = status;
    notifyListeners();
  }
}

enum ConnectionStatus { notChecked, checking, connected, failed }

