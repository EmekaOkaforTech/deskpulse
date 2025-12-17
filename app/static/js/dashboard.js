/**
 * DeskPulse Dashboard JavaScript - Real-Time Updates
 *
 * Story 2.5: Static placeholder stubs
 * Story 2.6: SocketIO real-time updates ACTIVATED
 */

// Debug mode toggle - set to false for production to reduce console noise
const DEBUG = false;

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

    // Set initial timestamp
    updateTimestamp();
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
        return;
    }

    if (data.posture_state === null) {
        // User present but posture not classifiable
        statusDot.className = 'status-indicator status-offline';
        statusText.textContent = 'Detecting Posture...';
        postureMessage.textContent =
            'Sit at your desk for posture classification to begin';
        return;
    }

    // Update status based on posture (UX Design: colorblind-safe palette)
    if (data.posture_state === 'good') {
        statusDot.className = 'status-indicator status-good';  // Green
        statusText.textContent = '✓ Good Posture';
        postureMessage.textContent =
            'Great! Keep up the good posture.';
    } else if (data.posture_state === 'bad') {
        statusDot.className = 'status-indicator status-bad';  // Amber
        statusText.textContent = '⚠ Bad Posture';

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
 * Update today's statistics (Epic 4 will implement).
 *
 * @param {Object} stats - Today's posture statistics
 */
function updateTodayStats(stats) {
    // Epic 4: Real implementation
    console.log('Stats update received:', stats);
}


// Update timestamp every second
setInterval(updateTimestamp, 1000);


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


// ==================================================
// Story 3.5: Posture Correction Confirmation Feedback
// ==================================================
/**
 * Handle posture_corrected event from server.
 *
 * Displays positive confirmation when user corrects posture after alert.
 * UX Design: Green color, checkmark, celebration message, brief display.
 *
 * Story 3.5: Posture Correction Confirmation Feedback
 *
 * @param {Object} data - Correction event data
 * @param {string} data.message - Confirmation message
 * @param {number} data.previous_duration - Bad posture duration (seconds)
 * @param {string} data.timestamp - Event timestamp (ISO format)
 */
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

        logger.info('Posture correction feedback displayed');

    } catch (error) {
        console.error('Error handling posture_corrected event:', error);
    }
});


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
