"""
FFmpeg Command Builder
Constructs complete FFmpeg commands for video assembly
"""

import logging
import re
from typing import List, Dict
from .motion_effects import MotionEffectBuilder
from .subtitle_style import SubtitleStyleBuilder
from .utils import check_gpu_available

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
        
        motion_effect = self.settings.get('motion_effect', 'Zoom In')
        logger.info(f"Applying VIDEO-LEVEL motion effect: {motion_effect}")
        
        # Start command
        cmd = ['ffmpeg', '-y']
        
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
        
        # Build filter complex
        filter_parts = []
        
        # Process each image - NO motion effects, just crop/scale
        for i, img_path in enumerate(images):
            image_filter = MotionEffectBuilder.build_filter(
                motion_effect,  # Not used in new version
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
        
        # Apply VIDEO-LEVEL motion effect AFTER concatenation
        video_motion_filter = MotionEffectBuilder.build_video_level_filter(
            motion_effect,
            duration,
            fps
        )
        
        if video_motion_filter:
            # Apply motion effect to concatenated video
            filter_parts.append(f"[vconcat]{video_motion_filter}[vmotion]")
            video_input_for_subtitles = "[vmotion]"
            logger.info(f"Applied video-level {motion_effect} effect to entire video")
        else:
            # No motion effect (Static)
            video_input_for_subtitles = "[vconcat]"
            logger.info("No motion effect applied (Static)")
        
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
        cmd.extend(['-map', f'{num_images}:a'])
        
        # Bitrate calculation
        if motion_effect == "Static":
            target_bitrate = f"{int(1 + fps * 0.03)}M"
            max_bitrate = f"{int(1.5 + fps * 0.04)}M"
        else:
            target_bitrate = f"{int(1.5 + fps * 0.05)}M"
            max_bitrate = f"{int(2 + fps * 0.06)}M"
        
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