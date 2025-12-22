# Active Context

## Current Work Focus
The project is currently in a stable state with core features implemented. The primary focus is on **Project Analysis** and **Documentation** to prepare for version control (GitHub).

## Recent Changes
- Deep analysis of the codebase performed to understand the structure.
- `memory-bank` documentation created to capture the system state.

## Current State
- **Codebase**: Python source files in `src/`, entry point `main.py`.
- **Dependencies**: `pytubefix`, `PyQt6`, `Pillow`, `mutagen`, `requests` defined in `requirements.txt`.
- **Config**: Local configuration handled via `config.json` (auto-generated).
- **Logging**: Application logs to `ytdx.log`.

## Next Steps
1.  Verify `.gitignore` to ensure cleaner repository.
2.  Initialize Git repository (if not already done).
3.  Upload to GitHub.

## Active Decisions
- **Architecture**: Separated GUI (`gui.py`) from logic (`downloader.py`) to allow for easier maintenance and potential CLI support in the future.
- **Threading**: Downloads run in `QThread` to keep the UI responsive.
- **FFmpeg**: Application checks for system FFmpeg but supports manual path selection to accommodate portable usage.
- **Localization**: Custom `LanguageManager` to handle dynamic language switching.
