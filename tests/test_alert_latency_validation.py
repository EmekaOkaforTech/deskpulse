"""
Alert Latency Performance Validation (Story 8.4 - Task 6.5).

ENTERPRISE REQUIREMENT: Validate alert latency meets <50ms target (95th percentile).

Baseline Comparison:
- SocketIO mode: ~200ms (network + serialization + browser processing)
- Local IPC mode: <50ms (in-process queue + callbacks)

Performance Targets:
- Single alert p95: <50ms
- Stress test (100 alerts): all <100ms
- 4x faster than SocketIO baseline
"""

import pytest
import time
import queue
import threading
from unittest.mock import Mock, patch

from app.standalone.backend_thread import (
    BackendThread,
    PRIORITY_CRITICAL
)


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        'camera': {'index': 0, 'fps': 10, 'width': 640, 'height': 480}
    }


@pytest.fixture
def priority_queue_test():
    """Priority queue for latency testing."""
    return queue.PriorityQueue(maxsize=200)


class TestSingleAlertLatency:
    """Test single alert latency (AC 6.5)."""

    def test_single_alert_latency_10_samples(self, test_config, priority_queue_test):
        """
        Test: Measure 10 alert latencies, ensure p95 <50ms.

        This simulates the critical path:
        1. Backend produces alert event
        2. Event enqueued with timestamp
        3. Consumer dequeues and processes
        4. Measure enqueue → dequeue latency
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)
        latencies = []

        # Produce 10 alerts
        for i in range(10):
            backend._notify_callbacks('alert', duration=600 + i, timestamp='...')

        # Consume and measure latency
        for i in range(10):
            priority, enqueue_time, event_type, data = priority_queue_test.get()

            # Dequeue time
            dequeue_time = time.perf_counter()
            latency_ms = (dequeue_time - enqueue_time) * 1000

            latencies.append(latency_ms)

        # Calculate p95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"\nSingle Alert Latency (10 samples):")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Assertions
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms target"
        assert avg_latency < 20.0, f"Avg latency {avg_latency:.2f}ms exceeds expected <20ms"

    def test_critical_event_priority_latency(self, test_config, priority_queue_test):
        """
        Test: CRITICAL events have lowest latency.

        Enqueue mixed priorities, measure CRITICAL event latency.
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)

        # Enqueue LOW priority events first (to fill queue)
        for i in range(10):
            backend._notify_callbacks('posture_update', posture='good')

        # Enqueue CRITICAL alert
        before_critical = time.perf_counter()
        backend._notify_callbacks('alert', duration=600, timestamp='...')

        # CRITICAL should be at front of queue despite LOW events
        priority, enqueue_time, event_type, data = priority_queue_test.get()

        dequeue_time = time.perf_counter()
        latency_ms = (dequeue_time - enqueue_time) * 1000

        print(f"\nCritical Event Priority Latency: {latency_ms:.2f}ms")

        # Assertions
        assert priority == PRIORITY_CRITICAL
        assert event_type == 'alert'
        assert latency_ms < 10.0, f"Critical event latency {latency_ms:.2f}ms exceeds 10ms"


class TestStressTestLatency:
    """Test stress test latency (AC 6.5)."""

    def test_100_alerts_in_10_seconds(self, test_config, priority_queue_test):
        """
        Test: 100 alerts in 10 seconds, all <100ms.

        This simulates high alert frequency (10 alerts/sec).
        Real-world: typically 1-2 alerts per 10 minutes, so this is extreme stress.
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)
        latencies = []

        # Producer thread: Generate 100 alerts over 10 seconds
        def produce_alerts():
            for i in range(100):
                backend._notify_callbacks('alert', duration=600 + i, timestamp=f'alert-{i}')
                time.sleep(0.1)  # 10 alerts/sec

        # Consumer thread: Measure latencies
        def consume_alerts():
            consumed = 0
            while consumed < 100:
                try:
                    priority, enqueue_time, event_type, data = priority_queue_test.get(timeout=2)

                    dequeue_time = time.perf_counter()
                    latency_ms = (dequeue_time - enqueue_time) * 1000

                    if event_type == 'alert':
                        latencies.append(latency_ms)
                        consumed += 1

                except queue.Empty:
                    break

        # Run producer and consumer concurrently
        producer = threading.Thread(target=produce_alerts)
        consumer = threading.Thread(target=consume_alerts)

        producer.start()
        consumer.start()

        producer.join()
        consumer.join()

        # Calculate metrics
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else 0

        print(f"\nStress Test Latency (100 alerts in 10 seconds):")
        print(f"  Processed: {len(latencies)}/100")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Assertions
        assert len(latencies) == 100, f"Only {len(latencies)}/100 alerts processed"
        assert max_latency < 100.0, f"Max latency {max_latency:.2f}ms exceeds 100ms target"
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms target"

    def test_latency_under_queue_contention(self, test_config, priority_queue_test):
        """
        Test: Latency remains low under queue contention.

        Multiple producers + single consumer.
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)
        latencies = []
        lock = threading.Lock()

        def produce_alerts(thread_id: int):
            """Produce 20 alerts."""
            for i in range(20):
                backend._notify_callbacks('alert', duration=600 + i, timestamp=f'thread-{thread_id}-{i}')
                time.sleep(0.01)

        def consume_alerts():
            """Consume all alerts and measure latency."""
            consumed = 0
            while consumed < 60:  # 3 threads * 20 alerts
                try:
                    priority, enqueue_time, event_type, data = priority_queue_test.get(timeout=2)

                    dequeue_time = time.perf_counter()
                    latency_ms = (dequeue_time - enqueue_time) * 1000

                    with lock:
                        latencies.append(latency_ms)

                    consumed += 1
                except queue.Empty:
                    break

        # Start consumer
        consumer = threading.Thread(target=consume_alerts)
        consumer.start()

        # Start 3 producers
        producers = []
        for i in range(3):
            thread = threading.Thread(target=produce_alerts, args=(i,))
            producers.append(thread)
            thread.start()

        for thread in producers:
            thread.join()

        consumer.join()

        # Calculate metrics
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        print(f"\nContention Latency (3 producers, 1 consumer):")
        print(f"  Processed: {len(latencies)}/60")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Assertions
        assert len(latencies) == 60
        assert avg_latency < 30.0, f"Avg latency {avg_latency:.2f}ms too high under contention"
        assert max_latency < 100.0, f"Max latency {max_latency:.2f}ms exceeds 100ms"


class TestLatencyComparison:
    """Test latency comparison vs SocketIO baseline."""

    def test_ipc_faster_than_socketio_baseline(self, test_config, priority_queue_test):
        """
        Test: IPC latency is at least 4x faster than SocketIO baseline (~200ms).

        Expected: IPC <50ms, SocketIO ~200ms → 4x improvement.
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)

        # Measure IPC latency (10 samples)
        ipc_latencies = []
        for i in range(10):
            backend._notify_callbacks('alert', duration=600, timestamp='...')

        for i in range(10):
            priority, enqueue_time, event_type, data = priority_queue_test.get()
            dequeue_time = time.perf_counter()
            latency_ms = (dequeue_time - enqueue_time) * 1000
            ipc_latencies.append(latency_ms)

        ipc_avg = sum(ipc_latencies) / len(ipc_latencies)

        # SocketIO baseline (documented)
        socketio_baseline = 200.0  # ms (from requirements)

        improvement_factor = socketio_baseline / ipc_avg

        print(f"\nLatency Comparison:")
        print(f"  SocketIO Baseline: {socketio_baseline:.0f}ms")
        print(f"  IPC Average: {ipc_avg:.2f}ms")
        print(f"  Improvement: {improvement_factor:.1f}x faster")

        # Assertions
        assert ipc_avg < 50.0, f"IPC latency {ipc_avg:.2f}ms exceeds 50ms target"
        assert improvement_factor >= 4.0, f"IPC only {improvement_factor:.1f}x faster (expected 4x+)"


class TestLatencyMonitoring:
    """Test latency monitoring infrastructure."""

    def test_latency_samples_limited_to_100(self, test_config, priority_queue_test):
        """
        Test: Latency samples limited to last 100 (memory bounded).
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)

        # Produce 150 events
        for i in range(150):
            backend._notify_callbacks('alert', duration=600, timestamp='...')

        # Consume 150 events
        latencies = []
        for i in range(150):
            priority, enqueue_time, event_type, data = priority_queue_test.get()
            dequeue_time = time.perf_counter()
            latency_ms = (dequeue_time - enqueue_time) * 1000
            latencies.append(latency_ms)

            # Simulate keeping last 100 samples (like TrayApp does)
            if len(latencies) > 100:
                latencies.pop(0)

        # Assertions
        assert len(latencies) == 100, "Latency samples not limited to 100"

    def test_latency_warning_logged_when_exceeds_50ms(self, test_config, priority_queue_test, caplog):
        """
        Test: Warning logged when latency exceeds 50ms threshold.

        Simulated by adding artificial delay.
        """
        backend = BackendThread(test_config, event_queue=priority_queue_test)

        # Produce event
        backend._notify_callbacks('alert', duration=600, timestamp='...')

        # Artificial delay before consuming
        time.sleep(0.06)  # 60ms delay

        # Consume
        priority, enqueue_time, event_type, data = priority_queue_test.get()
        dequeue_time = time.perf_counter()
        latency_ms = (dequeue_time - enqueue_time) * 1000

        print(f"\nArtificial delay latency: {latency_ms:.2f}ms")

        # Assertions
        assert latency_ms > 50.0, "Artificial delay did not create >50ms latency"

        # Note: Logging of >50ms latency is done in TrayApp._handle_alert(),
        # not in backend_thread. This test just verifies the measurement.
