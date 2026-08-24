import 'package:flutter/material.dart';

/// A minimal line-chart sparkline drawn with CustomPainter, used for
/// patient risk trends. Deliberately dependency-free to keep pubspec.yaml
/// lean per the brief.
class Sparkline extends StatelessWidget {
  const Sparkline({
    super.key,
    required this.values,
    this.color = Colors.blue,
    this.height = 48,
    this.strokeWidth = 2.2,
    this.fill = true,
  });

  final List<num> values;
  final Color color;
  final double height;
  final double strokeWidth;
  final bool fill;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(
        painter: _SparklinePainter(
          values: values,
          color: color,
          strokeWidth: strokeWidth,
          fill: fill,
        ),
      ),
    );
  }
}

class _SparklinePainter extends CustomPainter {
  _SparklinePainter({
    required this.values,
    required this.color,
    required this.strokeWidth,
    required this.fill,
  });

  final List<num> values;
  final Color color;
  final double strokeWidth;
  final bool fill;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final minV = values.reduce((a, b) => a < b ? a : b).toDouble();
    final maxV = values.reduce((a, b) => a > b ? a : b).toDouble();
    final range = (maxV - minV).abs() < 0.0001 ? 1.0 : (maxV - minV);

    final dx = values.length > 1 ? size.width / (values.length - 1) : 0.0;

    Offset pointAt(int i) {
      final normalized = (values[i].toDouble() - minV) / range;
      final y = size.height - (normalized * size.height * 0.85) - (size.height * 0.075);
      return Offset(dx * i, y);
    }

    final linePath = Path()..moveTo(pointAt(0).dx, pointAt(0).dy);
    for (var i = 1; i < values.length; i++) {
      linePath.lineTo(pointAt(i).dx, pointAt(i).dy);
    }

    if (fill) {
      final fillPath = Path.from(linePath)
        ..lineTo(pointAt(values.length - 1).dx, size.height)
        ..lineTo(pointAt(0).dx, size.height)
        ..close();
      final fillPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: 0.18), color.withValues(alpha: 0.0)],
        ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
      canvas.drawPath(fillPath, fillPaint);
    }

    final linePaint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(linePath, linePaint);

    final dotPaint = Paint()..color = color;
    canvas.drawCircle(pointAt(values.length - 1), strokeWidth * 1.6, dotPaint);
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter oldDelegate) {
    return oldDelegate.values != values ||
        oldDelegate.color != color ||
        oldDelegate.fill != fill;
  }
}

