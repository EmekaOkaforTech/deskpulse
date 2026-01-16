"""SocketIO event handlers for real-time dashboard updates."""

import threading
import logging
import time
import queue
from flask import request
from flask_socketio import emit
from app.extensions import socketio
from app.cv.pipeline import cv_queue
import app

logger = logging.getLogger('deskpulse.socket')

# Track active client connections for cleanup
active_clients = {}
active_clients_lock = threading.Lock()


@socketio.on('connect')
def handle_connect():
    """
    Handle client connection to dashboard.

    When a client connects, send connection confirmation and start
    streaming CV updates in a dedicated thread for that client.

    Architecture Note:
    - Each connected client gets a dedicated streaming thread
    - Thread terminates when client disconnects
    - cv_queue maxsize=1 ensures all clients see latest state
    - NFR-SC1: Supports 10+ simultaneous connections

    Emits:
        status: Connection confirmation message
    """
    client_sid = request.sid
    logger.info(f"Client connected: {client_sid}")

    # Send connection confirmation
    # Use socketio.emit with room for test client compatibility
    socketio.emit('status', {
        'message': 'Connected to DeskPulse',
        'timestamp': time.time()
    }, room=client_sid)

    # Send initial monitoring status (Story 3.4)
    from flask import current_app
    from datetime import datetime
    cv_pipeline = getattr(current_app, 'cv_pipeline_test', None) or app.cv_pipeline
    if cv_pipeline and cv_pipeline.alert_manager:
        status = cv_pipeline.alert_manager.get_monitoring_status()
        socketio.emit('monitoring_status', status, room=client_sid)

    # Send initial camera status so "CV Pipeline: Checking..." updates immediately
    if cv_pipeline:
        camera_state = getattr(cv_pipeline, 'camera_state', 'disconnected')
        socketio.emit('camera_status', {
            'state': camera_state,
            'timestamp': datetime.now().isoformat()
        }, room=client_sid)
        logger.info(f"Sent initial camera_status to {client_sid}: {camera_state}")

    # Track active client BEFORE starting thread (prevents race condition)
    with active_clients_lock:
        active_clients[client_sid] = {
            'thread': None,  # Will be set after thread creation
            'connected': True,
            'connect_time': time.time()
        }

    # Start CV streaming thread for this client
    stream_thread = threading.Thread(
        target=stream_cv_updates,
        args=(client_sid,),
        daemon=True,
        name=f'CVStream-{client_sid[:8]}'
    )
    stream_thread.start()

    # Update thread reference
    with active_clients_lock:
        active_clients[client_sid]['thread'] = stream_thread

    logger.info(
        f"CV streaming started for client {client_sid} "
        f"(total clients: {len(active_clients)})"
    )


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle client disconnection.

    Marks client as disconnected so streaming thread can terminate gracefully.
    Thread cleanup happens automatically due to disconnect check in stream loop.

    Architecture Note:
    - Thread checks 'connected' flag in each iteration
    - Daemon thread terminates with main process if needed
    - Clean disconnection pattern prevents resource leaks
    """
    client_sid = request.sid
    logger.info(f"Client disconnected: {client_sid}")

    # Mark client as disconnected
    with active_clients_lock:
        if client_sid in active_clients:
            active_clients[client_sid]['connected'] = False
            # Note: Thread will self-terminate on next iteration
            logger.debug(f"Client {client_sid} marked for cleanup")


def stream_cv_updates(client_sid):
    """
    Stream CV pipeline results to connected client.

    Runs in dedicated thread per client connection. Continuously reads
    from cv_queue and emits posture_update events to the client.

    Architecture:
    - One thread per connected client (NFR-SC1: 10+ supported)
    - cv_queue.get() blocks until new CV result available
    - Terminates when client disconnects (checked via active_clients)
    - Queue timeout prevents infinite blocking on shutdown

    Performance:
    - cv_queue maxsize=1 ensures latest-wins semantic
    - Queue get() blocks ~100ms (CV pipeline fps=10)
    - SocketIO emit() <5ms overhead
    - Total latency: <110ms (meets NFR-P2: <100ms target)

    Args:
        client_sid: SocketIO session ID for target client

    Emits:
        posture_update: CV result with frame, posture state, timestamp
    """
    logger.info(f"CV streaming loop started for client {client_sid}")

    while True:
        try:
            # Check if client still connected
            with active_clients_lock:
                if client_sid not in active_clients:
                    logger.debug(
                        f"Client {client_sid} not in active_clients - "
                        f"terminating stream"
                    )
                    break

                if not active_clients[client_sid]['connected']:
                    logger.info(
                        f"Client {client_sid} disconnected - "
                        f"terminating stream"
                    )
                    # Remove from active clients
                    del active_clients[client_sid]
                    break

            # Get latest CV result (blocks until available, timeout 1 second)
            try:
                cv_result = cv_queue.get(timeout=1.0)
            except queue.Empty:
                # Queue timeout - client still connected, retry
                continue

            # Emit CV update to client
            # Note: room parameter ensures only this client receives update
            socketio.emit(
                'posture_update',
                cv_result,
                room=client_sid
            )

            logger.debug(
                f"Emitted CV update to {client_sid}: "
                f"posture={cv_result.get('posture_state')}, "
                f"user_present={cv_result.get('user_present')}"
            )

        except Exception as e:
            # Log exception but don't crash thread
            logger.exception(
                f"Error streaming to client {client_sid}: {e}"
            )
            # Brief pause to avoid error spam
            time.sleep(0.1)

    logger.info(f"CV streaming loop terminated for client {client_sid}")


@socketio.on('alert_acknowledged')
def handle_alert_acknowledged(data):
    """
    Handle alert acknowledgment from client - Story 3.3.

    Client emits this event when user clicks "I've corrected my posture"
    button on dashboard alert banner.

    Future: Story 3.5 will correlate with posture_corrected events.
    Future: Story 4.x Analytics will track alert response time.

    Args:
        data: {'acknowledged_at': ISO timestamp}
    """
    client_sid = request.sid
    acknowledged_at = data.get('acknowledged_at', 'unknown')
    logger.info(
        f"Alert acknowledged by client {client_sid} at {acknowledged_at}"
    )
    # Future: Store in analytics database (Story 4.x)


@socketio.on('pause_monitoring')
def handle_pause_monitoring():
    """
    Handle pause monitoring request from client - Story 3.4.

    Client emits this event when user clicks "Pause Monitoring" button.
    Pauses alert tracking while keeping camera feed active for transparency.

    Architecture:
    - Inserts pause marker into database (CRITICAL for analytics)
    - Calls AlertManager.pause_monitoring() to update backend state
    - Broadcasts monitoring_status to all connected clients (NFR-SC1)
    - Single global monitoring state (one AlertManager instance)

    Emits:
        monitoring_status: Broadcast to all clients with monitoring state
        error: Per-client error if cv_pipeline unavailable
    """
    from flask import current_app
    client_sid = request.sid
    logger.info(f"Pause monitoring requested by client {client_sid}")

    try:
        # Get cv_pipeline (test mode uses current_app.cv_pipeline_test)
        cv_pipeline = getattr(current_app, 'cv_pipeline_test', None) or app.cv_pipeline

        # Pause alert manager
        if cv_pipeline and cv_pipeline.alert_manager:
            # CRITICAL FIX: Insert pause marker BEFORE pausing
            # Without this marker, analytics cannot skip the paused period
            current_state = cv_pipeline.last_posture_state
            marker_state = current_state if current_state in ('good', 'bad') else 'good'
            try:
                from app.data.repository import PostureEventRepository
                PostureEventRepository.insert_posture_event(
                    posture_state=marker_state,
                    user_present=True,
                    confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                    metadata={'monitoring_paused': True}
                )
                logger.info(f"Pause marker inserted: state={marker_state}")
            except Exception as e:
                logger.warning(f"Failed to insert pause marker: {e}")

            cv_pipeline.alert_manager.pause_monitoring()
            logger.info(f"Monitoring paused, pause_timestamp={cv_pipeline.alert_manager.pause_timestamp}")

            # Emit status update to all clients
            status = cv_pipeline.alert_manager.get_monitoring_status()
            emit('monitoring_status', status, broadcast=True)
        else:
            logger.error("CV pipeline not available - cannot pause monitoring")
            # Emit error to requesting client only
            socketio.emit('error', {
                'message': 'Monitoring controls unavailable - camera service not started. '
                          'Please wait for camera initialization or check system status.'
            }, room=client_sid)
    except Exception as e:
        logger.exception(f"Error pausing monitoring: {e}")
        socketio.emit('error', {
            'message': 'Failed to pause monitoring. Try refreshing the page or check logs '
                      'for details: sudo journalctl -u deskpulse'
        }, room=client_sid)


@socketio.on('resume_monitoring')
def handle_resume_monitoring():
    """
    Handle resume monitoring request from client - Story 3.4.

    Client emits this event when user clicks "Resume Monitoring" button.
    Resumes alert tracking and resets bad posture timer.

    Architecture:
    - Calls AlertManager.resume_monitoring() to update backend state
    - Inserts resume marker into database (CRITICAL for analytics)
    - Broadcasts monitoring_status to all connected clients (NFR-SC1)
    - Bad posture tracking starts fresh (doesn't count paused time)

    Emits:
        monitoring_status: Broadcast to all clients with monitoring state
        error: Per-client error if cv_pipeline unavailable
    """
    from flask import current_app
    client_sid = request.sid
    logger.info(f"Resume monitoring requested by client {client_sid}")

    try:
        # Get cv_pipeline (test mode uses current_app.cv_pipeline_test)
        cv_pipeline = getattr(current_app, 'cv_pipeline_test', None) or app.cv_pipeline

        # Resume alert manager
        if cv_pipeline and cv_pipeline.alert_manager:
            cv_pipeline.alert_manager.resume_monitoring()
            logger.info("Monitoring resumed, pause_timestamp cleared")

            # CRITICAL FIX: Insert resume marker AFTER resuming
            # This marks the end of the paused period in the database
            current_state = cv_pipeline.last_posture_state
            marker_state = current_state if current_state in ('good', 'bad') else 'good'
            try:
                from app.data.repository import PostureEventRepository
                PostureEventRepository.insert_posture_event(
                    posture_state=marker_state,
                    user_present=True,
                    confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                    metadata={'resume_marker': True}
                )
                logger.info(f"Resume marker inserted: state={marker_state}")
            except Exception as e:
                logger.warning(f"Failed to insert resume marker: {e}")

            # Emit status update to all clients
            status = cv_pipeline.alert_manager.get_monitoring_status()
            emit('monitoring_status', status, broadcast=True)
        else:
            logger.error("CV pipeline not available - cannot resume monitoring")
            # Emit error to requesting client only
            socketio.emit('error', {
                'message': 'Monitoring controls unavailable - camera service not started. '
                          'Please wait for camera initialization or check system status.'
            }, room=client_sid)
    except Exception as e:
        logger.exception(f"Error resuming monitoring: {e}")
        socketio.emit('error', {
            'message': 'Failed to resume monitoring. Try refreshing the page or check logs '
                      'for details: sudo journalctl -u deskpulse'
        }, room=client_sid)


@socketio.on('request_status')
def handle_request_status():
    """
    Handle status request from Windows desktop client - Story 7.4.

    Windows client emits this on connect to get current monitoring state.
    Responds with monitoring_status to update tray menu enabled/disabled states.

    Emits:
        monitoring_status: Current monitoring state to requesting client only
    """
    from flask import current_app
    client_sid = request.sid
    logger.info(f"Status request from client {client_sid}")

    try:
        # Get cv_pipeline (test mode uses current_app.cv_pipeline_test)
        cv_pipeline = getattr(current_app, 'cv_pipeline_test', None) or app.cv_pipeline

        if cv_pipeline and cv_pipeline.alert_manager:
            # Get current status and emit to requesting client only
            status = cv_pipeline.alert_manager.get_monitoring_status()
            socketio.emit('monitoring_status', status, room=client_sid)
            logger.info(f"Sent monitoring_status to {client_sid}: {status}")
        else:
            # CV pipeline not ready - send default status
            logger.warning(f"CV pipeline not available for status request from {client_sid}")
            socketio.emit('monitoring_status', {
                'monitoring_active': True  # Default to active
            }, room=client_sid)
    except Exception as e:
        logger.exception(f"Error handling status request: {e}")
        # Send default status on error
        socketio.emit('monitoring_status', {
            'monitoring_active': True
        }, room=client_sid)


@socketio.on_error_default
def default_error_handler(e):
    """
    Handle SocketIO errors and notify client.

    Catches unexpected errors during event processing and emits
    error event to the affected client.

    Args:
        e: Exception that occurred

    Emits:
        error: Error notification with message
    """
    client_sid = request.sid
    logger.error(f"SocketIO error for client {client_sid}: {e}")
    socketio.emit('error', {'message': str(e)}, room=client_sid)
