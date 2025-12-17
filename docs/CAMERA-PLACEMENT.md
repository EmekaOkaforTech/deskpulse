# Camera Placement Guide for DeskPulse

## Optimal Camera Positioning for Accurate Posture Detection

DeskPulse uses MediaPipe Pose to track your nose, shoulders, and hips. Proper camera placement is critical for accurate posture classification.

---

## Recommended Setup

### 📐 **Position: Directly in Front of User**
- **Best**: Camera centered on top of monitor, facing you directly
- **Alternative**: Slightly to the side of monitor (within 30° angle), still facing inward toward user
- **Avoid**: Extreme side angles (>45°) - shoulders and hips may not be visible

### 📏 **Height: Eye Level or Slightly Above**
- **Ideal**: Camera at eye level or 2-6 inches above eye level
- **Why**: Captures head, shoulders, torso, and hips in frame
- **Avoid**: Camera too low (below chest) or too high (above head by >12 inches)

### 📍 **Distance: 2-3 Feet (Arm's Length)**
- **Ideal**: 24-36 inches away from your face
- **Why**: Full upper body visible without cropping
- **Test**: Sit normally - you should see your head, shoulders, and hips in the camera view

### 🎯 **Angle: Perpendicular or Slight Downward Tilt**
- **Ideal**: Camera facing straight at you (0° tilt)
- **Acceptable**: Slight downward tilt (10-20°) if mounted above eye level
- **Avoid**: Extreme upward tilt (camera below desk pointing up)

---

## Visual Reference

```
                    [CAMERA]
                       |
                       | 2-3 feet
                       ↓
        ┌──────────────────────────┐
        │      MONITOR             │
        │                          │
        └──────────────────────────┘

         😊  ←  USER (You)
        ┌─┴─┐
        │   │  ← Shoulders visible
        └───┘
         / \   ← Hips visible
```

**Camera should capture:**
- ✅ Head (nose landmark)
- ✅ Shoulders (left & right)
- ✅ Torso
- ✅ Hips (left & right)

---

## Testing Your Setup

### Step 1: Check Camera View
1. Open dashboard: http://192.168.10.133:5000
2. Look at the video feed with skeleton overlay
3. Verify you can see:
   - Green/amber dots on your nose
   - Green/amber dots on both shoulders
   - Green/amber dots on both hips

### Step 2: Test Posture Detection
1. **Good Posture Test**:
   - Sit upright, shoulders back, head aligned over shoulders
   - Dashboard should show: ✓ Good Posture
   - Angles should be < 7°

2. **Bad Posture Test - Slouch**:
   - Round your shoulders forward, let head drop
   - Dashboard should show: ⚠ Bad Posture (nose-shoulder angle > 7°)

3. **Bad Posture Test - Forward Lean**:
   - Lean chest toward desk
   - Dashboard should show: ⚠ Bad Posture (shoulder-hip angle > 7°)

---

## Troubleshooting

### "No User Detected" - Even Though I'm There
**Problem**: Camera can't see key landmarks
**Solutions**:
- Move camera further back (increase distance to 3 feet)
- Adjust camera angle to capture full torso
- Check lighting - face and upper body should be well-lit
- Avoid backlighting (window behind you)

### "Always Shows Good Posture" - Even When Slouching
**Problem**: Camera angle not capturing posture changes
**Solutions**:
- Ensure camera is at eye level or above (not below chest)
- Move camera to front-center position (not extreme side angle)
- Check that hips are visible in frame (not cropped by desk)
- Adjust angle threshold in config if needed: `/home/dev/.config/deskpulse/config.ini`

### "Posture Flickers Between Good/Bad"
**Problem**: Borderline posture or unstable tracking
**Solutions**:
- Improve lighting (even, non-flickering light source)
- Reduce camera movement (stable mount)
- May need to adjust threshold sensitivity

---

## Configuration

### Adjust Sensitivity (Advanced)

Edit: `/home/dev/.config/deskpulse/config.ini`

```ini
[posture]
angle_threshold = 7  # Degrees from vertical (lower = stricter)
```

**Threshold Guidelines:**
- **5°**: Very strict - catches minor slouching (may be too sensitive)
- **7°**: Recommended - catches bad posture that causes discomfort
- **10°**: Moderate - only flags significant poor posture
- **15°**: Lenient - only extreme poor posture flagged

**Based on real-world testing:**
- 10-12° sustained slouch → causes backache over a workday
- **7° threshold recommended** to catch harmful posture early

---

## Ideal Desk Setup Examples

### Setup A: Monitor-Mounted Camera (Recommended)
```
┌─────────────────┐
│  [CAMERA]       │ ← Camera clipped to top of monitor
│                 │
│    MONITOR      │
│                 │
└─────────────────┘

      😊  ← You, 2-3 feet away
```
**Pros**: Perfect frontal view, eye-level height, stable mount
**Cons**: None

### Setup B: Tripod on Desk
```
    [CAMERA]
       |
       | ← Tripod ~6 inches tall
    ───┴───
    DESK

      😊  ← You, 2-3 feet behind camera
```
**Pros**: Adjustable height/angle, portable
**Cons**: Takes desk space, may get bumped

### Setup C: Side-Mounted (Acceptable)
```
MONITOR
  │
  │        [CAMERA] ← 20-30° angle from center
  │          /
  │        /
  │      /
  └────😊  ← You
```
**Pros**: Works if monitor top is unavailable
**Cons**: Slight reduction in accuracy, ensure both shoulders visible

---

## Camera Requirements

**Minimum Specs:**
- Resolution: 480p (640x480) or higher
- Frame rate: 5 FPS minimum (10 FPS recommended)
- Field of view: 60° or wider
- Connection: USB 2.0 or better

**Tested Cameras:**
- ✅ Logitech C930e (excellent)
- ✅ Most USB webcams work fine

---

## Privacy Note

🔒 **All processing is 100% local**
- Camera feed never leaves your Raspberry Pi
- No cloud uploads, no external connections
- Data stored locally only

---

## Need Help?

If posture detection isn't working accurately after following this guide:
1. Check logs: `journalctl -f -u deskpulse | grep "Posture classified"`
2. Verify angles shown: `shoulder-hip` and `nose-shoulder`
3. Adjust camera position incrementally
4. File issue: https://github.com/anthropics/deskpulse/issues

---

**Last Updated**: 2025-12-12
**Version**: Story 2.7 (Enhanced posture detection with nose-shoulder angle)
