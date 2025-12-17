# Manual Test Plan: Alert Response Loop Integration

**Story:** 3-6-alert-response-loop-integration-testing
**Date:** 2025-12-15
**Status:** Ready for Manual Testing
**Epic:** 3 - Alert & Notification System (Final Story)

## Overview

This manual test plan validates the complete alert response loop integration across all Epic 3 components (Stories 3.1-3.5). The goal is to verify that the "gently persistent, not demanding" UX design works seamlessly from bad posture detection through correction.

## Prerequisites

- **Hardware:** Raspberry Pi 4 with USB camera (Logitech C270 or compatible)
- **Software:** DeskPulse service running (systemd or development mode)
- **Browser:** Chromium/Chrome with notification permission granted
- **Desktop:** LXDE with libnotify installed
- **Service Status:** Verify running: `sudo systemctl status deskpulse`
- **Dashboard Access:** http://localhost:5000

## Quick Verification Checklist

✅ **Infrastructure:**
- DeskPulse service running and healthy
- Camera connected and detected: `v4l2-ctl --list-devices`
- Dashboard accessible: http://localhost:5000/
- SocketIO connection established (check browser console)
- Notification permission granted (browser + desktop)
- Logs accessible: `journalctl -u deskpulse -f`

---

## Test Scenario 1: Basic Alert Flow (Happy Path) - AC1

**Objective:** Verify complete alert cycle from good posture → bad → alert → correction

**Story Coverage:** All Epic 3 components (Stories 3.1-3.5)

**Duration:** ~15 minutes

### Preconditions
1. DeskPulse service running: `sudo systemctl status deskpulse`
2. Dashboard open in browser: http://localhost:5000
3. Good posture initially (sit up straight, shoulders back)
4. Camera view shows you clearly
5. Terminal open for logs: `journalctl -u deskpulse -f | grep -i alert`

### Test Steps

#### Step 1: Good Posture Baseline (0-1 minutes)
**Action:** Sit in good posture for 1 minute

**Expected Results:**
- ✅ Dashboard status: "✓ Good posture - keep it up!" (green text)
- ✅ Status indicator: Green circle
- ✅ Alert banner: Not visible
- ✅ Duration counter: Not visible or shows "0s"

**Logs to Verify:**
```
# Should NOT see:
"Alert threshold reached" or "Bad posture detected"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** __________PASS_____________________________________

---

#### Step 2: Bad Posture Detection (1-2 minutes)
**Action:** Slouch (bad posture) and maintain for 30 seconds

**Expected Results:**
- ✅ Dashboard status: "⚠ Adjust your posture - shoulders back, spine straight" (amber text)
- ✅ Status indicator: Amber circle
- ✅ Alert banner: Not visible yet (under threshold)
- ✅ Duration tracking: "Xs" (incrementing)
- ✅ No notifications yet

**Logs to Verify:**
```
# Should see:
"Bad posture detected - tracking duration"
# Should NOT see:
"Alert threshold reached"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** __FAIL , Bad posture maintained for 3mins and there was no banner or tracking duration anywhere on the page - ps fix__________________________________________

---

#### Step 3: Threshold Reached (10 minutes bad posture)
**Action:** Continue bad posture for full 10 minutes (total elapsed time)

**Expected Results at 10-minute mark:**

**Desktop Notification (Story 3.2):**
- ✅ Notification appears with libnotify
- ✅ Title: "DeskPulse"
- ✅ Message: "You've been in bad posture for 10 minutes. Time for a posture check!"
- ✅ Icon: Warning icon (dialog-warning)
- ✅ Urgency: Normal

**Browser Notification (Story 3.3):**
- ✅ Browser notification appears
- ✅ Title: "DeskPulse Posture Alert"
- ✅ Body: "Bad posture detected for 10 minutes"
- ✅ Icon: DeskPulse logo
- ✅ Auto-closes after 10 seconds

**Dashboard Alert Banner (Story 3.3):**
- ✅ Warm yellow background (#fffbeb)
- ✅ Amber border (2px solid #f59e0b)
- ✅ Icon: ⚠️ Posture Alert
- ✅ Message: "Bad posture detected for 10 minutes"
- ✅ Button: "I've corrected my posture" (secondary style)

**Dashboard UI:**
- ✅ Status remains amber
- ✅ Duration counter: "600s" or "10m 0s"
- ✅ Posture message: Still showing bad posture warning

**Logs to Verify:**
```
"Alert threshold reached: 600s >= 600s"
"Sending alert notification: duration=600s"
"Desktop notification sent successfully"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Screenshots:** ☐ Desktop notification / ☐ Browser notification / ☐ Dashboard alert banner
**Notes:** _______Fail , bad posture maintained over 10mins and there was no notification for my browser , no dashboard alert banner________________________________________

---

#### Step 4: Posture Correction (Good posture restored)
**Action:** Sit up straight (correct posture) immediately

**Expected Results within 5 seconds:**

**Desktop Notification (Story 3.5):**
- ✅ Confirmation notification appears
- ✅ Title: "DeskPulse"
- ✅ Message: "✓ Good posture restored! Nice work!"
- ✅ Icon: Dialog-information
- ✅ Urgency: Normal

**Browser Notification (Story 3.5):**
- ✅ Confirmation notification appears
- ✅ Title: "DeskPulse"
- ✅ Body: "✓ Good posture restored! Nice work!"
- ✅ Icon: DeskPulse logo

**Dashboard Alert Banner:**
- ✅ Banner clears completely (disappears)
- ✅ No residual yellow highlight

**Dashboard UI:**
- ✅ Status: "✓ Good posture - keep it up!" (green text)
- ✅ Status indicator: Green circle
- ✅ Duration counter: Resets to "0s" or disappears
- ✅ Green confirmation message visible for ~5 seconds

**Logs to Verify:**
```
"Posture corrected after alert - bad duration was [~600]s"
"Sending confirmation notification"
"Desktop notification sent successfully"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Screenshots:** ☐ Confirmation notification / ☐ Dashboard green confirmation
**Notes:** ________There is an alert when posture changes, Great!keep up the good posture or sit up straight and align your shoulders, there are no other alerts on the page except these_______________________________________

---

#### Step 5: State Reset Verification
**Action:** Verify alert state reset completely

**Expected Results:**
- ✅ No alert banner visible
- ✅ Duration counter reset to 0
- ✅ Status indicator green
- ✅ No pending alerts in logs

**Logs to Verify:**
```
# Should see state reset indicators:
"AlertManager state reset: bad_posture_start_time=None, last_alert_time=None"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _________FAIL, no state reset indicators seen.______________________________________

---

## Test Scenario 2: User Ignores Alert (Cooldown Behavior) - AC2

**Objective:** Verify alert cooldown prevents notification spam

**Story Coverage:** Story 3.1 (AlertManager cooldown logic)

**Duration:** ~20 minutes

### Preconditions
Same as Scenario 1

### Test Steps

#### Step 1: First Alert at 10 Minutes
**Action:** Trigger alert by sitting in bad posture for 10 minutes

**Expected Results:**
- ✅ Desktop + browser notifications appear (as in Scenario 1, Step 3)
- ✅ Dashboard alert banner appears

**Actual Result:** ☐ PASS / ☐ FAIL
**Time Alert Triggered:** _____FAIL - none seen__________

---

#### Step 2: Cooldown Period (12 minutes total)
**Action:** Continue bad posture for 2 more minutes (12 minutes total elapsed)

**Expected Results:**
- ✅ Dashboard alert banner PERSISTS (does not clear)
- ✅ Duration counter continues: "720s" or "12m 0s"
- ✅ **NO new notifications sent** (cooldown active)
- ✅ Status remains amber

**Logs to Verify:**
```
# Should see:
"Alert cooldown active - suppressing notification (time_since_last < 300s)"
# Should NOT see:
"Sending alert notification" (between 10-15 min mark)
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ______________FAIL - None Seen_________________________________

---

#### Step 3: Cooldown Expired (15 minutes total)
**Action:** Continue bad posture until 15 minutes total elapsed

**Expected Results at 15-minute mark:**
- ✅ **Reminder notification sent** (desktop + browser)
- ✅ Desktop notification: "You've been in bad posture for 15 minutes. Time for a posture check!"
- ✅ Browser notification: "Bad posture detected for 15 minutes"
- ✅ Dashboard alert banner persists (message updates to "15 minutes")
- ✅ Duration counter: "900s" or "15m 0s"

**Logs to Verify:**
```
"Alert cooldown expired - sending reminder (duration: 900s)"
"Sending alert notification: duration=900s"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Time Reminder Sent:** _______________
**Notes:** _______________FAIL No notification_______________

---

#### Step 4: Verify Additional Reminders (20 minutes)
**Action:** (Optional) Continue bad posture to 20 minutes

**Expected Results at 20-minute mark:**
- ✅ Another reminder notification (cooldown expired again)
- ✅ Duration counter: "1200s" or "20m 0s"

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ________FAIL No notification___________________

---

## Test Scenario 3: Privacy Pause (State Management) - AC3

**Objective:** Verify pause/resume monitoring controls work correctly with alert tracking

**Story Coverage:** Story 3.4 (Pause/Resume) + Story 3.1 (AlertManager state)

**Duration:** ~15 minutes

### Preconditions
Same as Scenario 1

### Test Steps

#### Step 1: Start Bad Posture Tracking
**Action:** Sit in bad posture for 3 minutes

**Expected Results:**
- ✅ Bad posture detected, duration tracking starts
- ✅ Duration counter: ~"180s" or "3m 0s"

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ____FAIL No notification_______________________

---

#### Step 2: Pause Monitoring
**Action:** Click "Pause Monitoring" button in dashboard

**Expected Results immediately:**
- ✅ Dashboard status: "⏸ Monitoring Paused" indicator appears
- ✅ Camera feed: CONTINUES (transparency - user sees they're still captured)
- ✅ Alert tracking: STOPS (duration counter disappears or freezes)
- ✅ Alert state: RESET (bad_posture_start_time, last_alert_time cleared)

**Logs to Verify:**
```
"Monitoring paused - resetting alert state"
"AlertManager state reset: bad_posture_start_time=None, last_alert_time=None"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Screenshots:** ☐ Pause indicator visible
**Notes:** _________pass__________________________________

---

#### Step 3: Remain in Bad Posture While Paused
**Action:** Continue bad posture for 5 more minutes while paused

**Expected Results:**
- ✅ **NO alerts triggered** (regardless of posture or time)
- ✅ **NO notifications sent**
- ✅ **NO duration tracking**
- ✅ Pause indicator persists
- ✅ Camera feed continues

**Logs to Verify:**
```
# Should NOT see:
"Bad posture detected" or "Alert threshold reached"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ____________pass_______________________________

---

#### Step 4: Resume Monitoring
**Action:** Click "Resume Monitoring" button

**Expected Results:**
- ✅ Dashboard status: "Monitoring Active" (or similar)
- ✅ Pause indicator disappears
- ✅ Alert tracking enabled again
- ✅ **Fresh tracking session** (previous bad posture duration NOT carried over)

**Logs to Verify:**
```
"Monitoring resumed - alert tracking active"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _____pass______________________________________

---

#### Step 5: New Bad Posture Session After Resume
**Action:** Continue bad posture for 2 minutes after resume

**Expected Results:**
- ✅ Bad posture detected
- ✅ Duration counter: Starts fresh from "0s" (NOT ~"480s" from before pause)
- ✅ Alert threshold countdown: Fresh 10-minute timer starts

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** __________FAIL No notification_________________

---

#### Step 6: Verify No False Confirmation
**Action:** Correct posture (sit up straight)

**Expected Results:**
- ✅ Dashboard shows good posture
- ✅ **NO confirmation notification** (no alert was sent, so no confirmation needed)
- ✅ Status returns to green

**Logs to Verify:**
```
# Should NOT see:
"Posture corrected after alert" or "Sending confirmation"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ____________________FAIL No notification_______

---

## Test Scenario 4: User Absent (Graceful Degradation) - AC4

**Objective:** Verify alert tracking resets when user leaves desk

**Story Coverage:** Story 3.1 (AlertManager) + Story 2.7 (Camera state management)

**Duration:** ~5 minutes

### Preconditions
Same as Scenario 1

### Test Steps

#### Step 1: Start Bad Posture Tracking
**Action:** Sit in bad posture for 2 minutes

**Expected Results:**
- ✅ Bad posture detected, duration tracking
- ✅ Duration counter: ~"120s" or "2m 0s"

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _____Fail_____________________________________

---

#### Step 2: Leave Desk (User Absent)
**Action:** Step out of camera view completely

**Expected Results within 1-2 seconds:**
- ✅ Dashboard status: "👤 Step into camera view to begin monitoring"
- ✅ Status indicator: Gray (not tracking)
- ✅ Duration counter: Disappears or resets to "0s"
- ✅ Alert tracking: RESET (bad_posture_start_time cleared)

**Logs to Verify:**
```
"User not present - resetting alert tracking"
"AlertManager state reset: bad_posture_start_time=None"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Screenshots:** ☐ "Absent" UI state
**Notes:** ______Fail, Duration counter not working or visible

---

#### Step 3: Remain Absent
**Action:** Stay out of camera view for 2 minutes

**Expected Results:**
- ✅ **NO alerts triggered** (user_present=False)
- ✅ **NO duration tracking**
- ✅ Dashboard maintains "absent" message
- ✅ Status indicator remains gray

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _________FAIL Alert triggering not working_____

---

#### Step 4: Return to Desk in Bad Posture
**Action:** Return to camera view in bad posture (slouching)

**Expected Results:**
- ✅ Pose detected immediately
- ✅ Dashboard status: Bad posture warning (amber)
- ✅ Status indicator: Amber
- ✅ **Fresh tracking starts** (does NOT count time away)
- ✅ Duration counter: Starts from "0s"
- ✅ New 10-minute threshold countdown begins

**Logs to Verify:**
```
"User present - pose detected"
"Bad posture detected - tracking duration"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ____FAIL _________________________________

---

#### Step 5: Camera Disconnect Test (Optional)
**Action:** Physically disconnect USB camera (or stop DeskPulse service)

**Expected Results:**
- ✅ Dashboard status: Camera error or "disconnected" message
- ✅ Alert tracking: RESET (same as user absence)
- ✅ Status indicator: Gray or error state

**Logs to Verify:**
```
"Camera disconnected - resetting alert tracking"
"Camera state: disconnected"
```

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ___________Pass________________________________

---

## Test Scenario 5: Edge Cases and Regression Testing

### Test 5.1: Rapid Posture Changes
**Objective:** Verify no alert spam from rapid good/bad cycles

**Steps:**
1. Alternate between good and bad posture every 30 seconds for 5 minutes
2. Never stay in bad posture for 10+ minutes

**Expected Results:**
- ✅ NO alerts triggered (never reached threshold)
- ✅ NO confirmation notifications
- ✅ Duration counter resets each time posture improves
- ✅ No exceptions in logs

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** ____________FAIL no notification to test with

---

### Test 5.2: Browser Tab Inactive
**Objective:** Verify SocketIO events still received when tab inactive

**Steps:**
1. Open dashboard, grant notification permission
2. Switch to different browser tab
3. Trigger alert (10 minutes bad posture)

**Expected Results:**
- ✅ Browser notification appears (even with tab inactive)
- ✅ Dashboard alert banner appears when tab reactivated
- ✅ SocketIO connection maintained

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _____Fail - No browser notification appears__

---

### Test 5.3: Service Restart During Bad Posture
**Objective:** Verify graceful handling of service restart

**Steps:**
1. Start bad posture tracking (5 minutes elapsed)
2. Restart DeskPulse: `sudo systemctl restart deskpulse`
3. Dashboard reconnects automatically

**Expected Results:**
- ✅ Dashboard reconnects via SocketIO
- ✅ Alert tracking resets (fresh session after restart)
- ✅ No error messages to user
- ✅ Previous bad posture duration NOT carried over

**Actual Result:** ☐ PASS / ☐ FAIL
**Notes:** _______Fail - 
dev@pi:~/deskpulse $ sudo systemctl status deskpulse
Unit deskpulse.service could not be found.
dev@pi:~/deskpulse $ journalctl -u deskpulse -f | grep -i alert



---

## Debugging Tips

### If Alerts Don't Trigger
1. Check logs: `journalctl -u deskpulse -f | grep -i alert`
2. Verify threshold config: Should be 600 seconds (10 minutes)
3. Check AlertManager state: Look for "bad_posture_start_time" in logs
4. Verify camera is detecting pose: Look for "Pose detected" logs

### If Notifications Don't Appear
**Desktop (libnotify):**
1. Test manually: `notify-send "Test" "Message"`
2. Check config: `NOTIFICATION_ENABLED=True` in config
3. Verify libnotify installed: `dpkg -l | grep libnotify`

**Browser:**
1. Check permission: DevTools console → `Notification.permission`
2. Verify SocketIO: Console should show "SocketIO connected"
3. Check network tab for WebSocket connection

### If Dashboard Doesn't Update
1. Hard reload: Ctrl+Shift+R
2. Check browser console for JavaScript errors
3. Verify SocketIO connection: `socket.connected` should be true
4. Check network tab: WebSocket should be active

---

## Test Completion Criteria

### All Scenarios Must Pass
- ☐ **Scenario 1:** Basic Alert Flow (Happy Path)
- ☐ **Scenario 2:** User Ignores Alert (Cooldown Behavior)
- ☐ **Scenario 3:** Privacy Pause (State Management)
- ☐ **Scenario 4:** User Absent (Graceful Degradation)
- ☐ **Edge Cases:** Rapid changes, tab inactive, service restart

### Quality Checks
- ☐ No exceptions or errors in logs
- ☐ All desktop notifications appear correctly
- ☐ All browser notifications appear correctly
- ☐ Dashboard alert banner appearance/disappearance works
- ☐ Green confirmation message auto-resets after 5 seconds
- ☐ Logs show complete audit trail for each scenario
- ☐ Alert cooldown prevents spam (5-minute intervals)
- ☐ Pause/resume state management works correctly
- ☐ User absence resets tracking gracefully

---

## Test Results Summary

**Tester:** _______________________________________________
**Date:** _______________________________________________
**Environment:** _______________________________________________
**Camera Model:** ___Pi Cam 3__________________________________
**Browser:** ____Firefox____________________________________

**Overall Status:** ☐ ALL PASS / ☐ PARTIAL FAIL / ☐ BLOCKED
FAIL
**Issues Found:**
```
(List any issues, edge cases, or unexpected behaviors)
```

**Screenshots Attached:**
- ☐ Desktop notification (alert)
- ☐ Desktop notification (confirmation)
- ☐ Browser notification (alert)
- ☐ Browser notification (confirmation)
- ☐ Dashboard alert banner
- ☐ Dashboard pause indicator
- ☐ Dashboard "user absent" state

---

## Next Steps After Testing

1. ☐ Document any issues found in GitHub issues or story notes
2. ☐ Attach screenshots to story file or documentation
3. ☐ Update story file with test execution results
4. ☐ Run full automated test suite to verify no regressions
5. ☐ Run `/bmad:bmm:workflows:code-review` for Epic 3 completion review
6. ☐ Mark story as "review" in sprint-status.yaml
7. ☐ Prepare Epic 3 retrospective summary

---

## Epic 3 Integration Verification

Story 3.6 validates that ALL Epic 3 components work together:

- ✅ **Story 3.1:** Alert threshold tracking (10 min, 5 min cooldown)
- ✅ **Story 3.2:** Desktop notifications (libnotify)
- ✅ **Story 3.3:** Browser notifications (SocketIO)
- ✅ **Story 3.4:** Pause/resume monitoring controls
- ✅ **Story 3.5:** Posture correction confirmation feedback
- ✅ **Story 3.6:** Integration testing (this test plan)

**Epic 3 Status:** ☐ COMPLETE / ☐ ISSUES FOUND

---

**End of Manual Test Plan**
