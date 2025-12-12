/**
 * DeskPulse Dashboard JavaScript - Real-Time Updates
 *
 * Story 2.5: Static placeholder stubs
 * Story 2.6: SocketIO real-time updates ACTIVATED
 */

// Initialize SocketIO connection on page load
let socket;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DeskPulse Dashboard loaded - initializing SocketIO...');

    // Initialize SocketIO client (connects to same host as page)
    socket = io();

    // Connection event handlers
    socket.on('connect', function() {
        console.log('SocketIO connected:', socket.id);
        updateConnectionStatus('connected');
    });

    socket.on('disconnect', function() {
        console.log('SocketIO disconnected');
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
        console.log('Server status:', data.message);
    });

    // CV update handler - CORE REAL-TIME FUNCTIONALITY
    socket.on('posture_update', function(data) {
        console.log('Posture update received:', data.posture_state);
        updatePostureStatus(data);
        updateCameraFeed(data.frame_base64);
        updateTimestamp();
    });

    // Error handler - server-side errors
    socket.on('error', function(data) {
        console.error('Server error:', data.message);
        updateConnectionStatus('error');
        const postureMessage = document.getElementById('posture-message');
        if (postureMessage) {
            postureMessage.textContent = 'Connection error. Please refresh the page.';
        }
    });

    // Set initial timestamp
    updateTimestamp();
});


/**
 * Update connection status indicator.
 *
 * @param {string} status - 'connected', 'disconnected', or 'error'
 */
function updateConnectionStatus(status) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const cvStatus = document.getElementById('cv-status');

    if (!statusDot || !statusText || !cvStatus) {
        console.error('Missing required DOM elements for updateConnectionStatus');
        return;
    }

    if (status === 'connected') {
        statusDot.className = 'status-indicator status-good';
        statusText.textContent = 'Monitoring Active';
        cvStatus.textContent = 'Running (Real-time updates active)';
    } else if (status === 'error') {
        statusDot.className = 'status-indicator status-bad';
        statusText.textContent = 'Connection Error';
        cvStatus.textContent = 'Please refresh the page';
    } else {
        statusDot.className = 'status-indicator status-offline';
        statusText.textContent = 'Connecting...';
        cvStatus.textContent = 'Reconnecting...';
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
        postureMessage.textContent =
            'Sit up straight and align your shoulders';
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
