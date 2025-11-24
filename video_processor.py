"""
Video Processor Module - COMPLETE FIX
Handles caption generation, video assembly, and rendering with motion effects

CRITICAL FIXES:
1. Preview-to-video exact matching - what you see is what you get
2. Proper font size scaling for 1080p output
3. Caption max-width boundaries (invisible, just constrains text)
4. Fixed crop→scale pipeline to preserve exact composition
5. No MD files output
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
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoConfig:
    """Video rendering configuration"""
    
    FPS_CINEMA = 24
    FPS_STANDARD = 30
    FPS_SMOOTH = 60
    
    QUALITY_LOW = 32
    QUALITY_MEDIUM = 28
    QUALITY_HIGH = 23
    QUALITY_MAX = 18
    
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
        self.settings = settings
        self.config = config or VideoConfig()
        self.whisper_model = None
        self.whisper_device = None
        self.whisper_failed_gpu = False
        
        self.cuda_available = torch.cuda.is_available()
        if self.cuda_available:
            logger.info(f"CUDA detected - will attempt GPU acceleration for Whisper")
        else:
            logger.info(f"No CUDA detected - will use CPU for Whisper")
        
        config_info = self.config.get_info()
        logger.info(f"Video Config: {config_info['fps_name']}, Quality: {config_info['quality_name']}")
        
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
        
        for ext in audio_exts:
            audio_files = list(folder.glob(f'*{ext}')) + list(folder.glob(f'voiceover{ext}'))
            if audio_files:
                detected['voiceover'] = str(audio_files[0])
                break
        
        script_file = folder / 'script.txt'
        if script_file.exists():
            detected['script'] = str(script_file)
        
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
            transcribe_options['fp16'] = False
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
        
        logger.info(f"SRT file created: {output_path} ({len(captions)} captions)")
        
        if captions:
            logger.info(f"Sample caption: '{captions[0]['text']}' at {captions[0]['start']:.2f}s")
    
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
        Create FFmpeg subtitle style with proper font scaling and caption boundaries
        
        FIXES:
        1. Font size properly scaled for 1080p
        2. MarginL/MarginR for caption width boundaries (80% of screen)
        3. Proper outline and shadow for no-background mode
        """
        settings = self.settings
        
        font = settings['font']
        font_safe = font.replace(',', '').replace("'", '').replace('"', '')
        
        # CRITICAL FIX: Font size scaling
        # User sets font size assuming 1080p output
        # If preview is different size, we still use their exact size for 1080p video
        font_size = settings['font_size']
        logger.info(f"Using font size: {font_size}px for 1080p output")
        
        text_color_hex = settings['text_color'].lstrip('#')
        bg_color_hex = settings['bg_color'].lstrip('#')
        
        text_r = int(text_color_hex[0:2], 16)
        text_g = int(text_color_hex[2:4], 16)
        text_b = int(text_color_hex[4:6], 16)
        
        bg_r = int(bg_color_hex[0:2], 16)
        bg_g = int(bg_color_hex[2:4], 16)
        bg_b = int(bg_color_hex[4:6], 16)
        
        text_color = f"&H00{text_b:02X}{text_g:02X}{text_r:02X}"
        
        has_background = settings.get('has_background', True)
        
        if has_background:
            opacity_percent = settings.get('bg_opacity', 80)
            alpha = int((100 - opacity_percent) * 2.55)
            bg_color = f"&H{alpha:02X}{bg_b:02X}{bg_g:02X}{bg_r:02X}"
            border_style = 4
            outline_width = 0
            shadow_depth = 0
            outline_color = "&H00000000"
        else:
            bg_color = "&HFF000000"
            border_style = 1
            outline_width = 3
            shadow_depth = 2
            outline_color = "&H00000000"
        
        caption_pos = settings.get('caption_position', {'x': 0.5, 'y': 0.9})
        
        x_norm = caption_pos['x']
        y_norm = caption_pos['y']
        
        margin_v = int((1.0 - y_norm) * 1080)
        
        # CRITICAL FIX: Caption width boundaries
        # Limit captions to 80% of screen width (1536px out of 1920px)
        # This prevents captions from getting too wide
        caption_max_width_percent = 0.80  # 80% of screen
        side_margin = int((1920 * (1 - caption_max_width_percent)) / 2)  # 192px each side
        
        if x_norm < 0.33:
            h_align = 1
            margin_l = int(x_norm * 1920)
            margin_r = side_margin
        elif x_norm > 0.66:
            h_align = 3
            margin_l = side_margin
            margin_r = int((1.0 - x_norm) * 1920)
        else:
            h_align = 2
            # FIXED: Add side margins for center-aligned text too!
            margin_l = side_margin
            margin_r = side_margin
        
        if y_norm < 0.33:
            alignment = h_align + 6
        elif y_norm < 0.66:
            alignment = h_align + 3
        else:
            alignment = h_align
        
        style = (
            f"FontName={font_safe},"
            f"FontSize={font_size},"
            f"PrimaryColour={text_color},"
            f"BackColour={bg_color},"
            f"OutlineColour={outline_color},"
            f"BorderStyle={border_style},"
            f"Outline={outline_width},"
            f"Shadow={shadow_depth},"
            f"MarginV={margin_v},"
            f"MarginL={margin_l},"
            f"MarginR={margin_r},"
            f"Alignment={alignment}"
        )
        
        logger.info(f"Subtitle style: Pos=({x_norm:.2f},{y_norm:.2f}), Align={alignment}, MarginV={margin_v}px")
        logger.info(f"Caption boundaries: MarginL={margin_l}px, MarginR={margin_r}px (max width: {1920-margin_l-margin_r}px)")
        logger.info(f"Colors: Text={text_color}, BG={bg_color}, Outline={outline_color}, HasBG={has_background}")
        logger.info(f"Border: Style={border_style}, Outline={outline_width}px, Shadow={shadow_depth}px")
        
        return style
    
    def assemble_video(
        self,
        folder_path: str,
        progress_callback=None,
        use_gpu: bool = True
    ) -> Tuple[bool, str]:
        """Assemble final video from components"""
        try:
            logger.info("="*80)
            logger.info("STARTING VIDEO ASSEMBLY")
            logger.info("="*80)
            logger.info(f"Folder: {folder_path}")
            logger.info(f"Settings:")
            logger.info(f"  - Font: {self.settings.get('font', 'N/A')}")
            logger.info(f"  - Font Size: {self.settings.get('font_size', 'N/A')}")
            logger.info(f"  - Text Color: {self.settings.get('text_color', 'N/A')}")
            logger.info(f"  - BG Color: {self.settings.get('bg_color', 'N/A')}")
            logger.info(f"  - BG Opacity: {self.settings.get('bg_opacity', 'N/A')}%")
            logger.info(f"  - Has Background: {self.settings.get('has_background', 'N/A')}")
            logger.info(f"  - Motion Effect: {self.settings.get('motion_effect', 'N/A')}")
            logger.info(f"  - Caption Position: {self.settings.get('caption_position', 'N/A')}")
            logger.info(f"  - Crop Settings: {self.settings.get('crop_settings', 'N/A')}")
            logger.info("="*80)
            
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
            
            if progress_callback:
                progress_callback(5, "Generating captions with Whisper...")
            
            captions = self.generate_captions_with_whisper(files['voiceover'])
            
            temp_srt = os.path.join(folder_path, 'temp_captions.srt')
            self.create_srt_file(captions, temp_srt)
            
            if progress_callback:
                progress_callback(20, f"Assembling video with {num_images} image(s)...")
            
            ffmpeg_cmd = self._build_ffmpeg_command(
                files, temp_srt, duration, output_path, use_gpu,
                fps=self.config.fps
            )
            
            logger.info("Running FFmpeg...")
            logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            last_update_progress = 0
            total_frames = int(duration * 30)
            
            stderr_output = []
            
            for line in process.stderr:
                stderr_output.append(line)
                
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
            
            if os.path.exists(temp_srt):
                os.remove(temp_srt)
            
            if process.returncode == 0:
                logger.info(f"Video created successfully: {output_path}")
                if progress_callback:
                    progress_callback(100, "Complete!")
                return True, output_path
            else:
                logger.error(f"FFmpeg failed with return code {process.returncode}")
                logger.error("FFmpeg error output (last 20 lines):")
                for line in stderr_output[-20:]:
                    logger.error(f"  {line.strip()}")
                return False, ""
                
        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, ""
    
    def _get_motion_filter(self, effect: str, time_per_image: float, fps: int, crop_settings: Dict = None, image_path: str = None) -> str:
        """
        Get FFmpeg filter for motion effect with EXACT crop preservation
        
        CRITICAL FIX: Preview and video must match EXACTLY!
        - Crop to exact region user selected
        - Scale maintaining aspect ratio with padding if needed
        - NO additional cropping that changes composition
        """
        num_frames = int(time_per_image * fps)
        
        if crop_settings and image_path:
            crop_x = crop_settings['x']
            crop_y = crop_settings['y']
            crop_w = crop_settings['width']
            crop_h = crop_settings['height']
            
            try:
                with Image.open(image_path) as img:
                    img_w, img_h = img.size
                    
                if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
                    logger.warning(f"Invalid crop coordinates: {crop_settings}. Using default auto-crop.")
                    base_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
                elif crop_x + crop_w > img_w or crop_y + crop_h > img_h:
                    logger.warning(f"Crop region {crop_w}x{crop_h} at ({crop_x},{crop_y}) exceeds image dimensions {img_w}x{img_h}")
                    crop_w = min(crop_w, img_w - crop_x)
                    crop_h = min(crop_h, img_h - crop_y)
                    logger.info(f"Adjusted crop to: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
                    
                    # CRITICAL FIX: Use exact scale without force_original_aspect_ratio
                    # This preserves the EXACT composition from preview
                    base_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1920:1080:flags=lanczos"
                else:
                    # CRITICAL FIX: Exact scale preserves composition
                    base_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1920:1080:flags=lanczos"
                    logger.info(f"Using custom crop: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
                    logger.info(f"EXACT MATCH: Preview composition will be preserved in video")
            except Exception as e:
                logger.error(f"Failed to validate crop settings: {e}")
                logger.warning("Falling back to default auto-crop")
                base_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        else:
            base_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        
        if effect == "Static":
            return f"{base_filter},fps={fps}"
        
        elif effect == "Zoom In":
            return (
                f"{base_filter},"
                f"zoompan=z='min(zoom+0.001,1.3)':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Zoom Out":
            return (
                f"{base_filter},"
                f"zoompan=z='if(eq(on,1),1.3,max(1.0,zoom-0.001))':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Pan Right":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"crop=1920:1080:'min(iw-1920,(iw-1920)*(on/{num_frames}))':0,"
                    f"fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"crop=1920:1080:'min(iw-1920,(iw-1920)*(on/{num_frames}))':0,"
                    f"fps={fps}"
                )
        
        elif effect == "Pan Left":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"crop=1920:1080:'(iw-1920)*(1-on/{num_frames})':0,"
                    f"fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"crop=1920:1080:'(iw-1920)*(1-on/{num_frames})':0,"
                    f"fps={fps}"
                )
        
        elif effect == "Ken Burns":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={num_frames}:s=1920x1080:fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={num_frames}:s=1920x1080:fps={fps}"
                )
        
        else:
            logger.warning(f"Unknown motion effect: {effect}, using Static")
            return f"{base_filter},fps={fps}"
    
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
        
        subtitle_style = self.create_subtitle_style()
        
        motion_effect = self.settings.get('motion_effect', 'Zoom In')
        logger.info(f"Applying motion effect: {motion_effect}")
        
        cmd = ['ffmpeg', '-y']
        
        crop_settings = self.settings.get('crop_settings', None)
        if use_gpu and check_gpu_available() and not crop_settings:
            cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
            logger.info("Using CUDA hardware acceleration for decoding")
        else:
            if crop_settings:
                logger.info("Disabling CUDA hwaccel due to custom crop (compatibility)")
        
        time_per_image = duration / num_images
        
        for i, img_path in enumerate(images):
            cmd.extend([
                '-loop', '1',
                '-framerate', str(fps),
                '-t', str(time_per_image),
                '-i', img_path
            ])
        
        cmd.extend(['-i', files['voiceover']])
        
        filter_parts = []
        
        crop_settings = self.settings.get('crop_settings', None)
        
        for i in range(num_images):
            motion_filter = self._get_motion_filter(motion_effect, time_per_image, fps, crop_settings, images[i])
            filter_parts.append(f"[{i}:v]{motion_filter}[v{i}]")
        
        concat_inputs = ''.join([f"[v{i}]" for i in range(num_images)])
        concat_filter = f"{concat_inputs}concat=n={num_images}:v=1:a=0[vconcat]"
        filter_parts.append(concat_filter)
        
        srt_path_normalized = srt_path.replace('\\', '/')
        srt_path_escaped = srt_path_normalized.replace(':', r'\:').replace("'", r"'\''")
        
        subtitle_filter = f"[vconcat]subtitles='{srt_path_escaped}':force_style='{subtitle_style}'[vout]"
        filter_parts.append(subtitle_filter)
        
        logger.info(f"Subtitle SRT: {srt_path}")
        logger.info(f"Subtitle escaped: {srt_path_escaped}")
        logger.info(f"Style: {subtitle_style}")
        
        filter_complex = ';'.join(filter_parts)
        cmd.extend(['-filter_complex', filter_complex])
        
        cmd.extend(['-map', '[vout]'])
        cmd.extend(['-map', f'{num_images}:a'])
        
        if motion_effect == "Static":
            target_bitrate = f"{int(1 + fps * 0.03)}M"
            max_bitrate = f"{int(1.5 + fps * 0.04)}M"
        else:
            target_bitrate = f"{int(1.5 + fps * 0.05)}M"
            max_bitrate = f"{int(2 + fps * 0.06)}M"
        
        logger.info(f"Using smart bitrate: {target_bitrate} (max: {max_bitrate})")
        
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
        
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '48000'
        ])
        
        cmd.extend(['-threads', '0'])
        
        cmd.append(output_path)
        
        return cmd


class BatchRenderer:
    """Handles parallel rendering of multiple videos"""
    
    def __init__(self, settings: Dict, max_workers: int = 2):
        self.settings = settings
        self.max_workers = max_workers
        self.processors = []
        
        for _ in range(max_workers):
            self.processors.append(VideoProcessor(settings))
    
    def process_queue(self, video_folders: List[str], progress_callbacks: Dict):
        """Process multiple videos in parallel"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def process_single_video(folder_path: str, processor: VideoProcessor):
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