/**
 * DeskPulse Dashboard JavaScript - Real-Time Updates
 *
 * Story 2.5: Static placeholder stubs
 * Story 2.6: SocketIO real-time updates ACTIVATED
 */

// Debug mode - controlled by URL parameter or localStorage
// Usage: Add ?debug=true to URL or run localStorage.setItem('debug', 'true') in console
const DEBUG = new URLSearchParams(window.location.search).get('debug') === 'true' ||
              localStorage.getItem('debug') === 'true';

if (DEBUG) {
    console.log('Debug mode enabled - verbose stats logging active');
}

// Initialize SocketIO connection on page load
let socket;

// Track monitoring state to prevent posture updates from overwriting paused UI
// Story 3.4: Prevents race condition where posture_update events (10 FPS)
// overwrite the "Monitoring Paused" UI immediately after pause
// Initialize to null until first monitoring_status received (prevents race condition)
let monitoringActive = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DeskPulse Dashboard loaded - initializing SocketIO...');

    // Initialize SocketIO client (connects to same host as page)
    socket = io();

    // Initialize network settings toggle
    initializeNetworkSettings();

    // Initialize browser notifications (Story 3.3)
    initBrowserNotifications();

    // Initialize pause/resume controls (Story 3.4)
    initPauseResumeControls();

    // Connection event handlers
    socket.on('connect', function() {
        if (DEBUG) console.log('SocketIO connected:', socket.id);
        updateConnectionStatus('connected');
    });

    socket.on('disconnect', function() {
        if (DEBUG) console.log('SocketIO disconnected');
        updateConnectionStatus('disconnected');

        // Show reconnection feedback (SocketIO auto-reconnects by default)
        setTimeout(function() {
            if (!socket.connected) {
                console.log('Attempting reconnection...');
                const statusText = document.getElementById('status-text');
                if (statusText) {
                    statusText.textContent = 'Reconnecting...';
                }
            }
        }, 3000);
    });

    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        updateConnectionStatus('error');
    });

    socket.on('status', function(data) {
        if (DEBUG) console.log('Server status:', data.message);
    });

    // CV update handler - CORE REAL-TIME FUNCTIONALITY
    socket.on('posture_update', function(data) {
        if (DEBUG) console.log('Posture update received:', data.posture_state);

        // Story 3.6: Log alert tracking for debugging (only when duration > 0)
        if (data.alert && data.alert.duration > 0 && DEBUG) {
            console.log('[TRACKING] Bad posture duration:', {
                duration: data.alert.duration,
                threshold_reached: data.alert.threshold_reached,
                should_alert: data.alert.should_alert
            });
        }

        updatePostureStatus(data);
        updateCameraFeed(data.frame_base64);
        updateTimestamp();
    });

    // Camera status handler - Story 2.7
    socket.on('camera_status', function(data) {
        if (DEBUG) console.log('Camera status received:', data.state);
        updateCameraStatus(data.state);
    });

    // Error handler - server-side errors
    socket.on('error', function(data) {
        console.error('Server error:', data.message);
        updateConnectionStatus('error');
        // Error message shown in posture-message by updateConnectionStatus
    });

    // Alert triggered handler - Story 3.3 Task 2
    socket.on('alert_triggered', function(data) {
        // Story 3.6: Always log alert events for debugging (enterprise audit trail)
        console.log('[ALERT] Alert triggered event received:', {
            message: data.message,
            duration: data.duration,
            timestamp: data.timestamp
        });

        // Send browser notification if permission granted
        sendBrowserNotification(data);

        // Show dashboard alert banner (Task 3)
        showDashboardAlert(data.message, data.duration);
    });

    // Monitoring status handler - Story 3.4 Task 3
    socket.on('monitoring_status', function(data) {
        if (DEBUG) console.log('Monitoring status update:', data);
        updateMonitoringUI(data);
    });

    // Posture correction confirmation handler - Story 3.5
    // Displays positive feedback when user corrects posture after alert
    socket.on('posture_corrected', (data) => {
        if (DEBUG) console.log('Posture correction confirmed:', data);

        try {
            // Clear alert banner (stale after correction)
            clearDashboardAlert();

            // Update posture message with positive feedback
            const postureMessage = document.getElementById('posture-message');
            if (postureMessage) {
                postureMessage.textContent = data.message;  // "✓ Good posture restored! Nice work!"
                postureMessage.style.color = '#10b981';     // Green (positive reinforcement)

                // Auto-reset to normal after 5 seconds
                setTimeout(() => {
                    postureMessage.style.color = '';  // Reset to default
                }, 5000);
            }

            // Browser notification (if permission granted)
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('DeskPulse', {
                    body: data.message,
                    icon: '/static/img/logo.png',
                    tag: 'posture-corrected',          // Replace previous notification
                    requireInteraction: false          // Auto-dismiss (not persistent)
                });
            }

            console.log('Posture correction feedback displayed');

        } catch (error) {
            console.error('Error handling posture_corrected event:', error);
        }
    });

    // Set initial timestamp
    updateTimestamp();

    // Initialize today's stats display (Story 4.3)
    loadTodayStats();

    // Initialize 7-day history table (Story 4.4)
    load7DayHistory();

    // Load and display trend message (Story 4.5)
    loadTrendData();
});


/**
 * Update connection status indicator.
 *
 * NOTE: cv-status element is owned by updateCameraStatus() (Story 2.7).
 * This function only updates SocketIO connection indicators.
 *
 * @param {string} status - 'connected', 'disconnected', or 'error'
 */
function updateConnectionStatus(status) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    if (!statusDot || !statusText) {
        console.error('Missing required DOM elements for updateConnectionStatus');
        return;
    }

    if (status === 'connected') {
        statusDot.className = 'status-indicator status-good';
        statusText.textContent = 'Monitoring Active';
        // cv-status updated by camera_status events only
    } else if (status === 'error') {
        statusDot.className = 'status-indicator status-bad';
        statusText.textContent = 'Connection Error';
        // Show error in posture message instead
        const postureMessage = document.getElementById('posture-message');
        if (postureMessage) {
            postureMessage.textContent = 'Connection error. Please refresh the page.';
        }
    } else {
        statusDot.className = 'status-indicator status-offline';
        statusText.textContent = 'Connecting...';
        // cv-status shows camera state, not SocketIO state
    }
}


/**
 * Update camera status indicator and messaging - Story 2.7.
 *
 * UX Design: Visibility without alarm (architecture.md:789-865)
 * - Connected: Minimal indicator, no interruption
 * - Degraded: Brief "reconnecting..." message, no panic
 * - Disconnected: Clear troubleshooting guidance
 *
 * @param {string} state - Camera state ('connected'|'degraded'|'disconnected')
 */
function updateCameraStatus(state) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const postureMessage = document.getElementById('posture-message');
    const cvStatus = document.getElementById('cv-status');

    // Defensive: Check elements exist
    if (!statusDot || !statusText || !postureMessage || !cvStatus) {
        console.error('Camera status UI elements not found');
        return;
    }

    if (state === 'connected') {
        // Normal operation - quiet confidence
        statusDot.className = 'status-indicator status-good';
        statusText.textContent = 'Monitoring Active';
        cvStatus.textContent = 'Camera connected, monitoring active';
        postureMessage.textContent = 'Sit at your desk to begin posture tracking';

    } else if (state === 'degraded') {
        // Temporary issue - reassuring, not alarming
        statusDot.className = 'status-indicator status-warning';
        statusText.textContent = '⚠ Camera Reconnecting...';
        cvStatus.textContent = 'Brief camera issue, reconnecting (2-3 seconds)';
        postureMessage.textContent = 'Camera momentarily unavailable, automatic recovery in progress';

    } else if (state === 'disconnected') {
        // Sustained failure - clear troubleshooting guidance
        statusDot.className = 'status-indicator status-bad';
        statusText.textContent = '❌ Camera Disconnected';
        cvStatus.textContent = 'Camera connection lost, retrying every 10 seconds';
        postureMessage.textContent = 'Check USB connection or restart service if issue persists';
    }
}


/**
 * Update posture status display with real-time CV data.
 *
 * @param {Object} data - Posture update data from SocketIO
 * @param {string} data.posture_state - 'good', 'bad', or null
 * @param {boolean} data.user_present - User detection status
 * @param {number} data.confidence_score - Detection confidence (0.0-1.0)
 */
function updatePostureStatus(data) {
    // Story 3.4: Don't update UI if monitoring is paused or not yet initialized
    // Prevents posture_update events (10 FPS) from overwriting "Monitoring Paused" UI
    // Also prevents race condition where posture_update arrives before initial monitoring_status
    if (monitoringActive === false) {
        if (DEBUG) console.log('Monitoring paused - skipping posture UI update');
        return;
    }

    if (monitoringActive === null) {
        if (DEBUG) console.log('Monitoring state not yet initialized - skipping posture UI update');
        return;
    }

    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const postureMessage = document.getElementById('posture-message');

    if (!statusDot || !statusText || !postureMessage) {
        console.error('Missing required DOM elements for updatePostureStatus');
        return;
    }

    if (!data.user_present) {
        // No user detected
        statusDot.className = 'status-indicator status-offline';
        statusText.textContent = 'No User Detected';
        postureMessage.textContent =
            'Step into camera view to begin posture monitoring';
        postureMessage.style.color = '';  // Reset to default (neutral)
        return;
    }

    if (data.posture_state === null) {
        // User present but posture not classifiable
        statusDot.className = 'status-indicator status-offline';
        statusText.textContent = 'Detecting Posture...';
        postureMessage.textContent =
            'Sit at your desk for posture classification to begin';
        postureMessage.style.color = '';  // Reset to default (neutral)
        return;
    }

    // Update status based on posture (UX Design: colorblind-safe palette)
    if (data.posture_state === 'good') {
        statusDot.className = 'status-indicator status-good';  // Green
        statusText.textContent = '✓ Good Posture';
        postureMessage.textContent =
            'Great! Keep up the good posture.';
        postureMessage.style.color = '#10b981';  // Green (positive feedback)
    } else if (data.posture_state === 'bad') {
        statusDot.className = 'status-indicator status-bad';  // Amber
        statusText.textContent = '⚠ Bad Posture';
        postureMessage.style.color = '#ef4444';  // Red (negative feedback)

        // Story 3.6: Display duration tracking and threshold progress
        // Backend sends data.alert = {duration: int, threshold_reached: bool, should_alert: bool}
        if (data.alert && data.alert.duration > 0) {
            const minutes = Math.floor(data.alert.duration / 60);
            const seconds = data.alert.duration % 60;
            const threshold_minutes = 10; // Default threshold from config

            // Format duration nicely: "3m 25s" or "12m 5s"
            const durationStr = `${minutes}m ${seconds}s`;

            if (data.alert.threshold_reached) {
                // Past threshold - use urgent messaging
                postureMessage.textContent =
                    `⚠ Bad posture for ${durationStr}! Please correct your posture now.`;
            } else {
                // Under threshold - show progress
                postureMessage.textContent =
                    `Bad posture: ${durationStr} / ${threshold_minutes}m - Sit up straight and align your shoulders`;
            }
        } else {
            // No duration tracking yet (just started bad posture)
            postureMessage.textContent =
                'Sit up straight and align your shoulders';
        }
    }

    // Display confidence if in debug mode
    const confidencePercent = Math.round(data.confidence_score * 100);
    console.log(
        `Posture: ${data.posture_state}, ` +
        `Confidence: ${confidencePercent}%`
    );
}


/**
 * Update camera feed image with latest frame.
 *
 * @param {string} frameBase64 - Base64-encoded JPEG frame
 */
function updateCameraFeed(frameBase64) {
    if (!frameBase64) {
        // No frame available - show placeholder
        showCameraPlaceholder();
        return;
    }

    const cameraFrame = document.getElementById('camera-frame');
    const cameraPlaceholder = document.getElementById('camera-placeholder');

    if (!cameraFrame || !cameraPlaceholder) {
        console.error('Missing required DOM elements for updateCameraFeed');
        return;
    }

    // Show camera frame, hide placeholder
    cameraFrame.src = 'data:image/jpeg;base64,' + frameBase64;
    cameraFrame.style.display = 'block';
    cameraPlaceholder.style.display = 'none';
}


/**
 * Show camera placeholder (when no frame available).
 */
function showCameraPlaceholder() {
    const cameraFrame = document.getElementById('camera-frame');
    const cameraPlaceholder = document.getElementById('camera-placeholder');

    if (!cameraFrame || !cameraPlaceholder) {
        console.error('Missing required DOM elements for showCameraPlaceholder');
        return;
    }

    cameraFrame.style.display = 'none';
    cameraPlaceholder.style.display = 'block';
}


/**
 * Update timestamp display to current time.
 */
function updateTimestamp() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const lastUpdate = document.getElementById('last-update');
    if (lastUpdate) {
        lastUpdate.textContent = timeString;
    }
}


/**
 * Load and display today's posture statistics - Story 4.3 AC1.
 * Fetches from /api/stats/today and updates dashboard display.
 *
 * Called on page load and every 30 seconds for real-time updates.
 */
async function loadTodayStats() {
    try {
        const response = await fetch('/api/stats/today');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const stats = await response.json();
        updateTodayStatsDisplay(stats);

    } catch (error) {
        console.error('Failed to load today stats:', error);
        handleStatsLoadError(error);
    }
}

/**
 * Update dashboard display with today's statistics - Story 4.3 AC1.
 *
 * @param {Object} stats - Statistics object from API
 * @param {string} stats.date - ISO 8601 date string ("2025-12-19")
 * @param {number} stats.good_duration_seconds - Time in good posture
 * @param {number} stats.bad_duration_seconds - Time in bad posture
 * @param {number} stats.user_present_duration_seconds - Total active time
 * @param {number} stats.posture_score - 0-100 percentage
 * @param {number} stats.total_events - Event count
 * @returns {void}
 */
function updateTodayStatsDisplay(stats) {
    // Update good posture time
    const goodTime = formatDuration(stats.good_duration_seconds);
    const goodTimeElement = document.getElementById('good-time');
    if (goodTimeElement) {
        goodTimeElement.textContent = goodTime;
    }

    // Update bad posture time
    const badTime = formatDuration(stats.bad_duration_seconds);
    const badTimeElement = document.getElementById('bad-time');
    if (badTimeElement) {
        badTimeElement.textContent = badTime;
    }

    // Update posture score with color-coding (UX Design: Progress framing)
    const score = Math.round(stats.posture_score);
    const scoreElement = document.getElementById('posture-score');

    if (scoreElement) {
        scoreElement.textContent = score + '%';

        // Color-code score (green ≥70%, amber 40-69%, gray <40%)
        // UX Design: Quietly capable - visual feedback without alarm
        if (score >= 70) {
            scoreElement.style.color = '#10b981';  // Green (good performance)
        } else if (score >= 40) {
            scoreElement.style.color = '#f59e0b';  // Amber (needs improvement)
        } else {
            scoreElement.style.color = '#6b7280';  // Gray (low score)
        }
    }

    if (DEBUG) {
        console.log(
            `Today's stats updated: ${score}% ` +
            `(${goodTime} good, ${badTime} bad, ${stats.total_events} events)`
        );
    }
}

/**
 * Format duration in seconds to human-readable string - Story 4.3 AC1.
 *
 * Matches server-side format_duration() pattern (analytics.py:217-248).
 *
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration ("2h 15m", "45m", or "0m")
 * @example
 * formatDuration(7890) // "2h 11m"
 * formatDuration(300)  // "5m"
 * formatDuration(0)    // "0m"
 */
function formatDuration(seconds) {
    // Handle zero and negative durations (edge case)
    if (seconds <= 0) {
        return '0m';
    }

    // Calculate hours and minutes
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    // Format based on duration
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

/**
 * Handle stats load error - Story 4.3 AC1.
 * Displays error state in stats display without disrupting dashboard.
 *
 * @param {Error} error - Error object from fetch failure
 * @returns {void}
 */
function handleStatsLoadError(error) {
    // Update display with error placeholders
    const goodTimeElement = document.getElementById('good-time');
    const badTimeElement = document.getElementById('bad-time');
    const scoreElement = document.getElementById('posture-score');

    if (goodTimeElement) goodTimeElement.textContent = '--';
    if (badTimeElement) badTimeElement.textContent = '--';

    if (scoreElement) {
        scoreElement.textContent = '--%';
        scoreElement.style.color = '#6b7280';  // Gray
    }

    // Show user-friendly error message in footer
    const article = document.querySelector('article');
    const footer = article?.querySelector('footer small');
    if (footer) {
        footer.textContent = 'Unable to load stats - retrying in 30 seconds';
        footer.style.color = '#ef4444';  // Red error color
    }

    // Log for debugging
    console.error('Stats unavailable:', error.message);
}


/**
 * Load and display 7-day posture history - Story 4.4 AC2.
 * Fetches from /api/stats/history and renders table with trend indicators.
 * Includes retry logic for transient network errors.
 *
 * @param {number} retries - Number of retry attempts (default: 3)
 * @returns {Promise<void>}
 */
async function load7DayHistory(retries = 3) {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const response = await fetch('/api/stats/history');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // API returns: {"history": [{date, good_duration_seconds, bad_duration_seconds, posture_score, ...}, ...]}
            // history array is ordered oldest to newest (6 days ago → today)
            display7DayHistory(data.history);
            return; // Success - exit retry loop

        } catch (error) {
            if (attempt === retries) {
                // Final attempt failed - show error state
                console.error('Failed to load 7-day history after', retries, 'attempts:', error);
                handleHistoryLoadError(error);
            } else {
                // Retry with exponential backoff (1s, 2s, 3s)
                if (DEBUG) {
                    console.log(`Retry attempt ${attempt}/${retries} for history load...`);
                }
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }
}

/**
 * Display 7-day history table with trend indicators - Story 4.4 AC2.
 *
 * @param {Array} history - Array of daily stats objects from API
 *                          Format: [{date, good_duration_seconds, bad_duration_seconds, posture_score, total_events}, ...]
 * @returns {void}
 */
function display7DayHistory(history) {
    const container = document.getElementById('history-table-container');

    if (!container) {
        console.error('History container element not found in DOM');
        return;
    }

    // Edge case: No historical data yet (new installation, first day)
    if (!history || history.length === 0) {
        container.innerHTML = `
            <p style="text-align: center; padding: 2rem; color: #6b7280;">
                No historical data yet. Start monitoring to build your history!
            </p>
        `;
        return;
    }

    // Build table HTML with Pico CSS semantic grid
    let tableHTML = `
        <table role="grid">
            <thead>
                <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Good Time</th>
                    <th scope="col">Bad Time</th>
                    <th scope="col">Score</th>
                    <th scope="col">Trend</th>
                </tr>
            </thead>
            <tbody>
    `;

    // Iterate through history (oldest to newest) to build table rows
    history.forEach((day, index) => {
        const dateStr = formatHistoryDate(day.date);
        const goodTime = formatDuration(day.good_duration_seconds);
        const badTime = formatDuration(day.bad_duration_seconds);
        const score = Math.round(day.posture_score);

        // Calculate trend indicator (compare to previous day)
        let trendIcon = '—';
        let trendColor = '#6b7280';
        let trendTitle = 'First day in range';

        if (index > 0) {
            const prevScore = Math.round(history[index - 1].posture_score);
            const scoreDiff = score - prevScore;

            if (scoreDiff > 5) {
                trendIcon = '↑';
                trendColor = '#10b981';  // Green (improving)
                trendTitle = `Up ${scoreDiff} points from previous day`;
            } else if (scoreDiff < -5) {
                trendIcon = '↓';
                trendColor = '#f59e0b';  // Amber (declining)
                trendTitle = `Down ${Math.abs(scoreDiff)} points from previous day`;
            } else {
                trendIcon = '→';
                trendColor = '#6b7280';  // Gray (stable)
                trendTitle = `Stable (${scoreDiff >= 0 ? '+' : ''}${scoreDiff} points)`;
            }
        }

        // Color-code score (green ≥70%, amber 40-69%, gray <40%)
        let scoreColor = '#6b7280';
        if (score >= 70) {
            scoreColor = '#10b981';
        } else if (score >= 40) {
            scoreColor = '#f59e0b';
        }

        tableHTML += `
            <tr>
                <td>${dateStr}</td>
                <td>${goodTime}</td>
                <td>${badTime}</td>
                <td style="color: ${scoreColor}; font-weight: bold;">${score}%</td>
                <td style="color: ${trendColor}; font-size: 1.5rem;" title="${trendTitle}">
                    ${trendIcon}
                </td>
            </tr>
        `;
    });

    tableHTML += `
            </tbody>
        </table>
    `;

    // Render table
    container.innerHTML = tableHTML;

    // Show celebration message if today is best day (UX Design: Celebration messaging)
    checkAndShowCelebration(history);

    if (DEBUG) {
        console.log(`7-day history table rendered: ${history.length} days displayed`);
    }
}

/**
 * Format date for history table display - Story 4.4 AC2.
 *
 * Converts ISO 8601 date string to user-friendly format:
 * - "Today" for current date
 * - "Yesterday" for previous date
 * - "Mon 12/4" for older dates (weekday + month/day)
 *
 * @param {string} dateStr - ISO 8601 date string from API ("2025-12-19")
 * @returns {string} Formatted date string
 * @example
 * formatHistoryDate("2025-12-19") // "Today" (if today)
 * formatHistoryDate("2025-12-18") // "Yesterday" (if yesterday)
 * formatHistoryDate("2025-12-13") // "Mon 12/13" (older date)
 */
function formatHistoryDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');  // Parse as midnight local time
    const today = new Date();
    today.setHours(0, 0, 0, 0);  // Reset to midnight for accurate comparison

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    // Format as "Today", "Yesterday", or "Mon 12/4"
    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    } else {
        const weekday = date.toLocaleDateString('en-US', { weekday: 'short' });
        const monthDay = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
        return `${weekday} ${monthDay}`;
    }
}

/**
 * Check if today is best day and show celebration message - Story 4.4 AC2.
 *
 * UX Design: Celebration messaging provides positive reinforcement.
 * Only celebrates if score ≥50% (don't celebrate poor performance).
 *
 * @param {Array} history - 7-day history array (oldest to newest)
 * @returns {void}
 */
function checkAndShowCelebration(history) {
    if (!history || history.length === 0) return;

    // Find today's data (last element in history array)
    const today = history[history.length - 1];

    // Find best day in 7-day history
    const bestDay = history.reduce((max, day) =>
        day.posture_score > max.posture_score ? day : max
    );

    // Celebrate if today is best day AND score is decent (≥50%)
    if (today.date === bestDay.date && today.posture_score >= 50) {
        const message = '🎉 Best posture day this week!';
        showCelebrationMessage(message);

        if (DEBUG) {
            console.log(`Celebration: ${message} (score: ${Math.round(today.posture_score)}%)`);
        }
    }
}

/**
 * Show temporary celebration message in posture message area - Story 4.4 AC2.
 *
 * Temporarily replaces posture message with celebration, then restores original.
 * Duration: 5 seconds (long enough to notice, short enough not to annoy).
 *
 * @param {string} message - Celebration message to display
 * @returns {void}
 */
function showCelebrationMessage(message) {
    const postureMessage = document.getElementById('posture-message');

    if (!postureMessage) return;  // Defensive: element may not exist

    const originalText = postureMessage.textContent;
    const originalColor = postureMessage.style.color;
    const originalWeight = postureMessage.style.fontWeight;

    // Show celebration
    postureMessage.textContent = message;
    postureMessage.style.color = '#10b981';  // Green
    postureMessage.style.fontWeight = 'bold';

    // Restore original after 5 seconds
    setTimeout(() => {
        postureMessage.textContent = originalText;
        postureMessage.style.color = originalColor;
        postureMessage.style.fontWeight = originalWeight;
    }, 5000);  // 5 seconds
}

/**
 * Handle history load error - Story 4.4 AC2.
 * Displays error state in history container without disrupting dashboard.
 *
 * @param {Error} error - Error object from fetch failure
 * @returns {void}
 */
function handleHistoryLoadError(error) {
    const container = document.getElementById('history-table-container');

    if (!container) return;  // Defensive programming

    container.innerHTML = `
        <p style="text-align: center; padding: 2rem; color: #ef4444;">
            Unable to load history. Please refresh the page to try again.
        </p>
    `;

    // Log for debugging
    console.error('History unavailable:', error.message);
}

/**
 * Load trend data from backend API - Story 4.5 AC3.
 * Fetches from /api/stats/trend and displays progress message.
 * Includes retry logic for transient network errors.
 *
 * @param {number} retries - Number of retry attempts (default: 3)
 * @returns {Promise<void>}
 */
async function loadTrendData(retries = 3) {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const response = await fetch('/api/stats/trend');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const trend = await response.json();

            // API returns: {trend, average_score, score_change, best_day, improvement_message}
            displayTrendMessage(trend);
            return; // Success - exit retry loop

        } catch (error) {
            if (attempt === retries) {
                // Final attempt failed - show error state
                console.error('Failed to load trend after', retries, 'attempts:', error);
                handleTrendLoadError(error);
            } else {
                // Retry with linear backoff (1s, 2s, 3s) - Code Review Fix #7
                if (DEBUG) {
                    console.log(`Retry attempt ${attempt}/${retries} for trend load...`);
                }
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }
}

/**
 * Display trend message in 7-day history section - Story 4.5 AC4.
 * Adds progress message below "7-Day History" header with color-coded indicator.
 *
 * UX Design: Progress framing principle - emphasize wins, reframe challenges.
 *
 * @param {Object} trend - Trend data from API
 * @param {string} trend.trend - 'improving', 'stable', 'declining', 'insufficient_data'
 * @param {number} trend.average_score - 7-day average score (0-100)
 * @param {number} trend.score_change - Points change first → last day
 * @param {string} trend.improvement_message - User-facing message
 * @returns {void}
 */
function displayTrendMessage(trend) {
    // Find 7-day history section header
    const historyHeader = document.querySelector('article header h3');

    if (!historyHeader || historyHeader.textContent !== '7-Day History') {
        // Header not found or not the right section - defensive programming
        if (DEBUG) {
            console.warn('7-Day History header not found for trend message placement');
        }
        return;
    }

    // Remove existing trend message if present (prevents duplicates on refresh)
    const existingMessage = historyHeader.parentElement.querySelector('.trend-message');
    if (existingMessage) {
        existingMessage.remove();
    }

    // Create trend message element
    const trendMessage = document.createElement('p');
    trendMessage.className = 'trend-message';
    trendMessage.style.margin = '0.5rem 0 0 0';
    trendMessage.style.fontSize = '0.9rem';
    trendMessage.style.fontWeight = 'bold';

    // Color-code and add visual indicator based on trend
    if (trend.trend === 'improving') {
        trendMessage.style.color = '#10b981';  // Green (success)
        trendMessage.innerHTML = `↑ ${trend.improvement_message}`;
    } else if (trend.trend === 'declining') {
        trendMessage.style.color = '#f59e0b';  // Amber (caution)
        trendMessage.innerHTML = `↓ ${trend.improvement_message}`;
    } else if (trend.trend === 'stable') {
        trendMessage.style.color = '#6b7280';  // Gray (neutral)
        trendMessage.innerHTML = `→ ${trend.improvement_message}`;
    } else {
        // insufficient_data - show message without indicator
        trendMessage.style.color = '#6b7280';  // Gray
        trendMessage.style.fontWeight = 'normal';
        trendMessage.textContent = trend.improvement_message;
    }

    // Insert message after header (visual hierarchy: Title → Progress → Table)
    // Defensive programming: Verify parent exists (Code Review Fix #10)
    if (!historyHeader.parentElement) {
        if (DEBUG) {
            console.error('7-Day History header has no parent element - cannot place trend message');
        }
        return;
    }
    historyHeader.parentElement.appendChild(trendMessage);

    if (DEBUG) {
        console.log(`Trend message displayed: ${trend.trend} (${trend.score_change} points)`);
    }
}

/**
 * Handle trend load error - Story 4.5 AC3.
 * Silently fails to avoid disrupting dashboard (trend is optional enhancement).
 *
 * @param {Error} error - Error object from fetch failure
 * @returns {void}
 */
function handleTrendLoadError(error) {
    // Trend message is optional enhancement - don't show error UI
    // Just log for debugging
    console.error('Trend unavailable:', error.message);
}


// Update timestamp every second
setInterval(updateTimestamp, 1000);

// Poll for stats updates every 30 seconds - Story 4.3 AC2
// Balances data freshness vs server load
const statsPollingInterval = setInterval(loadTodayStats, 30000);  // 30 seconds = 30000ms

// Refresh history every 30 seconds to stay in sync with today's stats - Story 4.4 AC2
const historyPollingInterval = setInterval(load7DayHistory, 30000);

// Refresh trend every 60 seconds to stay in sync with history updates - Story 4.5 AC5
// (Longer interval than history because trend changes less frequently)
const trendPollingInterval = setInterval(loadTrendData, 60000);  // 60 seconds = 60000ms

// Enterprise-grade polling cleanup using Page Visibility API
// Reference: https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event
// Chrome is phasing out beforeunload/unload events (unreliable on mobile)
// visibilitychange + pagehide provide reliable cleanup across all browsers
// Reference: https://www.rumvision.com/blog/time-to-unload-your-unload-events/

// Page Visibility API: Pause/resume polling based on tab visibility
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Tab hidden: User switched away, minimize polling
        if (DEBUG) console.log('Tab hidden - stats polling paused (Page Visibility API)');
        // Note: We keep interval running but could optimize by pausing here
    } else {
        // Tab visible again: Resume polling, fetch fresh data immediately
        if (DEBUG) console.log('Tab visible - fetching fresh stats and history (Page Visibility API)');
        loadTodayStats();  // Immediate refresh when user returns
        load7DayHistory();  // Story 4.4: Refresh history too
        loadTrendData();    // Story 4.5: Refresh trend too
    }
});

// pagehide event: Last reliable cleanup opportunity (fires before unload)
// Handles navigation, tab close, browser close on all platforms including mobile
// Reference: https://developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event
window.addEventListener('pagehide', () => {
    clearInterval(statsPollingInterval);
    clearInterval(historyPollingInterval);
    clearInterval(trendPollingInterval);
    if (DEBUG) console.log('Polling timers cleaned up (pagehide)');
});


/**
 * Initialize browser notifications - Story 3.3 Task 1.
 * Checks browser support, HTTPS context, and displays permission prompt if needed.
 */
function initBrowserNotifications() {
    console.log('Initializing browser notifications...');

    // Check browser support
    if (!('Notification' in window)) {
        console.warn('Browser notifications not supported');
        return;
    }

    // Check HTTPS context (required for notifications except localhost)
    // Only true localhost (127.0.0.1/localhost) is exempt from HTTPS requirement
    const isLocalhost = window.location.hostname === 'localhost' ||
                        window.location.hostname === '127.0.0.1' ||
                        window.location.hostname === '::1';

    const isSecureContext = window.isSecureContext || isLocalhost;

    if (!isSecureContext) {
        console.warn('Browser notifications require HTTPS (except localhost).');
        console.warn('Current URL:', window.location.href);
        console.warn('For network access (e.g., deskpulse.local), use HTTPS or notifications will not work.');
        console.warn('Notifications will gracefully degrade to visual alerts only.');
        return;
    }

    // Check current permission state
    const permission = Notification.permission;
    console.log('Notification permission:', permission);

    if (permission === 'default') {
        // Check if user previously dismissed prompt
        try {
            const dismissedTimestamp = localStorage.getItem('notificationPromptDismissed');
            if (dismissedTimestamp) {
                const daysSinceDismissal = (Date.now() - parseInt(dismissedTimestamp)) / (1000 * 60 * 60 * 24);
                if (daysSinceDismissal < 7) {
                    console.log('Notification prompt dismissed recently, not showing again');
                    return;
                }
            }
        } catch (e) {
            console.warn('Failed to read notification preference from localStorage:', e);
            // Continue to show prompt on error
        }

        // Show permission prompt
        createNotificationPrompt();
    } else if (permission === 'granted') {
        console.log('Browser notifications enabled');
    } else if (permission === 'denied') {
        console.log('Browser notifications denied by user');
    }
}


/**
 * Create notification permission prompt banner - Story 3.3 Task 1.
 * Light blue banner with Enable/Maybe Later buttons.
 */
function createNotificationPrompt() {
    // Check if prompt already exists
    if (document.getElementById('notification-prompt')) {
        return;
    }

    // Create prompt banner
    const prompt = document.createElement('article');
    prompt.id = 'notification-prompt';
    prompt.style.cssText = `
        background-color: #f0f9ff;
        border: 2px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    `;

    // Prompt message
    const message = document.createElement('div');
    message.style.flex = '1 1 300px';
    message.innerHTML = `
        <strong>🔔 Enable Browser Notifications</strong>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">
            Get posture alerts on this device even when the tab is in the background.
        </p>
    `;

    // Button container
    const buttons = document.createElement('div');
    buttons.style.cssText = 'display: flex; gap: 0.5rem; flex-wrap: wrap;';

    // Enable button
    const enableBtn = document.createElement('button');
    enableBtn.textContent = 'Enable';
    enableBtn.className = 'primary';
    enableBtn.style.cssText = 'margin: 0;';
    enableBtn.onclick = function() {
        Notification.requestPermission().then(function(permission) {
            console.log('Notification permission result:', permission);

            // Remove prompt
            prompt.remove();

            if (permission === 'granted') {
                showToast('Browser notifications enabled! You\'ll receive posture alerts.', 'success');
            } else if (permission === 'denied') {
                console.log('User denied notification permission');
            }
        });
    };

    // Maybe Later button
    const laterBtn = document.createElement('button');
    laterBtn.textContent = 'Maybe Later';
    laterBtn.className = 'secondary';
    laterBtn.style.cssText = 'margin: 0;';
    laterBtn.onclick = function() {
        // Store dismissal timestamp (don't ask again for 7 days)
        try {
            localStorage.setItem('notificationPromptDismissed', Date.now().toString());
            console.log('Notification prompt dismissed');
        } catch (e) {
            console.warn('Failed to store notification preference:', e);
            // Graceful degradation - prompt may reappear on reload
        }

        // Remove prompt
        prompt.remove();
    };

    // Assemble prompt
    buttons.appendChild(enableBtn);
    buttons.appendChild(laterBtn);
    message.appendChild(buttons);
    prompt.appendChild(message);

    // Insert at top of main container (after any existing alerts)
    const main = document.querySelector('main.container');
    if (main && main.firstChild) {
        main.insertBefore(prompt, main.firstChild);
    } else if (main) {
        main.appendChild(prompt);
    }

    console.log('Notification permission prompt displayed');
}


/**
 * Show toast notification - Story 3.3 Task 3 helper.
 * Used for success messages and info feedback.
 *
 * @param {string} message - Toast message text
 * @param {string} type - 'success', 'info', 'warning', or 'error'
 */
function showToast(message, type = 'info') {
    // Remove existing toast if present
    const existingToast = document.getElementById('toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    // Color mapping
    const colors = {
        success: { bg: '#d1fae5', border: '#10b981', text: '#065f46' },
        info: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
        warning: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
        error: { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' }
    };

    const color = colors[type] || colors.info;

    // Create toast
    const toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${color.bg};
        color: ${color.text};
        border: 2px solid ${color.border};
        border-radius: 8px;
        padding: 1rem 1.5rem;
        max-width: 400px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    toast.textContent = message;

    // Add slide-in animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    if (!document.getElementById('toast-animations')) {
        style.id = 'toast-animations';
        document.head.appendChild(style);
    }

    document.body.appendChild(toast);

    // Auto-remove after 5 seconds with slide-out animation
    setTimeout(function() {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(function() {
            toast.remove();
        }, 300);
    }, 5000);
}


/**
 * Send browser notification - Story 3.3 Task 2.
 * Creates Web Notification API notification with all enhancements.
 *
 * @param {Object} data - Alert data from server
 * @param {string} data.message - Alert message text
 * @param {number} data.duration - Duration in seconds
 * @param {string} data.timestamp - ISO timestamp
 */
function sendBrowserNotification(data) {
    // Check prerequisites
    if (!('Notification' in window)) {
        console.log('Browser notifications not supported, using visual alert only');
        return;
    }

    if (!socket || !socket.connected) {
        console.warn('SocketIO not connected, skipping browser notification');
        return;
    }

    if (Notification.permission !== 'granted') {
        console.log('Notification permission not granted, using visual alert only');
        return;
    }

    // Check notification sound preference (default: enabled)
    let soundEnabled = true;  // Default
    try {
        soundEnabled = localStorage.getItem('notificationSound') !== 'false';
    } catch (e) {
        console.warn('Failed to read notification sound preference:', e);
        // Use default: enabled
    }

    // Create notification with all options
    const options = {
        body: data.message,
        icon: '/static/img/logo.png',
        badge: '/static/img/favicon.ico',
        tag: 'posture-alert',  // Replaces previous notification (prevents spam)
        requireInteraction: false,  // Auto-dismiss allowed
        silent: !soundEnabled,  // Respect sound preference
        vibrate: [200, 100, 200],  // Mobile vibration pattern
        timestamp: Date.now()
    };

    try {
        const notification = new Notification('DeskPulse Posture Alert', options);

        // Click handler - focus dashboard tab
        notification.onclick = function(event) {
            event.preventDefault();

            // Try to focus window (browsers may restrict this)
            try {
                window.focus();
            } catch (e) {
                console.log('Window focus restricted:', e);
            }

            // Close notification
            notification.close();
        };

        // Auto-close after 10 seconds
        setTimeout(function() {
            notification.close();
        }, 10000);

        console.log('Browser notification sent:', data.message);

    } catch (error) {
        console.error('Failed to create browser notification:', error);
    }
}


/**
 * Show dashboard alert banner - Story 3.3 Task 3.
 * Warm yellow banner with acknowledgment button.
 *
 * @param {string} message - Alert message text
 * @param {number} duration - Duration in seconds
 */
function showDashboardAlert(message, duration) {
    // Check if alert banner already exists
    let alertBanner = document.getElementById('dashboard-alert-banner');

    if (alertBanner) {
        // Update existing banner with new message
        const messageElement = alertBanner.querySelector('.alert-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
        console.log('Dashboard alert updated:', message);
        return;
    }

    // Create new alert banner
    alertBanner = document.createElement('article');
    alertBanner.id = 'dashboard-alert-banner';
    alertBanner.style.cssText = `
        background-color: #fffbeb;
        border: 2px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    `;

    // Alert content
    const content = document.createElement('div');
    content.style.flex = '1 1 300px';

    const icon = document.createElement('strong');
    icon.textContent = '⚠️ Posture Alert';
    icon.style.cssText = 'color: #92400e; display: block; margin-bottom: 0.5rem;';

    const messageText = document.createElement('p');
    messageText.className = 'alert-message';
    messageText.textContent = message;
    messageText.style.cssText = 'margin: 0; color: #78350f;';

    content.appendChild(icon);
    content.appendChild(messageText);

    // Acknowledgment button
    const acknowledgeBtn = document.createElement('button');
    acknowledgeBtn.textContent = 'I\'ve corrected my posture';
    acknowledgeBtn.className = 'secondary';
    acknowledgeBtn.style.cssText = 'margin: 0; white-space: nowrap;';
    acknowledgeBtn.onclick = function() {
        // Emit acknowledgment event to server
        if (socket && socket.connected) {
            socket.emit('alert_acknowledged', {
                acknowledged_at: new Date().toISOString()
            });
            console.log('Alert acknowledged');
        }

        // Clear banner
        clearDashboardAlert();

        // Show feedback toast
        showToast('Thank you! Keep up the good posture.', 'success');
    };

    // Assemble banner
    alertBanner.appendChild(content);
    alertBanner.appendChild(acknowledgeBtn);

    // Insert at top of main container
    const main = document.querySelector('main.container');
    if (main && main.firstChild) {
        main.insertBefore(alertBanner, main.firstChild);
    } else if (main) {
        main.appendChild(alertBanner);
    }

    console.log('Dashboard alert banner displayed:', message);
}


/**
 * Clear dashboard alert banner - Story 3.3 Task 3.
 * Integration point for Story 3.5 posture_corrected event.
 */
function clearDashboardAlert() {
    const alertBanner = document.getElementById('dashboard-alert-banner');
    if (alertBanner) {
        alertBanner.remove();
        console.log('Dashboard alert banner cleared');
    }
}


/**
 * Initialize pause/resume monitoring controls - Story 3.4 Task 3.
 * Sets up button click handlers and SocketIO connection state management.
 */
function initPauseResumeControls() {
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');

    // Defensive: Check buttons exist
    if (!pauseBtn || !resumeBtn) {
        console.error('Pause/resume buttons not found');
        return;
    }

    // Pause button click handler
    pauseBtn.addEventListener('click', function() {
        // Check SocketIO connection
        if (!socket || !socket.connected) {
            console.warn('SocketIO not connected - cannot pause monitoring');
            showToast('Connection error - please try again', 'error');
            return;
        }

        // Optimistic UI: Show loading state immediately
        pauseBtn.disabled = true;
        const originalText = pauseBtn.textContent;
        pauseBtn.textContent = '⏸ Pausing...';

        socket.emit('pause_monitoring');
        if (DEBUG) console.log('Pause monitoring requested');

        // Re-enable button after timeout (safety fallback if broadcast fails)
        setTimeout(function() {
            if (pauseBtn.disabled) {
                pauseBtn.disabled = false;
                pauseBtn.textContent = originalText;
            }
        }, 3000);
    });

    // Resume button click handler
    resumeBtn.addEventListener('click', function() {
        // Check SocketIO connection
        if (!socket || !socket.connected) {
            console.warn('SocketIO not connected - cannot resume monitoring');
            showToast('Connection error - please try again', 'error');
            return;
        }

        // Optimistic UI: Show loading state immediately
        resumeBtn.disabled = true;
        const originalText = resumeBtn.textContent;
        resumeBtn.textContent = '▶️ Resuming...';

        socket.emit('resume_monitoring');
        if (DEBUG) console.log('Resume monitoring requested');

        // Re-enable button after timeout (safety fallback if broadcast fails)
        setTimeout(function() {
            if (resumeBtn.disabled) {
                resumeBtn.disabled = false;
                resumeBtn.textContent = originalText;
            }
        }, 3000);
    });

    if (DEBUG) console.log('Pause/resume controls initialized');
}


/**
 * Update monitoring UI based on monitoring_status event - Story 3.4 Task 3.
 * Handles pause/resume button visibility and status messaging.
 *
 * @param {Object} data - Monitoring status data
 * @param {boolean} data.monitoring_active - True if monitoring active
 * @param {number} data.threshold_seconds - Alert threshold (600)
 * @param {number} data.cooldown_seconds - Alert cooldown (300)
 */
function updateMonitoringUI(data) {
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const postureMessage = document.getElementById('posture-message');

    // Defensive: Check elements exist
    if (!pauseBtn || !resumeBtn) {
        console.error('Pause/resume buttons not found');
        return;
    }

    try {
        // Update global monitoring state (prevents posture_update from overwriting paused UI)
        monitoringActive = data.monitoring_active;

        if (data.monitoring_active) {
            // Monitoring active - show pause button
            pauseBtn.style.display = 'inline-block';
            pauseBtn.disabled = false;
            pauseBtn.textContent = '⏸ Pause Monitoring';
            resumeBtn.style.display = 'none';

            if (statusText) {
                statusText.textContent = 'Monitoring Active';
            }
            // Status dot color will be updated by posture_update event

        } else {
            // Monitoring paused - show resume button
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'inline-block';
            resumeBtn.disabled = false;
            resumeBtn.textContent = '▶️ Resume Monitoring';

            if (statusText) {
                statusText.textContent = '⏸ Monitoring Paused';
            }

            if (statusDot) {
                statusDot.className = 'status-indicator status-offline';
            }

            if (postureMessage) {
                postureMessage.textContent =
                    'Privacy mode: Camera monitoring paused. Click "Resume" when ready.';
            }

            // Clear alert banner (stale alert)
            clearDashboardAlert();
        }

        if (DEBUG) console.log('Monitoring UI updated:', data);

    } catch (error) {
        console.error('Error updating monitoring UI:', error);
    }
}


/**
 * Initialize network settings toggle.
 * Loads current config and sets up event listener.
 */
function initializeNetworkSettings() {
    const toggle = document.getElementById('network-access-toggle');
    const currentHost = document.getElementById('current-host');

    if (!toggle || !currentHost) return;

    // Fetch current network config
    fetch('/api/network-settings')
        .then(response => response.json())
        .then(data => {
            const isNetworkEnabled = data.host === '0.0.0.0';
            toggle.checked = isNetworkEnabled;
            currentHost.textContent = isNetworkEnabled ?
                '0.0.0.0 (Network Access)' : '127.0.0.1 (Localhost Only)';
        })
        .catch(error => {
            console.error('Failed to load network settings:', error);
            currentHost.textContent = 'Error loading settings';
        });

    // Handle toggle changes
    toggle.addEventListener('change', function() {
        const newHost = toggle.checked ? '0.0.0.0' : '127.0.0.1';

        // Save new setting
        fetch('/api/network-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host: newHost })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentHost.textContent = toggle.checked ?
                    '0.0.0.0 (Network Access)' : '127.0.0.1 (Localhost Only)';
                alert('Network settings saved! Please restart the app for changes to take effect.');
            } else {
                alert('Failed to save settings: ' + data.error);
                // Revert toggle on error
                toggle.checked = !toggle.checked;
            }
        })
        .catch(error => {
            console.error('Failed to save network settings:', error);
            alert('Failed to save settings. Check console for details.');
            // Revert toggle on error
            toggle.checked = !toggle.checked;
        });
    });
}
