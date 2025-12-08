---
stepsCompleted: [1, 2, 3, 4, 6, 7, 8, 9, 10, 11]
inputDocuments: ['docs/analysis/product-brief-deskpulse-2025-12-04.md']
workflowType: 'prd'
lastStep: 11
status: 'complete'
completedDate: '2025-12-05'
project_name: 'deskpulse'
user_name: 'Boss'
date: '2025-12-05'
---

# Product Requirements Document - deskpulse

**Author:** Boss
**Date:** 2025-12-05

## Executive Summary

DeskPulse is a privacy-first AI productivity and wellness monitoring system that runs entirely on a Raspberry Pi, helping remote workers overcome the silent crisis destroying their health and productivity: working in chronic pain without realizing it. By providing real-time posture analysis and focus tracking through local edge computing, DeskPulse transforms workplace awareness, helping users work healthier, accomplish more, and reclaim hours of lost productivity - all without cloud surveillance or subscription fees.

**The Core Problem:**
77% of remote workers struggle with productivity, but the real problem isn't discipline or focus - it's that **working in pain makes everything harder.** Remote workers have normalized chronic discomfort: neck pain, back pain, constant fatigue, and afternoon crashes. Most don't realize they're spending 50%+ of their day in bad posture that drains energy, destroys focus, and creates a cycle of guilt and declining health.

**The Invisible Connections:**
- Afternoon energy crashes → poor posture cutting off circulation
- Difficulty focusing → physical discomfort stealing cognitive resources
- Weekend "decompression" need → body recovering from 5 days of workspace abuse
- Anxiety and stress → constant low-level physical tension from bad ergonomics

We think we have productivity problems. We think we have focus problems. But often, **we have workspace health problems that manifest as everything else.**

**The Solution:**
DeskPulse uses a USB webcam connected to a Raspberry Pi 4/5 to provide real-time AI monitoring of posture (MediaPipe Pose) and focus patterns (computer vision), with **ALL processing happening locally** on the device - zero cloud uploads, complete privacy. Users get gentle alerts when bad posture is detected, daily/weekly analytics showing improvement over time, and a web dashboard accessible from any device on their local network.

**Target Users:**
- **Primary:** Individual developers, freelance designers, and corporate remote employees who experience productivity loss and physical pain from poor workspace ergonomics
- **Secondary:** Content creators (amplification channel), students (future community), small business employers (B2B revenue), open source contributors (growth engine)

### What Makes This Special

**1. Privacy-First Architecture**
100% local processing, zero cloud dependencies, users own their data completely - proving you don't have to sacrifice privacy for productivity.

**2. Edge Computing Accessibility**
Runs on affordable Raspberry Pi ($80 hardware) - democratizing AI for students in rural India, startup founders in Kenya, retirees in rural America, freelancers everywhere. $100 one-time investment vs $240+/year subscriptions.

**3. Open Source Foundation**
Transparent, auditable, customizable, community-driven - users can verify, modify, and extend it forever.

**4. Production-Ready from Day One**
Not a prototype - enterprise-grade code, comprehensive documentation, YouTube tutorials, real usable product from launch.

**5. Ethical Technology Philosophy**
Built to empower users, not extract value - proves commercial success and user respect can coexist.

**Unfair Advantages:**
- **Timing:** Remote work is permanent, health crisis is escalating, privacy concerns are mainstream (2025/2026 perfect conditions)
- **Technical Proof:** Demonstrates edge AI democratization, challenges narrative that only Big Tech can do real AI
- **Open Source Strategy:** Community building creates moat competitors can't easily copy
- **Clear Upgrade Path:** Free open source builds trust, Pro version monetizes without exploitation

**Why This Matters Beyond Features:**
DeskPulse proves that **personal technology can empower rather than exploit.** It runs on YOUR hardware, keeps YOUR data local, serves YOUR needs, and you own it forever. When this succeeds - GitHub stars, success stories, viral tutorials, business deployments - it proves we can build commercial-grade products that respect users and still win.

## Project Classification

**Technical Type:** IoT/Embedded System with Web Dashboard
**Domain:** General (Consumer Wellness/Productivity)
**Complexity:** Medium

### Technical Architecture

**Hardware Platform:**
- Primary: Raspberry Pi 4/5 (Linux-based single-board computer, not Arduino/microcontroller)
- Full Raspberry Pi OS (Debian-based)
- USB peripherals: Webcam (Logitech C270 or similar), optional external storage
- No GPU acceleration - all CV processing runs on Pi's CPU (key architectural constraint)

**Software Stack:**
- **Backend:** Python 3.9+ (computer vision processing + web server)
- **CV Libraries:** MediaPipe Pose (posture detection), OpenCV (camera handling)
- **Web Server:** Flask (lightweight, suitable for edge deployment)
- **Frontend:** Static HTML/CSS/JavaScript (no React/Vue complexity - keeps it performant on Pi)
- **Database:** SQLite (embedded, no separate database server)
- **Deployment:** systemd service (auto-start on boot)

**Architecture Characteristics:**
- Single-device system (not distributed)
- Fully local processing (no cloud dependencies)
- Real-time inference only (no ML training on device)
- Web dashboard for monitoring (not primary control interface)
- Local network access only (http://raspberrypi.local:5000)

**Complexity Drivers:**
- **Medium complexity because:**
  - Real-time computer vision processing (not trivial) at 5-15 FPS target
  - Established libraries reduce ML complexity (MediaPipe, OpenCV)
  - Local-only architecture (no distributed systems complexity)
  - Inference only (no training pipeline)
  - Edge computing constraints drive optimization needs

**Regulatory Position:**
- Consumer wellness/productivity tool (no medical claims)
- Consumer electronics category (not medical device)
- No FDA/CE medical device classification required
- No HIPAA compliance needed (personal data stays local)

**Key Technical Constraint:**
All computer vision processing must run efficiently on Raspberry Pi's ARM CPU without GPU acceleration. This constraint drives critical architecture decisions around model selection, frame rate targets, and processing optimization.

## Success Criteria

### User Success

**The "It Works!" Moment (Day 3-4):**
Users experience the "aha moment" when they see measurable improvement without consciously trying harder. This happens when bad posture drops by **30%+ from baseline**.

**Example transformation:**
- Day 1-2 baseline: 4.2 hours bad posture (52% of work time)
- Day 3-4: 2.9 hours bad posture (36% of work time)
- Result: 16% improvement visible in dashboard → creates belief system works

**Why 30% threshold:** Small enough to achieve quickly (within 3-4 days), big enough to feel real and motivate continued use.

**Core User Outcomes:**

1. **Posture Improvement (Primary MVP Metric)**
   - **Target:** 50%+ of users show posture score increase of 15+ points within 2 weeks
   - **Example:** 48% good posture → 72% good posture (24-point improvement)
   - **Measurement:** Automated tracking via dashboard analytics
   - **Success signal:** User sees daily progress in dashboard

2. **Pain Reduction (Week 2 Feature - Validates Product Value)**
   - **Target:** Self-reported pain levels decrease significantly (e.g., 7/10 → 3/10)
   - **Measurement:** End-of-day optional prompt: "How's your neck/back? 1-10 scale"
   - **Interface:** Bottom of daily report: `Pain level today? [slider 1-10] [Skip]`
   - **Data:** Stored alongside posture data, displayed as line chart (pain trend + posture trend)
   - **Why optional:** Avoids annoyance, still validates subjective improvement matches objective data

3. **Productivity Recovery (Growth Feature - Month 2-3)**
   - **Target:** 2+ hours/week measurable increase in productive time
   - **Note:** Requires focus tracking (phone detection, gaze analysis) - not in MVP
   - **MVP substitute:** Track "present at desk" vs "away" via person detection only

4. **Retention (Health Metric)**
   - **Target:** 70%+ still using after Week 2
   - **Measurement:** Active usage defined as running 4+ days/week
   - **Rationale:** If users stop after initial novelty, product doesn't deliver lasting value

**Qualitative Success Indicators:**
- No 3 PM energy crash
- Not stiff/sore at end of day
- Can work evenings/weekends without "recovering" from work week
- Actually finishing planned task lists

**User Success = They use it daily, their posture metrics improve by Day 3-4, and they tell others.**

---

### Business Success

**The One Number That Matters: Active Users**

Everything cascades from people actually using DeskPulse consistently. Success hierarchy:

1. **Primary:** Active users (using 4+ days/week)
2. **Supporting:** Revenue (proves monetization works)
3. **Amplification:** GitHub stars, media mentions (proves market interest)
4. **Health:** Retention rates (proves lasting value)

---

#### 3-Month Success (Validation Phase)

**Primary Metric:**
- **200+ active users** running DeskPulse 4+ days/week

**Supporting Metrics:**

*Users:*
- 500+ total installs (GitHub clones + downloads)
- 10% conversion rate: 50 Pro sales @ $29 = **$1,450 revenue**

*Community:*
- 250+ GitHub stars
- 15+ contributors (PRs merged)
- 3+ YouTubers made tutorials (not created by us)

*Strategic:*
- Front page Hacker News (1x)
- Featured in Raspberry Pi blog/newsletter
- 5+ business inquiries for team licenses

**The Month 3 "Keep Going" Decision:**

Must achieve **2 of 3** to continue:
- ✅ **150+ active users** (proves product-market fit)
- ✅ **$1,000+ revenue** (proves monetization works)
- ✅ **1 viral moment** (HN frontpage OR major YouTuber review OR tech blog feature)

**Rationale:** Users = it works, Revenue = it's viable, Virality = it can scale. If only 1 of 3, evaluate whether to pivot, iterate, or pause.

**The gut check:** "Are real humans getting real value?" If yes → keep building. If no → something's fundamentally wrong.

---

#### 12-Month Success (Growth Phase)

**Primary Metric:**
- **2,000+ active users** running DeskPulse 4+ days/week

**Supporting Metrics:**

*Users:*
- 5,000+ total installs
- 15% conversion rate: 300 Pro sales = **$8,700 cumulative revenue**

*Revenue:*
- **$500/month MRR** (Pro subscriptions if implemented)
- 5 B2B team licenses @ $500 each = **$2,500**
- **Total first year revenue: ~$11,200**

*Community:*
- 2,000+ GitHub stars
- 50+ contributors
- 20+ tutorial videos created by others
- Active Discord/forum (200+ members)

*Strategic:*
- Speaking opportunity at tech conference
- Partnership with ergonomic hardware company
- Media coverage (TechCrunch, Ars Technica mentions)

**Signal:** "This is sustainable and growing organically."

---

### Technical Success

**MVP Technical Validation (Week 1 Internal Testing):**

1. **Reliability:**
   - System runs for 8+ hours without crashing
   - Auto-starts on boot via systemd service
   - Handles camera disconnection/reconnection gracefully

2. **Accuracy:**
   - Posture detection achieves **70%+ accuracy** (acceptable false positive rate)
   - MediaPipe Pose landmarks detected consistently when user in frame
   - Binary classification (good/bad posture) is actionable

3. **Performance:**
   - **5+ FPS maintained** on Raspberry Pi 4 (minimum acceptable)
   - **10+ FPS target** on Raspberry Pi 5 (optimal)
   - No memory leaks during extended operation
   - CPU usage sustainable for 8+ hour sessions

4. **User Experience:**
   - Alerts fire correctly after 10 minutes bad posture (not before, not much after)
   - Daily reports generate with correct calculations
   - Web dashboard loads on local network from multiple devices
   - Camera feed visible with pose overlay in real-time

**Week 2 Validation (Early Testers):**

1. **Installation Success:**
   - 10-20 early testers install and run successfully
   - Setup takes <30 minutes for technical users
   - Documentation sufficient for self-service setup

2. **Retention Signal:**
   - 70%+ still using after Day 3 (retention signal)
   - No critical bugs that prevent core functionality

3. **Value Confirmation:**
   - Users report seeing their posture scores improve
   - At least 3 users say "this is actually helping me"
   - Users understand the alerts and dashboard without support

**Go/No-Go Decision Point:**

**Proceed to Public Launch if:**
- ✅ MVP proves users can see the "aha moment" (Day 3-4 improvement visible)
- ✅ Technical feasibility confirmed (runs reliably on target hardware)
- ✅ Early testers recommend to others (organic advocacy)
- ✅ Core problem validated (users confirm it solves posture awareness issue)

**Pivot or Iterate if:**
- ❌ Users stop using after Day 2-3 (retention failure)
- ❌ Accuracy too low to be useful (<60% correct detection)
- ❌ Technical issues make it unreliable (crashes, performance problems)
- ❌ Users don't see improvement (metrics don't change)

---

### Measurable Outcomes

**The 4 Core Success Numbers (12 Months):**

1. **Retention:** 70%+ still using after Week 2
2. **Engagement:** Users check dashboard 5+ days/week
3. **Improvement:** 50%+ show posture score increase of 15+ points
4. **Advocacy:** 30%+ recommend to others (measured via traffic sources, referrals)

**Bottom Line:** Success = They use it daily, their metrics improve, they tell others.

---

## Product Scope

### MVP - Minimum Viable Product (Week 1)

**The Essential Core Loop:**
Camera sees user → System detects "Good posture" or "Bad posture" → After 10 min bad → Alert notification → End of day → Text report → Next day → Can compare progress

**Must-Have Features:**

1. **Posture Detection (MediaPipe Pose)**
   - Binary good/bad posture classification
   - Real-time processing at 5-10 FPS minimum
   - Visual overlay showing detected pose landmarks
   - Manual camera positioning (user adjusts until shoulders visible)

2. **Real-Time Alerts**
   - Notification when bad posture detected for 10+ consecutive minutes
   - Simple alert mechanism (desktop notification or web dashboard pop-up)
   - User awareness without being intrusive

3. **Daily Summary Reports**
   - Text-based report showing hours/percentages
   - Example: "Today: 5.2h good posture, 2.8h bad posture (65% good)"
   - Clear, actionable data without requiring visualization

4. **7-Day Historical Data**
   - SQLite database storing timestamps + posture state
   - Multi-day tracking to show improvement trends
   - Simple text table format showing daily progress

5. **Basic Web Dashboard**
   - Live camera feed with pose overlay
   - Current posture status (Good/Bad indicator)
   - Today's running totals
   - Accessible from any device on local network (http://raspberrypi.local:5000)

**Technical Foundation:**
- **Hardware:** Raspberry Pi 4/5 + USB webcam (Logitech C270 or similar)
- **Software:** Python 3.9+, MediaPipe Pose, Flask (web server), SQLite
- **Performance Target:** 5-8 FPS on Pi 4, 10-15 FPS on Pi 5
- **Code Estimate:** 300-500 lines for core functionality

**Launch Criteria:**
Can detect posture, alert when bad, show daily summary, track across multiple days. Ugly-but-working is acceptable for early testers.

---

### Growth Features (Week 2 - Month 3)

**Week 2 Enhancements (Polish for Public Launch):**
- **Pain Tracking:** End-of-day optional prompt (1-10 scale) with trend visualization
- Charts/graphs dashboard (visual analytics)
- Automated camera calibration wizard
- Improved UI/UX design
- Comprehensive documentation
- One-click setup scripts
- Professional GitHub README
- YouTube tutorial materials

**Month 2-3 Features:**
- **Break Reminders:** Smart break suggestions based on learned user patterns
- **Focus Session Tracking:** Monitor when user is actively working vs. distracted (requires phone detection, gaze analysis)
- **Phone Detection (YOLOv8):** Identify phone usage and distractions
- **Advanced Analytics:** Weekly trends, pattern analysis, personalized insights
- **Export Reports:** PDF/CSV generation

**Pricing Introduction:**
- **DeskPulse Pro:** $29 one-time purchase
- **Features:** 30+ day history, advanced analytics, export reports, priority email support
- **Note:** Subscription model ($4.99/month) deferred as "future consideration" - simpler one-time pricing for MVP launch

---

### Vision (12-24 Months)

**Pro Version Expansion (Months 4-9):**
- Multi-user support (family/team deployments)
- Cloud backup (optional, privacy-preserving)
- Mobile app connectivity
- Integrations (Notion, Todoist, Calendar)

**B2B/Enterprise (Months 10-18):**
- Team dashboard with aggregate analytics (privacy-preserving, no individual surveillance)
- Manager insights (wellness metrics, not individual tracking)
- Bulk deployment tools
- SSO integration
- Compliance reporting (wellness duty of care)
- **Team licenses:** $50-100/person annually

**Platform/Ecosystem (Months 18-24):**
- Plugin system for community extensions
- Hardware partnerships (ergonomic equipment integration)
- API for third-party integrations
- White-label licensing for corporate wellness providers
- Speaking circuit and consulting opportunities

**The Ultimate Vision:**
DeskPulse becomes the reference implementation for privacy-first, edge-computing productivity tools - the "Home Assistant" of personal workspace optimization. Proves commercial success and user respect can coexist, inspiring a new generation of empowering (not exploitative) personal technology.

## User Journeys

### Journey 1: Alex Chen - Recovering Lost Time

**Opening Scene: The 3 PM Wall**

Alex is a 32-year-old software developer who loves his remote job - until 3 PM hits. Every single day. Like clockwork, his neck starts throbbing, his focus evaporates, and he stares at his code without processing it. He's been "working" for 8 hours but only accomplished maybe 5 hours of real work. The guilt is crushing: "I'm home all day, why am I getting so little done?"

He's tried everything. Pomodoro timers that he ignores when in flow state. A $600 ergonomic chair he still slouches in. Standing desk he forgets to adjust. Fitness tracker break reminders he dismisses. Nothing sticks because nothing shows him *why* his afternoons crash.

**Discovery: A Different Kind of Solution**

Late one night on Hacker News, Alex sees a post: "Open-source posture monitoring on Raspberry Pi - zero cloud uploads." The title hooks him instantly - "privacy-first" and "Raspberry Pi" signal his values. He clicks through to GitHub, reads the README, watches a 5-minute demo video. The data dashboard catches his eye: "Bad posture: 52% of work time. Longest focus session: 23 minutes."

Wait. What if his afternoon crashes aren't a discipline problem? What if they're a *posture* problem?

He already has a Raspberry Pi 4 from a previous project. Orders a Logitech C270 webcam on Amazon for $25. Total risk: $25 + 30 minutes. Low enough to try immediately.

**Rising Action: The Uncomfortable Truth**

**Day 1 (Monday 9:00 AM):** Alex follows the YouTube tutorial. Camera calibration takes 5 minutes. System boots up, dashboard shows live feed with his skeleton overlay. Kinda cool.

**Day 1 (9:15 AM):** First alert: "You've been slouching for 8 minutes."

Alex's reaction: "Huh, I was? I didn't even notice."

Throughout the day, alerts feel annoying but... revealing. He's becoming aware of something he'd been completely blind to.

**Day 2 (Evening):** Alex opens his daily report:
```
Bad posture: 52% of work time (4.2 hours)
Good posture: 48% (3.8 hours)
Longest focus session: 23 minutes
```

He stares at the numbers. "I worked 8 hours but only focused for 23 minutes at a stretch?! And I was slouched for HALF my day?"

**The aha moment:** The data doesn't lie. He doesn't have a willpower problem. He has a workspace health problem.

**Day 3-4:** Something shifts. His body starts building new habits unconsciously. Posture score improves to 68%. Focus sessions increase to 48 minutes average. And then... no 3 PM crash. He works through the afternoon with actual energy.

**Climax: The Week That Changed Everything**

**Day 7 (Sunday evening):** Alex reviews his week stats:
- Posture: 48% → 72% good (24-point improvement)
- Focus sessions: 23min → 52min average
- Productivity gain: +2.1 hours/week

He does the math: "This tiny $25 camera gave me 2 hours of my life back per week. That's 100 hours per year. That's 2.5 work weeks of productivity I was just... losing."

**Resolution: From User to Evangelist**

**Week 2:** A colleague complains about back pain in the team Slack.

Alex doesn't just commiserate anymore. He shares a screenshot of his dashboard: "Look at my week. This changed everything. And it's open source - runs on a Pi, nothing goes to the cloud."

**Month 2:** Alex has:
- Starred the GitHub repo
- Submitted a PR for dark mode
- Recommended it to 5 developer friends (2 adopted it)
- Written a Hacker News review: "I was skeptical, but this actually works"

When his company asks "what tools do you need?", he requests $100 reimbursement for webcam setups for interested team members.

**The Success Feeling:** Less guilt about productivity. Less physical pain. More energy for evening activities instead of collapsing exhausted. And the pride of contributing to an open source project that genuinely improved his quality of life.

**Journey Requirements Revealed:**
- Real-time posture detection with visual feedback
- Non-intrusive alert system (awareness without annoyance)
- Daily/weekly analytics dashboard with clear metrics
- Historical tracking to show improvement over time
- GitHub-friendly documentation for technical users
- Open source contribution pathway

---

### Journey 2: Maya Rodriguez - Making Every Hour Count

**Opening Scene: The Billable Hours Trap**

Maya is a 28-year-old freelance UI/UX designer who loves creating beautiful interfaces but hates the reality of freelancing: her income depends directly on billable hours. Every hour she loses to poor focus or physical discomfort is $50-75 she doesn't earn.

The precision mouse work creates constant shoulder tension. By Thursday, she's in pain. By Friday evening, she collapses on the couch instead of going to her evening dance class. The weekend isn't for fun - it's for "recovering" from five days of workspace abuse.

And the phone distractions... she loses 45+ minutes daily scrolling between client projects. Each context switch costs her flow state. She tried putting her phone in another room, but then misses important client messages.

**Discovery: A Friend's Recommendation**

Maya's developer friend Alex won't stop talking about this posture monitoring thing he set up. "You should try it," he says. "It helped me recover like 2 hours a week."

Maya is skeptical. She's not a hardware person. Setting up a Raspberry Pi sounds intimidating. But Alex offers to help her get started, and the $29 Pro version looks more her speed than tinkering with open source code.

**Rising Action: The Setup**

**Day 0:** Alex helps Maya assemble the Pi and camera. Takes 20 minutes. The YouTube tutorial is clear enough that she could have done it herself (surprising).

**Week 1:** The alerts are eye-opening. "Bad posture detected" becomes her new reality check. She didn't realize how much she hunches over her mouse during detailed design work.

**Week 1 (End-of-week report):**
```
Bad posture: 48% of work time
Pain level average: 6.5/10
Billable hours: 28
```

Seeing the numbers is brutal. Almost half her day in bad posture. No wonder her shoulders hurt.

**Week 2:** Maya starts responding to the alerts. Sits up straight. Takes micro-breaks when prompted. Notices she's less sore at end of day.

**Week 2 (End-of-week report):**
```
Bad posture: 31% of work time
Pain level average: 4/10
Billable hours: 32
```

Wait. She worked the same amount of time but billed 4 more hours? By feeling better and staying focused longer?

**Climax: The ROI Moment**

**Month 1:** Maya's billable hours increase from 28/week average to 33/week average. That's 5 extra hours x $60/hour = **$300 extra per week**. $1,200/month.

The $29 she spent on DeskPulse Pro paid for itself in *two hours*.

But the real win isn't just money. It's energy. She goes to her evening dance class on Thursdays now. She doesn't collapse on weekends. She feels like she has a life outside of work.

**Resolution: Professional Confidence**

**Month 3:** A high-value corporate client comments: "You're the most organized designer we've worked with. Your energy and professionalism really stand out."

Maya smiles. It's not that she works harder. She works *healthier*. Less pain = better design quality. Better focus = faster iteration. More energy = better client communication.

She recommends DeskPulse to her designer friends in Slack communities. "Best $29 I've spent on my business."

**Journey Requirements Revealed:**
- Easy setup for less technical users
- Pain tracking integration (validates the value)
- Clear ROI metrics (billable hours correlation)
- Simple one-time payment option ($29 Pro)
- Professional-looking dashboard (client-facing confidence)
- Week-over-week improvement visibility

---

### Journey 3: Jordan Park - Surviving Meeting Marathons

**Opening Scene: Zoom Fatigue Reality**

Jordan is a 35-year-old Customer Success Manager at a SaaS company. Remote work sounded great until the reality hit: 6-7 hours of back-to-back Zoom meetings. Every. Single. Day.

No control over break times between calls. Manager expects constant availability. By 2 PM, Jordan's back hurts. By 4 PM, meeting performance has visibly declined - Jordan sees their own slouched posture in the Zoom preview window and feels unprofessional.

The worst part? No energy left for family time. Kids want to play after work, but Jordan just wants to lie down.

**Discovery: Employer Wellness Initiative**

Jordan's company sends out a wellness survey. One question: "What tools would help you work more comfortably from home?"

Jordan Googles "posture monitoring for remote work" and finds DeskPulse. The privacy-first angle matters - Jordan doesn't want employer surveillance. Local processing means IT doesn't see individual data.

Downloads the setup guide. Looks... complicated. But there's a one-click installer script.

**Rising Action: The Discreet Setup**

**Day 1:** Jordan follows the installer script. Surprisingly works. Positions camera below monitor (not visible during Zoom calls - important).

**Week 1:** Dashboard runs in background. Gentle vibration alerts (phone app connected) during meetings when posture gets bad. Discreet enough that clients don't notice.

**Week 1 (Report):**
```
Bad posture during meetings: 71%
Average posture quality: Poor
Alert response rate: 23% (ignores most alerts during calls)
```

The stats are damning. But also validating - Jordan's back pain ISN'T just in their head.

**Week 3:** Jordan starts actually responding to alerts. Adjusts sitting position during meetings. Takes 30-second stand breaks between calls when possible.

**Climax: The Manager Conversation**

**Month 2:** Jordan's weekly report shows clear improvement:
```
Bad posture during meetings: 42% (down from 71%)
Pain level: 4/10 (down from 7/10)
End-of-day energy: Improved
```

Jordan screenshots the data and sends it to their manager with a request: "I need 5-minute breaks between back-to-back meetings. The data shows it improves my performance and reduces pain."

Manager approves. Company even reimburses the setup cost as "ergonomic equipment."

**Resolution: Work-Life Balance Restored**

**Month 4:** Jordan has energy after work. Plays with kids. Takes evening walks. Weekends aren't just "recovery" anymore - they're actually for living.

The Zoom preview doesn't show a slouched, exhausted person anymore. Jordan looks present, professional, engaged.

**The success metric:** Family noticed. "You seem happier lately." That's the win.

**Journey Requirements Revealed:**
- Discreet monitoring (not visible during video calls)
- Mobile app for gentle notifications
- Simple one-click installation for low-tech users
- Data export for workplace accommodation requests
- Meeting-specific analytics
- Energy/wellness tracking beyond just posture

---

### Journey 4: Sam Taylor - The First-Time Setup Journey

**Opening Scene: The YouTube Discovery**

Sam is a 25-year-old junior developer who just saw a YouTuber review DeskPulse. The concept sounds amazing - posture monitoring on a Pi! - but Sam has never set up a Raspberry Pi project before.

The GitHub README says "easy setup" but... is it really?

**Discovery Phase:**

**Concern #1:** "Do I have the right hardware?"
- Checks compatibility list: Raspberry Pi 4 or 5, any USB webcam
- Orders from Amazon: Pi 4 starter kit ($79) + Logitech C270 ($25)
- **Requirement revealed:** Clear hardware compatibility documentation

**Concern #2:** "Will I mess this up?"
- Finds installation guide with screenshots
- Step 1: Flash SD card with Raspberry Pi OS
- Step 2: Run one-line installer script
- **Requirement revealed:** One-click automated installer

**Rising Action: The Setup Experience**

**Step 1 - SD Card Flash (15 min):**
Sam uses Raspberry Pi Imager. Works perfectly. Green checkmark feels good.

**Step 2 - First Boot (5 min):**
Pi boots up. Connects to WiFi. Terminal appears. So far so good.

**Step 3 - Installer Script (10 min):**
```bash
curl -fsSL https://deskpulse.io/install.sh | bash
```

Script runs. Shows progress bars. Installs dependencies. Downloads MediaPipe. Configures systemd service.

**Climax: The "It Works!" Moment**

**Camera Calibration:**
Browser opens to `http://raspberrypi.local:5000`
Live camera feed appears with skeleton overlay
Green text: "Good posture detected!"

Sam sits back. Slouches deliberately.
Red text: "Bad posture detected"

"IT WORKS!"

**Resolution: From Setup to Daily Use**

**30 minutes later:** Sam is running DeskPulse successfully. No Stack Overflow searches needed. No debugging. It just... worked.

**Next day:** System auto-started on boot (systemd service working). First daily report arrives. Sam is hooked.

**Week 2:** Sam writes a blog post: "Setting up DeskPulse was easier than setting up my dev environment"

**Journey Requirements Revealed:**
- Hardware compatibility checker
- One-line automated installer script
- Clear progress indicators during setup
- Visual confirmation that system is working
- Troubleshooting guide for common issues
- Auto-start configuration (systemd)
- Browser-based setup (no SSH required for basics)

---

### Journey 5: Casey Liu - The Open Source Contributor

**Opening Scene: The GitHub Star**

Casey is a 29-year-old Python developer who stars interesting repos on GitHub and occasionally contributes. DeskPulse caught Casey's attention because: (1) practical use case, (2) MediaPipe integration looks interesting, (3) clean code structure in the README examples.

Casey stars the repo thinking "I'll try this someday."

**Discovery: From User to Contributor**

**Week 1:** Casey actually sets it up. Runs it for a few days. Notices the dashboard UI is... functional but ugly. Thinks: "I could improve this."

**Rising Action: The First PR**

**Investigation Phase:**
- Reads CONTRIBUTING.md (clear guidelines exist)
- Checks open issues tagged `good-first-issue`
- Finds: "Issue #24: Dark mode for dashboard"

**Development Phase:**
- Clones repo
- Reads architecture docs (Flask + vanilla JS, no framework complexity)
- Implements dark mode toggle (CSS + localStorage)
- Tests locally on Pi

**Submission Phase:**
- Creates PR with screenshots
- Maintainer responds within 24 hours: "Thanks! Small suggestion on the toggle placement"
- Casey makes adjustment
- **PR merged 2 days later**

**The Rush:** Seeing "Merged" badge. Knowing their code is running on other people's Pis. That dopamine hit.

**Climax: Becoming a Regular Contributor**

**Month 2-3:** Casey has submitted 4 more PRs:
- Camera auto-calibration wizard
- CSV export feature
- Notification sound customization
- Bug fix for camera reconnection

**Month 4:** Maintainer adds Casey to the core contributor team. Access to private contributor Discord. Early feature discussions.

**Resolution: Open Source Ownership**

**Month 6:** Casey's contributions are cited in a TechCrunch article about DeskPulse. LinkedIn gets updated. Job interviews mention the open source work.

But the real win? Casey improved a tool they use daily. Fixed their own pain points. Built features they wanted. And learned MediaPipe + Flask + Raspberry Pi deployment in the process.

**The Success Feeling:** Ownership. Pride. Resume boost. And a tool that's genuinely better because of their contributions.

**Journey Requirements Revealed:**
- CONTRIBUTING.md with clear guidelines
- Good-first-issue tagging system
- Well-documented codebase architecture
- Fast maintainer response time
- Contributor recognition (changelog, credits)
- Active community space (Discord/forum)
- Development setup documentation
- CI/CD for automated testing

---

### Journey Requirements Summary

These five journeys reveal distinct capability areas DeskPulse needs:

**Core Product (Alex, Maya, Jordan):**
- Real-time posture detection with MediaPipe Pose
- Non-intrusive alert system (desktop notifications, mobile vibrations)
- Daily/weekly analytics dashboard with trend visualization
- Pain tracking integration (optional end-of-day prompts)
- Historical data storage (SQLite) with 7-day free, 30+ day Pro
- Meeting-specific analytics for corporate users
- ROI/productivity correlation metrics

**Onboarding & Setup (Sam):**
- One-line automated installer script
- Hardware compatibility checker/documentation
- Camera calibration wizard with visual feedback
- Auto-start systemd service configuration
- Browser-based setup dashboard
- Clear troubleshooting documentation
- Progress indicators during installation

**Community & Growth (Casey):**
- CONTRIBUTING.md and development setup docs
- Good-first-issue labeling system
- Clean, documented codebase architecture
- Fast PR review process
- Contributor recognition system
- Community communication channels
- CI/CD pipeline for quality assurance

**Cross-Cutting Requirements:**
- Privacy-first: 100% local processing, no cloud
- Platform: Raspberry Pi 4/5, Debian-based OS
- Performance: 5-15 FPS real-time processing
- Tech stack: Python, MediaPipe, Flask, SQLite
- Deployment: systemd auto-start service
- Access: Local network web dashboard

## Innovation & Novel Patterns

### Core Innovation Thesis

DeskPulse proves that **edge AI + privacy + accessibility can coexist without compromising on any dimension.**

Most solutions force users to "choose 2 of 3":
- Cloud AI tools: Power + Accessibility, but sacrifice Privacy
- Privacy-focused tools: Privacy + (limited) Power, but sacrifice Accessibility (expensive, complex)
- DIY solutions: Privacy + Accessibility, but sacrifice Power (prototype quality)

DeskPulse delivers **all three** simultaneously, challenging fundamental industry assumptions about AI wellness monitoring.

---

### Innovation Area 1: Privacy-First Actually Works (40% - Market Differentiation)

**The Challenge to Conventional Wisdom:**
Current industry assumption: "AI wellness monitoring requires cloud infrastructure for real-time processing and analytics."

**What DeskPulse Proves:**
Local processing on edge devices can match cloud capabilities in quality while providing superior privacy and lower cost.

**How It's Different:**
- **Current market state:** Every competitor (Upright, SitApp, etc.) requires cloud upload for posture analysis
- **DeskPulse approach:** 100% local processing with MediaPipe Pose - zero cloud dependencies
- **Result:** Same quality monitoring + complete data ownership + no subscription fees

**Why This Matters:**
Changes industry assumption that "AI monitoring requires surveillance." Proves you can have sophisticated AI analytics without sacrificing user privacy or control.

**Validation Approach:**
- **Week 1 MVP:** Demonstrate equivalent accuracy (70%+ posture detection) to cloud competitors
- **User testing:** Verify users achieve same improvement metrics (30%+ posture improvement by Day 3-4)
- **Market positioning:** Privacy-first becomes competitive advantage, not compromise

**Risk Mitigation:**
- **If local processing insufficient:** Can add optional cloud backup (user-controlled, privacy-preserving)
- **Fallback:** Architecture supports pluggable processing backends if needed
- **Reality check:** MediaPipe Pose already proven on mobile devices - Pi 4/5 has comparable compute

---

### Innovation Area 2: Edge AI on $80 Hardware (35% - Technical Achievement)

**The Challenge to Conventional Wisdom:**
Conventional belief: "You need GPU acceleration or cloud compute for real-time pose estimation at usable frame rates."

**What DeskPulse Proves:**
Optimized MediaPipe + efficient code architecture achieves production-grade computer vision (10+ FPS) on commodity ARM CPU hardware.

**Technical Innovation:**
- **Hardware:** Raspberry Pi 4/5 ARM CPU (no GPU acceleration, no dedicated accelerator)
- **Performance target:** 5-8 FPS on Pi 4, 10-15 FPS on Pi 5
- **Processing:** Real-time pose estimation (33 landmark points) + posture classification
- **Constraint:** All CV processing must run efficiently without external compute

**Why This Matters:**
Democratizes AI - anyone globally with a $80 Raspberry Pi can build sophisticated monitoring systems. Challenges narrative that "only Big Tech can do real AI."

**How We Validate:**
- **Week 1 internal testing:** Sustained 8+ hour operation without crashes
- **Performance benchmarks:** Maintain target FPS under real-world conditions
- **Accuracy validation:** 70%+ pose detection accuracy (acceptable for awareness tool)
- **Scalability test:** Multiple users confirm consistent performance on same hardware

**Risk Mitigation:**
- **If Pi 4 insufficient:** Focus on Pi 5 (2-3x faster) as minimum hardware
- **Performance optimization:** Frame skipping, resolution reduction, model quantization
- **Fallback:** Can recommend Pi 5 + optional USB Coral TPU for users needing higher FPS
- **Market validation:** MediaPipe already runs on less powerful mobile devices - Pi is viable platform

---

### Innovation Area 3: Ethical Open Source Business Model (25% - Philosophical Leadership)

**The Challenge to Conventional Wisdom:**
Open source business models typically force choice: Either "forever-free with no sustainability" or "freemium with artificially crippled free tier."

**What DeskPulse Proves:**
Free open source can be fully functional production software while Pro version monetizes through genuine value-add (not artificial limitations).

**Business Model Innovation:**
- **Open Source (Free):** Complete, production-ready product with core functionality
  - 7-day history, posture detection, alerts, basic dashboard
  - Not a prototype, not feature-limited, genuinely useful
- **Pro Version ($29 one-time):** Convenience + extras, not essential features
  - 30+ day history, advanced analytics, export reports
  - Pricing: One-time purchase, not exploitative subscription
- **Philosophy:** Respect users first, monetize second

**Why This Matters:**
Proves you can build sustainable business AND respect users. Commercial success and user empowerment can coexist. Challenges SaaS norm of "recurring revenue through vendor lock-in."

**Market Context:**
- **Typical SaaS:** $20-40/month subscriptions ($2,400-$4,800 over 10 years)
- **Typical Open Source:** Forever-free but unsustainable (maintainer burnout)
- **DeskPulse Model:** One-time $29 purchase for premium, sustainable through community + B2B

**Validation Approach:**
- **Month 3:** 10% conversion rate (50 Pro sales from 500 installs) proves willingness to pay
- **Month 12:** $10K+ revenue proves business viability
- **Community health:** 50+ contributors proves open source sustainability
- **User sentiment:** Reviews mention "finally, software that respects me"

**Risk Mitigation:**
- **If conversion too low:** Can add subscription option later ($4.99/month)
- **If revenue insufficient:** B2B team licenses ($50-100/person) provide recurring revenue
- **Fallback:** Can adjust pricing or feature gates based on market feedback
- **Core principle:** Never compromise free version - keep it genuinely useful

---

### Innovation Area 4: Wellness Without Guilt (Cultural Shift)

**The Psychological Innovation:**
Most productivity tools create anxiety through surveillance. DeskPulse creates awareness without monitoring.

**The Difference:**
- **Traditional monitoring:** "You're being tracked" → guilt, resistance, eventual abandonment
- **DeskPulse approach:** "You're learning about yourself" → curiosity, ownership, sustained use
- **Key insight:** Your data, your device, your improvement (not employer surveillance)

**Why This Matters:**
People WANT to improve but HATE being monitored. DeskPulse threads this needle by making wellness monitoring feel empowering rather than invasive.

**Design Implications:**
- Alerts are gentle nudges, not accusations
- Data stays local (never feels like "someone's watching")
- Users choose when/how to review analytics
- No external accountability pressure (unless user wants it)

**Validation:**
- **Retention metric:** 70%+ still using after Week 2 (proves it doesn't feel like surveillance)
- **User language:** Reviews say "helps me" not "watches me"
- **Emotional response:** Users share improvements with pride, not shame

---

### Market Context & Competitive Landscape

**Current Market State (2025):**

**Cloud-Based Competitors:**
- **Upright, SitApp, PosturePal:** All require cloud upload, $20-40/month subscriptions
- **Value prop:** Professional-grade monitoring with mobile apps
- **Weakness:** Privacy invasion, recurring costs, vendor lock-in
- **Market position:** Established but vulnerable to privacy backlash

**Hardware Solutions:**
- **Ergonomic chairs, standing desks:** Symptom treatment without awareness
- **Wearables (Upright GO, etc.):** Physical devices with cloud dependency, $100+ hardware + subscription
- **Weakness:** Don't create lasting behavior change, still require cloud

**DIY/Open Source:**
- **Scattered GitHub projects:** Prototypes, not production-ready
- **Weakness:** Poor documentation, inconsistent quality, no community support

**DeskPulse Positioning:**
Combines best of all three: Professional quality (like cloud competitors) + Privacy (like DIY) + Accessibility (like ergonomic tools)

**Market Timing (2025-2026):**
- ✅ Remote work is permanent (normalized post-pandemic)
- ✅ Privacy concerns are mainstream (post-Cambridge Analytica, GDPR era)
- ✅ Health crisis escalating (chronic pain in remote workers widely recognized)
- ✅ Raspberry Pi ecosystem mature (strong community, reliable supply chain)
- ✅ Edge AI proven viable (MediaPipe, TensorFlow Lite demonstrated on mobile)

**Unfair Advantages:**
1. **First-mover:** No other privacy-first, edge-computing posture monitor at production quality
2. **Technical moat:** Open source creates community moat (hard for competitors to copy network effects)
3. **Timing:** Perfect conditions for privacy-first, wellness-focused productivity tools
4. **Positioning:** Proves edge AI democratization (becomes reference implementation)

---

### Validation Strategy

**Technical Validation (Week 1-2):**
- ✅ MediaPipe Pose achieves 70%+ accuracy on Raspberry Pi
- ✅ Sustained 10+ FPS performance on Pi 5, 5+ FPS on Pi 4
- ✅ 8+ hour continuous operation without crashes
- ✅ Real-time alerts fire correctly within 10-second window

**Market Validation (Month 1-3):**
- ✅ 200+ active users proves problem-solution fit
- ✅ 70%+ Week 2 retention proves product stickiness
- ✅ 10% conversion to Pro proves monetization viability
- ✅ Hacker News frontpage proves developer community interest

**Innovation Validation (Month 3-12):**
- ✅ Users report equivalent results to cloud competitors (validates edge AI works)
- ✅ Privacy-first messaging resonates in reviews and testimonials
- ✅ Media coverage cites as "reference implementation for edge AI"
- ✅ Community contributions prove open source sustainability

**Success Metrics:**
- **Technical:** "It actually works" - reliable, accurate, performant
- **Market:** "People actually use it" - 2,000+ active users by Month 12
- **Business:** "It's actually sustainable" - $10K+ revenue proves viability
- **Cultural:** "It changed the conversation" - cited as proof ethical tech can win

---

### Risk Mitigation & Fallback Plans

**Technical Risks:**

1. **Risk:** Pi hardware insufficient for real-time processing
   - **Mitigation:** Focus on Pi 5 (faster), optimize code aggressively
   - **Fallback:** Support optional USB Coral TPU for users needing higher performance
   - **Likelihood:** Low - MediaPipe proven on less powerful mobile devices

2. **Risk:** Accuracy below usable threshold (<60%)
   - **Mitigation:** Calibration wizard, user-specific training, simplified binary classification
   - **Fallback:** Can add manual posture tagging to improve model over time
   - **Likelihood:** Low - MediaPipe Pose already 90%+ accurate on good data

**Market Risks:**

3. **Risk:** Users don't convert to Pro version (revenue insufficient)
   - **Mitigation:** B2B team licenses, optional subscription model, consulting/services
   - **Fallback:** Can adjust pricing, add features to Pro tier
   - **Likelihood:** Medium - mitigated by multiple revenue streams

4. **Risk:** Privacy-first doesn't resonate as differentiator
   - **Mitigation:** Emphasize other benefits (cost savings, ownership, community)
   - **Fallback:** Still competitive on price and open source alone
   - **Likelihood:** Low - privacy concerns growing, not shrinking

**Community Risks:**

5. **Risk:** Open source community doesn't form (no contributors)
   - **Mitigation:** Good documentation, good-first-issue tagging, active maintainer engagement
   - **Fallback:** Can succeed as solo-maintained project if product is valuable
   - **Likelihood:** Low - practical tools with real users attract contributors

## IoT/Embedded System Requirements

### Project-Type Overview

DeskPulse is an **IoT/Embedded edge computing system** built on Raspberry Pi hardware with a web-based dashboard interface. The architecture prioritizes local processing, privacy, and simplicity over distributed systems complexity.

**Core Characteristics:**
- **Single-device system:** All processing happens on one Raspberry Pi (not distributed)
- **Edge computing:** Real-time CV inference without cloud dependencies
- **Web dashboard:** Browser-based monitoring accessible via local network
- **Always-on service:** Designed for 24/7 desktop operation
- **Zero-cloud architecture:** No internet required for operation

---

### Hardware Specifications

**Supported Single-Board Computers:**
- **Raspberry Pi 4** (4GB or 8GB RAM models)
- **Raspberry Pi 5** (4GB or 8GB RAM models) - Recommended for optimal performance
- **Not supported:** Raspberry Pi 3 (insufficient RAM), Arduino/microcontrollers (require full OS)
- **Future consideration:** Orange Pi, NVIDIA Jetson (Month 6+ if community contributes ports)

**Rationale for Limited SBC Support:**
Testing burden and MediaPipe compatibility varies significantly across SBC platforms. Initial focus on Pi 4/5 ensures production quality.

**Storage Requirements:**
- **Minimum:** 16GB SD card (Class 10 or better)
- **Recommended:** 32GB SD card for headroom
- **Breakdown:**
  - Raspberry Pi OS: ~8GB
  - MediaPipe models: ~2GB
  - SQLite data: ~1GB/year of usage
  - System headroom: ~5GB

**Memory Requirements:**
- **Minimum:** 4GB RAM (baseline for MediaPipe + Flask + OS)
- **Recommended:** 8GB RAM for performance headroom and multi-user dashboard access
- **Not supported:** Pi 3 (1GB RAM) - insufficient for real-time CV processing

**Required Peripherals:**
- **USB Webcam:** Logitech C270 or compatible (720p minimum, 1080p supported)
- **Power Supply:** Official Raspberry Pi power supply (5V 3A minimum for stable operation)
- **Case:** Ventilation recommended (passive cooling sufficient, active not required)
- **Optional:** Heatsinks for Pi 4 (Pi 5 has improved thermal management)

**Performance Targets:**
- **Pi 4:** 5-8 FPS sustained CV processing
- **Pi 5:** 10-15 FPS sustained CV processing
- **Constraint:** No GPU acceleration - all processing on ARM CPU

---

### Connectivity & Network Architecture

**Network Requirements:**
- **WiFi:** 802.11n minimum (802.11ac/ax preferred for stability)
- **Ethernet:** Preferred for reliable, low-latency operation
- **Internet:** Not required - system operates entirely on local network
- **Bandwidth:** Minimal (dashboard only, no video streaming to cloud)

**Device Discovery:**
- **mDNS/Bonjour:** Auto-discovery via `deskpulse.local` hostname
- **Fallback:** Display IP address on Pi terminal/screen at boot
- **Static IP:** Optional manual configuration for advanced users
- **Network binding:** Bind Flask to local network only (not exposed to internet)

**Multi-Device Dashboard Access:**
- **Simultaneous viewers:** Unlimited devices can access dashboard concurrently
- **Live updates:** WebSocket connection for real-time posture status across all clients
- **Supported clients:** Any device with modern web browser (laptop, phone, tablet)

**Remote Access:**
- **MVP:** Out of scope (local network only)
- **Future:** Documentation for user-configured VPN/Tailscale/WireGuard tunnels
- **Philosophy:** No built-in remote access (maintains privacy-first architecture)

---

### Power & Operation

**Power Consumption:**
- **Typical operation:** 5-8W (Pi 5), 4-6W (Pi 4)
- **Peak load:** 10W during intensive CV processing
- **24/7 cost estimate:** ~$0.15/day (~$55/year at average US electricity rates)

**Power Management:**
- **Operation mode:** Designed for 24/7 always-on desktop use
- **Graceful shutdown:** Not implemented (assumes continuous power)
- **Power loss recovery:** Automatic restart on power restore via systemd service
- **Data integrity:** SQLite WAL (Write-Ahead Logging) mode for crash resistance

**Operation Modes:**
- **Primary:** 24/7 operation with systemd auto-start on boot
- **Manual control:** Supported via systemd commands (stop/start/restart service)
- **Battery operation:** Not supported (desktop-only use case, no power optimization needed)

---

### Security & Privacy Model

**Dashboard Authentication:**
- **MVP (Week 1):** No password protection (trusts local network security)
- **Week 2:** Optional basic HTTP authentication (username/password)
- **Rationale:** Home users prioritize ease of access over authentication barriers on trusted networks

**Transport Security:**
- **MVP:** HTTP only (sufficient for local network)
- **Optional:** Self-signed certificate instructions in documentation for privacy-conscious users
- **Future:** HTTPS with Let's Encrypt for users exposing via VPN

**Data Encryption:**
- **At-rest:** No database encryption in MVP (local device = physical security model)
- **Future:** Optional SQLite encryption for Pro users (performance trade-off acceptable for paying users)
- **In-transit:** Local network only - no external data transmission

**Network Security:**
- **Firewall:** Expose port 5000 only (Flask default)
- **Binding:** Local network interfaces only (not 0.0.0.0)
- **External exposure:** No UPnP/port forwarding (explicitly not supported)
- **Attack surface:** Minimal - no remote code execution vectors, no file uploads

**Camera Privacy:**
- **Software indicator:** Dashboard displays "Recording" status with visual indicator
- **Privacy mode:** Pause button stops CV processing while keeping service running
- **Physical privacy:** Users responsible for webcam shutter/cover (recommended in docs)
- **No remote access:** Camera feed never leaves local network

---

### Update & Maintenance Strategy

**Update Mechanism:**
- **MVP (Week 1):** Manual update via `git pull && ./update.sh` script
- **Month 2:** In-dashboard "Check for updates" button queries GitHub releases
- **Method:** Git-based updates (transparent, auditable, aligns with open source philosophy)
- **Never auto-update:** User always confirms before applying updates

**Version Checking:**
- **Notification:** Dashboard banner when new version available
- **Check frequency:** Daily GitHub Releases API query (non-intrusive)
- **User control:** Can disable update notifications in settings

**Update Safety:**
- **Pre-update backup:** Automatic SQLite database backup before update
- **Rollback:** Git revert instructions in documentation
- **Schema migrations:** Database migration scripts run automatically with user confirmation
- **Failure recovery:** Rollback instructions if update fails

**Version Strategy:**
- **Semantic versioning:** v1.x.x = compatible, v2.x.x = breaking changes
- **Migration guide:** CHANGELOG includes migration instructions for breaking changes
- **Database compatibility:** Forward-compatible where possible, migration scripts for breaking changes

**Release Cadence:**
- **Week 1-4:** Weekly releases (rapid MVP iteration and bug fixes)
- **Month 2-6:** Bi-weekly releases (stabilization phase)
- **Month 6+:** Monthly releases (maintenance and feature additions)

---

### Technical Architecture Considerations

**System Architecture:**
```
┌─────────────────────────────────────────────┐
│         Raspberry Pi 4/5 (Local Device)     │
│                                             │
│  ┌─────────────┐      ┌──────────────────┐ │
│  │ USB Webcam  │─────▶│  Python Backend  │ │
│  │ (CV Input)  │      │  - MediaPipe     │ │
│  └─────────────┘      │  - OpenCV        │ │
│                       │  - Flask Server   │ │
│                       │  - SQLite DB      │ │
│                       └────────┬─────────┘ │
│                                │           │
│                       ┌────────▼─────────┐ │
│                       │  Web Dashboard   │ │
│                       │  - HTML/CSS/JS   │ │
│                       │  - Local Network │ │
│                       └──────────────────┘ │
└─────────────────────────────────────────────┘
         │
         │ Port 5000 (HTTP)
         ▼
┌─────────────────────────┐
│   Local Network Devices │
│   - Laptop              │
│   - Phone               │
│   - Tablet              │
└─────────────────────────┘
```

**Processing Pipeline:**
1. **Capture:** USB webcam → OpenCV frame grab (5-15 FPS)
2. **Inference:** MediaPipe Pose estimation (33 landmarks)
3. **Classification:** Binary posture classification (good/bad)
4. **Storage:** SQLite write (timestamp + posture state)
5. **Alert logic:** Check duration thresholds (10+ min bad posture)
6. **Dashboard:** WebSocket push updates to connected clients

**Key Constraints:**
- **No GPU:** All CV processing on ARM CPU (drives model selection)
- **No cloud:** Can't offload compute or storage to external services
- **Single device:** Can't distribute load across multiple nodes
- **Local network:** Can't rely on internet connectivity for any feature

**Architectural Benefits:**
- **Simple deployment:** Single device, no orchestration needed
- **Reliable:** No network dependencies, no cloud outages
- **Private:** Data never leaves user's physical control
- **Cost-effective:** No cloud hosting or bandwidth costs

---

### IoT-Specific Non-Functional Requirements

**Reliability:**
- **Uptime target:** 99%+ for 24/7 operation (occasional restarts acceptable)
- **Crash recovery:** Systemd auto-restart on failure
- **Data durability:** SQLite WAL mode prevents corruption on ungraceful shutdown
- **Camera reconnection:** Graceful handling of USB disconnect/reconnect

**Performance:**
- **CV processing:** 5-15 FPS sustained (depends on Pi model)
- **Dashboard latency:** <100ms from posture change to UI update
- **Startup time:** <60 seconds from power-on to operational
- **Memory footprint:** <2GB RAM usage during normal operation

**Maintainability:**
- **Logging:** Structured logs via Python logging module
- **Debugging:** SSH access for troubleshooting (user-enabled)
- **Monitoring:** System stats available via dashboard (CPU, memory, disk)
- **Updates:** Git-based for transparency and rollback capability

**Scalability:**
- **Single-user focus:** Not designed for multi-user concurrent monitoring
- **Dashboard clients:** Scales to 10+ simultaneous viewers (WebSocket connections)
- **Data growth:** SQLite handles years of historical data (1GB/year)
- **Future scaling:** B2B version could aggregate multiple Pi devices (future consideration)

---

### Implementation Considerations

**Development Environment:**
- **Primary platform:** Develop and test on Raspberry Pi 4/5 hardware
- **Emulation:** QEMU for x86 testing (limited - not identical to ARM)
- **CI/CD:** GitHub Actions with ARM runners for automated testing
- **Version control:** Git + GitHub for source and releases

**Deployment:**
- **Installation:** One-line bash installer script (`curl | bash`)
- **Configuration:** Environment variables + config.yaml
- **Service management:** systemd unit file for auto-start
- **Logs:** Stored in `/var/log/deskpulse/` with rotation

**Testing Strategy:**
- **Unit tests:** Python CV logic, posture classification
- **Integration tests:** End-to-end on actual Pi hardware
- **Performance tests:** FPS benchmarks, memory profiling
- **Hardware compatibility:** Test matrix for Pi 4 vs Pi 5

**Documentation Requirements:**
- **Hardware setup:** SD card flashing, peripheral connection
- **Software installation:** Step-by-step with screenshots
- **Troubleshooting:** Common issues and solutions
- **Network configuration:** Static IP, mDNS, firewall rules

---

**Quick Reference: Technical Specifications**

| Requirement | MVP (Week 1) | Week 2+ | Future |
|------------|--------------|---------|---------|
| **Storage** | 16GB min | 32GB rec | - |
| **RAM** | 4GB min | 8GB rec | - |
| **Authentication** | None | Optional | Required (Pro) |
| **HTTPS** | No | Optional | Yes (VPN users) |
| **Updates** | Manual git | Dashboard button | Auto-check |
| **Remote Access** | No | No | VPN docs |
| **Multi-SBC** | Pi 4/5 only | Same | Community ports |
| **Power Mode** | 24/7 only | Same | Optional schedules |

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**Approach:** Problem-Solving MVP
Solve the core problem (posture awareness without surveillance) with minimal features that deliver the "aha moment" by Day 3-4.

**Strategic Rationale:**
- **Validation-first:** Prove edge AI works on Pi hardware before scaling features
- **Solo-maintainable:** Initial scope designed for single developer sustainability
- **Lean build:** Week 1-2 focused execution, no scope creep
- **Feedback-driven:** Critical Week 3-4 community feedback loop before growth features

**Resource Requirements:**
- **MVP (Week 1-2):** Solo developer (full-time)
- **Feedback Phase (Week 3-4):** Solo + 10-20 early testers
- **Growth (Month 2+):** Solo + community contributors
- **Vision (Month 6+):** Potential small team (if B2B scales)

---

### Development Phases & Timing

**Phase 1: MVP Build (Week 1-2)**

Focus: Prove the core value proposition works technically and delivers user value.

**Must-Have Capabilities:**
- Real-time posture detection (MediaPipe Pose on Pi CPU)
- Binary good/bad classification with visual feedback
- Alert system (10+ min bad posture threshold)
- Daily text summary reports
- 7-day historical tracking (SQLite)
- Basic web dashboard (live feed + current status)
- Systemd auto-start service

**Launch Criteria:**
- Runs 8+ hours without crashing
- 70%+ posture detection accuracy
- 5+ FPS sustained on Pi 4, 10+ FPS on Pi 5
- 10-20 early testers can install and run successfully

**Core User Journeys Supported:**
- Alex (Developer) - Primary: Sees productivity recovery through posture improvement
- Sam (Setup User) - Onboarding: Can install and get system running in <30 minutes

---

**Phase 1.5: CRITICAL FEEDBACK LOOP (Week 3-4)**

**⚠️ DO NOT SKIP THIS PHASE**

Focus: Listen, iterate, validate before building growth features.

**Activities:**
- Deploy to 10-20 early testers (technical users)
- Monitor retention: Are 70%+ still using after Day 3?
- Collect feedback: What's working? What's broken? What's missing?
- Measure "aha moment": Do users see 30%+ posture improvement by Day 3-4?
- Iterate on core loop: Fix critical bugs, refine UX based on real usage

**Success Criteria:**
- **Retention:** 70%+ early testers still using after Week 2
- **Value confirmation:** 3+ users say "this is actually helping me"
- **Technical validation:** MVP runs reliably, no showstopper bugs
- **Core problem validated:** Users confirm it solves posture awareness issue

**Go/No-Go Decision:**
- ✅ **Proceed to Growth** if retention + value confirmation achieved
- ⚠️ **Iterate MVP** if retention low or users don't see value
- ❌ **Pivot** if fundamental technical or problem-solution fit issues

---

**Phase 2: Growth Features (Month 2-3)**

Focus: Polish public launch, add value-enhancing features.

**Week 2 Enhancements (Public Launch Polish):**
- Pain tracking (end-of-day prompt with trend visualization)
- Charts/graphs dashboard (visual analytics)
- Automated camera calibration wizard
- Improved UI/UX design
- One-click setup scripts
- Professional GitHub README + YouTube tutorials

**Month 2-3 Features:**
- Break reminders (smart suggestions based on learned patterns)
- Focus session tracking (phone detection, gaze analysis)
- Advanced analytics (weekly trends, pattern analysis)
- Export reports (PDF/CSV)
- Pro version launch ($29 one-time)

**Additional User Journeys Supported:**
- Maya (Designer) - ROI tracking through billable hours correlation
- Jordan (Corporate) - Meeting-specific analytics and workplace accommodation data
- Casey (Contributor) - Open source community features (CONTRIBUTING.md, good-first-issue)

**Success Metrics:**
- 200+ active users by Month 3
- $1,450 revenue (50 Pro sales @ $29)
- 250+ GitHub stars, 15+ contributors
- 1 viral moment (HN frontpage OR major YouTuber)

---

**Phase 3: Vision Features (Month 4-6+)**

Focus: B2B expansion, integrations, ecosystem building.

**Pro Version Expansion:**
- Multi-user support (family/team deployments)
- Cloud backup (optional, privacy-preserving)
- Mobile app connectivity
- Integrations (Notion, Todoist, Calendar)

**B2B/Enterprise:**
- Team dashboard with aggregate analytics
- Manager insights (wellness metrics, not surveillance)
- Bulk deployment tools
- SSO integration
- Compliance reporting
- Team licenses: $50-100/person annually

**Platform/Ecosystem:**
- Plugin system for community extensions
- Hardware partnerships (ergonomic equipment)
- API for third-party integrations
- White-label licensing

**Success Metrics:**
- 2,000+ active users by Month 12
- $10K+ Year 1 revenue
- 2,000+ GitHub stars, 50+ contributors
- Self-sustaining community

---

### Risk Mitigation Strategy

**Technical Risks:**

1. **Risk:** Pi hardware insufficient for real-time CV processing
   - **Mitigation:** Test on actual Pi 4/5 hardware Week 1, optimize aggressively
   - **Contingency:** Focus on Pi 5 as minimum, optional USB Coral TPU for power users
   - **Likelihood:** Low (MediaPipe proven on less powerful mobile devices)

2. **Risk:** Accuracy below usable threshold (<60%)
   - **Mitigation:** Camera calibration wizard, binary classification (simpler than precise angles)
   - **Contingency:** Manual posture tagging to improve model
   - **Likelihood:** Low (MediaPipe Pose 90%+ accurate on good input)

**Market Risks:**

3. **Risk:** Users don't adopt (retention failure)
   - **Mitigation:** Week 3-4 feedback loop catches issues early
   - **Contingency:** Iterate on core value prop before adding features
   - **Validation:** Must hit 70%+ Week 2 retention before proceeding to Growth

4. **Risk:** Privacy-first doesn't resonate as differentiator
   - **Mitigation:** Emphasize cost savings ($25 vs $240+/year) and ownership
   - **Contingency:** Still competitive on price and open source alone
   - **Likelihood:** Low (privacy concerns growing, not shrinking)

**Resource Risks:**

5. **Risk:** Solo developer overwhelmed
   - **Mitigation:** Ruthlessly lean MVP scope, community contributions for Growth phase
   - **Contingency:** Extend timelines, focus on core stability over features
   - **Strategy:** Open source community becomes development multiplier

---

### Scope Boundaries & Non-Goals

**Explicitly Out of Scope (MVP):**
- ❌ Perfect 95%+ accuracy (70%+ sufficient for awareness tool)
- ❌ Automated everything (manual camera positioning acceptable)
- ❌ Enterprise features (single-user mode only)
- ❌ Payment processing (Pro version after validation)
- ❌ Cloud connectivity (defeats privacy-first mission)
- ❌ Multi-device pose tracking (single Pi = single user)

**Deferred to Post-MVP:**
- Phone detection (YOLOv8) - adds complexity, not core value
- Gaze analysis for focus tracking - needs more testing
- Machine learning personalization - wait for more data
- Integrations with productivity tools - after Pro launch
- B2B/team features - after individual version proven

**Never in Scope:**
- Cloud-based processing (architectural principle)
- User surveillance features (ethical boundary)
- Vendor lock-in mechanisms (open source commitment)
- Artificial feature limitations in free version (respect users)

---

### Resource Planning

**Week 1-2 (MVP Build):**
- **Development:** 80 hours (full-time)
- **Testing:** 20 hours (self + initial validation)
- **Documentation:** 10 hours (basic setup guides)
- **Total:** ~110 hours solo developer time

**Week 3-4 (Feedback Loop):**
- **User support:** 15 hours (helping early testers)
- **Bug fixes:** 25 hours (addressing critical issues)
- **Iteration:** 20 hours (UX refinements based on feedback)
- **Total:** ~60 hours + continuous monitoring

**Month 2-3 (Growth Features):**
- **Feature development:** 60 hours
- **Community management:** 20 hours (PRs, issues, Discord)
- **Content creation:** 30 hours (tutorials, blog posts, marketing)
- **Total:** ~110 hours + community contributions

**Strategic Leverage:**
- Open source community provides free QA, feature development, documentation
- Early adopters become evangelists and marketers
- YouTube tutorials create organic discovery channel
- GitHub stars signal credibility to later adopters

---

**Strategic Summary:**

DeskPulse uses a **validation-first, feedback-driven development approach** with three clear gates:

1. **Week 2:** Technical validation (does it work reliably?)
2. **Week 4:** Problem-solution fit (do users find value?)
3. **Month 3:** Business validation (will people pay?)

Each gate must pass before proceeding to next phase. This prevents overbuilding features users don't want and ensures sustainable, user-driven development.

**Critical Success Factor:** The Week 3-4 feedback loop. Skip this, and you risk building the wrong thing fast.

## Functional Requirements

**Purpose:** These functional requirements define the complete capability inventory for DeskPulse. Every feature, interaction, and system behavior traces back to one of these requirements. This is the binding contract between product vision and implementation.

**Format:** FR# - [Actor] can [capability] [context/constraint]

---

### Posture Monitoring

**FR1:** System can capture video frames from USB webcam at 5-15 FPS depending on hardware
**FR2:** System can detect human pose landmarks using MediaPipe Pose estimation
**FR3:** System can classify current posture as "good" or "bad" based on detected landmarks
**FR4:** System can display real-time pose overlay on camera feed showing detected body landmarks
**FR5:** System can distinguish between "user present at desk" and "user away"
**FR6:** System can detect when camera is disconnected or obstructed
**FR7:** System can operate continuously for 8+ hours without manual intervention

---

### Alert & Notification System

**FR8:** System can detect when user has maintained bad posture for configurable duration (default 10 minutes)
**FR9:** System can send desktop notifications when bad posture threshold exceeded
**FR10:** System can display visual alerts on web dashboard when bad posture detected
**FR11:** Users can pause posture monitoring temporarily (privacy mode)
**FR12:** Users can resume posture monitoring after pause
**FR13:** System can indicate active monitoring status (recording indicator)

---

### Analytics & Reporting

**FR14:** System can store posture state (good/bad) with timestamps in local database
**FR15:** System can calculate daily posture statistics (hours good, hours bad, percentage)
**FR16:** System can generate end-of-day text summary reports
**FR17:** System can display 7-day historical posture data
**FR18:** System can calculate posture improvement trends (baseline vs current)
**FR19:** Users can view weekly and monthly posture analytics (Growth feature)
**FR20:** Users can track pain levels via end-of-day optional prompts (Growth feature)
**FR21:** Users can correlate pain levels with posture trends (Growth feature)
**FR22:** System can identify patterns in posture behavior over time (Growth feature)
**FR23:** Users can export historical data as CSV or PDF reports (Growth feature)

---

### System Management

**FR24:** Users can install DeskPulse via one-line automated installer script
**FR25:** System can auto-start monitoring service on boot via systemd
**FR26:** Users can manually start, stop, or restart the monitoring service
**FR27:** System can check for software updates from GitHub releases
**FR28:** Users can update DeskPulse to latest version with confirmation
**FR29:** System can backup database before applying updates
**FR30:** System can rollback to previous version if update fails
**FR31:** Users can configure system settings (alert thresholds, notification preferences)
**FR32:** System can display current system status (CPU, memory, disk usage)
**FR33:** System can log operational events for troubleshooting
**FR34:** Users can calibrate camera position and angle (Growth feature)

---

### Dashboard & Visualization

**FR35:** Users can access web dashboard from any device on local network
**FR36:** System can auto-discover on local network via mDNS (deskpulse.local)
**FR37:** Dashboard can display live camera feed with pose overlay
**FR38:** Dashboard can show current posture status (good/bad indicator)
**FR39:** Dashboard can display today's running posture totals
**FR40:** Dashboard can show 7-day historical data table
**FR41:** Multiple users can view dashboard simultaneously without interference
**FR42:** Dashboard can receive real-time updates via WebSocket connection
**FR43:** Dashboard can display charts and graphs for visual analytics (Growth feature)
**FR44:** Dashboard can show break reminder suggestions (Growth feature)
**FR45:** Users can customize dashboard appearance and layout (Growth feature)

---

### Data Management

**FR46:** System can store all data locally in SQLite database (zero cloud uploads)
**FR47:** System can protect data integrity using SQLite WAL mode
**FR48:** System can manage database growth (auto-cleanup or archival)
**FR49:** Users can delete their historical data if desired
**FR50:** System can distinguish between free tier data (7-day) and Pro tier data (30+ day)
**FR51:** Pro users can access extended historical data beyond 7 days
**FR52:** Users can enable optional database encryption at rest (Pro feature)

---

### Community & Contribution

**FR53:** Contributors can access CONTRIBUTING.md with clear guidelines
**FR54:** Contributors can identify good-first-issues for initial contributions
**FR55:** Contributors can clone repository and run development setup
**FR56:** Contributors can submit pull requests with automated CI/CD testing
**FR57:** Users can report bugs and feature requests via GitHub issues
**FR58:** Users can access comprehensive documentation (setup, troubleshooting, API)
**FR59:** Users can view changelog for version history and migration guides
**FR60:** Community members can participate in Discord/forum discussions

---

**Validation Summary:**

**Completeness Check:**
- ✅ All MVP capabilities covered (FR1-FR46)
- ✅ All Growth features covered (FR19-FR23, FR34, FR43-FR45, FR52)
- ✅ All user journey requirements covered (Alex, Maya, Jordan, Sam, Casey)
- ✅ IoT/Embedded requirements covered (FR35-FR42, FR46-FR47)
- ✅ Community/open source requirements covered (FR53-FR60)

**Altitude Check:**
- ✅ All FRs state WHAT capability exists, not HOW to implement
- ✅ No UI specifics (e.g., "button" vs "users can")
- ✅ No performance numbers (those go in NFRs)
- ✅ No technology choices (e.g., "MediaPipe" as context, not prescription)

**Total:** 60 Functional Requirements organized across 7 capability areas

## Non-Functional Requirements

**Purpose:** These requirements define **HOW WELL** DeskPulse must perform. Each requirement is specific, measurable, and testable. We've only included categories that matter for this product - no requirement bloat.

---

### Performance

**NFR-P1: Real-Time Processing**
- **Requirement:** System maintains 5+ FPS sustained on Raspberry Pi 4, 10+ FPS on Raspberry Pi 5 during continuous operation
- **Rationale:** Below 5 FPS, posture detection becomes too laggy for real-time awareness
- **Measurement:** FPS counter logged every minute during 8-hour test session

**NFR-P2: Dashboard Responsiveness**
- **Requirement:** Dashboard UI updates reflect posture changes within 100ms
- **Rationale:** Real-time feedback loses effectiveness if delayed
- **Measurement:** Timestamp delta between posture state change and WebSocket UI update

**NFR-P3: Startup Time**
- **Requirement:** System becomes operational within 60 seconds of power-on
- **Rationale:** Users expect quick availability after boot
- **Measurement:** Time from systemd service start to first successful pose detection

**NFR-P4: Resource Efficiency**
- **Requirement:** System operates within 2GB RAM and <80% CPU usage during normal operation
- **Rationale:** Leave headroom for Pi OS and user activities
- **Measurement:** Continuous monitoring via system stats dashboard

---

### Reliability

**NFR-R1: Uptime Target**
- **Requirement:** System achieves 99%+ uptime during continuous 24/7 operation (occasional restarts acceptable)
- **Rationale:** Users expect always-on monitoring without manual babysitting
- **Measurement:** Uptime tracking over 30-day period

**NFR-R2: Crash Recovery**
- **Requirement:** System automatically restarts within 30 seconds of unexpected crash via systemd
- **Rationale:** Users shouldn't need to manually intervene for transient failures
- **Measurement:** Simulate crashes and verify automatic recovery

**NFR-R3: Data Durability**
- **Requirement:** SQLite database maintains integrity during ungraceful shutdowns (power loss)
- **Rationale:** Users lose trust if historical data corrupts
- **Measurement:** Forced power-off tests with database verification

**NFR-R4: Camera Reconnection**
- **Requirement:** System detects camera disconnect and reconnects within 10 seconds when available
- **Rationale:** USB devices occasionally disconnect, system should recover gracefully
- **Measurement:** Simulate USB disconnect/reconnect cycles

**NFR-R5: Extended Operation**
- **Requirement:** System operates continuously for 8+ hours without memory leaks or performance degradation
- **Rationale:** Users work 8+ hour days, system must remain stable
- **Measurement:** 12-hour stress test with performance monitoring

---

### Security & Privacy

**NFR-S1: Local Processing Only**
- **Requirement:** Zero network traffic to external servers during normal operation (100% local processing)
- **Rationale:** Privacy-first is core innovation - any cloud upload breaks trust
- **Measurement:** Network traffic analysis confirms no external connections

**NFR-S2: Local Network Binding**
- **Requirement:** Flask web server binds only to local network interfaces (not 0.0.0.0)
- **Rationale:** Prevent accidental exposure to internet
- **Measurement:** Port scan confirms no external accessibility

**NFR-S3: Data Locality**
- **Requirement:** All user data (video frames, pose data, analytics) stored locally on Pi storage only
- **Rationale:** Users own their data - no cloud backup in free version
- **Measurement:** File system audit confirms all data in local paths

**NFR-S4: Camera Privacy Indicator**
- **Requirement:** Dashboard displays clear "Recording" status when CV processing active
- **Rationale:** Users must know when camera is active
- **Measurement:** Visual verification of status indicator

**NFR-S5: Authentication (Growth Feature)**
- **Requirement:** Optional HTTP basic auth protects dashboard access when enabled
- **Rationale:** Users on shared networks may want access control
- **Measurement:** Test authentication bypass attempts

---

### Maintainability

**NFR-M1: Code Quality**
- **Requirement:** Python code follows PEP 8 style guidelines with <10 linting violations per 1000 lines
- **Rationale:** Open source requires readable, maintainable code for contributors
- **Measurement:** Automated linting in CI/CD pipeline

**NFR-M2: Test Coverage**
- **Requirement:** Core posture detection logic achieves 70%+ unit test coverage
- **Rationale:** Contributors need confidence their changes don't break functionality
- **Measurement:** Coverage reports in CI/CD

**NFR-M3: Documentation Currency**
- **Requirement:** All public APIs and key functions have docstrings following NumPy/Google style
- **Rationale:** Contributors and users need to understand codebase
- **Measurement:** Doc coverage tooling in CI/CD

**NFR-M4: Logging**
- **Requirement:** All system errors and warnings logged with structured format (timestamps, severity, context)
- **Rationale:** Users and contributors need to troubleshoot issues
- **Measurement:** Log format validation

**NFR-M5: Upgrade Path**
- **Requirement:** Database schema migrations preserve existing user data across version updates
- **Rationale:** Users shouldn't lose historical data when upgrading
- **Measurement:** Migration testing in staging environment

---

### Scalability (Limited Scope)

**NFR-SC1: Multi-Viewer Dashboard**
- **Requirement:** Web dashboard supports 10+ simultaneous WebSocket connections without performance degradation
- **Rationale:** Users may want to view dashboard from multiple devices concurrently
- **Measurement:** Load testing with concurrent clients

**NFR-SC2: Data Growth**
- **Requirement:** SQLite database handles 1+ year of posture data (365 days × 8 hours × 10 FPS) without query performance degradation >10%
- **Rationale:** Users expect historical data to remain accessible
- **Measurement:** Synthetic data generation and query benchmarking

**NFR-SC3: Future Hardware Support**
- **Requirement:** Codebase architecture allows adding new SBC platforms (Orange Pi, Jetson) with <20% code modification
- **Rationale:** Community may want to port to other hardware
- **Measurement:** Architecture review for hardware abstraction

---

### Usability (MVP Focus)

**NFR-U1: Installation Time**
- **Requirement:** Technical users complete installation in <30 minutes following documentation
- **Rationale:** Complex setup creates abandonment
- **Measurement:** Time 10 early testers from SD card flash to first pose detection

**NFR-U2: Self-Service Troubleshooting**
- **Requirement:** 80%+ of common issues resolvable via documentation without developer support
- **Rationale:** Solo maintainer can't provide 24/7 support
- **Measurement:** Track support requests in early testing phase

**NFR-U3: Feedback Loop**
- **Requirement:** Users see posture improvement (30%+ bad posture reduction) within 3-4 days of usage
- **Rationale:** Users abandon if no "aha moment" by Day 4
- **Measurement:** Track early tester posture metrics Week 1

---

**NFR Prioritization:**

**P0 (Must Have for MVP):**
- NFR-P1 (FPS performance)
- NFR-R1, R2, R5 (Reliability basics)
- NFR-S1, S3 (Privacy core)
- NFR-U1, U3 (Installation and value)

**P1 (Week 2):**
- NFR-P2, P3 (Dashboard responsiveness)
- NFR-R3, R4 (Data durability, recovery)
- NFR-M1, M4 (Code quality, logging)

**P2 (Month 2-3):**
- NFR-S5 (Authentication)
- NFR-M2, M3, M5 (Testing, docs, migrations)
- NFR-SC1, SC2 (Multi-viewer, data growth)

**Total:** 22 Non-Functional Requirements across 6 relevant categories
