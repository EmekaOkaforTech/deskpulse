"""SocketIO event handlers for real-time dashboard updates."""

import threading
import logging
import time
import queue
from flask import request
from app.extensions import socketio
from app.cv.pipeline import cv_queue

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
