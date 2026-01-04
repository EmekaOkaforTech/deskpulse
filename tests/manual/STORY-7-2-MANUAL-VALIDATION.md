# Story 7.2 Manual Validation Checklist

**Story:** Windows Toast Notifications
**Date:** 2026-01-03
**Tester:** ___________________
**Environment:**
- Windows Version: ___________________
- Python Version: ___________________
- Pi Backend URL: ___________________

---

## Prerequisites

- [ ] Raspberry Pi backend running (app/cv/pipeline.py active)
- [ ] Windows desktop client built: `python -m app.windows_client`
- [ ] Backend reachable from Windows: `ping <pi-hostname>`
- [ ] Camera connected to Pi and working
- [ ] User seated at desk with camera capturing posture

---

## AC1: Posture Alert Toast Notification (alert_triggered Event)

**Objective:** Verify Windows toast notification appears when bad posture threshold exceeded.

### Setup
1. Start Pi backend: `python wsgi.py`
2. Start Windows client: `python -m app.windows_client`
3. Verify connection notification appears: "DeskPulse Connected"

### Test Steps
1. **Trigger bad posture:**
   - Slouch or lean away from camera
   - Wait for bad posture detection (should appear in dashboard)
   - Continue bad posture for 10+ minutes

2. **Verify alert notification:**
   - [ ] Toast notification appears with title: "Posture Alert ⚠️"
   - [ ] Message shows: "You've been in poor posture for X minutes. Time to adjust your position!"
   - [ ] Duration value X is correct (e.g., "10 minutes" for 600 seconds)
   - [ ] Notification shows for 10 seconds
   - [ ] Windows notification sound plays
   - [ ] DeskPulse icon shown (if icon.ico exists in %APPDATA%\DeskPulse)

3. **Verify action buttons:**
   - [ ] "View Dashboard" button present
   - [ ] "Dismiss" button present (or click X to dismiss)
   - [ ] Click "View Dashboard" → browser opens to Pi backend URL
   - [ ] Notification auto-dismisses after clicking button

4. **Verify Windows Action Center integration:**
   - [ ] Notification persists in Action Center after auto-dismiss
   - [ ] Click notification from Action Center → opens dashboard
   - [ ] App name shows "DeskPulse" in notification

**Backend Log Verification:**
```bash
# On Pi, check backend logs:
tail -f logs/deskpulse.log | grep "alert_triggered"
```
- [ ] Backend log shows: "Emitting alert_triggered event via SocketIO..."
- [ ] Backend log shows: "✅ alert_triggered event emitted successfully"
- [ ] Event includes `broadcast=True` (verify in code or confirm multi-client works)

**Windows Client Log Verification:**
```powershell
# Check Windows client logs:
type %APPDATA%\DeskPulse\logs\client.log | findstr "alert_triggered"
```
- [ ] Client log shows: "alert_triggered event received: Xs" (duration in seconds)
- [ ] Client log shows: "Posture alert notification queued: Xmin"
- [ ] Client log shows: "Notification shown (priority=1)"

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC2: Posture Correction Toast Notification (posture_corrected Event)

**Objective:** Verify Windows toast notification appears when user corrects posture after alert.

### Test Steps
1. **Trigger posture correction:**
   - Continue from AC1 test (bad posture alert received)
   - Sit up straight and restore good posture
   - Wait for dashboard to show "Good posture" status

2. **Verify correction notification:**
   - [ ] Toast notification appears with title: "Great Job! ✓"
   - [ ] Message shows: "Good posture restored. Your body thanks you!"
   - [ ] Notification shows for 5 seconds
   - [ ] Windows notification sound plays (positive tone preferred)
   - [ ] NO action buttons present (auto-dismiss only)

3. **Verify Windows Action Center:**
   - [ ] Notification appears in Action Center
   - [ ] Clicking notification does nothing (no action buttons)

**Backend Log Verification:**
```bash
tail -f logs/deskpulse.log | grep "posture_corrected"
```
- [ ] Backend log shows: "Posture correction confirmed: Xs"
- [ ] SocketIO event emitted with `broadcast=True`

**Windows Client Log Verification:**
```powershell
type %APPDATA%\DeskPulse\logs\client.log | findstr "posture_corrected"
```
- [ ] Client log shows: "posture_corrected event received"
- [ ] Client log shows: "Posture correction notification queued"
- [ ] Client log shows: "Notification shown (priority=2)"

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC3: Connection Status Toast Notifications

**Objective:** Verify connection/disconnection notifications appear once per event.

### Test 3.1: Connected Notification
1. **Test initial connection:**
   - Close Windows client if running
   - Start Windows client: `python -m app.windows_client`

2. **Verify connected notification:**
   - [ ] Toast notification appears with title: "DeskPulse Connected"
   - [ ] Message shows: "Connected to Raspberry Pi. Monitoring active."
   - [ ] Notification shows for 5 seconds
   - [ ] NO action buttons present

3. **Verify single notification:**
   - [ ] Notification appears ONCE on startup (not repeated)
   - [ ] No duplicate notifications during auto-reconnect attempts

**PASS/FAIL:** ________

### Test 3.2: Disconnected Notification
1. **Test disconnection:**
   - Stop Pi backend: `Ctrl+C` on wsgi.py
   - Wait for client to detect disconnection

2. **Verify disconnected notification:**
   - [ ] Toast notification appears with title: "DeskPulse Disconnected"
   - [ ] Message shows: "Lost connection to Raspberry Pi. Retrying..."
   - [ ] Notification shows for 5 seconds
   - [ ] NO action buttons present

3. **Verify single notification:**
   - [ ] Notification appears ONCE on disconnect (not repeated during reconnect attempts)

**PASS/FAIL:** ________

### Test 3.3: Reconnection
1. **Test reconnection:**
   - Restart Pi backend: `python wsgi.py`
   - Wait for client to reconnect

2. **Verify reconnected notification:**
   - [ ] "DeskPulse Connected" notification appears again
   - [ ] Notification appears ONCE (not spammed)

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC4: Notification Queue Management (Prevents Spam)

**Objective:** Verify notifications display one at a time and queue doesn't overflow.

### Test 4.1: Sequential Notification Processing
1. **Trigger multiple rapid events:**
   - Backend simulation: Manually trigger multiple SocketIO events rapidly
   - OR: Trigger bad posture, correct posture, disconnect, reconnect in quick succession

2. **Verify sequential processing:**
   - [ ] Notifications appear ONE AT A TIME (not overlapping)
   - [ ] Second notification waits until first dismisses
   - [ ] Notifications appear in priority order (alert > correction > connection)

**PASS/FAIL:** ________

### Test 4.2: Queue Full Behavior
1. **Flood notification queue:**
   - Simulate 6+ rapid SocketIO events (more than queue max of 5)
   - Can use backend script to emit events rapidly

2. **Verify queue full handling:**
   - [ ] Queue accepts maximum 5 notifications
   - [ ] 6th notification triggers drop of lowest-priority (connection)
   - [ ] High-priority alerts NEVER dropped
   - [ ] Windows client log shows: "Notification queue full, dropped lowest priority"

**Windows Client Log Verification:**
```powershell
type %APPDATA%\DeskPulse\logs\client.log | findstr "queue"
```
- [ ] Log shows queue size tracking: "Notification queued (priority=X, queue_size=Y)"
- [ ] Log shows drop warning if queue full

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC5: Notification Click Actions

**Objective:** Verify "View Dashboard" button opens browser correctly.

### Test Steps
1. **Trigger alert notification:**
   - Repeat AC1 test to get alert notification

2. **Test View Dashboard button:**
   - [ ] Click "View Dashboard" button
   - [ ] Default browser opens immediately (<500ms)
   - [ ] Browser navigates to correct backend URL (e.g., http://raspberrypi.local:5000)
   - [ ] Dashboard loads successfully
   - [ ] Notification auto-dismisses after clicking button

3. **Test dismiss action:**
   - Trigger another alert notification
   - [ ] Click "Dismiss" or X button
   - [ ] Notification closes immediately
   - [ ] No browser opens
   - [ ] No state change in application

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC6: SocketIO Event Handler Integration

**Objective:** Verify SocketIO events trigger correct notifications.

### Code Verification
- [ ] File `app/windows_client/socketio_client.py` contains:
  - [ ] `on_alert_triggered(data)` handler registered
  - [ ] `on_posture_corrected(data)` handler registered
  - [ ] `on_connect()` calls `notifier.show_connection_status(True)`
  - [ ] `on_disconnect()` calls `notifier.show_connection_status(False)`

### Functional Verification (covered in AC1-AC3)
- [ ] alert_triggered event → posture alert notification
- [ ] posture_corrected event → correction notification
- [ ] connect event → connected notification
- [ ] disconnect event → disconnected notification

**PASS/FAIL:** ________

---

## AC7: Enterprise-Grade Error Handling

**Objective:** Verify graceful degradation and resilience.

### Test 7.1: winotify Unavailable
1. **Simulate winotify failure:**
   - Rename winotify package: `pip uninstall winotify`
   - Restart Windows client

2. **Verify graceful degradation:**
   - [ ] Client starts successfully (no crash)
   - [ ] System tray icon appears and works
   - [ ] Log shows: "winotify not available - Toast notifications disabled"
   - [ ] SocketIO events still received
   - [ ] Application continues functioning (no notifications shown)

3. **Restore winotify:**
   - [ ] `pip install winotify>=1.1.0`
   - [ ] Restart client → notifications work again

**PASS/FAIL:** ________

### Test 7.2: Notification Display Failure
1. **Simulate notification failure:**
   - This is hard to simulate - review code instead
   - [ ] Code file `app/windows_client/notifier.py:191` has try/except around `notification.show()`
   - [ ] Exception logged with exc_info=True
   - [ ] Other notifications continue processing (no crash)

**PASS/FAIL:** ________

### Test 7.3: Thread Failure Recovery
1. **Code review:**
   - [ ] File `notifier.py:110` has try/except in `_notification_queue_loop`
   - [ ] Retry counter increments on failure: `_queue_thread_retries`
   - [ ] Max 3 retries before disabling: `if self._queue_thread_retries >= 3`
   - [ ] Sleep 5s between retries

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC8: Windows Notification Center Integration

**Objective:** Verify notifications persist in Action Center.

### Test Steps
1. **Trigger multiple notifications:**
   - Trigger alert, correction, connection notifications

2. **Verify Action Center:**
   - [ ] Open Windows Action Center (Win+A)
   - [ ] All DeskPulse notifications visible in list
   - [ ] Grouped under "DeskPulse" app name
   - [ ] Clicking old notification opens dashboard (alerts only)

3. **Verify user control:**
   - [ ] Open Windows Settings → Notifications
   - [ ] DeskPulse listed in app notifications
   - [ ] Can disable DeskPulse notifications
   - [ ] Disabled notifications: client continues working (system tray functional)

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## AC9: Notification Content Localization (Future-Ready)

**Objective:** Verify message templates support future localization.

### Code Review
- [ ] File `notifier.py:268` uses template string with {duration_minutes} variable
- [ ] Messages stored as inline strings (hardcoded English for MVP)
- [ ] Template pattern allows future variable substitution
- [ ] No localization implementation required for Story 7.2

**PASS/FAIL:** ________

---

## AC10: Logging for Notification Analytics

**Objective:** Verify comprehensive logging for troubleshooting and analytics.

### Test Steps
1. **Trigger all notification types:**
   - Alert, correction, connection, disconnection

2. **Verify Windows client logs:**
```powershell
type %APPDATA%\DeskPulse\logs\client.log
```

**Expected Log Entries (INFO level):**
- [ ] "Posture alert notification queued: Xmin"
- [ ] "Posture correction notification queued"
- [ ] "Connection status notification queued: connected=True"
- [ ] "Connection status notification queued: connected=False"
- [ ] "Notification shown (priority=X)"

**Expected Log Entries (WARNING level):**
- [ ] "Notification queue full, dropped lowest priority" (if queue full)

**Expected Log Entries (ERROR level):**
- [ ] "Failed to show notification: ..." (if notification fails)
- [ ] All errors include exc_info=True (stack traces)

3. **Verify logger name:**
   - [ ] Logger named: `deskpulse.windows.notifier`

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## Integration Testing

### Multi-Client Broadcast Test
**Objective:** Verify broadcast=True sends events to all clients.

1. **Setup:**
   - Open browser dashboard on Windows: http://<pi-url>:5000
   - Start Windows desktop client
   - Both clients connected

2. **Trigger alert:**
   - Maintain bad posture for 10+ minutes

3. **Verify both clients receive event:**
   - [ ] Browser dashboard shows alert message
   - [ ] Windows toast notification appears
   - [ ] Both notifications show same duration

**PASS/FAIL:** ________

### Stress Test
**Objective:** Verify system handles extended usage.

1. **Run for 2+ hours:**
   - [ ] Leave client running with Pi backend active
   - [ ] Trigger multiple posture events (alerts and corrections)
   - [ ] No memory leaks (Task Manager: stable memory usage)
   - [ ] No thread crashes (client.log: no "Max notification retries reached")
   - [ ] Notifications continue working after extended runtime

**PASS/FAIL:** ________
**Notes:** _____________________________________________________________

---

## Final Validation Checklist

**All Acceptance Criteria Validated:**
- [ ] AC1: Posture Alert Toast Notification
- [ ] AC2: Posture Correction Toast Notification
- [ ] AC3: Connection Status Toast Notifications
- [ ] AC4: Notification Queue Management
- [ ] AC5: Notification Click Actions
- [ ] AC6: SocketIO Event Handler Integration
- [ ] AC7: Enterprise-Grade Error Handling
- [ ] AC8: Windows Notification Center Integration
- [ ] AC9: Notification Content Localization (Future-Ready)
- [ ] AC10: Logging for Notification Analytics

**Integration Testing:**
- [ ] Multi-client broadcast test passed
- [ ] Stress test passed (2+ hours)

**Code Quality:**
- [ ] All unit tests passing (29 tests)
- [ ] No flake8 errors
- [ ] Code reviewed and approved

---

## Sign-Off

**Tester Signature:** ___________________
**Date:** ___________________
**Overall PASS/FAIL:** ________

**Story Status:**
- [ ] READY FOR PRODUCTION
- [ ] NEEDS REWORK (list issues below)

**Issues Found:**
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
