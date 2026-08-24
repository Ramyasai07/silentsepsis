import 'package:flutter/material.dart';
import 'repositories/alert_repository.dart';
import 'repositories/patient_repository.dart';
import 'repositories/ward_repository.dart';
import 'screens/home_shell.dart';
import 'services/api_config_service.dart';
import 'services/api_service.dart';
import 'theme/app_theme.dart';

/// Root widget: builds the shared services/repositories once and wires
/// them into the navigation shell.
class SilentSepsisApp extends StatefulWidget {
  const SilentSepsisApp({super.key});

  @override
  State<SilentSepsisApp> createState() => _SilentSepsisAppState();
}

class _SilentSepsisAppState extends State<SilentSepsisApp> {
  final ApiConfigService _apiConfigService = ApiConfigService();
  late final ApiService _apiService;
  late final PatientRepository _patientRepository;
  late final AlertRepository _alertRepository;
  late final WardRepository _wardRepository;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _apiService = ApiService(baseUrl: _apiConfigService.apiUrl);
    _patientRepository = const PatientRepository();
    _alertRepository = AlertRepository(_apiService);
    _wardRepository = WardRepository(_apiService);
    _apiConfigService.load().then((_) {
      if (mounted) setState(() => _ready = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SilentSepsis',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark,
      home: _ready
          ? HomeShell(
              patientRepository: _patientRepository,
              alertRepository: _alertRepository,
              wardRepository: _wardRepository,
              apiConfigService: _apiConfigService,
            )
          : const Scaffold(body: Center(child: CircularProgressIndicator())),
    );
  }
}




