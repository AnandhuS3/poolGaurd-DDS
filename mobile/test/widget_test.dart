// Widget tests for DDS Guard mobile app.
//
// NOTE: Full app smoke tests require Firebase to be initialized.
// These unit-level tests cover model and widget logic that can run without
// a real Firebase environment.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dds_mobile/models/alert_model.dart';
import 'package:dds_mobile/widgets/status_badge.dart';
import 'package:dds_mobile/widgets/alert_card.dart';

void main() {
  group('AlertModel', () {
    test('fromFcmData parses strings correctly', () {
      final data = {
        'alert_id': '42',
        'track_id': '7',
        'state': 'danger',
        'duration': '12.5',
        'confidence': '0.91',
        'camera_id': 'cam_01',
        'timestamp': '2025-01-01T10:00:00.000Z',
      };
      final alert = AlertModel.fromFcmData(data);
      expect(alert.alertId, 42);
      expect(alert.trackId, 7);
      expect(alert.state, AlertState.danger);
      expect(alert.duration, 12.5);
      expect(alert.confidence, closeTo(0.91, 0.001));
      expect(alert.cameraId, 'cam_01');
      expect(alert.acknowledged, false);
    });

    test('fromJson parses REST response correctly', () {
      final json = {
        'alert_id': 1,
        'track_id': 3,
        'state': 'warning',
        'duration': 5.0,
        'camera_id': 'cam_02',
        'timestamp': '2025-06-01T08:00:00.000Z',
        'acknowledged': true,
      };
      final alert = AlertModel.fromJson(json);
      expect(alert.state, AlertState.warning);
      expect(alert.acknowledged, true);
    });

    test('unknown state defaults to warning', () {
      expect(alertStateFromString('unknown_value'), AlertState.warning);
    });

    test('copyWithAcknowledged returns new model with ack=true', () {
      final alert = AlertModel(
        alertId: 1,
        trackId: 1,
        state: AlertState.danger,
        duration: 10,
        cameraId: 'cam_01',
        timestamp: DateTime.now(),
        acknowledged: false,
      );
      final acked = alert.copyWithAcknowledged();
      expect(acked.acknowledged, true);
      expect(alert.acknowledged, false); // original unchanged
    });
  });

  group('StatusBadge widget', () {
    testWidgets('shows DANGER label for danger state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: StatusBadge(state: AlertState.danger),
          ),
        ),
      );
      expect(find.text('DANGER'), findsOneWidget);
    });

    testWidgets('shows WARNING label for warning state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: StatusBadge(state: AlertState.warning),
          ),
        ),
      );
      expect(find.text('WARNING'), findsOneWidget);
    });
  });

  group('AlertCard widget', () {
    testWidgets('renders track id and camera', (tester) async {
      final alert = AlertModel(
        alertId: 5,
        trackId: 12,
        state: AlertState.danger,
        duration: 8.0,
        cameraId: 'cam_pool',
        timestamp: DateTime.now(),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AlertCard(alert: alert),
          ),
        ),
      );
      expect(find.text('Track 12'), findsOneWidget);
      expect(find.textContaining('cam_pool'), findsOneWidget);
    });
  });
}
