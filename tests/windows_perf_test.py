"""
30-minute Windows stability test for Story 8.3.

Monitors camera capture performance:
- Memory usage (target: <270 MB, +7% of Story 8.1 baseline 251.8 MB)
- CPU usage (target: <40%, +13% of Story 8.1 baseline 35.2%)
- Crashes (target: 0)
- Memory leaks (target: none)

Story 8.1 Windows Baseline (Build 26200.7462):
- Max Memory: 251.8 MB
- Avg Memory: 249.6 MB
- Avg CPU: 35.2%
- Crashes: 0
- Memory Leak: None
"""

import time
import psutil
import sys
import argparse
from datetime import datetime
from app.standalone.camera_windows import WindowsCamera

# Test configuration
DEFAULT_DURATION_MINUTES = 30
SAMPLE_INTERVAL_SECONDS = 5
TARGET_MAX_MEMORY_MB = 270  # +7% of 251.8 MB baseline
TARGET_AVG_CPU_PERCENT = 40  # +13% of 35.2% baseline

# Baseline reference (Story 8.1)
BASELINE_MAX_MEMORY_MB = 251.8
BASELINE_AVG_CPU_PERCENT = 35.2

def get_memory_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)

def get_cpu_percent():
    """Get current process CPU usage percentage."""
    process = psutil.Process()
    return process.cpu_percent(interval=1)

def main():
    parser = argparse.ArgumentParser(description='Story 8.3 Windows stability test')
    parser.add_argument('--duration', type=int, default=DEFAULT_DURATION_MINUTES * 60,
                        help=f'Test duration in seconds (default: {DEFAULT_DURATION_MINUTES * 60}s = 30min)')
    args = parser.parse_args()

    test_duration_minutes = args.duration / 60

    print("=" * 60)
    print("Story 8.3 - Windows Camera Stability Test")
    print("=" * 60)
    print()
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {test_duration_minutes:.1f} minutes")
    print(f"Sample interval: {SAMPLE_INTERVAL_SECONDS} seconds")
    print()
    print("Story 8.1 Windows Baseline:")
    print(f"  Max Memory: {BASELINE_MAX_MEMORY_MB} MB")
    print(f"  Avg CPU: {BASELINE_AVG_CPU_PERCENT}%")
    print()
    print("Story 8.3 Targets:")
    print(f"  Max Memory: <{TARGET_MAX_MEMORY_MB} MB (+7%)")
    print(f"  Avg CPU: <{TARGET_AVG_CPU_PERCENT}% (+13%)")
    print()
    print("=" * 60)
    print()

    # Open camera
    print("Opening camera...")
    camera = WindowsCamera(camera_index=0)
    if not camera.open():
        print("ERROR: Failed to open camera")
        return 1

    print(f"Camera opened successfully")
    print()

    # Performance tracking
    memory_samples = []
    cpu_samples = []
    errors = []
    start_time = time.time()
    end_time = start_time + args.duration
    last_report_time = start_time
    frame_count = 0

    print("Starting capture loop...")
    print()

    try:
        while time.time() < end_time:
            # Read frame
            ret, frame = camera.read()
            if not ret:
                errors.append(f"Frame read failed at {time.time() - start_time:.1f}s")
                continue

            frame_count += 1

            # Collect performance metrics every SAMPLE_INTERVAL_SECONDS
            if time.time() - last_report_time >= SAMPLE_INTERVAL_SECONDS:
                memory_mb = get_memory_mb()
                cpu_percent = get_cpu_percent()

                memory_samples.append(memory_mb)
                cpu_samples.append(cpu_percent)

                elapsed_minutes = (time.time() - start_time) / 60
                remaining_minutes = (end_time - time.time()) / 60

                print(f"[{elapsed_minutes:5.1f}m] Memory: {memory_mb:6.1f} MB | CPU: {cpu_percent:5.1f}% | Frames: {frame_count:6d} | Remaining: {remaining_minutes:4.1f}m")

                last_report_time = time.time()

    except KeyboardInterrupt:
        print()
        print("Test interrupted by user")
        return 1
    except Exception as e:
        print()
        print(f"ERROR: {e}")
        errors.append(str(e))
        return 1
    finally:
        camera.release()

    # Calculate statistics
    print()
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print()

    max_memory = max(memory_samples) if memory_samples else 0
    avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
    avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0

    # Memory leak detection (compare first 5 minutes vs last 5 minutes)
    first_5min_samples = memory_samples[:60]  # First 60 samples (5 minutes)
    last_5min_samples = memory_samples[-60:]   # Last 60 samples (5 minutes)

    avg_first_5min = sum(first_5min_samples) / len(first_5min_samples) if first_5min_samples else 0
    avg_last_5min = sum(last_5min_samples) / len(last_5min_samples) if last_5min_samples else 0
    memory_growth = avg_last_5min - avg_first_5min
    memory_growth_percent = (memory_growth / avg_first_5min * 100) if avg_first_5min > 0 else 0

    print(f"Duration: {test_duration_minutes:.1f} minutes")
    print(f"Frames captured: {frame_count}")
    print(f"Errors: {len(errors)}")
    print()
    print("Memory Usage:")
    print(f"  Max: {max_memory:.1f} MB (baseline: {BASELINE_MAX_MEMORY_MB} MB, target: <{TARGET_MAX_MEMORY_MB} MB)")
    print(f"  Avg: {avg_memory:.1f} MB")
    print(f"  First 5min avg: {avg_first_5min:.1f} MB")
    print(f"  Last 5min avg: {avg_last_5min:.1f} MB")
    print(f"  Growth: {memory_growth:+.1f} MB ({memory_growth_percent:+.1f}%)")
    print()
    print("CPU Usage:")
    print(f"  Avg: {avg_cpu:.1f}% (baseline: {BASELINE_AVG_CPU_PERCENT}%, target: <{TARGET_AVG_CPU_PERCENT}%)")
    print()

    # Pass/fail assessment
    passed = True
    print("Assessment:")

    if max_memory > TARGET_MAX_MEMORY_MB:
        print(f"  ❌ FAIL: Max memory {max_memory:.1f} MB exceeds target {TARGET_MAX_MEMORY_MB} MB")
        passed = False
    else:
        print(f"  ✅ PASS: Max memory {max_memory:.1f} MB within target {TARGET_MAX_MEMORY_MB} MB")

    if avg_cpu > TARGET_AVG_CPU_PERCENT:
        print(f"  ❌ FAIL: Avg CPU {avg_cpu:.1f}% exceeds target {TARGET_AVG_CPU_PERCENT}%")
        passed = False
    else:
        print(f"  ✅ PASS: Avg CPU {avg_cpu:.1f}% within target {TARGET_AVG_CPU_PERCENT}%")

    if errors:
        print(f"  ❌ FAIL: {len(errors)} errors occurred")
        passed = False
    else:
        print(f"  ✅ PASS: No errors")

    if memory_growth_percent > 5.0:
        print(f"  ⚠️  WARNING: Memory growth {memory_growth_percent:+.1f}% exceeds 5% threshold (possible leak)")
    elif memory_growth_percent > 0:
        print(f"  ✅ PASS: Memory growth {memory_growth_percent:+.1f}% within acceptable range")
    else:
        print(f"  ✅ PASS: No memory growth detected")

    print()
    print("=" * 60)

    if passed:
        print("✅ STABILITY TEST PASSED")
        print()
        print("Story 8.3 meets performance requirements:")
        print(f"  Memory: {max_memory:.1f} MB < {TARGET_MAX_MEMORY_MB} MB ✓")
        print(f"  CPU: {avg_cpu:.1f}% < {TARGET_AVG_CPU_PERCENT}% ✓")
        print(f"  Crashes: 0 ✓")
        return 0
    else:
        print("❌ STABILITY TEST FAILED")
        print()
        print("Performance targets not met. Review results above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
