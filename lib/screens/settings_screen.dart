import 'package:flutter/material.dart';
import '../services/api_config_service.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../widgets/section_header.dart';

/// API connection configuration, connection test, and basic app info.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.apiConfigService});

  final ApiConfigService apiConfigService;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: widget.apiConfigService.apiUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    final apiConfigService = widget.apiConfigService;
    await apiConfigService.setApiUrl(_urlController.text);
    apiConfigService.setConnectionStatus(ConnectionStatus.checking);
    final api = ApiService(baseUrl: apiConfigService.apiUrl);
    final ok = await api.checkConnection();
    api.dispose();
    apiConfigService.setConnectionStatus(
      ok ? ConnectionStatus.connected : ConnectionStatus.failed,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: AnimatedBuilder(
        animation: widget.apiConfigService,
        builder: (context, _) {
          final apiConfigService = widget.apiConfigService;
          return ListView(
            padding: const EdgeInsets.fromLTRB(28, 24, 28, 40),
            children: [
              const Text(
                'Settings',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 24),
              const SectionHeader(title: 'API connection'),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.line),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Backend API URL',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textDim,
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _urlController,
                      keyboardType: TextInputType.url,
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'http://localhost:8000',
                      ),
                      onSubmitted: (v) => apiConfigService.setApiUrl(v),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        _ConnectionStatusPill(status: apiConfigService.connectionStatus),
                        const Spacer(),
                        FilledButton(
                          onPressed: _testConnection,
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.accentDim,
                            foregroundColor: AppColors.accentStrong,
                            elevation: 0,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(6)),
                          ),
                          child: const Text('Test connection'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const SectionHeader(title: 'App information'),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.line),
                ),
                child: const Column(
                  children: [
                    _InfoRow(label: 'App', value: 'SilentSepsis'),
                    SizedBox(height: 10),
                    _InfoRow(label: 'Version', value: '1.0.0'),
                    SizedBox(height: 10),
                    _InfoRow(label: 'Purpose', value: 'Early sepsis-risk ward monitoring'),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ConnectionStatusPill extends StatelessWidget {
  const _ConnectionStatusPill({required this.status});

  final ConnectionStatus status;

  @override
  Widget build(BuildContext context) {
    late final Color color;
    late final String label;
    switch (status) {
      case ConnectionStatus.connected:
        color = AppColors.stable;
        label = 'Connected';
        break;
      case ConnectionStatus.failed:
        color = AppColors.critical;
        label = 'Connection failed';
        break;
      case ConnectionStatus.checking:
        color = AppColors.watch;
        label = 'Checking…';
        break;
      case ConnectionStatus.notChecked:
        color = AppColors.textDim;
        label = 'Not checked';
        break;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontSize: 11.5, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
        Text(value, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
      ],
    );
  }
}

