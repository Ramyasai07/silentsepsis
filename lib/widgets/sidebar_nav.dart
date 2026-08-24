import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class SidebarNavItem {
  const SidebarNavItem({required this.icon, required this.label});
  final IconData icon;
  final String label;
}

/// Persistent desktop-first left sidebar: wordmark, primary navigation,
/// and a footer slot. There is no authenticated user in this build, so
/// the footer intentionally shows a generic workstation/role marker
/// rather than a fabricated name or avatar.
class SidebarNav extends StatelessWidget {
  const SidebarNav({
    super.key,
    required this.items,
    required this.selectedIndex,
    required this.onSelect,
  });

  final List<SidebarNavItem> items;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  static const double width = 220;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(right: BorderSide(color: AppColors.line)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _Wordmark(),
          const Divider(height: 1),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              itemCount: items.length,
              itemBuilder: (context, i) {
                return _NavTile(
                  item: items[i],
                  selected: i == selectedIndex,
                  onTap: () => onSelect(i),
                );
              },
            ),
          ),
          const Divider(height: 1),
          const _FooterSection(),
        ],
      ),
    );
  }
}

class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 18),
      child: Row(
        children: [
          Container(
            width: 26,
            height: 26,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.accentDim,
              borderRadius: BorderRadius.circular(5),
              border: Border.all(color: AppColors.accent.withValues(alpha: 0.4)),
            ),
            child: const Icon(Icons.monitor_heart_outlined,
                size: 15, color: AppColors.accentStrong),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'SilentSepsis',
              style: TextStyle(
                fontSize: 14.5,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.2,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatefulWidget {
  const _NavTile({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final SidebarNavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_NavTile> createState() => _NavTileState();
}

class _NavTileState extends State<_NavTile> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final selected = widget.selected;
    final color = selected ? AppColors.textPrimary : AppColors.textSecondary;
    final iconColor = selected ? AppColors.accentStrong : AppColors.textDim;

    return Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(6),
            onTap: widget.onTap,
            child: Container(
              decoration: BoxDecoration(
                color: selected
                    ? AppColors.accentDim
                    : (_hovered ? AppColors.surfaceHover : Colors.transparent),
                borderRadius: BorderRadius.circular(6),
                border: selected
                    ? Border.all(color: AppColors.accent.withValues(alpha: 0.25))
                    : null,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              child: Row(
                children: [
                  Icon(widget.item.icon, size: 17, color: iconColor),
                  const SizedBox(width: 11),
                  Text(
                    widget.item.label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                      color: color,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _FooterSection extends StatelessWidget {
  const _FooterSection();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: AppColors.lineStrong),
            ),
            child: const Icon(Icons.person_outline,
                size: 15, color: AppColors.textDim),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Clinical workstation',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  'Ward operations',
                  style: TextStyle(fontSize: 11, color: AppColors.textDim),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

