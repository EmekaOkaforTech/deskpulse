# Story 7.3: Desktop Client WebSocket Integration - Manual E2E Validation

**Story:** 7-3-desktop-client-websocket-integration
**Test Date:** _____________
**Tester:** _____________
**Environment:** Windows + Raspberry Pi (DeskPulse backend)

---

## Prerequisites

- [ ] Windows 10/11 PC with DeskPulse Windows client installed
- [ ] Raspberry Pi running DeskPulse backend (Flask-SocketIO server)
- [ ] Network connectivity between Windows PC and Pi (same LAN or mDNS working)
- [ ] Backend URL configured in Windows client config.json (e.g., `http://raspberrypi.local:5000`)
- [ ] Pi camera operational (for posture detection)

---

## Test 1: Initial Connection

**Objective:** Verify Windows client connects to backend on startup

### Steps:
1. Start DeskPulse Windows client (double-click system tray icon or run from Start menu)
2. Observe system tray icon in Windows taskbar

### Expected Results:
- [ ] System tray icon appears in taskbar (head + spine graphic)
- [ ] Icon color changes from red (disconnected) to green (connected)
- [ ] Hover over icon shows tooltip: "DeskPulse - Today: X% good posture, Xh Xm tracked"
- [ ] Toast notification appears: "DeskPulse Connected - Connected to Raspberry Pi. Monitoring active."
- [ ] **Duration:** Connection completes within 5 seconds

### Actual Results:
_____________________________________________________________________________

---

## Test 2: Pause/Resume Monitoring Cycle

**Objective:** Verify pause/resume controls sync with backend

### Steps:
1. Right-click system tray icon
2. Select "Pause Monitoring" from context menu
3. Wait 2 seconds
4. Observe icon color
5. Open web dashboard in browser (`http://raspberrypi.local:5000`)
6. Verify "Resume Monitoring" button is enabled on web dashboard
7. Right-click system tray icon again
8. Select "Resume Monitoring"
9. Wait 2 seconds
10. Observe icon color

### Expected Results:
- [ ] After "Pause": Icon turns gray (monitoring paused state)
- [ ] Web dashboard shows "Resume Monitoring" button enabled (cross-client sync)
- [ ] Backend stops tracking posture events (check web dashboard stats - no new events)
- [ ] After "Resume": Icon turns green (monitoring active state)
- [ ] Web dashboard shows "Pause Monitoring" button enabled
- [ ] Backend resumes tracking posture events
- [ ] **Multi-client sync:** Both clients (Windows + web) show same state

### Actual Results:
_____________________________________________________________________________

---

## Test 3: Posture Alert Notifications

**Objective:** Verify alert_triggered event shows toast notification

### Steps:
1. Ensure monitoring active (green icon)
2. Maintain bad posture for 10+ minutes (slouch in chair, lean forward excessively)
3. Wait for backend to detect bad posture duration >= 600 seconds (10 minutes)
4. Observe Windows toast notification

### Expected Results:
- [ ] After 10 minutes of bad posture: Toast notification appears
- [ ] Notification title: "Posture Alert ⚠️"
- [ ] Notification message: "You've been in poor posture for X minutes. Time to adjust your position!"
- [ ] Notification has "View Dashboard" action button
- [ ] Clicking "View Dashboard" opens backend URL in browser
- [ ] **Sound:** Windows notification sound plays
- [ ] **Duration:** Notification stays visible for 10 seconds

### Actual Results:
_____________________________________________________________________________

---

## Test 4: Posture Correction Notifications

**Objective:** Verify posture_corrected event shows toast notification

### Steps:
1. After receiving posture alert (Test 3)
2. Correct posture (sit up straight, shoulders back)
3. Maintain good posture for 30+ seconds
4. Observe Windows toast notification

### Expected Results:
- [ ] Toast notification appears: "Great Job! ✓"
- [ ] Notification message: "Good posture restored. Your body thanks you!"
- [ ] **No action button** (auto-dismiss after 5 seconds)
- [ ] **Sound:** Windows notification sound plays
- [ ] Notification disappears after 5 seconds

### Actual Results:
_____________________________________________________________________________

---

## Test 5: Connection Resilience (Auto-Reconnect)

**Objective:** Verify client handles backend disconnect/reconnect gracefully

### Steps:
1. Start Windows client with backend running (green icon)
2. Stop Flask backend on Pi: `sudo systemctl stop deskpulse`
3. Wait 5 seconds
4. Observe icon color and toast notification
5. Wait 30 seconds (observe auto-reconnect attempts in logs)
6. Restart backend: `sudo systemctl start deskpulse`
7. Wait 15 seconds
8. Observe icon color and reconnection

### Expected Results:
- [ ] After backend stops: Icon turns red (disconnected)
- [ ] Toast notification: "DeskPulse Disconnected - Lost connection to Raspberry Pi. Retrying..."
- [ ] Tooltip shows: "DeskPulse - Disconnected"
- [ ] **Auto-reconnect:** Client attempts reconnection (check logs: 5s → 10s → 20s → 30s backoff)
- [ ] After backend restart: Icon turns green (reconnected)
- [ ] Toast notification: "DeskPulse Connected - Connected to Raspberry Pi. Monitoring active."
- [ ] Tooltip resumes showing live stats
- [ ] **No app restart required:** Reconnection happens automatically

### Actual Results:
_____________________________________________________________________________

---

## Test 6: Tooltip Live Stats Updates

**Objective:** Verify tooltip updates every 60 seconds with latest stats

### Steps:
1. Start Windows client (green icon)
2. Hover over icon to see initial tooltip
3. Wait 60 seconds
4. Hover over icon again
5. Note any changes in stats (posture score, duration tracked)
6. Wait another 60 seconds
7. Hover over icon again

### Expected Results:
- [ ] Initial tooltip: "DeskPulse - Today: X% good posture, Xh Xm tracked"
- [ ] After 60s: Tooltip updates with new stats (duration increases by 1 minute)
- [ ] After 120s: Tooltip updates again
- [ ] **Update frequency:** Every 60 seconds (check logs for "Tooltip updated from API")
- [ ] **Background operation:** No UI freezing or blocking during updates
- [ ] **Error handling:** If API fails, tooltip keeps previous value (no crash)

### Actual Results:
_____________________________________________________________________________

---

## Test 7: Multi-Client State Synchronization

**Objective:** Verify Windows client and web dashboard stay in sync

### Steps:
1. Open web dashboard in browser
2. Open Windows client (both showing green icon/monitoring active)
3. From **web dashboard**: Click "Pause Monitoring"
4. Observe Windows client icon
5. From **Windows client**: Right-click → Resume Monitoring
6. Observe web dashboard button state

### Expected Results:
- [ ] **Pause from web:** Windows client icon immediately turns gray (within 1 second)
- [ ] **Resume from Windows:** Web dashboard button changes from "Pause" to "Resume" (within 1 second)
- [ ] **Broadcast events:** Both clients receive monitoring_status events (check browser console)
- [ ] **Single source of truth:** Backend AlertManager state determines client state (no conflicts)

### Actual Results:
_____________________________________________________________________________

---

## Test 8: Error Handling - Backend Unavailable

**Objective:** Verify error event shows MessageBox to user

### Steps:
1. Stop camera service on Pi: `sudo systemctl stop deskpulse` (kills cv_pipeline)
2. Restart Flask backend without camera: `SKIP_CAMERA=1 venv/bin/python wsgi.py`
3. Windows client should reconnect (green icon)
4. Right-click icon → Click "Pause Monitoring"
5. Observe error handling

### Expected Results:
- [ ] MessageBox appears with title: "DeskPulse Backend Error"
- [ ] Message body: "Monitoring controls unavailable - camera service not started..."
- [ ] **User acknowledgment:** OK button allows user to dismiss error
- [ ] **Retry enabled:** User can click "Pause Monitoring" again after fixing backend
- [ ] **No crash:** Application continues running normally

### Actual Results:
_____________________________________________________________________________

---

## Test 9: Thread Management & Graceful Shutdown

**Objective:** Verify threads stop cleanly on application exit

### Steps:
1. Start Windows client (green icon, connected)
2. Right-click icon → Exit
3. Observe application shutdown
4. Check Windows Task Manager (Ctrl+Shift+Esc) → Details tab
5. Verify no lingering `deskpulse.exe` or Python processes

### Expected Results:
- [ ] Application exits within 2 seconds
- [ ] SocketIO disconnection logged: "Disconnecting from backend"
- [ ] Tooltip update thread stops: "Tooltip update thread stopped"
- [ ] No zombie processes in Task Manager
- [ ] Logs flushed completely (check log file for "Exiting DeskPulse Windows client")

### Actual Results:
_____________________________________________________________________________

---

## Test 10: Network Interruption Recovery

**Objective:** Verify client survives temporary network loss

### Steps:
1. Start Windows client (green icon, connected)
2. Disconnect Windows PC from network (disable Wi-Fi or unplug Ethernet)
3. Wait 10 seconds
4. Reconnect network
5. Wait 15 seconds
6. Observe reconnection

### Expected Results:
- [ ] After network loss: Icon turns red (disconnected)
- [ ] Toast notification: "DeskPulse Disconnected..."
- [ ] **Auto-reconnect:** Client retries connection (exponential backoff: 5s → 10s → 20s → 30s)
- [ ] After network restore: Icon turns green (reconnected)
- [ ] Toast notification: "DeskPulse Connected..."
- [ ] **No data loss:** Stats fetched fresh on reconnect (no missed events replayed)
- [ ] **Acceptable:** Stats are current-state only, not historical

### Actual Results:
_____________________________________________________________________________

---

## Performance Validation

### CPU Usage (Windows Task Manager)
- [ ] Idle (connected): < 1% CPU
- [ ] During tooltip update: < 2% CPU spike (60s interval)
- [ ] During notification display: < 3% CPU spike
- [ ] **Continuous monitoring:** No busy-wait loops

### Memory Usage (Windows Task Manager)
- [ ] Application: ~30-50MB RAM (Python + SocketIO + pystray + Pillow)
- [ ] No memory leaks after 1+ hour runtime (memory stable)

### Network Traffic (Pi backend logs)
- [ ] Initial connect: ~2KB (SocketIO handshake)
- [ ] Event emissions: ~100-500 bytes per event
- [ ] Tooltip API calls: ~1KB every 60s
- [ ] **Total:** < 1KB/s average (minimal)

---

## Sign-Off Checklist

**All Automated Tests:**
- [ ] 60/60 unit tests passing (pytest tests/test_windows*.py)

**All Manual E2E Tests:**
- [ ] Test 1: Initial Connection ✅
- [ ] Test 2: Pause/Resume Cycle ✅
- [ ] Test 3: Posture Alert Notifications ✅
- [ ] Test 4: Posture Correction Notifications ✅
- [ ] Test 5: Connection Resilience ✅
- [ ] Test 6: Tooltip Live Stats Updates ✅
- [ ] Test 7: Multi-Client Synchronization ✅
- [ ] Test 8: Error Handling ✅
- [ ] Test 9: Thread Management ✅
- [ ] Test 10: Network Interruption Recovery ✅

**Performance Validation:**
- [ ] CPU usage acceptable (< 3% average)
- [ ] Memory usage acceptable (< 50MB)
- [ ] Network traffic minimal (< 1KB/s)

**Enterprise-Grade Quality:**
- [ ] ✅ Real backend connections (NO MOCK DATA)
- [ ] ✅ Defensive extraction (all event handlers use `.get()` with defaults)
- [ ] ✅ Error handling (all exceptions logged, user-friendly MessageBoxes)
- [ ] ✅ Thread management (daemon threads, graceful shutdown)
- [ ] ✅ Auto-reconnect (exponential backoff 5s → 30s)
- [ ] ✅ Multi-client sync (broadcast events to all clients)

---

## Test Results Summary

**Passed:** _____ / 10 manual tests
**Failed:** _____ / 10 manual tests
**Blocked:** _____ / 10 manual tests

**Issues Found:**
_____________________________________________________________________________
_____________________________________________________________________________

**Sign-Off:**
- [ ] All critical tests passing (Tests 1-7 MUST pass)
- [ ] No blocking issues found
- [ ] Story 7.3 ready for production deployment

**Tester Signature:** _____________
**Date:** _____________
