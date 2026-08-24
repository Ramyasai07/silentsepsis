import 'package:flutter/material.dart';
import '../repositories/alert_repository.dart';
import '../repositories/patient_repository.dart';
import '../repositories/ward_repository.dart';
import '../services/api_config_service.dart';
import '../theme/app_colors.dart';
import '../widgets/sidebar_nav.dart';
import 'alerts_screen.dart';
import 'analytics_screen.dart';
import 'overview_screen.dart';
import 'patients_screen.dart';
import 'settings_screen.dart';
import 'wards_screen.dart';

/// Top-level scaffold: a persistent desktop-first left sidebar plus the
/// active section on the right. Patient Details is reached by selecting
/// a patient from the table and is pushed on top via Navigator, not a
/// sidebar destination.
class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.patientRepository,
    required this.alertRepository,
    required this.wardRepository,
    required this.apiConfigService,
  });

  final PatientRepository patientRepository;
  final AlertRepository alertRepository;
  final WardRepository wardRepository;
  final ApiConfigService apiConfigService;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static const _items = [
    SidebarNavItem(icon: Icons.dashboard_outlined, label: 'Overview'),
    SidebarNavItem(icon: Icons.groups_outlined, label: 'Patients'),
    SidebarNavItem(icon: Icons.notifications_outlined, label: 'Alerts'),
    SidebarNavItem(icon: Icons.local_hospital_outlined, label: 'Wards'),
    SidebarNavItem(icon: Icons.query_stats_outlined, label: 'Analytics'),
    SidebarNavItem(icon: Icons.settings_outlined, label: 'Settings'),
  ];

  void _goTo(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final screens = [
      OverviewScreen(
        patientRepository: widget.patientRepository,
        alertRepository: widget.alertRepository,
        onSeeAllAlerts: () => _goTo(2),
        onSeeAllPatients: () => _goTo(1),
      ),
      PatientsScreen(
        patientRepository: widget.patientRepository,
        alertRepository: widget.alertRepository,
      ),
      AlertsScreen(alertRepository: widget.alertRepository),
      WardsScreen(
        wardRepository: widget.wardRepository,
        patientRepository: widget.patientRepository,
      ),
      AnalyticsScreen(
        patientRepository: widget.patientRepository,
        alertRepository: widget.alertRepository,
        apiConfigService: widget.apiConfigService,
      ),
      SettingsScreen(apiConfigService: widget.apiConfigService),
    ];

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Row(
        children: [
          SidebarNav(
            items: _items,
            selectedIndex: _index,
            onSelect: _goTo,
          ),
          Expanded(
            child: IndexedStack(index: _index, children: screens),
          ),
        ],
      ),
    );
  }
}

