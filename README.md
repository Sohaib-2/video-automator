# Video Automator - Batch Video Editor

A desktop application for automating repetitive YouTube video editing tasks.

## What We've Built So Far

### ✅ Complete UI Implementation

The application includes:

1. **Main Window**
   - Clean, modern interface
   - Add folders button (drag & drop style)
   - Video queue display with progress bars
   - Start/Clear buttons for batch operations
   - Status bar for feedback

2. **Settings Dialog**
   - Font selection (10 YouTube-friendly fonts)
   - Font size control (20-100px)
   - Caption position (Top/Middle/Bottom Center)
   - Text color picker with preset colors
   - Background color picker
   - Background opacity control (0-100%)
   - Live preview of caption styling

3. **Video Queue System**
   - Custom list items for each video
   - Progress bars for each video
   - Status labels (Queued → Processing → Complete)
   - Visual feedback with icons and colors

4. **Settings Persistence**
   - Settings saved to `~/.video_automator_config.json`
   - Auto-loads on app restart
   - One-time configuration

## Features

### Current (UI Only)
- ✅ Beautiful, intuitive interface
- ✅ Settings dialog with live preview
- ✅ Video queue management
- ✅ Progress tracking UI
- ✅ Settings persistence
- ⏳ Rendering simulation (for testing)

### To Be Implemented
- ⏳ Actual video processing (FFmpeg/MoviePy)
- ⏳ Whisper caption generation
- ⏳ Parallel rendering (2-4 videos at once)
- ⏳ File detection (voiceover, script, images)
- ⏳ GPU acceleration

## How to Run

```bash
python video_automator.py
```

## UI Walkthrough

### 1. First Time Setup
1. Click **⚙️ Settings** button
2. Configure your caption preferences:
   - Choose font (Arial, Montserrat, etc.)
   - Set font size (recommended: 48px)
   - Select text color (White, Yellow, etc.)
   - Choose background color (Black for contrast)
   - Adjust opacity (80% is good)
   - Select position (Bottom Center recommended)
3. See live preview of your captions
4. Click **Save Settings** - these will be remembered!

### 2. Adding Videos
1. Click **📂 Add Folders**
2. Select a folder containing:
   - Voiceover audio file (.mp3, .wav)
   - script.txt
   - image1.png (first half of video)
   - image2.png (second half of video)
3. Repeat to add multiple folders
4. All videos appear in the queue

### 3. Batch Rendering
1. Click **▶️ Start Batch Render**
2. Watch progress bars update for each video
3. App will process multiple videos simultaneously
4. Walk away - it runs on its own!

## Folder Structure Expected

Each video folder should look like this:

```
video_project_1/
├── voiceover.mp3       (or .wav, .m4a)
├── script.txt          (transcript for captions)
├── image1.png          (displayed 0:00 - 12:30)
└── image2.png          (displayed 12:30 - 25:00)
```

## Technical Details

### Built With
- **Python 3.12**
- **PyQt5** - GUI framework
- **JSON** - Settings storage

### Coming Soon
- **FFmpeg** - Video processing
- **OpenAI Whisper** - Caption generation
- **MoviePy** - Video manipulation
- **Multiprocessing** - Parallel rendering

## Current Status

✅ **Phase 1: UI Design** - COMPLETE
- Main window layout
- Settings dialog
- Queue management
- Progress tracking

⏳ **Phase 2: Core Processing** - NEXT
- File detection
- Whisper integration
- Video assembly
- Caption burning

⏳ **Phase 3: Batch Rendering** - UPCOMING
- Parallel processing
- GPU acceleration
- Error handling
- Output management

## Next Steps

To complete the application, we need to:

1. **Implement file detection**
   - Scan folders for required files
   - Validate file formats
   - Show warnings if files missing

2. **Add Whisper integration**
   - Process voiceover audio
   - Generate timestamped captions
   - Sync with video timeline

3. **Build video processing pipeline**
   - Use FFmpeg/MoviePy
   - Assemble images with transitions
   - Burn in captions
   - Apply effects (zoom, filters)

4. **Implement parallel rendering**
   - Use Python multiprocessing
   - Queue management
   - Progress tracking
   - Error handling

5. **Add GPU acceleration**
   - NVENC for NVIDIA GPUs
   - AMF for AMD GPUs
   - Fallback to CPU

## Screenshots

(UI is now functional - you can open the app and test the interface!)

## License

This project is for personal use.
