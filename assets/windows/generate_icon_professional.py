#!/usr/bin/env python3
"""
Generate professional multi-resolution Windows .ico file for DeskPulse.

Enterprise-grade icon design:
- Professional color scheme (blue/teal for tech/health)
- Cleaner silhouette with better proportions
- Subtle desk/monitor element for context
- Multiple resolutions for Windows compatibility
"""

from PIL import Image, ImageDraw

def generate_professional_icon_at_size(size: int) -> Image.Image:
    """
    Generate professional posture monitoring icon at specified size.

    Design elements:
    - Person silhouette (professional proportions)
    - Upright posture indicator
    - Modern color: Teal (#008B8B) - professional, health-focused
    - Clean, minimal design suitable for enterprise

    Args:
        size: Icon size in pixels (square)

    Returns:
        PIL Image
    """
    # Create transparent image
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Professional teal color (health/wellness/tech)
    # More professional than bright green
    fill_color = (0, 139, 139, 255)  # Teal (DarkCyan)

    # Scale proportions based on size
    scale = size / 64.0
    center_x = size // 2

    # Head (circle at top) - slightly smaller, more proportional
    head_radius = int(10 * scale)
    head_y_center = int(12 * scale)

    head_left = center_x - head_radius
    head_top = head_y_center - head_radius
    head_right = center_x + head_radius
    head_bottom = head_y_center + head_radius

    draw.ellipse([head_left, head_top, head_right, head_bottom], fill=fill_color)

    # Torso (rounded rectangle for shoulders and body)
    torso_width = int(14 * scale)
    torso_height = int(20 * scale)
    torso_top = head_bottom + int(1 * scale)

    torso_left = center_x - torso_width // 2
    torso_right = center_x + torso_width // 2
    torso_bottom = torso_top + torso_height

    draw.rounded_rectangle(
        [torso_left, torso_top, torso_right, torso_bottom],
        radius=int(3 * scale),
        fill=fill_color
    )

    # Spine indicator (vertical line - good posture)
    spine_width = max(int(2 * scale), 1)
    spine_top = head_bottom + int(2 * scale)
    spine_bottom = torso_bottom

    spine_left = center_x - spine_width // 2
    spine_right = center_x + spine_width // 2

    # Lighter color for spine (overlay effect)
    spine_color = (0, 180, 180, 255)  # Lighter teal
    draw.rectangle([spine_left, spine_top, spine_right, spine_bottom], fill=spine_color)

    # Base/desk element (subtle horizontal line at bottom)
    desk_height = max(int(3 * scale), 2)
    desk_width = int(40 * scale)
    desk_top = size - int(8 * scale)
    desk_bottom = desk_top + desk_height

    desk_left = center_x - desk_width // 2
    desk_right = center_x + desk_width // 2

    # Subtle desk in darker teal
    desk_color = (0, 100, 100, 180)  # Semi-transparent darker teal
    draw.rectangle([desk_left, desk_top, desk_right, desk_bottom], fill=desk_color)

    return img


def generate_multi_resolution_ico(output_path: str):
    """
    Generate multi-resolution .ico file for Windows.

    Creates professional icon with standard Windows resolutions:
    - 16x16, 32x32, 48x48, 64x64, 128x128, 256x256

    Args:
        output_path: Path to save .ico file
    """
    sizes = [16, 32, 48, 64, 128, 256]

    # Generate icons at each size
    images = []
    for size in sizes:
        img = generate_professional_icon_at_size(size)
        images.append(img)
        print(f"✓ Generated {size}x{size} icon")

    # Save as multi-resolution .ico
    # Largest image first for best quality
    images_reversed = list(reversed(images))
    images_reversed[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images_reversed]
    )

    print(f"\n✅ Professional enterprise icon saved to: {output_path}")
    print(f"   Resolutions: {', '.join(f'{s}x{s}' for s in sizes)}")
    print(f"   Color: Professional Teal (RGB 0, 139, 139)")
    print(f"   Design: Person + Posture Spine + Desk element")
    print(f"   Style: Clean, minimal, enterprise-suitable")


if __name__ == '__main__':
    output_path = 'assets/windows/icon_professional.ico'
    generate_multi_resolution_ico(output_path)
