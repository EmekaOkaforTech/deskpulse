# DeskPulse Open Source & Commercial Strategy

**Document Version:** 1.0
**Date:** 2026-01-06
**Status:** Active Plan

---

## Executive Summary

DeskPulse will be split into two editions:
1. **Open Source Edition** (Free) - Raspberry Pi DIY version for makers
2. **Professional Edition** (Paid) - Standalone Windows app for end users

This strategy builds open source credibility while funding ongoing development through commercial sales.

---

## 1. PRODUCT EDITIONS

### Open Source Edition (FREE)
**Target Audience:** Developers, makers, privacy advocates, DIY enthusiasts

**What's Included:**
- Epic 1: Foundation & Installation
- Epic 2: Real-Time Posture Monitoring
- Epic 3: Alert & Notification System (Pi desktop)
- Epic 4: Progress Tracking (7-day history)
- Epic 5: System Reliability
- Epic 6: Community & Contribution Infrastructure

**Hardware Requirements:**
- Raspberry Pi 4 (2GB+ RAM)
- USB/CSI Camera
- MicroSD Card (16GB+)
- Power supply

**User Experience:**
1. Flash SD card with installer
2. Connect camera to Pi
3. Access web dashboard from any device
4. Get notifications on Pi desktop (libnotify)
5. View 7-day posture history

**Value Proposition:** "Complete DIY posture monitoring - own your data, zero cloud"

**Repository:** GitHub (public) - `github.com/[username]/deskpulse`

**License:** MIT or GPL-3.0 (TBD)

---

### Professional Edition (PAID)
**Target Audience:** Office workers, professionals, non-technical users

**What's Included:**
- ALL Open Source features PLUS:
- Epic 7: Windows Desktop Client (current - requires Pi)
- Epic 8: Standalone Windows Edition (NEW - no Pi needed)
  - Runs entirely on Windows PC
  - Uses PC webcam
  - System tray integration
  - Toast notifications
  - One-click installer
  - No browser tabs needed
- Epic 9: Premium Analytics (NEW)
  - 30+ day history (vs 7-day free)
  - Pain tracking
  - Pattern detection
  - Export reports (CSV/PDF)
  - Trend graphs

**Hardware Requirements:**
- Windows 10/11 PC
- Built-in or USB webcam
- NO Raspberry Pi needed

**User Experience:**
1. Download DeskPulse-Pro-Setup.exe
2. Double-click installer
3. Grant webcam permission
4. Teal icon appears in system tray
5. Done - monitoring starts automatically

**Value Proposition:** "Professional posture monitoring without the DIY hassle"

**Pricing:**
- $29 one-time purchase OR
- $5/month subscription
- 14-day free trial (full features)

**Distribution:** Direct download, Gumroad, or own store

**Repository:** Private Gitea (closed source)

---

## 2. WHY THIS SPLIT WORKS

### Open Source Builds Credibility
- **Gives back to community:** Backend is the "hard tech" - shows real skill
- **Enables auditing:** Privacy-focused users can verify no telemetry
- **Attracts contributors:** Developers can improve, learn, fork
- **Builds reputation:** "Made by someone who contributes, not just extracts"

### Paid Version Is Fair Value Exchange
- **Not restricting features:** Free version is complete and functional
- **Adding convenience:** Windows standalone = pure convenience layer
- **Time vs money trade:** DIY (free time) vs ready-made (pay money)
- **Funds development:** Pro sales enable continued improvement

### Successful Examples Using This Model
1. **Syncthing** (free P2P sync) vs **Resilio Sync** (paid, easier UX)
2. **Home Assistant** (free self-host) vs **Nabu Casa Cloud** (paid convenience)
3. **Plausible Analytics** (free self-host) vs **Plausible Cloud** (paid hosting)
4. **Bitwarden** (free self-host) vs **Bitwarden Premium** (paid features)

---

## 3. EPIC COVERAGE & GAPS

### Current Epic Status

✅ **Epic 1:** Foundation & Installation - Complete (Open Source)
✅ **Epic 2:** Real-Time Posture Monitoring - Complete (Open Source)
✅ **Epic 3:** Alert & Notification - Complete (Open Source)
✅ **Epic 4:** Progress Tracking - Complete (Open Source, 7-day limit)
⏳ **Epic 5:** System Reliability - Planned (Open Source)
⏳ **Epic 6:** Community Infrastructure - Planned (Open Source)
✅ **Epic 7:** Windows Desktop Client - Complete (Pro - requires Pi)

### Critical Gap Identified

**Epic 7 Issue:** Windows client still requires Raspberry Pi backend
- User must buy Pi ($50-80)
- User must set up Pi (technical)
- User must configure network
- **This defeats "non-tech users" value proposition**

**Solution Required:** Epic 8 - Standalone Windows Edition

---

### Epic 8: Standalone Windows Edition (NEW - HIGH PRIORITY)

**Goal:** Full DeskPulse runs on Windows PC without Raspberry Pi

**User Value:** Non-technical users get complete posture monitoring with one installer

**Stories:**

**8.1: Windows Backend Port**
- Port Flask app to run on Windows
- Windows service instead of systemd
- Local file-based configuration
- Windows-compatible paths

**8.2: Windows Camera Capture**
- OpenCV with DirectShow backend (Windows cameras)
- Camera selection dialog (multiple webcams)
- Camera permission handling (Windows 10/11)
- Fallback to generic USB Video Class

**8.3: Local Windows Architecture**
- Remove SocketIO dependency (local IPC instead)
- Direct function calls (no network needed)
- SQLite database in %APPDATA%/DeskPulse
- Single-process architecture

**8.4: Unified System Tray App**
- Backend runs as background thread
- Tray manager in foreground thread
- Direct notification (no SocketIO)
- Embedded web server for dashboard (optional)

**8.5: All-in-One Installer**
- Single DeskPulse-Pro-Setup.exe
- Installs backend + client together
- Windows service registration
- Auto-start configuration
- Uninstaller included

**Dependencies:** Epic 7 (reuse tray UI code)

**Timeline:** 2-3 weeks (5 stories)

---

### Epic 9: Premium Analytics Features (NEW - FUTURE)

**Goal:** Advanced analytics that justify Pro pricing

**Stories:**

**9.1: Extended History (30+ days)**
- Remove 7-day limit for Pro users
- Efficient database queries for long ranges
- Monthly summary views

**9.2: Pain Tracking**
- User reports pain levels (1-10 scale)
- Correlate with posture data
- Pain trend graphs

**9.3: Pattern Detection**
- Time-of-day analysis (when you slouch most)
- Meeting day vs focus day patterns
- Correlation with calendar events (if integrated)

**9.4: Export & Reporting**
- CSV export (all data)
- PDF reports (weekly/monthly summaries)
- Charts and visualizations

**Dependencies:** Epic 8 (standalone Windows)

**Timeline:** 2-3 weeks (4 stories)

---

## 4. REPOSITORY STRATEGY

### Gitea (Private - Source of Truth)
**Location:** `192.168.10.126:Emeka/deskpulse.git`

**Contains:**
- ALL code (open source + pro features)
- Full development history
- All branches and tags
- Windows client code
- Build scripts
- Internal documentation

**Purpose:** Development repository, full version control

**Access:** Private (you only)

---

### GitHub (Public - Open Source Distribution)
**Location:** `github.com/[username]/deskpulse` (to be created)

**Contains:**
- Open Source Edition only (Epics 1-6)
- No Windows client code
- No Pro features
- Community-focused README
- CONTRIBUTING.md
- MIT/GPL-3.0 license

**Purpose:** Open source distribution, community contributions

**Access:** Public

**Branch Strategy:**
```
main              → Stable releases (v1.0.0, v1.1.0)
develop           → Active development
open-source-v1.0  → Clean branch (no Windows code)
```

---

## 5. YOUTUBE VIDEO STRATEGY

### Video 1: "I Built an Open Source Posture Monitor" (FIRST)
**Goal:** Build credibility, attract makers

**Target Audience:** Developers, makers, DIY enthusiasts

**Content:**
1. **Problem:** Bad posture from desk work (0:00-1:00)
2. **Solution Overview:** Raspberry Pi + camera + MediaPipe (1:00-2:00)
3. **Setup Walkthrough:** Installing, connecting camera (2:00-5:00)
4. **Dashboard Demo:** Live monitoring, alerts working (5:00-7:00)
5. **Code Walkthrough:** Flask backend, OpenCV pipeline (7:00-9:00)
6. **Call to Action:** Star repo, contribute, build your own (9:00-10:00)

**Tone:** Educational, humble, maker-friendly

**Key Messages:**
- "All open source - link in description"
- "Your data stays local, zero cloud"
- "Built with standard tools - Flask, OpenCV, MediaPipe"

**Length:** 10-12 minutes

**Release:** Week 1 (establish credibility first)

---

### Video 2: "Why I Built a Windows Version" (FOLLOW-UP)
**Goal:** Introduce Pro version, explain value

**Target Audience:** Professionals, office workers

**Content:**
1. **Feedback:** "People loved the Pi version but wanted simpler setup" (0:00-1:00)
2. **Problem:** Pi setup too technical for non-makers (1:00-2:00)
3. **Solution:** Standalone Windows app, no Pi needed (2:00-3:00)
4. **Demo:** One-click install, tray icon, notifications (3:00-6:00)
5. **Comparison:** Free vs Pro (clear table) (6:00-7:00)
6. **Transparency:** "Pi version stays free forever" (7:00-8:00)

**Tone:** Professional, transparent, value-focused

**Key Messages:**
- "Core tech is still open source"
- "Windows version = pure convenience"
- "Fair trade: your time vs $29"

**Length:** 8-10 minutes

**Release:** Week 3-4 (after open source video gains traction)

---

### Video 3: "30 Days of Posture Tracking - Real Results" (PROOF)
**Goal:** Show real value, build trust

**Target Audience:** Potential Pro customers

**Content:**
1. **Setup:** Started tracking 30 days ago (0:00-1:00)
2. **Data:** Week-by-week improvement charts (1:00-5:00)
3. **Insights:** When I slouch most, patterns (5:00-8:00)
4. **Honest Assessment:** "Took real effort, not magic" (8:00-10:00)
5. **Pro Features Demo:** Analytics, exports (10:00-12:00)
6. **Offer:** Try free version, upgrade if you want more (12:00-13:00)

**Tone:** Results-driven, honest, data-focused

**Key Messages:**
- "Real data from actual use"
- "Improvement is possible but requires awareness"
- "Analytics help you understand patterns"

**Length:** 12-15 minutes

**Release:** Week 6-8 (after Pro version is stable)

---

## 6. MESSAGING FRAMEWORK

### When Asked: "Why not all open source?"

**Response:**
"The core technology IS open source - you can build the full system yourself with a Raspberry Pi. The Windows standalone version is pure convenience for people who value their time more than $29. I'm funding ongoing development through Pro sales, which benefits both free and paid users. Your data stays local either way - zero cloud, zero telemetry."

---

### When Asked: "Why charge for Windows client?"

**Response:**
"The Windows version eliminates the need for a Raspberry Pi, which saves you $50-80 in hardware plus setup time. It's a fair value exchange: DIY (free + your time) vs ready-made (paid + instant). The Pi version will always remain free and fully functional."

---

### When Asked: "Will free version get updates?"

**Response:**
"Yes. Bug fixes, security updates, and core feature improvements go to both versions. Pro features (extended analytics, Windows standalone) fund development that benefits everyone. Open source means you can also contribute improvements yourself."

---

## 7. PRICING STRATEGY

### Price Points
**One-Time Purchase:** $29 (recommended)
**Monthly Subscription:** $5/month (ongoing support)

**Rationale:**
- $29 = Cost of 1-2 lunches (easy decision)
- One-time respects users (not subscription trap)
- Monthly option for users who prefer ongoing updates
- Below competitor pricing ($40-60 for posture apps)

### Trial Period
**14-day free trial** (full Pro features)
- Builds trust
- Users see value before paying
- Reduces refund requests

### Upgrade Path
**Free → Pro:**
1. User tries Pi version (free)
2. Loves it but wants simpler setup
3. Upgrades to Windows standalone ($29)
4. Data can be migrated (export/import)

---

## 8. COMPETITIVE POSITIONING

### vs Commercial Posture Apps ($40-60)
**DeskPulse Advantages:**
- Lower price ($29 vs $40-60)
- Open source core (trust, privacy)
- Local processing (no cloud)
- Customizable (open source)

### vs DIY Projects (free)
**DeskPulse Advantages:**
- Professional UX (not hobbyist)
- Actively maintained
- Documentation and support
- One-click installer (Pro)

### vs Enterprise Solutions ($100+/seat)
**DeskPulse Advantages:**
- One-time payment (not per-seat)
- Self-hosted (data privacy)
- No vendor lock-in
- Much lower cost

---

## 9. EXECUTION ROADMAP

### Phase 1: Open Source Release (Week 1-2)
- [ ] Create `open-source-v1.0` branch
- [ ] Remove Windows client code
- [ ] Remove Pro features (keep 7-day limit)
- [ ] Update README (open source focus)
- [ ] Add CONTRIBUTING.md
- [ ] Choose license (MIT recommended)
- [ ] Test full installation flow
- [ ] Create GitHub repository
- [ ] Push open source branch
- [ ] Tag v1.0.0 release
- [ ] Record Video 1 (open source intro)
- [ ] Publish to Reddit (r/raspberry_pi, r/selfhosted)

### Phase 2: Epic 8 Development (Week 3-5)
- [ ] Story 8.1: Port backend to Windows
- [ ] Story 8.2: Windows camera capture
- [ ] Story 8.3: Local architecture (no SocketIO)
- [ ] Story 8.4: Unified tray app
- [ ] Story 8.5: All-in-one installer
- [ ] Test on clean Windows 10/11 machines
- [ ] Create user documentation
- [ ] Record Video 2 (Windows Pro intro)

### Phase 3: Pro Launch (Week 6-7)
- [ ] Set up payment processing (Gumroad/Stripe)
- [ ] Create product page
- [ ] Write sales copy
- [ ] Design screenshots/demo GIF
- [ ] Beta test with 5-10 users
- [ ] Incorporate feedback
- [ ] Launch DeskPulse Pro
- [ ] Publish Video 2
- [ ] Monitor sales and feedback

### Phase 4: Epic 9 Analytics (Week 8-10)
- [ ] Story 9.1: Extended history
- [ ] Story 9.2: Pain tracking
- [ ] Story 9.3: Pattern detection
- [ ] Story 9.4: Export & reporting
- [ ] Record Video 3 (real results)
- [ ] Update Pro version (v1.1.0)
- [ ] Email existing customers (free upgrade)

---

## 10. SUCCESS METRICS

### Open Source Success
- ⭐ GitHub stars: 100+ in first month
- 🍴 Forks: 20+ in first quarter
- 💬 Issues/discussions: Active community
- 📝 Contributions: 3+ external contributors
- 📊 Clones/downloads: 500+ in first quarter

### Commercial Success
- 💰 Sales: 50+ units in first quarter ($1,450+ revenue)
- 🌟 Reviews: 4.5+ star average
- 🔄 Trial conversion: 20%+ trial to paid
- 📈 MRR: $100+ monthly recurring (subscriptions)
- 🗣️ Referrals: 10%+ from word-of-mouth

### Community Health
- 📖 Documentation quality: Clear, complete
- 🐛 Bug response time: <48 hours
- 🔧 Feature request engagement: Transparent roadmap
- 🤝 Contributor experience: Welcoming, helpful
- 📣 Brand sentiment: Positive (trustworthy, fair)

---

## 11. RISK MITIGATION

### Risk: "Free version is good enough, no one buys Pro"
**Mitigation:**
- Epic 8 provides clear value (no Pi needed = saves $50-80)
- Trial period lets users experience Pro features
- Target different audiences (makers vs professionals)

### Risk: "Open source community angry about paid version"
**Mitigation:**
- Be transparent from day 1
- Free version is complete and functional
- Not restricting existing features
- Fund development that benefits both
- Examples: Plausible, Bitwarden do this successfully

### Risk: "Someone forks and competes"
**Mitigation:**
- MIT license allows this (expected)
- Compete on UX, support, updates
- First-mover advantage
- Brand recognition ("DeskPulse")

### Risk: "Can't maintain both versions"
**Mitigation:**
- Shared codebase (backend is same)
- Pro features are additions, not forks
- Automate testing (CI/CD)
- Clear development workflow

---

## 12. LEGAL & LICENSING

### Open Source License
**Recommended:** MIT License

**Why MIT:**
- Most permissive (encourages adoption)
- Commercial-friendly (allows derivatives)
- Well-understood by community
- Used by Flask, OpenCV, MediaPipe

**Alternative:** GPL-3.0 (keeps derivatives open source)

### Pro License
**Proprietary EULA:**
- Single-user license (1 PC)
- No redistribution
- No reverse engineering
- Updates included for 1 year

### Trademark
**"DeskPulse":**
- Register trademark (optional, ~$300)
- Protects brand name
- Prevents confusion with forks

---

## 13. DOCUMENTATION REQUIREMENTS

### Open Source Documentation
- [ ] README.md (installation, features, screenshots)
- [ ] CONTRIBUTING.md (how to contribute)
- [ ] LICENSE (MIT/GPL-3.0)
- [ ] CHANGELOG.md (version history)
- [ ] docs/INSTALLATION.md (detailed setup)
- [ ] docs/ARCHITECTURE.md (technical overview)
- [ ] docs/API.md (for contributors)

### Pro Documentation
- [ ] User Guide (PDF + web)
- [ ] Quick Start Guide (1-page)
- [ ] FAQ (common questions)
- [ ] Troubleshooting Guide
- [ ] Privacy Policy
- [ ] Terms of Service
- [ ] Refund Policy

---

## 14. SUPPORT STRATEGY

### Open Source Support
- GitHub Issues (public)
- GitHub Discussions (community Q&A)
- Best-effort response (no SLA)
- Community-driven support

### Pro Support
- Email support (support@deskpulse.com)
- Response within 48 hours
- Priority bug fixes
- Feature request consideration

---

## APPENDIX A: EPIC DEPENDENCIES

```
Epic 1 (Foundation) ────┐
                        ├──> Epic 2 (Monitoring) ──┐
                        │                          ├──> Epic 3 (Alerts) ──┐
                        │                          │                       ├──> Epic 4 (Analytics)
                        │                          │                       │
                        └──────────────────────────┴───────────────────────┴──> Epic 5 (Reliability)
                                                                               │
                                                                               ├──> Epic 6 (Community)
                                                                               │
Epic 2 + Epic 3 + Epic 4 ──────────────────────────────────────────────────> Epic 7 (Windows Client - requires Pi)
                                                                               │
Epic 7 ────────────────────────────────────────────────────────────────────> Epic 8 (Windows Standalone - no Pi)
                                                                               │
Epic 8 ────────────────────────────────────────────────────────────────────> Epic 9 (Premium Analytics)
```

**Open Source:** Epics 1-6
**Pro (requires Pi):** Epic 7
**Pro (standalone):** Epic 8, 9

---

## APPENDIX B: COMPARISON TABLE

| Feature | Open Source (FREE) | Pro (PAID) |
|---------|-------------------|------------|
| **Platform** | Raspberry Pi | Windows 10/11 |
| **Hardware** | Pi 4 + Camera | PC + Webcam |
| **Setup Complexity** | Moderate (DIY) | Simple (1-click) |
| **Dashboard** | Web browser | Web + Tray |
| **Notifications** | Pi desktop only | Windows toast |
| **History** | 7 days | 30+ days |
| **Analytics** | Basic | Advanced |
| **Export** | No | CSV/PDF |
| **Pain Tracking** | No | Yes |
| **Support** | Community | Email (48hr) |
| **Updates** | Yes | Yes (priority) |
| **Price** | FREE | $29 one-time |

---

**Document End**

This strategy document should be reviewed quarterly and updated based on:
- Community feedback
- Sales performance
- Competitive landscape
- Technology changes
