#!/usr/bin/env python3
"""Verify multi-resolution .ico file."""

from PIL import Image

icon_path = 'assets/windows/icon.ico'

try:
    img = Image.open(icon_path)

    print(f"✅ Icon file opened successfully: {icon_path}")
    print(f"Format: {img.format}")
    print(f"Mode: {img.mode}")
    print(f"Size: {img.size}")

    # ICO files contain multiple images
    # Try to load all frames
    if hasattr(img, 'n_frames'):
        print(f"Frames: {img.n_frames}")

    # Get all sizes if available
    if hasattr(img, 'info') and 'sizes' in img.info:
        print(f"Available sizes: {img.info['sizes']}")

    print("\n✅ Icon verification complete")

except Exception as e:
    print(f"❌ Error verifying icon: {e}")
    exit(1)
