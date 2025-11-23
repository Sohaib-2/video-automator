"""
Video Processor Module
Handles caption generation, video assembly, and rendering with motion effects
"""

import os
import json
import subprocess
from pathlib import Path
import whisper
import torch
from typing import Dict, List, Tuple, Optional
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoConfig:
    """
    Video rendering configuration
    ADJUST THESE SETTINGS TO CONTROL FILE SIZE, QUALITY, AND SPEED
    """
    
    # FRAME RATE OPTIONS
    FPS_CINEMA = 24      # Cinematic look, smallest files
    FPS_STANDARD = 30    # YouTube standard, balanced size
    FPS_SMOOTH = 60      # Very smooth, larger files
    
    # QUALITY PRESETS
    QUALITY_LOW = 32       # Small files (~50-100MB per 10min)
    QUALITY_MEDIUM = 28    # Medium files (~100-200MB per 10min) - RECOMMENDED
    QUALITY_HIGH = 23      # Large files (~200-400MB per 10min)
    QUALITY_MAX = 18       # Huge files (~400-800MB per 10min)
    
    def __init__(self):
        self.fps = self.FPS_STANDARD
        self.quality = self.QUALITY_MEDIUM
        
    def get_info(self):
        """Get human-readable info about current settings"""
        fps_name = {24: "Cinema (24fps)", 30: "Standard (30fps)", 60: "Smooth (60fps)"}
        quality_name = {32: "Low", 28: "Medium", 23: "High", 18: "Maximum"}
        
        return {
            'fps': self.fps,
            'fps_name': fps_name.get(self.fps, f"{self.fps}fps"),
            'quality': self.quality,
            'quality_name': quality_name.get(self.quality, "Custom")
        }


class VideoProcessor:
    """Handles video processing operations"""
    
    def __init__(self, settings: Dict, config: VideoConfig = None):
        """
        Initialize video processor with settings
        
        Args:
            settings: Dictionary containing caption settings and motion effects
            config: VideoConfig object for FPS and quality settings
        """
        self.settings = settings
        self.config = config or VideoConfig()
        self.whisper_model = None
        self.whisper_device = None
        self.whisper_failed_gpu = False
        
        # Check CUDA availability
        self.cuda_available = torch.cuda.is_available()
        if self.cuda_available:
            logger.info(f"CUDA detected - will attempt GPU acceleration for Whisper")
        else:
            logger.info(f"No CUDA detected - will use CPU for Whisper")
        
        # Log config
        config_info = self.config.get_info()
        logger.info(f"Video Config: {config_info['fps_name']}, Quality: {config_info['quality_name']}")
        
        # Log motion effect
        motion_effect = settings.get('motion_effect', 'Zoom In')
        logger.info(f"Motion Effect: {motion_effect}")
        
    def load_whisper_model(self, model_size: str = "base"):
        """Load Whisper model with GPU/CPU fallback"""
        if self.cuda_available and not self.whisper_failed_gpu:
            try:
                logger.info(f"Loading Whisper model '{model_size}' on GPU (CUDA)...")
                self.whisper_model = whisper.load_model(model_size, device="cuda")
                self.whisper_device = "cuda"
                logger.info("✓ Whisper model loaded successfully on GPU")
                return
            except Exception as e:
                logger.warning(f"⚠ GPU loading failed: {str(e)}")
                logger.info("Falling back to CPU...")
                self.whisper_failed_gpu = True
        
        try:
            logger.info(f"Loading Whisper model '{model_size}' on CPU...")
            self.whisper_model = whisper.load_model(model_size, device="cpu")
            self.whisper_device = "cpu"
            logger.info("✓ Whisper model loaded successfully on CPU")
        except Exception as e:
            logger.error(f"✗ Failed to load Whisper model: {str(e)}")
            raise
    
    def detect_files_in_folder(self, folder_path: str) -> Dict[str, any]:
        """Detect required files in a video folder"""
        folder = Path(folder_path)
        detected = {
            'voiceover': None,
            'script': None,
            'images': []
        }
        
        audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
        image_exts = ['.png', '.jpg', '.jpeg', '.webp']
        
        # Find voiceover
        for ext in audio_exts:
            audio_files = list(folder.glob(f'*{ext}')) + list(folder.glob(f'voiceover{ext}'))
            if audio_files:
                detected['voiceover'] = str(audio_files[0])
                break
        
        # Find script
        script_file = folder / 'script.txt'
        if script_file.exists():
            detected['script'] = str(script_file)
        
        # Find all images (sorted by name)
        all_images = []
        for ext in image_exts:
            all_images.extend(folder.glob(f'*{ext}'))
        
        all_images = sorted(all_images, key=lambda x: x.name)
        detected['images'] = [str(img) for img in all_images]
        
        return detected
    
    def validate_folder(self, folder_path: str) -> Tuple[bool, str]:
        """Validate if folder has all required files"""
        detected = self.detect_files_in_folder(folder_path)
        
        missing = []
        if not detected['voiceover']:
            missing.append('voiceover audio')
        if not detected['images'] or len(detected['images']) == 0:
            missing.append('at least 1 image')
        
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        
        num_images = len(detected['images'])
        if num_images == 1:
            info = "Found 1 image (will be used throughout entire video)"
        else:
            info = f"Found {num_images} images (will be distributed across video duration)"
        
        return True, info
    
    def generate_captions_with_whisper(self, audio_path: str) -> List[Dict]:
        """Generate captions from audio using Whisper"""
        if not self.whisper_model:
            self.load_whisper_model()
        
        logger.info(f"Transcribing audio: {audio_path} (device: {self.whisper_device})")
        
        transcribe_options = {
            'word_timestamps': True,
            'verbose': False
        }
        
        if self.whisper_device == "cuda":
            transcribe_options['fp16'] = False  # Force FP32 on GPU for stability
            logger.info("Using FP32 precision on GPU (more stable)")
        
        try:
            result = self.whisper_model.transcribe(audio_path, **transcribe_options)
            
            captions = []
            for segment in result['segments']:
                captions.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip()
                })
            
            logger.info(f"✓ Generated {len(captions)} caption segments")
            return captions
            
        except Exception as e:
            logger.error(f"✗ Transcription failed on {self.whisper_device}: {str(e)}")
            
            if self.whisper_device == "cuda" and not self.whisper_failed_gpu:
                logger.warning("⚠ GPU transcription failed, retrying on CPU...")
                self.whisper_failed_gpu = True
                self.whisper_model = None
                self.load_whisper_model()
                return self.generate_captions_with_whisper(audio_path)
            else:
                logger.error("Cannot recover from transcription error")
                raise
    
    def create_srt_file(self, captions: List[Dict], output_path: str):
        """Create SRT subtitle file from captions"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                start_time = self._format_timestamp(caption['start'])
                end_time = self._format_timestamp(caption['end'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption['text']}\n\n")
        
        logger.info(f"SRT file created: {output_path}")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
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
        Create FFmpeg subtitle style from settings with custom position
        FIXED: Now uses caption_position from settings instead of fixed alignment
        """
        settings = self.settings
        
        font = settings['font'].replace(' ', '')
        font_size = settings['font_size']
        text_color = self._hex_to_bgr(settings['text_color'])
        bg_color = self._hex_to_bgr(settings['bg_color'])
        
        # FIXED: Properly use background opacity
        has_background = settings.get('has_background', True)
        if has_background:
            # Convert 0-100 to 0-255, then invert for alpha (0=transparent, 255=opaque)
            bg_opacity_value = int(settings['bg_opacity'] * 2.55)
            bg_alpha = f"{bg_opacity_value:02X}"
        else:
            # No background = fully transparent
            bg_alpha = "00"
        
        # Update bg_color to include alpha
        bg_color_with_alpha = f"{bg_color[:-2]}{bg_alpha}"
        
        # FIXED: Get custom caption position from settings
        caption_pos = settings.get('caption_position', {'x': 0.5, 'y': 0.9})
        
        x_norm = caption_pos['x']
        y_norm = caption_pos['y']
        
        # FIXED: Calculate pixel positions for 1920x1080 frame
        # MarginV is distance from BOTTOM of screen
        margin_v = int((1.0 - y_norm) * 1080)
        
        # Determine alignment based on horizontal position
        if x_norm < 0.33:
            alignment = 1  # Bottom left
            margin_l = int(x_norm * 1920)
            margin_r = 0
        elif x_norm > 0.66:
            alignment = 3  # Bottom right
            margin_l = 0
            margin_r = int((1.0 - x_norm) * 1920)
        else:
            alignment = 2  # Bottom center
            margin_l = 0
            margin_r = 0
        
        # FIXED: Adjust alignment for vertical position
        if y_norm < 0.33:
            # Top row
            alignment += 6  # 1→7, 2→8, 3→9
        elif y_norm < 0.66:
            # Middle row
            alignment += 3  # 1→4, 2→5, 3→6
        # else: bottom row (no change needed)
        
        style = (
            f"FontName={font},"
            f"FontSize={font_size},"
            f"PrimaryColour={text_color},"
            f"BackColour={bg_color_with_alpha},"
            f"BorderStyle=4,"  # Background box
            f"Outline=0,"
            f"Shadow=0,"
            f"MarginV={margin_v},"
            f"MarginL={margin_l},"
            f"MarginR={margin_r},"
            f"Alignment={alignment}"
        )
        
        logger.info(f"Caption style: Position=({x_norm:.2f}, {y_norm:.2f}), Alignment={alignment}, MarginV={margin_v}, HasBG={has_background}, Opacity={settings.get('bg_opacity', 80)}%")
        
        return style
    
    def _hex_to_bgr(self, hex_color: str) -> str:
        """Convert hex color to FFmpeg BGR format with alpha placeholder"""
        hex_color = hex_color.lstrip('#')
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Return with FF alpha (will be replaced in create_subtitle_style)
        return f"&HFF{b:02X}{g:02X}{r:02X}"
    
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
            files = self.detect_files_in_folder(folder_path)
            
            is_valid, error = self.validate_folder(folder_path)
            if not is_valid:
                logger.error(f"Validation failed: {error}")
                return False, ""
            
            folder_name = os.path.basename(folder_path)
            output_path = os.path.join(folder_path, f"{folder_name}.mp4")
            
            duration = self.get_audio_duration(files['voiceover'])
            num_images = len(files['images'])
            logger.info(f"Video duration: {duration:.2f} seconds, Images: {num_images}")
            
            # Generate captions
            if progress_callback:
                progress_callback(5, "Generating captions with Whisper...")
            
            captions = self.generate_captions_with_whisper(files['voiceover'])
            
            temp_srt = os.path.join(folder_path, 'temp_captions.srt')
            self.create_srt_file(captions, temp_srt)
            
            if progress_callback:
                progress_callback(20, f"Assembling video with {num_images} image(s)...")
            
            # Build FFmpeg command with motion effect
            ffmpeg_cmd = self._build_ffmpeg_command(
                files, temp_srt, duration, output_path, use_gpu,
                fps=self.config.fps
            )
            
            logger.info("Running FFmpeg...")
            logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg with progress tracking
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            last_update_progress = 0
            total_frames = int(duration * 30)
            
            for line in process.stderr:
                if progress_callback:
                    frame_match = re.search(r'frame=\s*(\d+)', line)
                    if frame_match:
                        current_frame = int(frame_match.group(1))
                        frame_progress = (current_frame / total_frames)
                        ffmpeg_progress = min(frame_progress * 80, 79)
                        total_progress = int(20 + ffmpeg_progress)
                        
                        if total_progress > last_update_progress:
                            last_update_progress = total_progress
                            current_time = current_frame / 30
                            progress_callback(total_progress, f"Rendering video... {int(current_time)}/{int(duration)}s")
                    
                    elif 'time=' in line and last_update_progress < 95:
                        try:
                            time_match = re.search(r'time=(?:(\d{1,2}):)?(\d{1,2}):(\d{2}(?:\.\d{2})?)', line)
                            if time_match:
                                hours = int(time_match.group(1)) if time_match.group(1) else 0
                                minutes = int(time_match.group(2))
                                seconds = float(time_match.group(3))
                                current_time = hours * 3600 + minutes * 60 + seconds
                                
                                ffmpeg_progress = min((current_time / duration) * 75, 75)
                                total_progress = int(20 + ffmpeg_progress)
                                
                                if total_progress > last_update_progress:
                                    last_update_progress = total_progress
                                    progress_callback(total_progress, f"Rendering video... {int(current_time)}/{int(duration)}s")
                        except Exception as e:
                            logger.debug(f"Progress parsing error: {e}")
            
            process.wait()
            
            if progress_callback and process.returncode == 0:
                progress_callback(99, "Finalizing video...")
            
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
                return False, ""
                
        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, ""
    
    def _get_motion_filter(self, effect: str, time_per_image: float, fps: int) -> str:
        """
        Get FFmpeg filter for motion effect
        
        Args:
            effect: Motion effect name (Static, Zoom In, Zoom Out, Pan Right, Pan Left, Ken Burns)
            time_per_image: Duration of image in seconds
            fps: Frame rate
            
        Returns:
            FFmpeg filter string
        """
        num_frames = int(time_per_image * fps)
        
        if effect == "Static":
            # No motion - fastest render
            return f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={fps}"
        
        elif effect == "Zoom In":
            # Zoom from 1.0 to 1.3
            return (
                f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                f"zoompan=z='min(zoom+0.001,1.3)':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Zoom Out":
            # Zoom from 1.3 to 1.0
            return (
                f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                f"zoompan=z='if(eq(on,1),1.3,max(1.0,zoom-0.001))':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Pan Right":
            # Pan from left to right
            return (
                f"scale=2304:1296:force_original_aspect_ratio=increase,"  # Scale up 20%
                f"crop=1920:1080:'min(iw-1920,(iw-1920)*(on/{num_frames}))':0,"  # Pan right
                f"fps={fps}"
            )
        
        elif effect == "Pan Left":
            # Pan from right to left
            return (
                f"scale=2304:1296:force_original_aspect_ratio=increase,"  # Scale up 20%
                f"crop=1920:1080:'(iw-1920)*(1-on/{num_frames})':0,"  # Pan left
                f"fps={fps}"
            )
        
        elif effect == "Ken Burns":
            # Zoom in + subtle pan
            return (
                f"scale=2304:1296:force_original_aspect_ratio=increase,"  # Scale up for room
                f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        else:
            # Default to static if unknown
            logger.warning(f"Unknown motion effect: {effect}, using Static")
            return f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={fps}"
    
    def _build_ffmpeg_command(
        self,
        files: Dict,
        srt_path: str,
        duration: float,
        output_path: str,
        use_gpu: bool,
        fps: int = 30
    ) -> List[str]:
        """Build FFmpeg command for video assembly with motion effects"""
        
        images = files['images']
        num_images = len(images)
        
        # Get subtitle style with FIXED position
        subtitle_style = self.create_subtitle_style()
        
        # Get motion effect
        motion_effect = self.settings.get('motion_effect', 'Zoom In')
        logger.info(f"Applying motion effect: {motion_effect}")
        
        # Base command
        cmd = ['ffmpeg', '-y']
        
        # Hardware acceleration
        if use_gpu and check_gpu_available():
            cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
            logger.info("Using CUDA hardware acceleration for decoding")
        
        # Calculate time per image
        time_per_image = duration / num_images
        
        # Add each image as input
        for i, img_path in enumerate(images):
            cmd.extend([
                '-loop', '1',
                '-framerate', str(fps),
                '-t', str(time_per_image),
                '-i', img_path
            ])
        
        # Add audio input
        cmd.extend(['-i', files['voiceover']])
        
        # Build filter complex with motion effect
        filter_parts = []
        
        # Apply motion effect to each image
        for i in range(num_images):
            motion_filter = self._get_motion_filter(motion_effect, time_per_image, fps)
            filter_parts.append(f"[{i}:v]{motion_filter}[v{i}]")
        
        # Concatenate all video streams
        concat_inputs = ''.join([f"[v{i}]" for i in range(num_images)])
        concat_filter = f"{concat_inputs}concat=n={num_images}:v=1:a=0[vconcat]"
        filter_parts.append(concat_filter)
        
        # Add subtitles with FIXED positioning
        srt_path_escaped = srt_path.replace('\\', '/').replace(':', r'\:')
        subtitle_filter = f"[vconcat]subtitles={srt_path_escaped}:force_style='{subtitle_style}'[vout]"
        filter_parts.append(subtitle_filter)
        
        filter_complex = ';'.join(filter_parts)
        cmd.extend(['-filter_complex', filter_complex])
        
        # Map output
        cmd.extend(['-map', '[vout]'])
        cmd.extend(['-map', f'{num_images}:a'])
        
        # Smart bitrate based on motion effect
        if motion_effect == "Static":
            # Static images need minimal bitrate
            target_bitrate = f"{int(1 + fps * 0.03)}M"
            max_bitrate = f"{int(1.5 + fps * 0.04)}M"
        else:
            # Motion effects need more bitrate
            target_bitrate = f"{int(1.5 + fps * 0.05)}M"
            max_bitrate = f"{int(2 + fps * 0.06)}M"
        
        logger.info(f"Using smart bitrate: {target_bitrate} (max: {max_bitrate})")
        
        # Encoder settings
        quality_cq = self.config.quality
        
        if use_gpu and check_gpu_available():
            cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p1',
                '-tune', 'hq',
                '-rc', 'vbr',
                '-cq', str(quality_cq),
                '-b:v', target_bitrate,
                '-maxrate', max_bitrate,
                '-bufsize', '4M',
                '-profile:v', 'high',
                '-level', '4.2',
                '-spatial-aq', '1',
                '-temporal-aq', '1',
                '-rc-lookahead', '20'
            ])
            logger.info(f"Using GPU encoding with {fps} fps, CQ={quality_cq}")
        else:
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'faster',
                '-tune', 'film',
                '-crf', str(quality_cq),
                '-profile:v', 'high',
                '-level', '4.2'
            ])
            logger.info(f"Using CPU encoding with {fps} fps, CRF={quality_cq}")
        
        # Audio codec
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '48000'
        ])
        
        # Threading
        cmd.extend(['-threads', '0'])
        
        # Output
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
        
        for _ in range(max_workers):
            self.processors.append(VideoProcessor(settings))
    
    def process_queue(self, video_folders: List[str], progress_callbacks: Dict):
        """Process multiple videos in parallel"""
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
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i, folder in enumerate(video_folders):
                processor = self.processors[i % len(self.processors)]
                future = executor.submit(process_single_video, folder, processor)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                logger.info(f"Completed: {result[0]} - Success: {result[1]}")
            
            return results


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_gpu_available() -> bool:
    """Check if NVIDIA GPU is available for encoding"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False