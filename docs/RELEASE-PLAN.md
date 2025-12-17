# DeskPulse Release Plan

## Open Source Release (v1.0) - Core Product

**License:** GPL v3
**Target Date:** After Epic 3 Retrospective
**Scope:** Epics 1-3 + Stories 4.1-4.3

### Features Included

**Epic 1: Foundation (Stories 1.1-1.7)**
- Flask application architecture
- SQLite database with WAL mode
- Configuration management
- systemd service with auto-start
- Logging infrastructure
- One-line installer script
- Development setup documentation

**Epic 2: Real-Time Monitoring (Stories 2.1-2.7)**
- OpenCV camera capture
- MediaPipe pose detection
- Binary posture classification (good/bad)
- Multi-threaded CV pipeline
- Real-time dashboard with Pico CSS
- SocketIO live updates
- Camera state management and graceful degradation

**Epic 3: Alerts & Notifications (Stories 3.1-3.6)**
- Alert threshold tracking (10-minute bad posture trigger)
- Desktop notifications (libnotify)
- Browser notifications (SocketIO)
- Pause/resume monitoring controls
- Posture correction confirmation feedback
- Integration testing

**Epic 4: Today's Summary ONLY (Stories 4.1-4.3)**
- Story 4.1: Posture event database persistence
- Story 4.2: Daily statistics calculation engine
- Story 4.3: Dashboard "Today's Summary" display
  - Good posture time today
  - Bad posture time today
  - Today's posture score percentage

**Value Proposition:**
Fully functional real-time posture monitoring with alerts and daily accountability. Users can track their posture throughout the workday and get immediate feedback.

---

## Pro Release (v1.0) - Analytics & Advanced Features

**License:** Commercial (Proprietary)
**Target Date:** After Epic 4 Complete
**Scope:** Stories 4.4-4.6 + Epic 5+

### Features Included

**Epic 4: Historical Analytics (Stories 4.4-4.6)**
- Story 4.4: 7-day historical data table
- Story 4.5: Trend calculation and progress messaging
- Story 4.6: End-of-day summary report

**Epic 5: System Management (Stories 5.1-5.4)**
- GitHub release update checking
- Database backup before updates
- Update mechanism with rollback
- System health monitoring dashboard

**Future Pro Features (Epics 6+)**
- 30-day and all-time trend charts
- Goal setting and achievements
- Detailed posture quality scores (beyond binary)
- Data export (CSV/PDF)
- Custom alert schedules (work hours only)
- Multiple user profiles
- Advanced posture metrics (shoulder alignment, head tilt, etc.)

**Value Proposition:**
Behavior change through historical insights. Users see if they're improving over weeks/months, get actionable insights, and can track long-term posture health trends.

---

## Value Separation Strategy

**Open Source = Immediate Utility**
- "How am I doing RIGHT NOW?"
- Real-time monitoring + today's snapshot
- Basic accountability

**Pro = Behavior Change**
- "Am I IMPROVING over time?"
- Historical trends and pattern recognition
- Progress motivation and insights

---

## Technical Separation

**Shared Infrastructure:**
- Both use same database schema (designed for extensibility)
- Both use same CV pipeline and alert system
- Both use same Flask/SocketIO architecture

**Pro-Only Backend:**
- Stories 4.4-4.6 logic (historical calculations)
- Epic 5 update mechanisms
- Advanced analytics engines

**Pro-Only Frontend:**
- Historical data visualizations
- Trend charts and progress graphs
- Advanced dashboard sections

**Licensing Mechanism:**
- Feature flags in configuration
- Pro features disabled in open source build
- License key validation for Pro features (future)

---

## Repository Strategy

**Option A (Recommended): Monorepo with Feature Flags**
- Single repository: `anthropics/deskpulse`
- Pro features behind `if config.PRO_ENABLED:` flags
- Open source builds exclude Pro code via build script
- Simpler maintenance, shared infrastructure

**Option B: Separate Repositories**
- Open source: `anthropics/deskpulse`
- Pro: `anthropics/deskpulse-pro` (private)
- Pro extends open source as dependency
- More complex, potential sync issues

**Decision:** Option A - Use monorepo with feature flags for simplicity.

---

## Release Checklist

### Pre-Release (Open Source v1.0)
- [ ] Epic 3 Retrospective complete
- [ ] Implement Stories 4.1-4.3 (Today's Summary)
- [ ] Remove "Story 2.6+" misleading text from dashboard
- [ ] Create CONTRIBUTING.md
- [ ] Create comprehensive README.md
- [ ] Add LICENSE (GPL v3)
- [ ] GitHub issue templates
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Installation documentation
- [ ] Architecture documentation

### Release (Open Source v1.0)
- [ ] Tag release: `v1.0.0`
- [ ] GitHub release with installer script
- [ ] Announce on relevant communities
- [ ] Monitor initial issues and feedback

### Post-Release (Pro v1.0)
- [ ] Implement Stories 4.4-4.6
- [ ] Implement Epic 5
- [ ] Add Pro licensing mechanism
- [ ] Create Pro marketing site
- [ ] Set up payment processing
- [ ] Define Pro pricing model
