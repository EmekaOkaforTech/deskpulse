# DeskPulse Roadmap

**Last Updated:** 2026-03-04

---

## Design Principles

These principles guide every feature decision in DeskPulse:

1. **Encouragement over Criticism** — Celebrate progress, reframe setbacks positively
2. **Progress Framing** — "Improved 6 points this week" not "32% bad posture"
3. **Non-Intrusive** — Helpful reminders without interrupting flow
4. **Privacy-First** — All processing is local; no data leaves your device

---

## Current Features

### Real-Time Posture Monitoring
Live camera feed with MediaPipe pose detection, posture classification, and
configurable alert thresholds. Desktop and browser notifications delivered
when bad posture persists beyond the threshold (default: 10 minutes).

### Smart Coach Messages ✅
Contextual, encouraging feedback based on posture state, streak duration,
and time of day — replacing static "Good / Bad" status labels.

### Achievement System ✅
Nine unlockable achievements across three categories:

- **Daily** — Reward consistent good posture within a single day
- **Weekly** — Recognise sustained consistency over a 7-day window
- **Milestone** — One-time awards for key habits formed

All achievements require meaningful monitoring time to earn, preventing
false awards from brief sessions.

### 7-Day Analytics
Daily posture score, good/bad duration, trend direction, and a full
7-day history table available on the dashboard.

### Pause / Resume Controls
One-click pause halts monitoring and alerts without stopping the app.
Duration statistics do not accumulate while paused.

### End-of-Day Summary
An automatic daily summary notification at 23:55 showing the day's
posture score and time breakdown.

---

## Planned Features

### Goal Setting
User-defined daily posture score targets with visual progress tracking.
Enables intentional improvement rather than passive monitoring.

**Status:** Planned — community contributions welcome

### Extended Analytics
Deeper insight into posture patterns: identify problematic times of day,
track improvement over longer periods, and export data in standard formats.

**Status:** Planned

---

## Contributing

The best way to influence the roadmap is to open a GitHub issue or discussion.
Features requested by the community and backed by clear use cases will be
prioritised.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and
contribution guidelines.
