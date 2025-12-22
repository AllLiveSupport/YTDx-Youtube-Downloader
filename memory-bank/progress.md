# Progress

## Completed Features
- [x] **Core Architecture**: Modular setup with `main`, `gui`, `downloader`, `language`.
- [x] **Video Download**:
    - [x] Resolution selection (up to 4K).
    - [x] Video/Audio merging via FFmpeg.
- [x] **Audio Download**:
    - [x] MP3 and M4A support.
    - [x] Thumbnail embedding.
    - [x] Metadata tagging.
- [x] **Playlist Support**:
    - [x] Video playlists.
    - [x] Audio playlists.
- [x] **UI/UX**:
    - [x] Modern PyQt6 interface.
    - [x] Dark/Light theme switching.
    - [x] Multi-language support (TR, EN, ES, RU).
    - [x] Progress bars and status updates.
- [x] **Settings**:
    - [x] Custom FFmpeg path selection.
    - [x] Cache clearing.
    - [x] Download folder selection.

## Known Issues / Limitations
- **YouTube API Changes**: Susceptible to breaking if YouTube updates their player logic (mitigated by using `pytubefix`).
- **FFmpeg Dependency**: Requires external binary, though handling is robust.

## Upcoming Tasks
- [ ] **Data Persistence**: Save download history (partially implemented with `download_history.json` presence?).
- [ ] **GitHub Integration**: Upload project to version control.
