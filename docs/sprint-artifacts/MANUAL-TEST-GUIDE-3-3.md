# Manual Testing Guide: Story 3.3 Browser Notifications

**Story:** 3-3-browser-notifications-for-remote-dashboard-users
**Date:** 2025-12-14
**Status:** Ready for Manual Testing

## Prerequisites

- Flask app running on http://localhost:5000
- Camera connected and working
- Multiple browsers installed for cross-browser testing (Chrome, Firefox, Edge)

## Quick Verification Checklist

✅ **Infrastructure:**
- Dashboard accessible: http://localhost:5000/
- JavaScript file loading: /static/js/dashboard.js
- Logo icon accessible: /static/img/logo.png (1236 bytes)
- Favicon accessible: /static/img/favicon.ico (3315 bytes)
- SocketIO connection established

---

## Test 1: Permission Request

**Objective:** Verify permission prompt appears and handles user actions correctly

**Steps:**
1. Clear browser localStorage: `localStorage.clear()` in DevTools console
2. Clear notification permission: Browser Settings → Site Settings → Notifications → Reset
3. Reload dashboard: http://localhost:5000/
4. **Expected:** Light blue notification prompt banner appears at top with:
   - Message: "Enable Browser Notifications"
   - Two buttons: "Enable" and "Maybe Later"

**Test 1.1: Enable Button**
1. Click "Enable" button
2. **Expected:** Browser permission dialog appears
3. Click "Allow" in browser dialog
4. **Expected:**
   - Prompt banner disappears
   - Success toast appears: "Browser notifications enabled! You'll receive posture alerts."
   - Console logs: "Notification permission result: granted"

**Test 1.2: Maybe Later Button**
1. Clear localStorage and reload
2. Click "Maybe Later" button
3. **Expected:**
   - Prompt banner disappears
   - Console logs: "Notification prompt dismissed"
   - localStorage entry created: `notificationPromptDismissed`
4. Reload page
5. **Expected:** Prompt does NOT reappear (7-day cooldown)

**Test 1.3: Permission Denied**
1. Clear localStorage and reset browser permission
2. Reload dashboard, click "Enable"
3. Click "Block" in browser permission dialog
4. **Expected:**
   - Prompt disappears
   - No error messages
   - Visual alerts still work (graceful degradation)

---

## Test 2: Notification on Alert

**Objective:** Verify browser notification appears when posture alert triggers

**Setup:**
1. Grant notification permission (Test 1.1)
2. Ensure good posture initially

**Steps:**
1. Sit in bad posture for 10 minutes
2. **Expected at 10 minutes:**
   - Browser notification appears with:
     - Title: "DeskPulse Posture Alert"
     - Body: "Bad posture detected for 10 minutes"
     - Icon: DeskPulse logo
     - Notification sound plays (if enabled)
   - Dashboard alert banner appears (warm yellow)
   - Console logs: "Alert triggered", "Browser notification sent"

**Test 2.1: Notification Auto-Close**
1. Wait 10 seconds after notification appears
2. **Expected:** Notification auto-closes

**Test 2.2: Notification Click-to-Focus**
1. Trigger alert, switch to different tab
2. Click notification
3. **Expected:**
   - Dashboard tab receives focus
   - Notification closes

---

## Test 3: Alert Cooldown (Story 3.1 Integration)

**Objective:** Verify tag replacement prevents notification spam

**Steps:**
1. Sit in bad posture for 10 minutes → first alert
2. Continue bad posture for 5 more minutes (15 min total) → second alert
3. **Expected:**
   - First notification at 10 minutes
   - Second notification at 15 minutes REPLACES first (only one visible)
   - Dashboard banner message updates
   - No duplicate notifications piling up

**Verification:**
- Check notification center: only ONE "DeskPulse Posture Alert" visible
- Console logs show "Alert triggered" multiple times

---

## Test 4: Permission Denied Fallback

**Objective:** Verify graceful degradation when notifications blocked

**Steps:**
1. Deny notification permission in browser
2. Trigger posture alert (10 minutes bad posture)
3. **Expected:**
   - NO browser notification appears
   - Dashboard alert banner STILL appears (warm yellow)
   - Console logs: "Notification permission not granted, using visual alert only"

---

## Test 5: Multi-Client Broadcast (NFR-SC1)

**Objective:** Verify alerts broadcast to all connected clients

**Setup:**
1. Open dashboard in 3 different browser windows:
   - Chrome: http://localhost:5000/
   - Firefox: http://localhost:5000/
   - Edge: http://localhost:5000/
2. Grant notification permission in all 3 browsers
3. Arrange windows side-by-side

**Steps:**
1. Trigger posture alert (10 minutes bad posture)
2. **Expected in ALL 3 browsers simultaneously:**
   - Browser notification appears
   - Dashboard alert banner appears
   - Console logs show "Alert triggered"

**Test 5.1: Independent State**
1. Dismiss banner in Chrome (click "I've corrected my posture")
2. **Expected:**
   - Chrome banner clears, toast appears
   - Firefox and Edge banners remain (independent state)

---

## Test 6: Cross-Browser Compatibility

**Browsers to Test:**
- Desktop: Chrome, Firefox, Edge
- Mobile (optional): Android Chrome, iOS Safari 16.4+

**Per Browser:**
1. Load dashboard
2. Grant notification permission
3. Trigger alert
4. Verify:
   - Permission prompt works
   - Notification appears correctly
   - Icon displays (logo.png)
   - Sound plays (if enabled)
   - Banner appears and dismisses

**Expected Results:**
- All desktop browsers: Full support
- Mobile browsers: May vary (iOS requires 16.4+, Android Chrome works)

---

## Test 7: HTTPS Detection

**Objective:** Verify HTTPS warning for non-localhost access

**Steps:**
1. Access dashboard via local IP: http://192.168.x.x:5000/
2. Open browser DevTools console
3. **Expected Console Warnings:**
   ```
   Browser notifications require HTTPS (except localhost). Current URL: http://192.168.x.x:5000/
   Notifications will gracefully degrade to visual alerts only.
   ```

**Test 7.1: Localhost Works Without HTTPS**
1. Access via http://localhost:5000/ or http://127.0.0.1:5000/
2. **Expected:** No HTTPS warnings, notifications work

**Test 7.2: .local Domain (mDNS)**
1. If configured, access via http://deskpulse.local:5000/
2. **Expected:** No HTTPS warnings (treated as localhost)

---

## Test 8: localStorage Preferences

**Objective:** Verify localStorage features work correctly

**Test 8.1: Notification Sound Preference**
1. Open console: `localStorage.setItem('notificationSound', 'false')`
2. Trigger alert
3. **Expected:** Notification appears but is SILENT

4. Reset: `localStorage.setItem('notificationSound', 'true')`
5. Trigger alert
6. **Expected:** Notification appears WITH sound

**Test 8.2: Prompt Dismissal Persistence**
1. Dismiss permission prompt ("Maybe Later")
2. Reload page multiple times
3. **Expected:** Prompt does NOT reappear for 7 days

4. Force reset: `localStorage.removeItem('notificationPromptDismissed')`
5. Reload
6. **Expected:** Prompt reappears

---

## Test 9: SocketIO Event Verification

**Objective:** Verify alert acknowledgment event emitted

**Steps:**
1. Open Network tab in DevTools, filter by "WS" (WebSocket)
2. Trigger alert
3. Click "I've corrected my posture" button
4. **Expected in WebSocket frames:**
   - Outgoing: `alert_acknowledged` event with timestamp
   - Console logs: "Alert acknowledged"
   - Banner clears
   - Success toast appears

---

## Test 10: Visual Alert Banner

**Objective:** Verify dashboard alert banner styling and behavior

**Steps:**
1. Trigger alert
2. **Expected Banner Appearance:**
   - Background: Warm yellow (#fffbeb)
   - Border: 2px solid amber (#f59e0b)
   - Icon: ⚠️ Posture Alert (dark amber text)
   - Message: "Bad posture detected for X minutes" (brown text)
   - Button: "I've corrected my posture" (secondary style)

**Test 10.1: Banner Persistence**
1. Alert banner appears
2. Navigate to different part of page
3. Reload page
4. **Expected:** Banner persists until dismissed

**Test 10.2: Banner Update**
1. First alert at 10 minutes
2. Second alert at 15 minutes
3. **Expected:**
   - Banner updates message to "15 minutes"
   - Does NOT create duplicate banner

---

## Known Limitations

1. **Mobile Safari:** Requires iOS 16.4+ for Web Notification API
2. **HTTPS Requirement:** Production deployment needs HTTPS (localhost exempted)
3. **Browser Focus:** Some browsers restrict window.focus() - expected behavior
4. **Notification Persistence:** Tag replacement may vary slightly by browser

---

## Debugging Tips

**If notifications don't appear:**
1. Check browser console for errors
2. Verify permission: `Notification.permission` should be "granted"
3. Check SocketIO connection: `socket.connected` should be true
4. Verify icon assets return 200 OK

**If banner doesn't appear:**
1. Check console for JavaScript errors
2. Verify SocketIO event received: Look for "Alert triggered" log
3. Inspect DOM for #dashboard-alert-banner element

**If permission prompt doesn't appear:**
1. Check localStorage: `localStorage.getItem('notificationPromptDismissed')`
2. Verify browser support: `'Notification' in window`
3. Check HTTPS context: `window.isSecureContext`

---

## Testing Completion Criteria

✅ All 10 test scenarios executed
✅ Cross-browser testing (minimum Chrome + Firefox)
✅ Permission states handled (default, granted, denied)
✅ SocketIO events verified
✅ Icons display correctly
✅ Graceful degradation confirmed
✅ No console errors in any browser

---

## Next Steps After Testing

1. Document any browser-specific issues found
2. Take screenshots of notifications and banners
3. Run `/bmad:bmm:workflows:code-review` for senior developer review
4. Mark story as "review" in sprint-status.yaml
