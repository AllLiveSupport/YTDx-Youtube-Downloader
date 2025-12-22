# Tech Context

## Technology Stack
- **Language**: Python 3.7+
- **GUI Framework**: PyQt6 (Qt 6 bindings for Python)
- **Core Library**: `pytubefix` (Fork/fix of pytube for YouTube interaction)

## External Dependencies
- **FFmpeg**: Required for merging video/audio streams and format conversion. The app expects `ffmpeg.exe` in PATH or capable of manual selection.

## Python Libraries
| Library | Purpose |
|---------|---------|
| `pytubefix` | YouTube video extraction and stream analysis |
| `PyQt6` | User Interface creation |
| `Pillow` | Image processing for thumbnails |
| `mutagen` | Metadata tagging (ID3 for MP3, MP4 tags for M4A) |
| `requests` | HTTP requests for thumbnails |

## Development Setup
- **Requirements**: `pip install -r requirements.txt`
- **Execution**: `python main.py`
- **Structure**:
    - `src/`: Source code modules.
    - `languages/`: JSON translation files.
    - `logs/`: Application logs.
    - `icons/`: Resources.

## Constraints
- **FFmpeg**: Must be present for high-quality downloads (merging audio/video).
- **Network**: Heavy reliance on YouTube's structure; `pytubefix` updates are critical if YouTube changes their API/DOM.
- **Platform**: Primarily developed for Windows (uses `subprocess.STARTUPINFO` for burying console windows), but likely cross-platform compatible with minor adjustments.
