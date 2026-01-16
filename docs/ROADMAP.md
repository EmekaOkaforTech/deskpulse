# DeskPulse Feature Roadmap

**Last Updated:** 2026-01-16
**Status:** Active Development

---

## Engagement & Retention Strategy

DeskPulse aims to transform posture monitoring from passive observation to active habit formation through thoughtful engagement features.

### Design Principles

1. **Encouragement over Criticism** - Celebrate wins, reframe challenges
2. **Progress Framing** - "Improved 6 points" not "32% bad posture"
3. **Non-Intrusive** - Helpful without being annoying
4. **Privacy-First** - All processing local, no cloud dependencies

---

## Feature Phases

### Phase 1: Smart Coach Messages (Open Source)

**Status:** In Development

Replace static "Good posture" / "Bad posture" messages with contextual, encouraging feedback.

#### Smart Coach Message Categories

**Good Posture Messages (Rotation):**
1. "Great posture! Keep it up."
2. "Looking good! Your back thanks you."
3. "Perfect form! You're building great habits."
4. "Excellent! This is how champions sit."
5. "Your posture is on point today!"

**Good Posture Streak Messages (after 5+ minutes):**
6. "5 minutes of great posture! You're on a roll."
7. "Consistency is key - you've got this!"
8. "Your posture streak is growing stronger."

**Bad Posture - Gentle Reminders:**
9. "Time for a quick posture check!"
10. "Let's straighten up - your spine will thank you."
11. "Small adjustment needed - sit tall!"
12. "Quick reset: shoulders back, chin level."

**Recovery Encouragement (after correcting):**
13. "Nice recovery! That's the spirit."
14. "Back on track - great adjustment!"
15. "Every correction builds better habits."

**Time-Based Messages:**
- Morning (6am-12pm): "Starting the day with good posture!"
- Afternoon (12pm-5pm): "Keeping strong through the afternoon!"
- Evening (5pm-9pm): "Finishing the day right!"

#### Implementation Details

- Messages rotate to avoid repetition (track last 3 shown)
- Good posture streaks tracked for milestone messages
- Integration with existing `posture-message` element
- No database changes required (client-side logic)

---

### Phase 2: Achievement System (Open Source)

**Status:** Planned

Milestone badges to celebrate progress and encourage consistency.

#### Achievement Categories

**Daily Achievements:**
- First Perfect Hour: 60 minutes of good posture
- Posture Champion: 80%+ daily score
- Consistency King: 4+ hours good posture

**Weekly Achievements:**
- Week Warrior: 7-day streak with 70%+ average
- Improvement Hero: 10+ point improvement from last week
- Perfect Week: 5 days with 80%+ scores

**Milestone Achievements:**
- Getting Started: Complete first full day
- Habit Builder: 7-day tracking streak
- Posture Pro: 30-day tracking streak
- Transformation: First time hitting 90% daily score

#### Storage

- Achievements stored in SQLite (`achievements` table)
- Fields: `id`, `type`, `earned_at`, `metadata`
- Display in dedicated "Achievements" dashboard section

---

### Phase 3: Goal Setting & Challenges (Open Source)

**Status:** Planned

Personalized goals to drive engagement.

#### Features

- Set daily posture score target (default: 70%)
- Visual progress bar toward daily goal
- Weekly challenge system:
  - "Improve by 5 points this week"
  - "Maintain 75%+ for 3 consecutive days"
  - "No bad posture alerts today"

---

### Phase 4: Analytics Insights (Premium)

**Status:** Future

Advanced analytics reserved for premium tier.

#### Premium Features

- **Extended History:** 30+ days (vs 7-day free)
- **Pattern Detection:** Identify problematic times/days
- **Correlation Analysis:** Link posture to calendar events
- **Custom Reports:** PDF export with insights
- **Multi-Device Sync:** Sync data across devices

---

## Open Source vs Premium Feature Matrix

| Feature | Open Source | Premium |
|---------|-------------|---------|
| Real-time Monitoring | ✅ | ✅ |
| Smart Coach Messages | ✅ | ✅ |
| Achievement Badges | ✅ | ✅ |
| Goal Setting | ✅ | ✅ |
| Weekly Challenges | ✅ | ✅ |
| 7-Day History | ✅ | ✅ |
| 30+ Day History | ❌ | ✅ |
| Pattern Detection | ❌ | ✅ |
| Custom Reports | ❌ | ✅ |
| Data Export (CSV) | ✅ | ✅ |
| Data Export (PDF) | ❌ | ✅ |
| Multi-Device Sync | ❌ | ✅ |
| Priority Support | ❌ | ✅ |

---

## Implementation Priority

### Current Sprint (Phase 1)

1. ~~Fix pause monitoring bug~~ ✅
2. ~~Fix CV Pipeline status display~~ ✅
3. ~~Fix System Status pause reflection~~ ✅
4. Remove redundant UI indicators
5. Implement Smart Coach messages (10-15)
6. Test and verify improvements

### Next Sprint (Phase 2)

1. Design achievement system schema
2. Implement achievement tracking
3. Create achievement display UI
4. Add achievement notifications

### Future Sprints

- Phase 3: Goal setting and challenges
- Phase 4: Premium analytics features
- Epic 5: Reliability improvements
- Epic 6: Community/CI infrastructure

---

## Technical Notes

### Smart Coach Message Implementation

```javascript
// Message selection algorithm (pseudo-code)
function selectCoachMessage(postureState, streakMinutes, timeOfDay) {
    if (postureState === 'good') {
        if (streakMinutes >= 5) {
            return pickStreakMessage(streakMinutes);
        }
        return pickRandomGoodMessage(lastShownMessages);
    } else {
        return pickRandomBadMessage(lastShownMessages);
    }
}
```

### Achievement Tracking

```sql
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON for flexible data
);
```

---

## Changelog

### 2026-01-16
- Created roadmap document
- Defined Phase 1-4 feature breakdown
- Documented Open Source vs Premium split
- Phase 1 implementation started
