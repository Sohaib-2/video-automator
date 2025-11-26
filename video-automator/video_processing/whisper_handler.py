"""
Whisper Handler
Manages Whisper model loading and audio transcription with GPU/CPU fallback
"""

import logging
import whisper
import torch
from typing import List, Dict
from utils.resource_path import get_resource_path
import os

logger = logging.getLogger(__name__)


class WhisperHandler:
    """Handles Whisper model loading and transcription"""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.cuda_available = torch.cuda.is_available()
        self.failed_gpu = False
        
        if self.cuda_available:
            logger.info("CUDA detected - will attempt GPU acceleration for Whisper")
        else:
            logger.info("No CUDA detected - will use CPU for Whisper")
    
    def load_model(self, model_size: str = "base"):
        # Check for bundled model first
        bundled_model = get_resource_path(f"models/{model_size}.pt")
        
        if self.cuda_available and not self.failed_gpu:
            try:
                logger.info(f"Loading Whisper model '{model_size}' on GPU (CUDA)...")
                
                # Use bundled model if exists
                if os.path.exists(bundled_model):
                    logger.info(f"Using bundled model: {bundled_model}")
                    self.model = whisper.load_model(bundled_model, device="cuda")
                else:
                    logger.info("Downloading model (first time only)...")
                    self.model = whisper.load_model(model_size, device="cuda")
                
                self.device = "cuda"
                logger.info("✓ Whisper model loaded successfully on GPU")
                return
            except Exception as e:
                logger.warning(f"⚠ GPU loading failed: {str(e)}")
                logger.info("Falling back to CPU...")
                self.failed_gpu = True
        
        try:
            logger.info(f"Loading Whisper model '{model_size}' on CPU...")
            
            # Use bundled model if exists
            if os.path.exists(bundled_model):
                logger.info(f"Using bundled model: {bundled_model}")
                self.model = whisper.load_model(bundled_model, device="cpu")
            else:
                logger.info("Downloading model (first time only)...")
                self.model = whisper.load_model(model_size, device="cpu")
            
            self.device = "cpu"
            logger.info("✓ Whisper model loaded successfully on CPU")
        except Exception as e:
            logger.error(f"✗ Failed to load Whisper model: {str(e)}")
            raise
    def transcribe(self, audio_path: str) -> List[Dict]:
        """
        Transcribe audio file to generate caption segments
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of caption dictionaries with 'start', 'end', 'text' keys
        """
        if not self.model:
            self.load_model()
        
        logger.info(f"Transcribing audio: {audio_path} (device: {self.device})")
        
        transcribe_options = {
            'word_timestamps': True,
            'verbose': False
        }
        
        if self.device == "cuda":
            transcribe_options['fp16'] = False
            logger.info("Using FP32 precision on GPU (more stable)")
        
        try:
            result = self.model.transcribe(audio_path, **transcribe_options)
            
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
            logger.error(f"✗ Transcription failed on {self.device}: {str(e)}")
            
            if self.device == "cuda" and not self.failed_gpu:
                logger.warning("⚠ GPU transcription failed, retrying on CPU...")
                self.failed_gpu = True
                self.model = None
                self.load_model()
                return self.transcribe(audio_path)
            else:
                logger.error("Cannot recover from transcription error")
                raise