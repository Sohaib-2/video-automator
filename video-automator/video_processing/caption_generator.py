"""
Caption Generator
Creates SRT subtitle files from caption data with smart sentence splitting
"""

import logging
from typing import List, Dict
import re

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
    def split_into_shorter_segments(captions: List[Dict], max_words: int = 8) -> List[Dict]:
        """
        Split long captions into shorter segments to prevent multi-line wrapping
        
        Args:
            captions: List of caption dictionaries with 'start', 'end', 'text'
            max_words: Maximum words per caption segment
            
        Returns:
            List of split caption segments
        """
        result = []
        
        for caption in captions:
            text = caption['text'].strip()
            words = text.split()
            duration = caption['end'] - caption['start']
            
            # If caption is short enough, keep as is
            if len(words) <= max_words:
                result.append(caption)
                continue
            
            # Split into chunks
            chunks = []
            current_chunk = []
            
            for word in words:
                current_chunk.append(word)
                
                # Split at natural breaks (commas, periods) or at max_words
                if len(current_chunk) >= max_words or (
                    word.endswith((',', '.', '!', '?')) and len(current_chunk) >= max_words // 2
                ):
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
            
            # Add remaining words
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Create new caption segments with proportional timing
            num_chunks = len(chunks)
            time_per_chunk = duration / num_chunks
            
            for i, chunk in enumerate(chunks):
                result.append({
                    'start': caption['start'] + (i * time_per_chunk),
                    'end': caption['start'] + ((i + 1) * time_per_chunk),
                    'text': chunk
                })
                logger.debug(f"Split caption into {num_chunks} segments: '{chunk[:30]}...'")
        
        return result
    
    @staticmethod
    def create_srt_file(captions: List[Dict], output_path: str, split_long: bool = True, max_words: int = 8):
        """
        Create SRT subtitle file from captions
        
        Args:
            captions: List of caption dictionaries with 'start', 'end', 'text'
            output_path: Path where SRT file will be saved
            split_long: Whether to split long captions into shorter segments
            max_words: Maximum words per caption when splitting
        """
        # Split long captions if enabled
        if split_long:
            captions = CaptionGenerator.split_into_shorter_segments(captions, max_words)
        
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