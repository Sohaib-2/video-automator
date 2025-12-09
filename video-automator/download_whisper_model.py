"""
Download Whisper Base Model
Run this once to download the model for bundling
"""

import whisper
import os
import shutil

print("Downloading Whisper base model...")
model = whisper.load_model("base")
print("Model downloaded successfully!")

# Find where whisper cached it
cache_dir = os.path.expanduser("~/.cache/whisper")
model_file = os.path.join(cache_dir, "base.pt")

# Create models directory in project
project_models_dir = "video-automator/models"
os.makedirs(project_models_dir, exist_ok=True)

# Copy to project
destination = os.path.join(project_models_dir, "base.pt")
if os.path.exists(model_file):
    shutil.copy2(model_file, destination)
    print(f"Model copied to: {destination}")

    # Get file size
    size_mb = os.path.getsize(destination) / (1024 * 1024)
    print(f"Model size: {size_mb:.1f} MB")
else:
    print("Could not find cached model file")
    print(f"Expected location: {model_file}")
