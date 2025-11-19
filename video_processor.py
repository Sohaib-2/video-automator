"""
Video Processor Module
Handles caption generation, video assembly, and rendering
"""

import os
import json
import subprocess
from pathlib import Path
import whisper
from typing import Dict, List, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video processing operations"""
    
    def __init__(self, settings: Dict):
        """
        Initialize video processor with settings
        
        Args:
            settings: Dictionary containing caption settings (font, color, position, etc.)
        """
        self.settings = settings
        self.whisper_model = None
        
    def load_whisper_model(self, model_size: str = "base"):
        """
        Load Whisper model for caption generation
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       - tiny: fastest, least accurate
                       - base: good balance (RECOMMENDED)
                       - small: better accuracy, slower
                       - medium: high accuracy, much slower
                       - large: best accuracy, very slow
        """
        logger.info(f"Loading Whisper model: {model_size}")
        self.whisper_model = whisper.load_model(model_size, device="cpu")
        logger.info("Whisper model loaded successfully")
    
    def detect_files_in_folder(self, folder_path: str) -> Dict[str, any]:
        """
        Detect required files in a video folder
        
        Args:
            folder_path: Path to the video project folder
            
        Returns:
            Dictionary with paths to detected files:
            {
                'voiceover': path or None,
                'script': path or None,
                'images': [list of image paths] (can be 1, 2, or more)
            }
        """
        folder = Path(folder_path)
        detected = {
            'voiceover': None,
            'script': None,
            'images': []
        }
        
        # Audio extensions
        audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
        # Image extensions
        image_exts = ['.png', '.jpg', '.jpeg', '.webp']
        
        # Find voiceover (first audio file)
        for ext in audio_exts:
            audio_files = list(folder.glob(f'*{ext}')) + list(folder.glob(f'voiceover{ext}'))
            if audio_files:
                detected['voiceover'] = str(audio_files[0])
                break
        
        # Find script
        script_file = folder / 'script.txt'
        if script_file.exists():
            detected['script'] = str(script_file)
        
        # Find all images (sorted by name for consistent ordering)
        all_images = []
        for ext in image_exts:
            all_images.extend(folder.glob(f'*{ext}'))
        
        # Sort images by name to ensure consistent order
        all_images = sorted(all_images, key=lambda x: x.name)
        detected['images'] = [str(img) for img in all_images]
        
        return detected
    
    def validate_folder(self, folder_path: str) -> Tuple[bool, str]:
        """
        Validate if folder has all required files
        
        Args:
            folder_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        detected = self.detect_files_in_folder(folder_path)
        
        missing = []
        if not detected['voiceover']:
            missing.append('voiceover audio')
        if not detected['images'] or len(detected['images']) == 0:
            missing.append('at least 1 image')
        
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        
        # Info about images
        num_images = len(detected['images'])
        if num_images == 1:
            info = "Found 1 image (will be used throughout entire video)"
        else:
            info = f"Found {num_images} images (will be distributed across video duration)"
        
        return True, info
    
    def generate_captions_with_whisper(self, audio_path: str) -> List[Dict]:
        """
        Generate captions from audio using Whisper
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of caption segments with timestamps:
            [
                {'start': 0.0, 'end': 2.5, 'text': 'Hello everyone'},
                {'start': 2.5, 'end': 5.8, 'text': 'Welcome back'},
                ...
            ]
        """
        if not self.whisper_model:
            self.load_whisper_model()
        
        logger.info(f"Transcribing audio: {audio_path}")
        
        # Transcribe with word-level timestamps
        result = self.whisper_model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=False
        )
        
        # Extract segments with timestamps
        captions = []
        for segment in result['segments']:
            captions.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'].strip()
            })
        
        logger.info(f"Generated {len(captions)} caption segments")
        return captions
    
    def create_srt_file(self, captions: List[Dict], output_path: str):
        """
        Create SRT subtitle file from captions
        
        Args:
            captions: List of caption segments
            output_path: Path to save SRT file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                # Format timestamps (HH:MM:SS,mmm)
                start_time = self._format_timestamp(caption['start'])
                end_time = self._format_timestamp(caption['end'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption['text']}\n\n")
        
        logger.info(f"SRT file created: {output_path}")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file in seconds
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def create_subtitle_style(self) -> str:
        """
        Create FFmpeg subtitle style from settings
        
        Returns:
            FFmpeg subtitle filter style string
        """
        settings = self.settings
        
        # Font name (remove spaces for FFmpeg)
        font = settings['font'].replace(' ', '')
        
        # Font size
        font_size = settings['font_size']
        
        # Colors (convert hex to BGR for FFmpeg)
        text_color = self._hex_to_bgr(settings['text_color'])
        bg_color = self._hex_to_bgr(settings['bg_color'])
        
        # Opacity (0-255)
        bg_opacity = int(settings['bg_opacity'] * 2.55)
        
        # Position (FFmpeg alignment: 1=bottom left, 2=bottom center, 3=bottom right, etc.)
        position_map = {
            'Top Center': 8,
            'Middle Center': 5,
            'Bottom Center': 2
        }
        alignment = position_map.get(settings['position'], 2)
        
        # Build style string
        style = (
            f"FontName={font},"
            f"FontSize={font_size},"
            f"PrimaryColour={text_color},"
            f"BackColour={bg_color},"
            f"BorderStyle=4,"  # Box background
            f"Outline=0,"
            f"Shadow=0,"
            f"MarginV=50,"  # Vertical margin
            f"Alignment={alignment}"
        )
        
        return style
    
    def _hex_to_bgr(self, hex_color: str) -> str:
        """
        Convert hex color to FFmpeg BGR format with alpha
        
        Args:
            hex_color: Color in hex format (#RRGGBB)
            
        Returns:
            FFmpeg color format (&HAABBGGRR)
        """
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')
        
        # Parse RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # FFmpeg uses ABGR format in hex
        return f"&H00{b:02X}{g:02X}{r:02X}"
    
    def assemble_video(
        self,
        folder_path: str,
        progress_callback=None,
        use_gpu: bool = True
    ) -> Tuple[bool, str]:
        """
        Assemble final video from components
        
        Args:
            folder_path: Path to video project folder
            progress_callback: Function to call with progress updates (0-100)
            use_gpu: Whether to use GPU acceleration
            
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # Detect files
            files = self.detect_files_in_folder(folder_path)
            
            # Validate
            is_valid, error = self.validate_folder(folder_path)
            if not is_valid:
                logger.error(f"Validation failed: {error}")
                return False, ""
            
            # Create output in the SAME folder as input
            folder_name = os.path.basename(folder_path)
            output_path = os.path.join(folder_path, f"{folder_name}.mp4")
            
            # Get audio duration
            duration = self.get_audio_duration(files['voiceover'])
            
            num_images = len(files['images'])
            logger.info(f"Video duration: {duration:.2f} seconds, Images: {num_images}")
            
            # Generate captions
            if progress_callback:
                progress_callback(10, "Generating captions...")
            
            captions = self.generate_captions_with_whisper(files['voiceover'])
            
            # Create temporary SRT file
            temp_srt = os.path.join(folder_path, 'temp_captions.srt')
            self.create_srt_file(captions, temp_srt)
            
            if progress_callback:
                progress_callback(30, f"Assembling video with {num_images} image(s)...")
            
            # Build FFmpeg command
            ffmpeg_cmd = self._build_ffmpeg_command(
                files, temp_srt, duration, output_path, use_gpu
            )
            
            logger.info("Running FFmpeg...")
            logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg with progress tracking
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Collect stderr for error reporting
            stderr_output = []
            
            # Monitor progress
            for line in process.stderr:
                stderr_output.append(line)
                if progress_callback and 'time=' in line:
                    # Parse time from FFmpeg output
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        hours, minutes, seconds = time_str.split(':')
                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        progress = min(30 + int((current_time / duration) * 70), 100)
                        progress_callback(progress, "Rendering video...")
                    except:
                        pass
            
            process.wait()
            
            # Clean up temp file
            if os.path.exists(temp_srt):
                os.remove(temp_srt)
            
            if process.returncode == 0:
                logger.info(f"Video created successfully: {output_path}")
                if progress_callback:
                    progress_callback(100, "Complete!")
                return True, output_path
            else:
                logger.error(f"FFmpeg failed with return code {process.returncode}")
                # Log last 20 lines of stderr for debugging
                logger.error("FFmpeg stderr (last 20 lines):")
                for line in stderr_output[-20:]:
                    logger.error(line.strip())
                return False, ""
                
        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}")
            return False, ""
    
    def _build_ffmpeg_command(
        self,
        files: Dict,
        srt_path: str,
        duration: float,
        output_path: str,
        use_gpu: bool
    ) -> List[str]:
        """Build FFmpeg command for video assembly with variable number of images"""
        
        images = files['images']
        num_images = len(images)
        
        # Get subtitle style
        subtitle_style = self.create_subtitle_style()
        
        # Base command
        cmd = ['ffmpeg', '-y']  # -y to overwrite output file
        
        # Calculate time per image
        time_per_image = duration / num_images
        
        # Add each image as input
        for i, img_path in enumerate(images):
            cmd.extend([
                '-loop', '1',
                '-t', str(time_per_image),
                '-i', img_path
            ])
        
        # Add audio input
        cmd.extend(['-i', files['voiceover']])
        
        # Build filter complex for concatenating images with zoom effect AND subtitles
        filter_parts = []
        
        for i in range(num_images):
            # Scale and add zoom effect to each image
            zoom_filter = (
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                f"zoompan=z='min(zoom+0.0015,1.5)':d={int(time_per_image * 30)}:s=1920x1080:fps=30[v{i}]"
            )
            filter_parts.append(zoom_filter)
        
        # Concatenate all video streams
        concat_inputs = ''.join([f"[v{i}]" for i in range(num_images)])
        concat_filter = f"{concat_inputs}concat=n={num_images}:v=1:a=0[vconcat]"
        filter_parts.append(concat_filter)
        
        # Add subtitles to the concatenated video (MUST be in filter_complex, not separate -vf)
        # Escape the path and style for FFmpeg
        srt_path_escaped = srt_path.replace('\\', '/').replace(':', r'\:')
        subtitle_filter = f"[vconcat]subtitles={srt_path_escaped}:force_style='{subtitle_style}'[vout]"
        filter_parts.append(subtitle_filter)
        
        filter_complex = ';'.join(filter_parts)
        
        cmd.extend(['-filter_complex', filter_complex])
        
        # Map output video
        cmd.extend(['-map', '[vout]'])
        
        # Map audio (last input is audio)
        cmd.extend(['-map', f'{num_images}:a'])
        
        # Encoder settings (NO -vf here, it's all in filter_complex now!)
        if use_gpu:
            # Try NVIDIA GPU encoding
            cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',  # Medium preset
                '-b:v', '5M',  # 5 Mbps bitrate
                '-maxrate', '5M',
                '-bufsize', '10M'
            ])
        else:
            # CPU encoding
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',  # Quality (lower = better, 23 is good)
            ])
        
        # Audio codec
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '48000'
        ])
        
        # Output file
        cmd.append(output_path)
        
        return cmd


class BatchRenderer:
    """Handles parallel rendering of multiple videos"""
    
    def __init__(self, settings: Dict, max_workers: int = 2):
        """
        Initialize batch renderer
        
        Args:
            settings: Caption settings
            max_workers: Maximum number of parallel renders
        """
        self.settings = settings
        self.max_workers = max_workers
        self.processors = []
        
        # Create processor instances for parallel rendering
        for _ in range(max_workers):
            self.processors.append(VideoProcessor(settings))
    
    def process_queue(self, video_folders: List[str], progress_callbacks: Dict):
        """
        Process multiple videos in parallel
        
        Args:
            video_folders: List of folder paths to process
            progress_callbacks: Dictionary mapping folder paths to progress callback functions
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def process_single_video(folder_path: str, processor: VideoProcessor):
            """Process a single video"""
            callback = progress_callbacks.get(folder_path)
            
            success, output_path = processor.assemble_video(
                folder_path,
                progress_callback=callback,
                use_gpu=True
            )
            
            return folder_path, success, output_path
        
        # Process videos in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i, folder in enumerate(video_folders):
                processor = self.processors[i % len(self.processors)]
                future = executor.submit(process_single_video, folder, processor)
                futures.append(future)
            
            # Collect results
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                logger.info(f"Completed: {result[0]} - Success: {result[1]}")
            
            return results


# Utility function to check if FFmpeg is available
def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# Utility function to check GPU availability
def check_gpu_available() -> bool:
    """Check if NVIDIA GPU is available for encoding"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False