# System Patterns

## Architecture
The application follows a modular structure separating various concerns:

### 1. Entry Point (`main.py`)
- Initializes the `QApplication`.
- Sets up `logging`.
- Loads `LanguageManager` preferences.
- Launches `MainWindow`.
- Handles application restart logic.

### 2. GUI Layer (`src/gui.py`, `src/custom_widgets.py`)
- **MainWindow**: The central hub. Manages tabs (Download, Audio, Settings).
- **DownloadThread**: A `QThread` subclass that offloads blocking download tasks. communicating back via Signals (`progress_signal`, `status_signal`, `finished_signal`).
- **Widgets**: Custom widgets like `TranslatedLineEdit` provide context menus with localized text.

### 3. Logic Layer (`src/downloader.py`)
- **Downloader**: Main facade for operations.
  - Handles `pytubefix` interactions.
  - Manages `FFmpegManager`.
  - Implements retry logic and error handling.
- **FFmpegManager**: specialized class for detecting and running FFmpeg commands.
- **Callbacks**: Uses callback pattern to report progress to the GUI/Thread.

### 4. Infrastructure Layer (`src/language.py`)
- **LanguageManager**: Singleton handling loading JSON translations and saving preferences to `config.json`.

## Design Patterns
- **Singleton**: Used for `LanguageManager` to ensure global access to settings/translations.
- **Observer/Signals**: PyQt Signals/Slots used extensively for async updates from background threads to UI.
- **Facade**: `Downloader` class acts as a facade over `pytubefix` and `ffmpeg`, simplifying the interface for the GUI.
- **Strategy**: (Implicit) Selection of best video/audio streams based on quality settings.

## Data Flow
1.  User Input (GUI) -> `DownloadThread` (Start)
2.  `DownloadThread` -> `Downloader` (Execute)
3.  `Downloader` -> `pytubefix` (Download streams) -> `FFmpegManager` (Merge) -> `mutagen` (Tag)
4.  Updates -> `progress_callback` -> `DownloadThread` -> Signal -> GUI Update
