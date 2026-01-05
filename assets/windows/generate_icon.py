#!/usr/bin/env python3
"""
Generate multi-resolution Windows .ico file for DeskPulse application.

Creates icon matching the system tray design:
- Green person silhouette with spine
- Multiple resolutions for Windows compatibility
"""

from PIL import Image, ImageDraw


def generate_icon_at_size(size: int) -> Image.Image:
    """
    Generate posture icon at specified size.

    Args:
        size: Icon size in pixels (square)

    Returns:
        PIL Image
    """
    # Create transparent image
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Green color (connected state from TrayManager)
    fill_color = (0, 200, 0, 255)

    # Scale proportions based on size
    # Original 64x64 design:
    #   Head: [20, 8, 44, 32] = width 24, height 24, x_center 32, y_top 8
    #   Spine: [30, 32, 34, 56] = width 4, height 24, x_center 32

    # Calculate scaled dimensions
    scale = size / 64.0

    # Head (circle at top)
    head_width = int(24 * scale)
    head_height = int(24 * scale)
    head_x_center = size // 2
    head_y_top = int(8 * scale)

    head_left = head_x_center - head_width // 2
    head_top = head_y_top
    head_right = head_left + head_width
    head_bottom = head_top + head_height

    draw.ellipse([head_left, head_top, head_right, head_bottom], fill=fill_color)

    # Spine (vertical rectangle)
    spine_width = max(int(4 * scale), 2)  # Minimum 2 pixels wide
    spine_height = int(24 * scale)
    spine_x_center = size // 2
    spine_y_top = head_bottom

    spine_left = spine_x_center - spine_width // 2
    spine_top = spine_y_top
    spine_right = spine_left + spine_width
    spine_bottom = spine_top + spine_height

    draw.rectangle([spine_left, spine_top, spine_right, spine_bottom], fill=fill_color)

    return img


def generate_multi_resolution_ico(output_path: str):
    """
    Generate multi-resolution .ico file.

    Creates icon with standard Windows resolutions:
    - 16x16, 32x32, 48x48, 64x64, 128x128, 256x256

    Args:
        output_path: Path to save .ico file
    """
    sizes = [16, 32, 48, 64, 128, 256]

    # Generate icons at each size
    images = []
    for size in sizes:
        img = generate_icon_at_size(size)
        images.append(img)
        print(f"Generated {size}x{size} icon")

    # Save as multi-resolution .ico
    # PIL/Pillow supports multiple resolutions when saving ICO
    # The largest image should be first for best quality
    images_reversed = list(reversed(images))  # Start with 256x256
    images_reversed[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images_reversed]
    )

    print(f"\n✅ Multi-resolution icon saved to: {output_path}")
    print(f"   Resolutions: {', '.join(f'{s}x{s}' for s in sizes)}")
    print(f"   Color: Green (RGB 0, 200, 0)")
    print(f"   Design: Head + Spine posture icon")


if __name__ == '__main__':
    output_path = 'assets/windows/icon.ico'
    generate_multi_resolution_ico(output_path)
