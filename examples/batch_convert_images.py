#!/usr/bin/env python3
"""
Example: Batch convert multiple image formats for storage optimization.

This example demonstrates how to convert multiple images between formats,
which is useful for:
- Storage optimization (PNG to JPEG, high quality to lower quality)
- Format compatibility across devices
- Web optimization (large images to web-friendly formats)
- Batch processing workflows
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict

def convert_image(input_path: str, output_path: str, quality: int = 80,
                 resize: Tuple[int, int] = None, **kwargs) -> bool:
    """
    Convert a single image to a different format.

    Args:
        input_path: Path to input image
        output_path: Path to output image
        quality: JPEG/WebP quality (1-100, higher = better quality)
        resize: Optional (width, height) tuple for resizing
        **kwargs: Additional FFmpeg options

    Returns:
        True if conversion successful, False otherwise
    """
    ffmpeg = FFmpegRunner()

    args = ["-i", input_path]

    # Build video filter chain
    vf_filters = []

    # Add resizing if specified
    if resize:
        width, height = resize
        vf_filters.append(f"scale={width}:{height}")

    # Apply filters if any
    if vf_filters:
        args.extend(["-vf", ",".join(vf_filters)])

    # Set quality based on output format
    output_ext = os.path.splitext(output_path)[1].lower()

    if output_ext in ['.jpg', '.jpeg']:
        args.extend(["-q:v", str(min(31, max(1, 31 - int(quality * 31 / 100))))])  # FFmpeg quality scale
    elif output_ext in ['.webp']:
        args.extend(["-quality", str(quality)])
    elif output_ext in ['.png']:
        args.extend(["-compression_level", str(min(9, max(0, 9 - int(quality * 9 / 100))))])

    # Additional kwargs
    for key, value in kwargs.items():
        if key.startswith('ffmpeg_'):  # Allow direct FFmpeg options
            args.extend([f"-{key[7:]}", str(value)])

    # Treat image-to-image conversions as single-frame outputs.
    args.extend(["-frames:v", "1"])
    if output_ext in [".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
        args.extend(["-update", "1"])
    args.extend(["-y", output_path])

    result = ffmpeg.run(args)

    if result.returncode == 0:
        return True
    else:
        print(f"Failed to convert {input_path}: {result.stderr}")
        return False

def batch_convert_images(input_dir: str, output_dir: str,
                        input_formats: List[str] = ['*.png', '*.jpg', '*.jpeg', '*.tiff', '*.bmp'],
                        output_format: str = 'jpg', quality: int = 85,
                        resize: Tuple[int, int] = None, max_workers: int = 4) -> Dict[str, int]:
    """
    Batch convert all images in a directory to a new format.

    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save converted images
        input_formats: List of file patterns to match (e.g., ['*.png', '*.jpg'])
        output_format: Output format (without dot, e.g., 'jpg', 'webp', 'png')
        quality: Output quality (1-100)
        resize: Optional (width, height) tuple for resizing all images
        max_workers: Maximum number of concurrent conversions

    Returns:
        Dictionary with conversion statistics
    """
    os.makedirs(output_dir, exist_ok=True)

    # Find all input files
    input_files = []
    for pattern in input_formats:
        input_files.extend(glob.glob(os.path.join(input_dir, pattern)))

    if not input_files:
        print(f"No files found matching patterns: {input_formats}")
        return {"total": 0, "successful": 0, "failed": 0}

    print(f"Found {len(input_files)} files to convert")

    # Track results
    results = {"total": len(input_files), "successful": 0, "failed": 0}

    def convert_single_file(input_file: str) -> bool:
        """Convert a single file and return success status."""
        filename = os.path.basename(input_file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}.{output_format}")

        success = convert_image(input_file, output_path, quality=quality, resize=resize)
        return success

    # Convert files concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(convert_single_file, f): f for f in input_files}

        for future in as_completed(future_to_file):
            input_file = future_to_file[future]
            try:
                success = future.result()
                if success:
                    results["successful"] += 1
                    print(f"✓ Converted: {os.path.basename(input_file)}")
                else:
                    results["failed"] += 1
                    print(f"✗ Failed: {os.path.basename(input_file)}")
            except Exception as exc:
                results["failed"] += 1
                print(f"✗ Error converting {os.path.basename(input_file)}: {exc}")

    return results

def optimize_images_for_web(input_dir: str, output_dir: str, max_width: int = 1920,
                           max_height: int = 1080, quality: int = 85) -> Dict[str, int]:
    """
    Optimize images for web usage with resizing and format conversion.

    Args:
        input_dir: Directory containing images
        output_dir: Directory to save optimized images
        max_width: Maximum width for resizing
        max_height: Maximum height for resizing
        quality: JPEG/WebP quality

    Returns:
        Dictionary with conversion statistics
    """
    print("Optimizing images for web...")
    os.makedirs(output_dir, exist_ok=True)

    # Get image metadata to determine if resizing is needed
    ffprobe = FFprobeRunner()

    def should_resize(image_path: str) -> Tuple[bool, Tuple[int, int]]:
        """Check if image needs resizing and return target dimensions."""
        try:
            # Use FFprobeRunner.probe to get metadata
            metadata = ffprobe.probe(image_path)
            if "video" in metadata:
                width = metadata["video"].get("width", 0)
                height = metadata["video"].get("height", 0)

                if width > max_width or height > max_height:
                    # Calculate new dimensions maintaining aspect ratio
                    ratio = min(max_width / width, max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    return True, (new_width, new_height)

            return False, (0, 0)
        except:
            return False, (0, 0)

    # Custom conversion function that checks dimensions
    def convert_with_resize_check(input_file: str) -> bool:
        filename = os.path.basename(input_file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}.jpg")

        needs_resize, dimensions = should_resize(input_file)

        if needs_resize:
            print(f"Resizing {filename} to {dimensions[0]}x{dimensions[1]}")
            return convert_image(input_file, output_path, quality=quality, resize=dimensions)
        else:
            return convert_image(input_file, output_path, quality=quality)

    # Find all images
    image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.tiff', '*.bmp', '*.gif']
    input_files = []
    for pattern in image_patterns:
        input_files.extend(glob.glob(os.path.join(input_dir, pattern)))

    if not input_files:
        print("No image files found")
        return {"total": 0, "successful": 0, "failed": 0}

    print(f"Found {len(input_files)} images to optimize")

    # Convert sequentially (FFmpeg probing might be intensive)
    results = {"total": len(input_files), "successful": 0, "failed": 0}

    for input_file in input_files:
        success = convert_with_resize_check(input_file)
        if success:
            results["successful"] += 1
            print(f"✓ Optimized: {os.path.basename(input_file)}")
        else:
            results["failed"] += 1
            print(f"✗ Failed: {os.path.basename(input_file)}")

    return results

def convert_to_webp_batch(input_dir: str, output_dir: str, quality: int = 80,
                         lossless: bool = False) -> Dict[str, int]:
    """
    Convert images to WebP format for better web performance.

    Args:
        input_dir: Directory containing images
        output_dir: Directory to save WebP images
        quality: WebP quality (1-100)
        lossless: Use lossless compression

    Returns:
        Dictionary with conversion statistics
    """
    print("Converting to WebP format...")

    # WebP specific options
    webp_options = {}
    if lossless:
        webp_options["ffmpeg_lossless"] = "1"
    # Note: quality is handled by the convert_image function for WebP

    return batch_convert_images(
        input_dir=input_dir,
        output_dir=output_dir,
        output_format="webp",
        quality=quality,
        **webp_options
    )

def main():
    """Demonstrate batch image conversion capabilities."""

    # Example 1: Basic batch conversion (PNG to JPEG)
    print("=== Batch converting PNG to JPEG ===")
    results = batch_convert_images(
        input_dir="images/",
        output_dir="converted/jpg/",
        input_formats=["*.png"],
        output_format="jpg",
        quality=90
    )
    print(f"Converted {results['successful']}/{results['total']} images")

    # Example 2: Web optimization with resizing
    print("\n=== Optimizing images for web ===")
    results = optimize_images_for_web(
        input_dir="images/",
        output_dir="optimized/",
        max_width=1920,
        max_height=1080,
        quality=85
    )
    print(f"Optimized {results['successful']}/{results['total']} images")

    # Example 3: Convert to WebP for better compression
    print("\n=== Converting to WebP format ===")
    results = convert_to_webp_batch(
        input_dir="images/",
        output_dir="webp/",
        quality=80,
        lossless=False
    )
    print(f"Converted {results['successful']}/{results['total']} images to WebP")

    # Example 4: Resize all images to thumbnails
    print("\n=== Creating thumbnails ===")
    results = batch_convert_images(
        input_dir="images/",
        output_dir="thumbnails/",
        output_format="jpg",
        quality=80,
        resize=(320, 240)
    )
    print(f"Created {results['successful']}/{results['total']} thumbnails")

    print("\nBatch image conversion examples completed!")

if __name__ == "__main__":
    main()
