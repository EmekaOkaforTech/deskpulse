#!/bin/bash
# DeskPulse Startup Script
# Suppresses C++ library warnings from TensorFlow/MediaPipe on ARM processors
# These warnings are harmless but create poor user experience

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Environment variables to suppress warnings
export TF_CPP_MIN_LOG_LEVEL=3
export TF_ENABLE_ONEDNN_OPTS=0
export MEDIAPIPE_DISABLE_GPU=1
export GLOG_minloglevel=3
export GRPC_VERBOSITY=ERROR

# Start DeskPulse with stderr filtered to remove C++ warnings
# Only show lines that don't match the known harmless warning patterns
python run.py 2>&1 | grep -v \
    -e "Error in cpuinfo" \
    -e "prctl(PR_SVE" \
    -e "XNNPACK delegate" \
    -e "inference_feedback_manager" \
    -e "absl::InitializeLog" \
    -e "^W0000"
