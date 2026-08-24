import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// A small uppercase label used to introduce a section of a screen, with
/// an optional trailing action (e.g. "See all").
class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title, this.trailing});

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            title.toUpperCase(),
            style: const TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: AppColors.textDim,
              letterSpacing: 0.6,
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

