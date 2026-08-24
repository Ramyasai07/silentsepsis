import 'dart:convert';

import 'package:http/http.dart' as http;

/// API client for the SilentSepsis backend.
///
/// Authenticates once and automatically attaches the bearer token to
/// protected API requests.
class ApiService {
  ApiService({required this.baseUrl, http.Client? client})
      : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  String? _accessToken;
  Future<void>? _loginFuture;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<void> login({
    required String username,
    required String password,
  }) async {
    final response = await _client.post(
      _uri('/auth/login'),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'username': username,
        'password': password,
      },
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'Login failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is! Map<String, dynamic> ||
        decoded['access_token'] is! String) {
      throw const FormatException('Invalid login response');
    }

    _accessToken = decoded['access_token'] as String;
  }

  Future<Map<String, String>> _headers() async {
    if (_accessToken == null) {
      _loginFuture ??= login(
        username: 'admin@silentsepsis.test',
        password: 'StrongPass123',
      ).whenComplete(() {
        _loginFuture = null;
      });

      await _loginFuture;
    }

    return {
      'Authorization': 'Bearer $_accessToken',
    };
  }

  Future<http.Response> _get(String path) async {
    final response = await _client.get(
      _uri(path),
      headers: await _headers(),
    );

    if (response.statusCode == 401) {
      _accessToken = null;

      await login(
        username: 'admin@silentsepsis.test',
        password: 'StrongPass123',
      );

      return _client.get(
        _uri(path),
        headers: await _headers(),
      );
    }

    return response;
  }

  Future<bool> checkConnection() async {
    try {
      final response = await _get('/patients');
      return response.statusCode < 500;
    } catch (_) {
      return false;
    }
  }

  Future<List<dynamic>> getPatients() async {
    final response = await _get('/patients');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /patients failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is List) {
      return decoded;
    }

    if (decoded is Map<String, dynamic> && decoded['value'] is List) {
      return decoded['value'] as List<dynamic>;
    }

    throw const FormatException(
      'Unexpected /patients response format',
    );
  }

  Future<Map<String, dynamic>> getPatient(String id) async {
    final response = await _get('/patients/$id');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /patients/$id failed (${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getAlerts() async {
    final response = await _get('/alerts');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /alerts failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is List) {
      return decoded;
    }

    if (decoded is Map<String, dynamic> && decoded['value'] is List) {
      return decoded['value'] as List<dynamic>;
    }

    throw const FormatException(
      'Unexpected /alerts response format',
    );
  }

  Future<List<dynamic>> getWards() async {
    final response = await _get('/wards');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /wards failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is List) {
      return decoded;
    }

    if (decoded is Map<String, dynamic> && decoded['value'] is List) {
      return decoded['value'] as List<dynamic>;
    }

    throw const FormatException(
      'Unexpected /wards response format',
    );
  }

  Future<Map<String, dynamic>> getWardSummary(String wardId) async {
    final response = await _get('/wards/$wardId/summary');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /wards/$wardId/summary failed '
        '(${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getPatientVitals(String patientId) async {
    final response = await _get('/patients/$patientId/vitals');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /patients/$patientId/vitals failed '
        '(${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is List) {
      return decoded;
    }

    if (decoded is Map<String, dynamic> && decoded['value'] is List) {
      return decoded['value'] as List<dynamic>;
    }

    throw const FormatException(
      'Unexpected vitals response format',
    );
  }

  Future<Map<String, dynamic>> getPatientVitalsLatest(
    String patientId,
  ) async {
    final response =
        await _get('/patients/$patientId/vitals/latest');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET latest vitals failed '
        '(${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getPatientPredictionLatest(
    String patientId,
  ) async {
    final response =
        await _get('/patients/$patientId/predictions/latest');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET latest prediction failed '
        '(${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAlert(String alertId) async {
    final response = await _get('/alerts/$alertId');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /alerts/$alertId failed (${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<void> acknowledgeAlert(String alertId) async {
    await _client.patch(
      _uri('/alerts/$alertId/acknowledge'),
      headers: await _headers(),
    );
  }

  Future<void> confirmAlert(String alertId) async {
    await _client.patch(
      _uri('/alerts/$alertId/confirm'),
      headers: await _headers(),
    );
  }

  Future<void> dismissAlert(String alertId) async {
    await _client.patch(
      _uri('/alerts/$alertId/dismiss'),
      headers: await _headers(),
    );
  }

  Future<void> resolveAlert(String alertId) async {
    await _client.patch(
      _uri('/alerts/$alertId/resolve'),
      headers: await _headers(),
    );
  }

  Future<dynamic> getAnalytics() async {
    final response = await _get('/analytics');

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'GET /analytics failed (${response.statusCode}): ${response.body}',
      );
    }

    return jsonDecode(response.body);
  }

  void dispose() => _client.close();
}


