# Distribution Checklist - Story 8.6

**Story**: 8.6 All-in-One Installer for Windows Standalone Edition
**Version**: 2.0.0
**Target Release Date**: ___________

---

## Phase 1: Pre-Build Verification

### Story Dependencies
- [ ] Story 8.5 status = "done" in sprint-status.yaml
- [ ] All Story 8.5 tests passing (38/38 unit + integration tests)
- [ ] Story 8.5 Windows validation complete (Windows 10 + Windows 11)
- [ ] Story 8.5 30-minute stability test passed (0 crashes)
- [ ] All Story 8.5 deliverables committed to git

### Code Quality
- [ ] No uncommitted changes in working directory
- [ ] All tests passing on development machine
- [ ] No TODO or FIXME comments in critical code paths
- [ ] No debug logging enabled in production code

### Build Prerequisites
- [ ] Python 3.9+ (64-bit) installed
- [ ] PyInstaller 6.0+ available
- [ ] Inno Setup 6 installed (for installer)
- [ ] All dependencies installed (requirements.txt + requirements-windows.txt)
- [ ] Icon file exists: `assets/windows/icon_professional.ico`
- [ ] Working directory is project root

---

## Phase 2: Build Executable

### Build Standalone Executable
- [ ] Run build script:
  ```powershell
  .\build\windows\build_standalone.ps1
  ```
- [ ] Build completes without errors
- [ ] Build log saved: `build/windows/build_standalone.log`
- [ ] Executable created: `dist/DeskPulse-Standalone/DeskPulse.exe`
- [ ] Distribution size verified: **___ MB** (expected: 200-300 MB)

### Build Verification
- [ ] Backend components bundled:
  - [ ] `dist/DeskPulse-Standalone/_internal/cv2/` exists
  - [ ] `dist/DeskPulse-Standalone/_internal/mediapipe/` exists
  - [ ] `dist/DeskPulse-Standalone/_internal/flask/` exists
  - [ ] `dist/DeskPulse-Standalone/_internal/numpy/` exists
- [ ] Icon bundled: `dist/DeskPulse-Standalone/assets/windows/icon_professional.ico`
- [ ] Epic 7 hook restored: `build/windows/hook-app.py` (no .epic7.bak suffix)

### Test Standalone Executable (Development Machine)
- [ ] Launch `dist/DeskPulse-Standalone/DeskPulse.exe`
- [ ] Application starts within 5 seconds
- [ ] Tray icon appears (teal - monitoring)
- [ ] No console window appears
- [ ] No ImportError or DLL errors
- [ ] Camera detection works
- [ ] All menu items functional
- [ ] Application quits cleanly

---

## Phase 3: Build Installer

### Build Windows Installer
- [ ] Run Inno Setup compiler:
  ```powershell
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
  ```
- [ ] Installer builds without errors
- [ ] Installer created: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
- [ ] Installer size verified: **___ MB** (expected: 150-250 MB)

### Calculate Checksums
- [ ] Calculate SHA256 checksum:
  ```powershell
  certutil -hashfile build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe SHA256
  ```
- [ ] SHA256: `________________________________________________________________`
- [ ] Save checksum to: `build/windows/Output/SHA256SUMS.txt`

---

## Phase 4: Testing - Windows 10

### Setup Windows 10 Test VM
- [ ] VM created: Windows 10 22H2 (Build 19045+)
- [ ] Clean state verified (no Python, no dev tools)
- [ ] Webcam configured (if VM supports USB passthrough)
- [ ] VM snapshot taken: "Clean-Windows10-PreInstaller"

### Transfer Installer to VM
- [ ] Installer copied to VM (method: _______________)
- [ ] SHA256 checksum verified on VM

### Run Validation Tests
- [ ] Run all tests from `validation-report-8-6-windows10-template.md`
- [ ] Complete validation report: `validation-report-8-6-windows10-YYYY-MM-DD.md`
- [ ] Validation result: [ ] PASS  [ ] FAIL

### Windows 10 Test Results
**Required Tests (ALL must PASS)**:
- [ ] Installation successful
- [ ] First launch successful (<5s startup)
- [ ] All functionality works (pause/resume, stats, settings, about, quit)
- [ ] Camera integration works (or graceful degradation if no camera)
- [ ] Performance within targets (<255 MB RAM, <35% CPU)
- [ ] 30-minute stability test passed (0 crashes)
- [ ] Auto-start works (after reboot)
- [ ] Uninstaller works (data preservation prompt)
- [ ] Backend components bundled (cv2, mediapipe, flask)

**Windows 10 Final Verdict**: [ ] APPROVED FOR RELEASE  [ ] REJECTED (fixes required)

---

## Phase 5: Testing - Windows 11

### Setup Windows 11 Test VM
- [ ] VM created: Windows 11 22H2 (Build 22621+)
- [ ] Clean state verified (no Python, no dev tools)
- [ ] Webcam configured (if VM supports USB passthrough)
- [ ] VM snapshot taken: "Clean-Windows11-PreInstaller"

### Transfer Installer to VM
- [ ] Installer copied to VM (method: _______________)
- [ ] SHA256 checksum verified on VM

### Run Validation Tests
- [ ] Run all tests from `validation-report-8-6-windows11-template.md`
- [ ] Complete validation report: `validation-report-8-6-windows11-YYYY-MM-DD.md`
- [ ] Validation result: [ ] PASS  [ ] FAIL

### Windows 11 Test Results
**Required Tests (ALL must PASS)**:
- [ ] Installation successful
- [ ] First launch successful (<5s startup)
- [ ] All functionality works
- [ ] Windows 11 specific features work (toast notifications in notification center, tray icon rendering)
- [ ] Camera integration works (or graceful degradation)
- [ ] Performance within targets
- [ ] 30-minute stability test passed (0 crashes)
- [ ] Auto-start works
- [ ] Uninstaller works
- [ ] Backend components bundled

**Windows 11 Final Verdict**: [ ] APPROVED FOR RELEASE  [ ] REJECTED (fixes required)

---

## Phase 6: Documentation

### Update Project Documentation
- [ ] Update README.md:
  - [ ] Add "Windows Standalone Edition" section
  - [ ] Document download link (placeholder for GitHub Release)
  - [ ] Document system requirements (Windows 10/11, webcam, no Python needed)
  - [ ] Explain differences from Pi edition (no Pi needed, uses PC webcam)
  - [ ] Add installation instructions with SmartScreen bypass

- [ ] Update CHANGELOG.md:
  - [ ] Add "v2.0.0 - Standalone Windows Edition" section
  - [ ] List all features (backend, CV pipeline, tray UI, notifications, auto-start)
  - [ ] List all Story 8.1-8.6 changes
  - [ ] Document installer size, performance expectations

### Build Documentation
- [ ] `build/windows/README_STANDALONE.md` exists and is comprehensive
- [ ] Build documentation tested (followed on clean machine)
- [ ] Troubleshooting section covers common issues

---

## Phase 7: GitHub Release Preparation

### Create Release Notes
**Release Title**: `DeskPulse v2.0.0 - Standalone Windows Edition`

**Release Notes** (use template from Story 8.6 AC8):
- [ ] Overview section written
- [ ] Download links section (placeholder for asset URLs)
- [ ] SHA256 checksum included
- [ ] "What's Included" section complete
- [ ] Installation instructions written
- [ ] System requirements documented
- [ ] SmartScreen bypass instructions detailed
- [ ] Support links included

### Prepare Release Assets
- [ ] Installer ready: `DeskPulse-Standalone-Setup-v2.0.0.exe`
- [ ] Checksum file ready: `SHA256SUMS.txt`
- [ ] Validation reports ready:
  - [ ] `validation-report-8-6-windows10-YYYY-MM-DD.md`
  - [ ] `validation-report-8-6-windows11-YYYY-MM-DD.md`
- [ ] Screenshots ready:
  - [ ] Tray icon (monitoring state)
  - [ ] Menu screenshot
  - [ ] About dialog
  - [ ] Toast notification
  - [ ] Windows 11 notification center

---

## Phase 8: GitHub Release (PRODUCTION)

### Create Git Tag
- [ ] Ensure all changes committed
- [ ] Create annotated tag:
  ```bash
  git tag -a v2.0.0-standalone -m "DeskPulse v2.0.0 - Standalone Windows Edition"
  ```
- [ ] Push tag to remote:
  ```bash
  git push origin v2.0.0-standalone
  ```

### Create GitHub Release
- [ ] Navigate to: https://github.com/EmekaOkaforTech/deskpulse/releases/new
- [ ] Tag: `v2.0.0-standalone`
- [ ] Release title: `DeskPulse v2.0.0 - Standalone Windows Edition`
- [ ] Release notes: (paste from Phase 7)
- [ ] Mark as: [ ] Pre-release  [x] Latest release
- [ ] Upload assets:
  - [ ] `DeskPulse-Standalone-Setup-v2.0.0.exe` (150-250 MB)
  - [ ] `SHA256SUMS.txt`
- [ ] Publish release

### Verify Release
- [ ] Release visible at: https://github.com/EmekaOkaforTech/deskpulse/releases
- [ ] Download link works
- [ ] SHA256 checksum visible in release notes
- [ ] Assets downloadable

---

## Phase 9: Download Verification

### Test Download from GitHub Release
- [ ] Download installer from GitHub Release on clean Windows 10 VM
- [ ] Verify SHA256 checksum matches published checksum
- [ ] Run installer from GitHub download
- [ ] Verify SmartScreen bypass instructions work ("More info" → "Run anyway")
- [ ] Application installs and runs successfully
- [ ] All functionality works

### Test Download from GitHub Release (Windows 11)
- [ ] Download installer from GitHub Release on clean Windows 11 VM
- [ ] Verify SHA256 checksum matches
- [ ] Run installer from GitHub download
- [ ] Verify SmartScreen bypass instructions work
- [ ] Application installs and runs successfully
- [ ] All functionality works

---

## Phase 10: Post-Release

### Update Story Status
- [ ] Mark Story 8.6 as "done" in `sprint-status.yaml`
- [ ] Update story file with completion notes
- [ ] Update Dev Agent Record with final summary

### Git Commit
- [ ] Commit all story updates:
  ```bash
  git add .
  git commit -m "Story 8.6: DONE - All-in-one installer complete

  - PyInstaller spec: build/windows/standalone.spec
  - Build script: build/windows/build_standalone.ps1
  - Inno Setup: build/windows/installer_standalone.iss
  - Documentation: build/windows/README_STANDALONE.md
  - Installer: DeskPulse-Standalone-Setup-v2.0.0.exe (XXX MB)
  - Tested: Windows 10 + Windows 11 VMs (clean installs)
  - Performance: Startup <5s, Memory <255 MB, 0 crashes
  - Distribution: GitHub Release v2.0.0-standalone

  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
  ```
- [ ] Push to remote: `git push origin master`

### Notifications
- [ ] Announce release (if applicable): Discord, Twitter, etc.
- [ ] Update project homepage (if applicable)
- [ ] Notify stakeholders

---

## Phase 11: Monitoring (First 48 Hours)

### Issue Tracking
- [ ] Monitor GitHub Issues for installer problems
- [ ] Monitor GitHub Discussions for user questions
- [ ] Check for common installation errors

### Known Issues Log
**Issues Reported**:
1.
2.
3.

**Action Items**:
- [ ] Create hotfix if critical issue found
- [ ] Update release notes with known issues
- [ ] Document workarounds

---

## Final Sign-Off

### Distribution Completion
- [ ] All builds successful
- [ ] All tests passed (Windows 10 + Windows 11)
- [ ] GitHub Release published
- [ ] Download verification complete
- [ ] Story marked "done"
- [ ] Git commits pushed

### Performance Validation Summary
| Metric | Target | Windows 10 | Windows 11 | Status |
|--------|--------|------------|------------|--------|
| Installer Size | 150-250 MB | ___ MB | ___ MB | [ ] PASS  [ ] FAIL |
| Startup Time | <5s | ___ s | ___ s | [ ] PASS  [ ] FAIL |
| Memory (30 min) | <255 MB | ___ MB | ___ MB | [ ] PASS  [ ] FAIL |
| CPU (avg) | <35% | ___% | ___% | [ ] PASS  [ ] FAIL |
| Crashes (30 min) | 0 | ___ | ___ | [ ] PASS  [ ] FAIL |

**Overall Distribution Status**: [ ] SUCCESS  [ ] PARTIAL (issues found)  [ ] FAILED

---

**Completed By**: _______________
**Date**: YYYY-MM-DD
**Signature**: _______________
