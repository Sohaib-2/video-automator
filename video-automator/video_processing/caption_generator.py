"""
Caption Generator
Creates SRT subtitle files from caption data
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class CaptionGenerator:
    """Handles SRT subtitle file generation"""
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def create_srt_file(captions: List[Dict], output_path: str):
        """
        Create SRT subtitle file from captions
        
        Args:
            captions: List of caption dictionaries with 'start', 'end', 'text'
            output_path: Path where SRT file will be saved
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                start_time = CaptionGenerator.format_timestamp(caption['start'])
                end_time = CaptionGenerator.format_timestamp(caption['end'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption['text']}\n\n")
        
        logger.info(f"SRT file created: {output_path} ({len(captions)} captions)")
        
        if captions:
            logger.info(f"Sample caption: '{captions[0]['text']}' at {captions[0]['start']:.2f}s")