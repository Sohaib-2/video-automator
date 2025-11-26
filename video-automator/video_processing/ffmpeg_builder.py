"""
FFmpeg Command Builder
Constructs complete FFmpeg commands for video assembly with intensity-controlled effects
UPDATED: Support for video overlay effects (real grain video files)
"""

import logging
import re
from typing import List, Dict
from .motion_effects import MotionEffectBuilder
from .subtitle_style import SubtitleStyleBuilder
from .utils import check_gpu_available
from utils.resource_path import get_ffmpeg_path

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """Builds FFmpeg commands for video assembly"""
    
    def __init__(self, settings: Dict, config):
        """
        Initialize FFmpeg command builder
        
        Args:
            settings: Video style settings
            config: VideoConfig instance
        """
        self.settings = settings
        self.config = config
    
    def build_command(
        self,
        files: Dict,
        srt_path: str,
        duration: float,
        output_path: str,
        use_gpu: bool = True
    ) -> List[str]:
        """
        Build complete FFmpeg command for video assembly
        
        Args:
            files: Dict with 'images', 'voiceover' paths
            srt_path: Path to SRT subtitle file
            duration: Total video duration in seconds
            output_path: Output video file path
            use_gpu: Whether to use GPU acceleration
            
        Returns:
            List of FFmpeg command arguments
        """
        images = files['images']
        num_images = len(images)
        fps = self.config.fps
        
        # Build subtitle style
        style_builder = SubtitleStyleBuilder(self.settings)
        subtitle_style = style_builder.build()
        
        # Get motion effects (can be list or single string for backward compatibility)
        motion_effects = self.settings.get('motion_effects', None)
        
        # Handle backward compatibility
        if motion_effects is None:
            # Check old single effect key
            old_effect = self.settings.get('motion_effect', 'Static')
            motion_effects = [old_effect]
        elif isinstance(motion_effects, str):
            # Convert single string to list
            motion_effects = [motion_effects]
        
        # Get intensity values
        intensities = self.settings.get('motion_effect_intensities', {
            'Noise': 50,
            'Tilt': 50
        })
        
        logger.info(f"Selected motion effects: {', '.join(motion_effects)}")
        logger.info(f"Effect intensities: {intensities}")
        
        # Start command
        ffmpeg_cmd = get_ffmpeg_path()
        cmd = [ffmpeg_cmd, '-y']
        
        # Hardware acceleration
        crop_settings = self.settings.get('crop_settings', None)
        if use_gpu and check_gpu_available() and not crop_settings:
            cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
            logger.info("Using CUDA hardware acceleration for decoding")
        else:
            if crop_settings:
                logger.info("Disabling CUDA hwaccel due to custom crop (compatibility)")
        
        # Add image inputs
        time_per_image = duration / num_images
        for img_path in images:
            cmd.extend([
                '-loop', '1',
                '-framerate', str(fps),
                '-t', str(time_per_image),
                '-i', img_path
            ])
        
        # Add audio input
        cmd.extend(['-i', files['voiceover']])
        
        # Build motion effects and detect video overlay
        video_motion_result = MotionEffectBuilder.build_video_level_filters(
            motion_effects,
            duration,
            fps,
            intensities
        )
        
        # Check for video overlay instructions (grain overlay)
        has_video_overlay = False
        video_overlay_info = None
        video_motion_filters = None
        grain_input_index = None
        
        if video_motion_result:
            # Check if result contains BOTH video overlay AND other filters
            if isinstance(video_motion_result, str) and "|FILTERS|" in video_motion_result:
                # Format: "VIDEO_OVERLAY:path:opacity:duration|FILTERS|filter1,filter2"
                parts = video_motion_result.split("|FILTERS|")
                overlay_part = parts[0]
                filters_part = parts[1]
                
                # Parse overlay
                if overlay_part.startswith("VIDEO_OVERLAY:"):
                    has_video_overlay = True
                    overlay_parts = overlay_part.split(":")
                    
                    if len(overlay_parts) >= 4:
                        video_overlay_info = {
                            'path': overlay_parts[1],
                            'opacity': float(overlay_parts[2]),
                            'duration': float(overlay_parts[3])
                        }
                        
                        # Add grain video input with looping
                        grain_input_index = num_images + 1  # After all images and audio
                        grain_path = video_overlay_info['path']
                        
                        cmd.extend([
                            '-stream_loop', '-1',  # Loop the grain video indefinitely
                            '-i', grain_path,      # Input grain video
                            '-t', str(duration)    # Limit to match main video duration
                        ])
                        
                        logger.info(f"✨ Added GRAIN OVERLAY: {grain_path} at index {grain_input_index}")
                        logger.info(f"   Opacity: {video_overlay_info['opacity']:.2f}")
                    
                    # Store other filters to apply BEFORE grain overlay
                    video_motion_filters = filters_part
                    logger.info(f"🎬 Will apply filters THEN grain: {video_motion_filters[:80]}...")
                
            elif isinstance(video_motion_result, str) and video_motion_result.startswith("VIDEO_OVERLAY:"):
                # Only video overlay, no other filters
                has_video_overlay = True
                parts = video_motion_result.split(":")
                
                if len(parts) < 4:
                    logger.error(f"Invalid VIDEO_OVERLAY format: {video_motion_result}")
                    logger.warning("Skipping video overlay due to parse error")
                else:
                    video_overlay_info = {
                        'path': parts[1],
                        'opacity': float(parts[2]),
                        'duration': float(parts[3])
                    }
                    
                    # Add grain video input with looping
                    grain_input_index = num_images + 1  # After all images and audio
                    grain_path = video_overlay_info['path']
                    
                    cmd.extend([
                        '-stream_loop', '-1',  # Loop the grain video indefinitely
                        '-i', grain_path,      # Input grain video
                        '-t', str(duration)    # Limit to match main video duration
                    ])
                    
                    logger.info(f"✨ Added REAL GRAIN OVERLAY: {grain_path} at index {grain_input_index}")
                    logger.info(f"   Opacity: {video_overlay_info['opacity']:.2f} | Duration: {duration:.2f}s")
                
            else:
                # Normal filter string only (Tilt, etc - no grain)
                video_motion_filters = video_motion_result
        
        # Build filter complex
        filter_parts = []
        
        # Process each image - NO motion effects, just crop/scale
        for i, img_path in enumerate(images):
            image_filter = MotionEffectBuilder.build_filter(
                "Static",  # Not used in new version
                time_per_image,
                fps,
                crop_settings,
                img_path
            )
            filter_parts.append(f"[{i}:v]{image_filter}[v{i}]")
        
        # Concatenate video streams
        concat_inputs = ''.join([f"[v{i}]" for i in range(num_images)])
        concat_filter = f"{concat_inputs}concat=n={num_images}:v=1:a=0[vconcat]"
        filter_parts.append(concat_filter)
        
        # Apply VIDEO-LEVEL effects AFTER concatenation
        if has_video_overlay and video_motion_filters:
            # BOTH GRAIN OVERLAY AND OTHER FILTERS (e.g., Tilt + Noise)
            # Strategy: Apply other filters FIRST, THEN overlay grain on top
            
            opacity = video_overlay_info['opacity']
            
            # Step 1: Apply other motion filters to concatenated video
            filter_parts.append(f"[vconcat]{video_motion_filters}[vfiltered]")
            
            # Step 2: Prepare grain overlay stream
            grain_filter = (
                f"[{grain_input_index}:v]"
                f"scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"format=rgba,"
                f"colorchannelmixer=aa={opacity}"
                f"[grain]"
            )
            filter_parts.append(grain_filter)
            
            # Step 3: Blend grain over filtered video
            overlay_filter = f"[vfiltered][grain]overlay[vmotion]"
            filter_parts.append(overlay_filter)
            
            video_input_for_subtitles = "[vmotion]"
            logger.info(f"🎬 Applied motion filters THEN grain overlay (opacity: {opacity:.2f})")
            
        elif has_video_overlay:
            # GRAIN OVERLAY ONLY (no other filters)
            opacity = video_overlay_info['opacity']
            
            # Prepare grain overlay stream
            grain_filter = (
                f"[{grain_input_index}:v]"
                f"scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"format=rgba,"
                f"colorchannelmixer=aa={opacity}"
                f"[grain]"
            )
            filter_parts.append(grain_filter)
            
            # Blend grain over main video
            overlay_filter = f"[vconcat][grain]overlay[vmotion]"
            filter_parts.append(overlay_filter)
            
            video_input_for_subtitles = "[vmotion]"
            logger.info(f"🎬 Applied REAL GRAIN overlay with {opacity:.2f} opacity")
            
        elif video_motion_filters:
            # OTHER MOTION EFFECTS ONLY (Tilt, etc - no grain)
            filter_parts.append(f"[vconcat]{video_motion_filters}[vmotion]")
            video_input_for_subtitles = "[vmotion]"
            logger.info(f"Applied {len([e for e in motion_effects if e != 'Static'])} motion effect(s)")
            
        else:
            # NO MOTION EFFECTS (Static)
            video_input_for_subtitles = "[vconcat]"
            logger.info("No motion effects applied (Static)")
        
        # Add subtitles to the final video stream
        srt_path_normalized = srt_path.replace('\\', '/')
        srt_path_escaped = srt_path_normalized.replace(':', r'\:').replace("'", r"'\''")
        
        subtitle_filter = f"{video_input_for_subtitles}subtitles='{srt_path_escaped}':force_style='{subtitle_style}'[vout]"
        filter_parts.append(subtitle_filter)
        
        logger.info(f"Subtitle SRT: {srt_path}")
        logger.info(f"Subtitle escaped: {srt_path_escaped}")
        logger.info(f"Style: {subtitle_style}")
        
        # Combine all filters
        filter_complex = ';'.join(filter_parts)
        cmd.extend(['-filter_complex', filter_complex])
        
        # Map outputs
        cmd.extend(['-map', '[vout]'])
        cmd.extend(['-map', f'{num_images}:a'])  # Audio from original position
        
        # Bitrate calculation - adjust based on effects
        has_motion = any(e != "Static" for e in motion_effects)
        
        if has_motion:
            target_bitrate = f"{int(1.5 + fps * 0.05)}M"
            max_bitrate = f"{int(2 + fps * 0.06)}M"
        else:
            target_bitrate = f"{int(1 + fps * 0.03)}M"
            max_bitrate = f"{int(1.5 + fps * 0.04)}M"
        
        logger.info(f"Using smart bitrate: {target_bitrate} (max: {max_bitrate})")
        
        quality_cq = self.config.quality
        
        # Video encoding
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
        
        # Audio encoding
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
    
    @staticmethod
    def parse_progress(line: str, duration: float) -> tuple[int, str]:
        """
        Parse FFmpeg progress from stderr line
        
        Args:
            line: FFmpeg stderr output line
            duration: Total video duration
            
        Returns:
            Tuple of (progress_percent, status_message)
        """
        # Try to parse frame number
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            current_frame = int(frame_match.group(1))
            total_frames = int(duration * 30)
            progress = min(int((current_frame / total_frames) * 80), 79) + 20
            current_time = current_frame / 30
            status = f"Rendering video... {int(current_time)}/{int(duration)}s"
            return progress, status
        
        # Try to parse time
        time_match = re.search(r'time=(?:(\d{1,2}):)?(\d{1,2}):(\d{2}(?:\.\d{2})?)', line)
        if time_match:
            hours = int(time_match.group(1)) if time_match.group(1) else 0
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            current_time = hours * 3600 + minutes * 60 + seconds
            
            progress = min(int((current_time / duration) * 75), 75) + 20
            status = f"Rendering video... {int(current_time)}/{int(duration)}s"
            return progress, status
        
        return -1, ""