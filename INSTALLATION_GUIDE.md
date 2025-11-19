# Video Automator - Installation & Usage Guide

## 🚀 Complete Installation Guide

### Step 1: Install FFmpeg (Required)

FFmpeg is the core video processing engine. Install it based on your OS:

#### Windows
1. Download from: https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add to PATH:
   - Right-click "This PC" → Properties → Advanced System Settings
   - Environment Variables → System Variables → Path → Edit
   - Add: `C:\ffmpeg\bin`
4. Restart terminal and test: `ffmpeg -version`

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

### Step 2: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# OR install individually:
pip install PyQt5
pip install openai-whisper
pip install moviepy
pip install ffmpeg-python
pip install torch torchaudio
```

**Note:** First run will download the Whisper model (~140MB for 'base' model)

### Step 3: Verify Installation

```bash
# Check FFmpeg
ffmpeg -version

# Check if GPU is available (optional)
nvidia-smi

# Run the app
python video_automator.py
```

---

## 📖 How to Use

### 1. First Time Setup

1. **Launch the app:**
   ```bash
   python video_automator.py
   ```

2. **Configure caption settings (one-time):**
   - Click the **⚙️ Settings** button
   - Choose your font (Arial Bold recommended for YouTube)
   - Set font size (48px is standard)
   - Pick text color (White or Yellow for visibility)
   - Select background color (Black for contrast)
   - Adjust opacity (80% recommended)
   - Choose position (Bottom Center for YouTube)
   - Click **Save Settings**

### 2. Prepare Your Video Folders

Each video project needs its own folder with these files:

```
my_video_project_1/
├── voiceover.mp3      # Your audio (can be .wav, .m4a, etc.)
├── script.txt         # Optional - Whisper will auto-generate if missing
├── image1.png         # First image (shows 0:00 to middle)
└── image2.png         # Second image (shows middle to end)
```

**File naming is flexible:**
- Audio: `voiceover.mp3`, `audio.wav`, or any audio file
- Images: `image1.png`, `img1.jpg`, `1.png` (and same for image2)
- Script: `script.txt` (optional)

### 3. Add Videos to Queue

1. Click **📂 Add Folders**
2. Select your video project folder
3. Repeat for each video you want to process
4. All videos appear in the queue

### 4. Start Batch Rendering

1. Click **▶️ Start Batch Render**
2. Choose how many videos to render simultaneously:
   - **1 video:** Slowest, most stable
   - **2 videos:** Good balance (recommended)
   - **3 videos:** Faster (needs good PC)
   - **4 videos:** Maximum speed (requires powerful PC with 16GB+ RAM)
3. Watch progress bars update in real-time
4. Videos are saved to: `~/VideoAutomator_Output/`

### 5. Find Your Videos

Output location: `~/VideoAutomator_Output/`
- Windows: `C:\Users\YourName\VideoAutomator_Output\`
- macOS/Linux: `/home/yourusername/VideoAutomator_Output/`

Files are named: `{folder_name}.mp4`

---

## ⚙️ Technical Details

### Video Processing Pipeline

1. **File Detection**
   - Scans folder for required files
   - Validates all files exist
   - Shows error if missing files

2. **Caption Generation (Whisper)**
   - Loads local Whisper model (first run downloads ~140MB)
   - Transcribes audio with word-level timestamps
   - Generates SRT subtitle file
   - Time: ~2-3 minutes for 25-min video

3. **Video Assembly (FFmpeg)**
   - Scales images to 1920x1080
   - Applies Ken Burns zoom effect
   - Concatenates image1 + image2
   - Burns in captions with your styling
   - Syncs with voiceover audio
   - Outputs 1080p MP4 (H.264)

4. **Parallel Rendering**
   - Multiple videos process simultaneously
   - Each video gets its own CPU/GPU resources
   - Queue system manages order
   - Real-time progress tracking

### Performance Benchmarks

**For 25-minute video:**

| Hardware | Single Video | 4 Videos (Parallel) |
|----------|--------------|---------------------|
| CPU only | ~15-20 mins | ~60-80 mins total |
| With NVIDIA GPU | ~7-10 mins | ~30-40 mins total |

**Recommended Specs:**
- **Minimum:** 8GB RAM, 4-core CPU
- **Recommended:** 16GB RAM, 6-core CPU, NVIDIA GPU
- **Optimal:** 32GB RAM, 8-core CPU, RTX 3060+

### GPU Acceleration

The app automatically detects and uses NVIDIA GPUs:
- ✅ Uses `h264_nvenc` encoder (5-10x faster)
- ✅ Fallback to CPU if GPU unavailable
- ✅ No configuration needed

Check if GPU is available:
```bash
nvidia-smi
```

### Whisper Model Sizes

You can change the model in `video_processor.py`:

| Model | Speed | Accuracy | Size |
|-------|-------|----------|------|
| tiny | Fastest | Lowest | 39 MB |
| base | Fast | Good | 74 MB ⭐ (default) |
| small | Medium | Better | 244 MB |
| medium | Slow | Great | 769 MB |
| large | Slowest | Best | 1.5 GB |

To change model, edit `video_processor.py` line ~30:
```python
self.whisper_model = whisper.load_model("small")  # Change "base" to "small"
```

---

## 🎨 Customization

### Caption Styling

All customizable in Settings dialog:

1. **Fonts:**
   - Arial, Arial Bold
   - Helvetica, Roboto
   - Montserrat, Open Sans
   - Lato, Poppins
   - Oswald, Raleway

2. **Colors:**
   - Text: Any hex color (#FFFFFF)
   - Background: Any hex color (#000000)
   - Opacity: 0-100%

3. **Position:**
   - Top Center
   - Middle Center
   - Bottom Center (recommended)

### Effects

Edit `video_processor.py` to customize:

**Zoom Speed** (line ~270):
```python
zoompan=z='min(zoom+0.0015,1.5)'  # Change 0.0015 for faster/slower zoom
```

**Video Quality** (line ~320):
```python
'-b:v', '5M',  # Bitrate: Higher = better quality but larger file
```

**Audio Quality** (line ~330):
```python
'-b:a', '192k',  # Audio bitrate: 192k is high quality
```

---

## 🐛 Troubleshooting

### "FFmpeg Not Found"
- **Solution:** Install FFmpeg and add to PATH (see Step 1)
- Test with: `ffmpeg -version`

### "Missing files" error
- **Check:** Each folder has voiceover audio, image1, and image2
- File names can be flexible (image1.png, img1.jpg, 1.png all work)

### Slow rendering
- **Use GPU:** Install NVIDIA drivers and CUDA
- **Reduce parallel renders:** Use 1-2 instead of 3-4
- **Use smaller Whisper model:** Change to "tiny" or "base"

### Out of memory
- **Reduce parallel renders:** Use 1-2 videos at a time
- **Close other apps:** Free up RAM
- **Upgrade RAM:** 16GB+ recommended for 3+ parallel renders

### Captions not appearing
- **Check SRT file:** Temp file created during processing
- **Verify audio:** Make sure voiceover has clear speech
- **Try different Whisper model:** "small" or "medium" more accurate

### GPU not detected
- **Install NVIDIA drivers:** https://nvidia.com/drivers
- **Check with:** `nvidia-smi`
- **App works without GPU:** Just slower (uses CPU)

---

## 📊 File Sizes

**Input (per video):**
- Images: ~1-5 MB each
- Audio (25 min): ~20-50 MB
- Total input: ~25-60 MB

**Output (per video):**
- 1080p MP4 (25 min): ~700-900 MB
- Depends on bitrate and content

---

## 🔄 Updates & Features

### Current Version: 1.0

**Included:**
- ✅ Batch video processing
- ✅ Auto caption generation (Whisper)
- ✅ Parallel rendering (2-4 videos)
- ✅ GPU acceleration
- ✅ Custom caption styling
- ✅ Ken Burns zoom effect
- ✅ 1080p output
- ✅ Progress tracking

**Coming Soon:**
- ⏳ Drag & drop folder support
- ⏳ Custom transitions
- ⏳ More zoom/pan effects
- ⏳ Background music mixing
- ⏳ Render presets
- ⏳ Estimated time remaining

---

## 💡 Tips & Best Practices

1. **Audio Quality:**
   - Use clear voiceover with minimal background noise
   - 48kHz sample rate recommended
   - Mono or stereo both work

2. **Image Requirements:**
   - Minimum: 1920x1080 pixels
   - Higher resolution OK (will be scaled)
   - PNG or JPG format
   - Landscape orientation recommended

3. **Batch Processing:**
   - Queue all videos before starting
   - Let it run overnight for large batches
   - Don't close app while rendering

4. **Storage:**
   - Ensure enough disk space (1GB per 25-min video)
   - SSD recommended for faster rendering
   - Output directory auto-created

5. **Performance:**
   - Close other apps during rendering
   - Use GPU for 5-10x speedup
   - 2-3 parallel renders optimal for most PCs

---

## 📞 Support

For issues or questions:
1. Check this guide first
2. Verify FFmpeg is installed
3. Check system requirements
4. Review troubleshooting section

---

## 📄 License

This project is for personal use.

Enjoy automated video editing! 🎬🚀
