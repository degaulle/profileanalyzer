"""
Image processing utilities for creating collages and extracting video frames
with parallel processing support
"""

import os
import requests
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from io import BytesIO
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class ImageProcessor:
    def __init__(self, output_dir="output/collages", max_workers=5):
        """Initialize image processor with parallel processing support"""
        self.output_dir = output_dir
        self.max_workers = max_workers
        self._lock = threading.Lock()
        os.makedirs(output_dir, exist_ok=True)

    def download_image(self, url: str) -> Image.Image:
        """Download image from URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert('RGB')
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
            # Return a placeholder image
            return Image.new('RGB', (400, 400), color='gray')

    def download_video(self, url: str, output_path: str) -> str:
        """Download video from URL with proper headers"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            print(f"Downloading video from: {url[:100]}...")
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()

            total_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            print(f"✓ Downloaded video: {total_size / 1024 / 1024:.2f} MB")

            # Verify file was created and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                print(f"✗ Video file empty or not created")
                return None

        except Exception as e:
            print(f"✗ Error downloading video: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None

    def download_images_parallel(self, image_urls: List[str]) -> List[Image.Image]:
        """
        Download multiple images in parallel for faster processing

        Args:
            image_urls: List of image URLs to download

        Returns:
            List of PIL Images
        """
        images = [None] * len(image_urls)

        def download_with_index(idx_url):
            idx, url = idx_url
            return idx, self.download_image(url)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(download_with_index, (idx, url)): idx
                      for idx, url in enumerate(image_urls)}

            for future in as_completed(futures):
                try:
                    idx, img = future.result()
                    images[idx] = img
                except Exception as e:
                    print(f"Error in parallel download: {e}")

        return images

    def create_image_collage(self, image_urls: List[str], caption: str,
                           post_info: dict, output_filename: str) -> str:
        """
        Create a collage from multiple images with text info

        Args:
            image_urls: List of image URLs
            caption: Post caption
            post_info: Dictionary with post metadata (likes, comments, etc.)
            output_filename: Output filename

        Returns:
            Path to saved collage
        """
        if not image_urls:
            return None

        # Download all images in parallel for faster processing
        images = self.download_images_parallel(image_urls)

        # Calculate grid dimensions
        num_images = len(images)
        if num_images == 1:
            grid_cols, grid_rows = 1, 1
        elif num_images == 2:
            grid_cols, grid_rows = 2, 1
        elif num_images <= 4:
            grid_cols, grid_rows = 2, 2
        elif num_images <= 6:
            grid_cols, grid_rows = 3, 2
        else:
            grid_cols, grid_rows = 3, 3

        # Resize images to uniform size
        img_width, img_height = 400, 400
        resized_images = []
        for img in images[:grid_cols * grid_rows]:  # Limit to grid size
            resized_images.append(img.resize((img_width, img_height), Image.Resampling.LANCZOS))

        # Create collage canvas
        collage_width = grid_cols * img_width
        collage_height = grid_rows * img_height + 150  # Extra space for text
        collage = Image.new('RGB', (collage_width, collage_height), 'white')

        # Paste images
        for idx, img in enumerate(resized_images):
            row = idx // grid_cols
            col = idx % grid_cols
            x = col * img_width
            y = row * img_height
            collage.paste(img, (x, y))

        # Add text information
        draw = ImageDraw.Draw(collage)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()

        # Text area starts after images
        text_y = grid_rows * img_height + 10

        # Post stats
        stats_text = f"❤ {post_info.get('likesCount', 0):,} likes  💬 {post_info.get('commentsCount', 0):,} comments"
        draw.text((10, text_y), stats_text, fill='black', font=font_bold)

        # Caption (truncated if too long)
        caption_preview = caption[:200] + "..." if len(caption) > 200 else caption
        if caption_preview:
            draw.text((10, text_y + 30), f"Caption: {caption_preview}", fill='black', font=font)

        # Post type indicator
        post_type = f"📸 {num_images} images" if num_images > 1 else "📸 Single image"
        draw.text((10, text_y + 80), post_type, fill='gray', font=font)

        # Save collage
        output_path = os.path.join(self.output_dir, output_filename)
        collage.save(output_path, quality=85)
        print(f"Saved image collage: {output_path}")
        return output_path

    def extract_video_frames(self, video_url: str, num_frames=9) -> List[Image.Image]:
        """
        Extract evenly-spaced frames from a video

        Args:
            video_url: URL of the video
            num_frames: Number of frames to extract (default: 9)

        Returns:
            List of PIL Images
        """
        # Download video to temporary file
        temp_video_path = os.path.join(self.output_dir, "temp_video.mp4")
        video_path = self.download_video(video_url, temp_video_path)

        if not video_path:
            print(f"✗ Failed to download video, cannot extract frames")
            return []

        frames = []
        try:
            print(f"Opening video file: {video_path}")
            # Check if file exists and has content
            if not os.path.exists(video_path):
                print(f"✗ Video file does not exist: {video_path}")
                return []

            file_size = os.path.getsize(video_path)
            print(f"Video file size: {file_size / 1024 / 1024:.2f} MB")

            if file_size == 0:
                print(f"✗ Video file is empty")
                return []

            # Open video
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                print(f"✗ OpenCV cannot open video file")
                cap.release()
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            print(f"Video info: {total_frames} frames, {fps:.2f} fps, {duration:.2f}s duration")

            if total_frames == 0:
                print(f"✗ Video has 0 frames")
                cap.release()
                return []

            if total_frames < num_frames:
                num_frames = total_frames

            # Calculate frame indices to extract
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append(pil_image)

            cap.release()

            print(f"✓ Extracted {len(frames)} frames from video")

            # Clean up temp video file
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        except Exception as e:
            print(f"✗ Error extracting frames from video: {e}")
            import traceback
            traceback.print_exc()

        return frames

    def create_video_collage(self, video_url: str, caption: str,
                           post_info: dict, output_filename: str) -> str:
        """
        Create a collage from video frames with text info

        Args:
            video_url: Video URL
            caption: Post caption
            post_info: Dictionary with post metadata
            output_filename: Output filename

        Returns:
            Path to saved collage
        """
        # Extract 9 frames
        frames = self.extract_video_frames(video_url, num_frames=9)

        if not frames:
            print(f"Failed to extract frames from video: {video_url}")
            return None

        # Create 3x3 grid
        grid_cols, grid_rows = 3, 3
        img_width, img_height = 400, 400

        # Resize frames
        resized_frames = [frame.resize((img_width, img_height), Image.Resampling.LANCZOS)
                         for frame in frames[:9]]

        # Create collage canvas
        collage_width = grid_cols * img_width
        collage_height = grid_rows * img_height + 150  # Extra space for text
        collage = Image.new('RGB', (collage_width, collage_height), 'white')

        # Paste frames
        for idx, frame in enumerate(resized_frames):
            row = idx // grid_cols
            col = idx % grid_cols
            x = col * img_width
            y = row * img_height
            collage.paste(frame, (x, y))

        # Add text information
        draw = ImageDraw.Draw(collage)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()

        # Text area
        text_y = grid_rows * img_height + 10

        # Post stats
        stats_text = f"❤ {post_info.get('likesCount', 0):,} likes  💬 {post_info.get('commentsCount', 0):,} comments"
        if 'videoViewCount' in post_info:
            stats_text += f"  👁 {post_info.get('videoViewCount', 0):,} views"
        draw.text((10, text_y), stats_text, fill='black', font=font_bold)

        # Caption
        caption_preview = caption[:200] + "..." if len(caption) > 200 else caption
        if caption_preview:
            draw.text((10, text_y + 30), f"Caption: {caption_preview}", fill='black', font=font)

        # Video indicator
        draw.text((10, text_y + 80), "🎥 Video (9 frames)", fill='gray', font=font)

        # Save collage
        output_path = os.path.join(self.output_dir, output_filename)
        collage.save(output_path, quality=85)
        print(f"Saved video collage: {output_path}")
        return output_path

    def create_sidecar_collage(self, post_data: dict, output_filename: str) -> str:
        """
        Create a collage for a sidecar post (multiple images/videos)

        Args:
            post_data: Post data dictionary
            output_filename: Output filename

        Returns:
            Path to saved collage
        """
        # Collect all images (including video thumbnails)
        image_urls = [img['url'] for img in post_data.get('images', [])]

        if not image_urls:
            return None

        return self.create_image_collage(
            image_urls,
            post_data.get('caption', ''),
            post_data,
            output_filename
        )

    def process_post_collage(self, post_data: dict, post_num: int) -> str:
        """
        Process a single post and create its collage (helper for parallel processing)

        Args:
            post_data: Post data dictionary
            post_num: Post number for filename

        Returns:
            Path to saved collage or None
        """
        post_type = post_data.get('type', '')

        try:
            if post_type == 'Video' and post_data.get('videos'):
                # Extract frames from video
                video_url = post_data['videos'][0]['url']
                collage_path = self.create_video_collage(
                    video_url,
                    post_data.get('caption', ''),
                    post_data,
                    f"post_{post_num}_video_collage.jpg"
                )
                return collage_path

            elif post_type in ['Image', 'Sidecar'] and post_data.get('images'):
                # Create image collage
                image_urls = [img['url'] for img in post_data['images']]
                collage_path = self.create_image_collage(
                    image_urls,
                    post_data.get('caption', ''),
                    post_data,
                    f"post_{post_num}_collage.jpg"
                )
                return collage_path

        except Exception as e:
            print(f"Error creating collage for post {post_num}: {e}")
            return None

    def generate_collages_parallel(self, posts: List[dict]) -> List[dict]:
        """
        Generate collages for multiple posts in parallel

        Args:
            posts: List of post data dictionaries

        Returns:
            Updated posts with collage_path added
        """
        print(f"\nGenerating collages for {len(posts)} posts in parallel (max {self.max_workers} workers)...")

        def process_with_index(idx_post):
            idx, post = idx_post
            post_num = idx + 1
            collage_path = self.process_post_collage(post, post_num)
            return idx, collage_path

        # Process posts in parallel
        collage_paths = [None] * len(posts)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_with_index, (idx, post)): idx
                      for idx, post in enumerate(posts)}

            completed = 0
            for future in as_completed(futures):
                try:
                    idx, collage_path = future.result()
                    collage_paths[idx] = collage_path
                    completed += 1
                    print(f"  Progress: {completed}/{len(posts)} collages completed")
                except Exception as e:
                    print(f"Error in parallel collage generation: {e}")

        # Update posts with collage paths
        for idx, post in enumerate(posts):
            post['collage_path'] = collage_paths[idx]

        print(f"✓ Completed {len(posts)} collages in parallel!\n")
        return posts
