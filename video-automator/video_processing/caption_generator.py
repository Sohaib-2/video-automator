"""
Caption Generator - IMPROVED
Creates SRT subtitle files with smart sentence splitting using HYBRID approach
Combines word limits + character limits + FFmpeg auto-wrapping safety net
"""

import logging
from typing import List, Dict
import re

logger = logging.getLogger(__name__)


class CaptionGenerator:
    """Handles SRT subtitle file generation with intelligent wrapping"""

    @staticmethod
    def apply_text_case(text: str, text_case: str = 'title') -> str:
        """
        Apply text case transformation to caption text

        Args:
            text: Original caption text
            text_case: Case style - 'title', 'upper', or 'normal'

        Returns:
            Transformed text
        """
        if text_case == 'upper':
            return text.upper()
        elif text_case == 'title':
            return text.title()
        else:  # 'normal' or any other value
            return text

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
    def wrap_caption_text(text: str, max_line_chars: int = 40) -> str:
        """
        Wrap long caption text by inserting line breaks at appropriate positions.
        This ensures captions display on 2 lines when they're too long for 1 line.

        Args:
            text: Caption text to wrap
            max_line_chars: Maximum characters per line before wrapping (default: 40)

        Returns:
            Text with line breaks inserted where appropriate
        """
        # If text is short enough, no wrapping needed
        if len(text) <= max_line_chars:
            return text

        # Find the best place to break (near middle, at a space)
        words = text.split()
        if len(words) <= 1:
            # Single long word - can't wrap nicely
            return text

        # Build lines by adding words until we exceed half the max length
        target_break = len(text) // 2
        current_line = []
        current_length = 0

        for i, word in enumerate(words):
            word_length = len(word)

            # Would adding this word exceed our target?
            if current_length + word_length > target_break and current_line:
                # Found a good breaking point
                line1 = ' '.join(current_line)
                line2 = ' '.join(words[i:])
                result = f"{line1}\n{line2}"
                logger.debug(f"Wrapped: '{text}' → '{result}'")
                return result

            current_line.append(word)
            current_length += word_length + 1  # +1 for space

        # If we got here, just return original (shouldn't happen)
        return text
    
    @staticmethod
    def split_into_shorter_segments(captions: List[Dict], max_words: int = 12, max_chars: int = 50) -> List[Dict]:
        """
        HYBRID APPROACH: Split long captions with word AND character limits

        This prevents both:
        - Long sentences from overflowing (word limit)
        - Individual long words from going off-screen (char limit)

        FFmpeg will still auto-wrap within these segments as a safety net.

        Args:
            captions: List of caption dictionaries with 'start', 'end', 'text'
            max_words: Maximum words per caption segment (default: 12 = ~2 lines max)
            max_chars: Maximum characters per caption (default: 50 = ensures 2-line wrapping)

        Returns:
            List of optimally-split caption segments
        """
        result = []
        
        for caption in captions:
            text = caption['text'].strip()
            words = text.split()
            duration = caption['end'] - caption['start']
            
            # Quick check: Does it already fit nicely?
            if len(words) <= max_words and len(text) <= max_chars:
                result.append(caption)
                logger.debug(f"✓ Caption OK: '{text}' ({len(words)} words, {len(text)} chars)")
                continue
            
            # Need to split - build chunks with BOTH limits
            chunks = []
            current_chunk = []
            current_length = 0
            
            for word in words:
                word_length = len(word)
                
                # Calculate what would happen if we add this word
                would_exceed_words = len(current_chunk) >= max_words
                would_exceed_chars = (current_length + word_length + 1) > max_chars  # +1 for space
                
                # Check for natural breaking points (punctuation)
                is_natural_break = word.endswith((',', '.', '!', '?', ';', ':'))
                near_word_limit = len(current_chunk) >= max_words // 2  # At least halfway
                
                # Decide: Should we break here?
                should_break = (
                    would_exceed_words or 
                    would_exceed_chars or 
                    (is_natural_break and near_word_limit)
                )
                
                if should_break and current_chunk:
                    # Finalize current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(chunk_text)
                    logger.debug(f"  → Chunk: '{chunk_text}' ({len(current_chunk)} words, {len(chunk_text)} chars)")
                    
                    # Start new chunk
                    current_chunk = []
                    current_length = 0
                
                # Add word to current chunk
                current_chunk.append(word)
                current_length += word_length + 1  # +1 for space between words
            
            # Don't forget the last chunk!
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                logger.debug(f"  → Chunk: '{chunk_text}' ({len(current_chunk)} words, {len(chunk_text)} chars)")
            
            # Safety check
            if not chunks:
                logger.warning(f"⚠ No chunks created for: '{text}' - using original")
                result.append(caption)
                continue
            
            # Distribute timing evenly across chunks
            num_chunks = len(chunks)
            time_per_chunk = duration / num_chunks
            
            for i, chunk in enumerate(chunks):
                result.append({
                    'start': caption['start'] + (i * time_per_chunk),
                    'end': caption['start'] + ((i + 1) * time_per_chunk),
                    'text': chunk
                })
            
            logger.info(f"✂ Split: '{text[:40]}...' → {num_chunks} segments")
        
        logger.info(f"📊 Caption splitting: {len(captions)} original → {len(result)} final segments")
        return result
    
    @staticmethod
    def create_srt_file(captions: List[Dict], output_path: str, split_long: bool = True, max_words: int = 12, max_chars: int = 50, text_case: str = 'title'):
        """
        Create SRT subtitle file from captions with intelligent splitting

        Args:
            captions: List of caption dictionaries with 'start', 'end', 'text'
            output_path: Path where SRT file will be saved
            split_long: Whether to split long captions (RECOMMENDED: True)
            max_words: Maximum words per caption (default: 12 = ~2 lines)
            max_chars: Maximum characters per caption (default: 50 = ensures 2-line wrapping)
            text_case: Text case style - 'title', 'upper', or 'normal' (default: 'title')
        """
        # Apply smart splitting if enabled
        if split_long:
            logger.info("🔧 Applying HYBRID caption splitting (word + char limits)...")
            captions = CaptionGenerator.split_into_shorter_segments(captions, max_words, max_chars)
        else:
            logger.warning("⚠ Caption splitting disabled - long captions may overflow!")

        # Write SRT file with text case transformation and wrapping
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                start_time = CaptionGenerator.format_timestamp(caption['start'])
                end_time = CaptionGenerator.format_timestamp(caption['end'])

                # Apply text case transformation
                caption_text = CaptionGenerator.apply_text_case(caption['text'], text_case)

                # Apply wrapping to ensure long captions split to 2 lines
                caption_text = CaptionGenerator.wrap_caption_text(caption_text, max_line_chars=40)

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption_text}\n\n")
        
        logger.info(f"✅ SRT file created: {output_path} ({len(captions)} caption segments)")
        
        # Log sample
        if captions:
            sample = captions[0]
            logger.info(f"📝 Sample: '{sample['text']}' @ {sample['start']:.2f}s ({len(sample['text'])} chars)")