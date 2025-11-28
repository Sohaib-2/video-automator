"""
Batch Renderer and Video Processor
Main classes for video assembly and batch processing
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import VideoConfig
from .whisper_handler import WhisperHandler
from .caption_generator import CaptionGenerator
from .ffmpeg_builder import FFmpegCommandBuilder
from .utils import (
    detect_files_in_folder,
    validate_folder,
    get_audio_duration
)
from utils.resource_path import get_resource_path

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Main video processor - handles single video assembly"""
    
    def __init__(self, settings: Dict, config: Optional[VideoConfig] = None):
        """
        Initialize video processor

        Args:
            settings: Video style settings dictionary
            config: Optional VideoConfig instance
        """
        self.settings = settings

        # Create config from settings if not provided
        if config is None:
            resolution = settings.get('video_resolution', '1080p')
            config = VideoConfig(resolution=resolution)

        self.config = config
        self.whisper_handler = WhisperHandler()

        config_info = self.config.get_info()
        logger.info(f"Video Config: {config_info['fps_name']}, Quality: {config_info['quality_name']}, Resolution: {config_info['resolution_name']}")

        motion_effect = settings.get('motion_effect', 'Zoom In')
        logger.info(f"Motion Effect: {motion_effect}")
    
    def detect_files(self, folder_path: str) -> Dict:
        """Detect files in folder - wrapper for utils function"""
        return detect_files_in_folder(folder_path)
    
    def validate_folder(self, folder_path: str) -> Tuple[bool, str]:
        """Validate folder - wrapper for utils function"""
        return validate_folder(folder_path)
    
    def assemble_video(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        use_gpu: bool = True
    ) -> Tuple[bool, str]:
        """
        Assemble final video from components
        
        Args:
            folder_path: Path to video project folder
            progress_callback: Optional callback for progress updates
            use_gpu: Whether to use GPU acceleration
            
        Returns:
            Tuple of (success, output_path)
        """
        try:
            logger.info("=" * 80)
            logger.info("STARTING VIDEO ASSEMBLY")
            logger.info("=" * 80)
            logger.info(f"Folder: {folder_path}")
            logger.info("Settings:")
            logger.info(f"  - Font: {self.settings.get('font', 'N/A')}")
            logger.info(f"  - Font Size: {self.settings.get('font_size', 'N/A')}")
            logger.info(f"  - Text Color: {self.settings.get('text_color', 'N/A')}")
            logger.info(f"  - BG Color: {self.settings.get('bg_color', 'N/A')}")
            logger.info(f"  - BG Opacity: {self.settings.get('bg_opacity', 'N/A')}%")
            logger.info(f"  - Has Background: {self.settings.get('has_background', 'N/A')}")
            logger.info(f"  - Has Outline: {self.settings.get('has_outline', 'N/A')}")
            logger.info(f"  - Outline Color: {self.settings.get('outline_color', 'N/A')}")
            logger.info(f"  - Motion Effect: {self.settings.get('motion_effect', 'N/A')}")
            logger.info(f"  - Caption Position: {self.settings.get('caption_position', 'N/A')}")
            logger.info(f"  - Crop Settings: {self.settings.get('crop_settings', 'N/A')}")
            logger.info("=" * 80)
            
            # Detect and validate files
            files = detect_files_in_folder(folder_path)
            is_valid, error = validate_folder(folder_path)
            if not is_valid:
                logger.error(f"Validation failed: {error}")
                return False, ""
            
            # Prepare output path
            folder_name = os.path.basename(folder_path)
            output_path = os.path.join(folder_path, f"{folder_name}.mp4")
            
            # Get audio duration
            duration = get_audio_duration(files['voiceover'])
            num_images = len(files['images'])
            logger.info(f"Video duration: {duration:.2f} seconds, Images: {num_images}")
            
            # Generate captions with Whisper
            if progress_callback:
                progress_callback(5, "Generating captions with Whisper...")
            
            captions = self.whisper_handler.transcribe(files['voiceover'])
            
            # Create SRT file with natural wrapping approach
            # Max 15 words / 75 chars - let FFmpeg WrapStyle=2 handle line breaks naturally
            # This reduces caption cuts and allows text to flow smoothly to 2-3 lines
            temp_srt = os.path.join(folder_path, 'temp_captions.srt')
            text_case = self.settings.get('text_case', 'title')
            CaptionGenerator.create_srt_file(captions, temp_srt, max_words=15, max_chars=75, text_case=text_case)
            
            # Build and run FFmpeg command
            if progress_callback:
                progress_callback(20, f"Assembling video with {num_images} image(s)...")
            
            ffmpeg_builder = FFmpegCommandBuilder(self.settings, self.config)
            ffmpeg_cmd = ffmpeg_builder.build_command(
                files, temp_srt, duration, output_path, use_gpu
            )
            
            logger.info("Running FFmpeg...")
            logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

            # Prepare environment for bundled fonts (EB Garamond)
            env = os.environ.copy()
            font = self.settings.get('font', 'Arial Bold')

            if 'EB Garamond' in font:
                # Use bundled EB Garamond fonts by setting fontconfig file
                fonts_dir = get_resource_path('resources/fonts')
                fonts_conf = os.path.join(fonts_dir, 'fonts.conf')

                if os.path.exists(fonts_conf):
                    # Set fontconfig to use our custom configuration
                    env['FONTCONFIG_FILE'] = fonts_conf
                    env['FONTCONFIG_PATH'] = fonts_dir
                    logger.info(f"Using bundled EB Garamond fonts from: {fonts_dir}")
                    logger.info(f"Fontconfig file: {fonts_conf}")

            # Execute FFmpeg with progress tracking
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            
            last_update_progress = 0
            stderr_output = []
            
            for line in process.stderr:
                stderr_output.append(line)
                
                if progress_callback:
                    progress, status = FFmpegCommandBuilder.parse_progress(line, duration)
                    if progress > last_update_progress:
                        last_update_progress = progress
                        progress_callback(progress, status)
            
            process.wait()
            
            if progress_callback and process.returncode == 0:
                progress_callback(99, "Finalizing video...")
            
            # Cleanup
            if os.path.exists(temp_srt):
                os.remove(temp_srt)
            
            # Check result
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


class BatchRenderer:
    """Handles parallel rendering of multiple videos"""
    
    def __init__(self, settings: Dict, max_workers: int = 2):
        """
        Initialize batch renderer
        
        Args:
            settings: Video style settings
            max_workers: Maximum number of parallel renders
        """
        self.settings = settings
        self.max_workers = max_workers
        self.processors = []
        
        # Create processor pool
        for _ in range(max_workers):
            self.processors.append(VideoProcessor(settings))
    
    def process_queue(
        self,
        video_folders: List[str],
        progress_callbacks: Dict[str, Callable]
    ) -> List[Tuple[str, bool, str]]:
        """
        Process multiple videos in parallel
        
        Args:
            video_folders: List of video project folder paths
            progress_callbacks: Dict mapping folder paths to progress callbacks
            
        Returns:
            List of (folder_path, success, output_path) tuples
        """
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