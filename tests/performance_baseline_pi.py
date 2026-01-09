#!/usr/bin/env python3
"""
Performance Baseline Test for Raspberry Pi (Story 8.2)

Tests MediaPipe Tasks API performance on Raspberry Pi 4.
Captures: Memory, CPU, FPS, crashes over extended period.

Usage:
    python tests/performance_baseline_pi.py --duration 300   # 5 minutes
    python tests/performance_baseline_pi.py --duration 1800  # 30 minutes
"""

import argparse
import time
import psutil
import os
import signal
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_baseline_test(duration_seconds=300):
    """
    Run performance baseline test.

    Args:
        duration_seconds: Test duration (default 300s = 5 minutes)
    """
    print("=" * 70)
    print(f"PERFORMANCE BASELINE TEST - Raspberry Pi")
    print(f"Story 8.2: MediaPipe Tasks API (0.10.18)")
    print("=" * 70)
    print(f"Duration: {duration_seconds}s ({duration_seconds//60} minutes)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Import here to get accurate startup time
    print("Importing dependencies...")
    import_start = time.time()

    from app import create_app
    from app.cv.detection import PoseDetector
    from app.cv.classification import PostureClassifier
    import numpy as np
    import cv2

    import_time = time.time() - import_start
    print(f"✅ Imports completed in {import_time:.2f}s")
    print()

    # Create Flask app
    print("Creating Flask app...")
    app = create_app(config_name='testing')

    # Initialize CV components
    print("Initializing CV components...")
    init_start = time.time()

    with app.app_context():
        detector = PoseDetector(app=app)
        classifier = PostureClassifier(app=app)

    init_time = time.time() - init_start
    print(f"✅ CV components initialized in {init_time:.2f}s")
    print()

    # Get process for monitoring
    process = psutil.Process(os.getpid())

    # Metrics collection
    memory_samples = []
    cpu_samples = []
    frame_times = []
    crash_count = 0
    frame_count = 0

    # Create synthetic test frame (640x480 BGR)
    test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

    # Draw simple stick figure for detection
    cv2.circle(test_frame, (320, 100), 20, (0, 0, 0), -1)  # Head
    cv2.line(test_frame, (320, 120), (320, 300), (0, 0, 0), 5)  # Torso
    cv2.line(test_frame, (320, 150), (250, 200), (0, 0, 0), 5)  # Left arm
    cv2.line(test_frame, (320, 150), (390, 200), (0, 0, 0), 5)  # Right arm
    cv2.line(test_frame, (320, 300), (280, 450), (0, 0, 0), 5)  # Left leg
    cv2.line(test_frame, (320, 300), (360, 450), (0, 0, 0), 5)  # Right leg

    print(f"Running performance test for {duration_seconds}s...")
    print(f"Target: 10 FPS = {duration_seconds * 10} frames")
    print()
    print("Metrics captured every second:")
    print("  - Memory (RSS): Resident Set Size")
    print("  - CPU (%): Per-core average")
    print("  - FPS: Frames processed per second")
    print()

    start_time = time.time()
    end_time = start_time + duration_seconds
    last_report = start_time

    try:
        while time.time() < end_time:
            frame_start = time.time()

            # Process frame
            with app.app_context():
                try:
                    detection_result = detector.detect_landmarks(test_frame)

                    if detection_result['user_present']:
                        posture = classifier.classify_posture(detection_result['landmarks'])

                    frame_count += 1

                except Exception as e:
                    crash_count += 1
                    print(f"❌ Frame processing error: {e}")

            frame_time = time.time() - frame_start
            frame_times.append(frame_time)

            # Capture metrics every second
            current_time = time.time()
            if current_time - last_report >= 1.0:
                # Memory (MB)
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / 1024 / 1024
                memory_samples.append(memory_mb)

                # CPU (%)
                cpu_percent = process.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)

                # FPS
                elapsed = current_time - start_time
                current_fps = frame_count / elapsed if elapsed > 0 else 0

                # Report
                print(f"[{int(elapsed):4d}s] "
                      f"Memory: {memory_mb:6.1f} MB | "
                      f"CPU: {cpu_percent:5.1f}% | "
                      f"FPS: {current_fps:5.2f} | "
                      f"Frames: {frame_count:5d} | "
                      f"Crashes: {crash_count}")

                last_report = current_time

            # Sleep to maintain ~10 FPS
            sleep_time = (1.0 / 10.0) - frame_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")

    finally:
        # Cleanup
        with app.app_context():
            detector.close()

    # Calculate final statistics
    total_time = time.time() - start_time

    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)

    if memory_samples:
        print(f"Memory (RSS):")
        print(f"  - Min:     {min(memory_samples):6.1f} MB")
        print(f"  - Max:     {max(memory_samples):6.1f} MB")
        print(f"  - Average: {sum(memory_samples)/len(memory_samples):6.1f} MB")
        print(f"  - Samples: {len(memory_samples)}")

    print()
    if cpu_samples:
        print(f"CPU Usage:")
        print(f"  - Min:     {min(cpu_samples):5.1f}%")
        print(f"  - Max:     {max(cpu_samples):5.1f}%")
        print(f"  - Average: {sum(cpu_samples)/len(cpu_samples):5.1f}%")
        print(f"  - Samples: {len(cpu_samples)}")

    print()
    print(f"Frame Processing:")
    print(f"  - Total frames:   {frame_count}")
    print(f"  - Total time:     {total_time:.1f}s")
    print(f"  - Average FPS:    {frame_count/total_time:.2f}")
    print(f"  - Target FPS:     10.00")
    print(f"  - Crashes/Errors: {crash_count}")

    if frame_times:
        avg_frame_time = sum(frame_times) / len(frame_times)
        print(f"  - Avg frame time: {avg_frame_time*1000:.1f}ms")

    print()
    print(f"Test Duration: {total_time:.1f}s (target: {duration_seconds}s)")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Return results for further processing
    return {
        'duration': total_time,
        'frames': frame_count,
        'crashes': crash_count,
        'memory': {
            'min': min(memory_samples) if memory_samples else 0,
            'max': max(memory_samples) if memory_samples else 0,
            'avg': sum(memory_samples)/len(memory_samples) if memory_samples else 0,
        },
        'cpu': {
            'min': min(cpu_samples) if cpu_samples else 0,
            'max': max(cpu_samples) if cpu_samples else 0,
            'avg': sum(cpu_samples)/len(cpu_samples) if cpu_samples else 0,
        },
        'fps': frame_count / total_time if total_time > 0 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description='Performance baseline test for Story 8.2')
    parser.add_argument('--duration', type=int, default=300,
                        help='Test duration in seconds (default: 300 = 5 minutes)')
    args = parser.parse_args()

    # Validate duration
    if args.duration < 60:
        print("❌ Error: Duration must be at least 60 seconds")
        sys.exit(1)

    if args.duration > 3600:
        print("⚠️  Warning: Duration > 1 hour may take very long")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Test cancelled")
            sys.exit(0)

    # Run test
    results = run_baseline_test(args.duration)

    # Determine pass/fail
    print()
    print("VALIDATION:")

    passed = True

    # Check for crashes
    if results['crashes'] > 0:
        print(f"❌ FAIL: {results['crashes']} crashes detected")
        passed = False
    else:
        print(f"✅ PASS: 0 crashes")

    # Check FPS (should be close to 10)
    if results['fps'] < 8.0:
        print(f"⚠️  WARN: FPS {results['fps']:.2f} below target (10.0)")
    else:
        print(f"✅ PASS: FPS {results['fps']:.2f} acceptable")

    # Check memory (should be stable, not continuously growing)
    if results['memory']['max'] > 0:
        mem_range = results['memory']['max'] - results['memory']['min']
        if mem_range > 100:  # More than 100MB variation
            print(f"⚠️  WARN: Memory variation {mem_range:.1f} MB (possible leak)")
        else:
            print(f"✅ PASS: Memory stable (range: {mem_range:.1f} MB)")

    print()
    if passed:
        print("✅ BASELINE TEST PASSED")
        return 0
    else:
        print("❌ BASELINE TEST FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
