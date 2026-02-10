from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

def process_logo(input_path, output_path, new_color=(0, 122, 255), size=(200, 200), 
                 threshold=240, enhance_quality=True, upscale_factor=2):
    """
    Process a logo by removing white background, resizing, changing color, and enhancing quality.
    
    Parameters:
    - input_path: Path to the input image
    - output_path: Path to save the processed image
    - new_color: RGB tuple for the new logo color (default: blue)
    - size: Target size as (width, height) tuple
    - threshold: Brightness threshold for background removal (0-255)
    - enhance_quality: Apply quality enhancement techniques
    - upscale_factor: Internal upscale multiplier for better quality (2-4 recommended)
    """
    
    # Open the image
    img = Image.open(input_path)
    
    # Store original size for comparison
    original_size = img.size
    
    # If enhance_quality is True, upscale the image first for better processing
    if enhance_quality and upscale_factor > 1:
        new_width = img.width * upscale_factor
        new_height = img.height * upscale_factor
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"✓ Upscaled from {original_size} to {img.size} for better quality")
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Enhance sharpness slightly
    if enhance_quality:
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
    
    # Convert to numpy array for processing
    data = np.array(img)
    
    # Calculate luminance (brightness) to use as alpha mask
    # Standard luminance formula: 0.299R + 0.587G + 0.114B
    luminance = (data[:,:,0] * 0.299 + data[:,:,1] * 0.587 + data[:,:,2] * 0.114)
    
    # Create alpha channel based on "darkness"
    # Darker pixels = higher alpha (more opaque)
    # Lighter pixels = lower alpha (more transparent)
    # Map range [0, 255] -> [255, 0]
    
    # We want white (255) to be transparent (0)
    # We want black (0) to be opaque (255)
    # But we want a "cutoff" point (threshold) where it becomes fully transparent
    
    # Soft thresholding logic
    # Everything above 'threshold' fades to 0
    # Everything below 'threshold' is scaled
    
    # Normalize luminance relative to threshold
    # Pixels brighter than threshold become 0 alpha
    # Pixels darker than threshold get alpha scaled from 0-255
    
    alpha_mask = np.zeros_like(luminance)
    
    # Soft edges: calculate distance from threshold
    # This creates a gradient instead of a hard cut
    mask_indices = luminance < threshold
    
    # To get crisp but smooth edges, we map the luminance range [0, threshold] to alpha [255, 0]
    # But maybe we just want to replace the color and keep existing anti-aliasing if the image was already transparent?
    
    # IMPROVED APPROACH: Use the luminance invserse as the new alpha
    # This preserves the "softness" of the edges from the original anti-aliasing (if it existed) or creates soft edges from greyscale
    
    # Scale alpha: (threshold - luminance) / threshold * 255
    # This makes pure black (0) -> 255 alpha
    # This makes threshold value -> 0 alpha
    
    alpha_mask[mask_indices] = ((threshold - luminance[mask_indices]) / threshold) * 255
    
    # Create new image data
    new_data = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
    
    # Set RGB to new_color
    new_data[:,:,0] = new_color[0]
    new_data[:,:,1] = new_color[1]
    new_data[:,:,2] = new_color[2]
    
    # Set Alpha
    new_data[:,:,3] = alpha_mask.astype(np.uint8)
    
    # Power curve to sharpen the edges while keeping them smooth (gamma correction-ish)
    # This pushes semi-transparent pixels towards either 0 or 255 to reduce "fuzziness" while keeping AA
    # However, for simple logo recoloring, the linear gradient above might be too soft.
    # Let's simple apply a sigmoid-like curve or just rely on the high-res downsample.
    
    # Convert back to image
    processed_img = Image.fromarray(new_data, 'RGBA')
    
    # Apply slight blur to smooth edges (anti-aliasing effect)
    if enhance_quality:
        # Extract alpha channel
        alpha = processed_img.split()[3]
        # Smooth the alpha channel edges
        alpha_smooth = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
        # Put it back
        processed_img.putalpha(alpha_smooth)
    
    # Crop to content (remove extra whitespace)
    bbox = processed_img.getbbox()
    if bbox:
        # Add small padding
        padding = 10 if enhance_quality else 5
        bbox = (
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(processed_img.width, bbox[2] + padding),
            min(processed_img.height, bbox[3] + padding)
        )
        processed_img = processed_img.crop(bbox)
    
    # Calculate final size maintaining aspect ratio
    img_ratio = processed_img.width / processed_img.height
    target_width, target_height = size
    
    if img_ratio > 1:  # Width > Height
        final_width = target_width
        final_height = int(target_width / img_ratio)
    else:  # Height >= Width
        final_height = target_height
        final_width = int(target_height * img_ratio)
    
    # Resize with high-quality resampling
    processed_img = processed_img.resize(
        (final_width, final_height), 
        Image.Resampling.LANCZOS
    )
    
    # Final sharpening pass for crisp edges
    if enhance_quality:
        enhancer = ImageEnhance.Sharpness(processed_img)
        processed_img = enhancer.enhance(1.3)
    
    # Save the result with maximum quality
    processed_img.save(output_path, 'PNG', optimize=False, compress_level=1)
    
    print(f"✓ Logo processed successfully!")
    print(f"✓ Saved to: {output_path}")
    print(f"✓ Final size: {processed_img.size}")
    print(f"✓ Quality enhancement: {'Enabled' if enhance_quality else 'Disabled'}")

# Example usage
if __name__ == "__main__":
    import argparse
    
    # Color options
    COLOR_BLUE = (0, 122, 255)
    COLOR_GREEN = (52, 199, 89)
    COLOR_PURPLE = (175, 82, 222)
    COLOR_RED = (255, 59, 48)
    COLOR_ORANGE = (255, 149, 0)
    COLOR_BLACK = (0, 0, 0)
    COLOR_TEAL = (48, 176, 199)
    COLOR_PINK = (255, 45, 85)
    COLOR_WHITE = (255, 255, 255)
    
    COLORS = {
        'blue': COLOR_BLUE,
        'green': COLOR_GREEN,
        'purple': COLOR_PURPLE,
        'red': COLOR_RED,
        'orange': COLOR_ORANGE,
        'black': COLOR_BLACK,
        'teal': COLOR_TEAL,
        'pink': COLOR_PINK,
        'white': COLOR_WHITE
    }
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process logo: remove background, resize, change color, and enhance quality')
    parser.add_argument('input', help='Input image file path')
    parser.add_argument('output', help='Output image file path')
    parser.add_argument('-c', '--color', default='blue', 
                        choices=list(COLORS.keys()),
                        help='Logo color (default: blue)')
    parser.add_argument('-s', '--size', type=int, default=300,
                        help='Maximum width/height in pixels (default: 300)')
    parser.add_argument('-t', '--threshold', type=int, default=240,
                        help='Background removal threshold 0-255 (default: 240)')
    parser.add_argument('--rgb', type=int, nargs=3, metavar=('R', 'G', 'B'),
                        help='Custom RGB color (e.g., --rgb 255 100 50)')
    parser.add_argument('--no-enhance', action='store_true',
                        help='Disable quality enhancement')
    parser.add_argument('-u', '--upscale', type=int, default=2,
                        help='Upscale factor for quality enhancement (default: 2)')
    
    args = parser.parse_args()
    
    # Determine color
    if args.rgb:
        selected_color = tuple(args.rgb)
    else:
        selected_color = COLORS[args.color]
    
    # Process the logo
    process_logo(
        input_path=args.input,
        output_path=args.output,
        new_color=selected_color,
        size=(args.size, args.size),
        threshold=args.threshold,
        enhance_quality=not args.no_enhance,
        upscale_factor=args.upscale
    )