"""OS-specific helpers so main.py runs on Windows, macOS and Linux.

Local media control is used when Spotify plays on this computer, so play/pause/next/previous
work without Spotify Premium:
  * Windows - Windows media session (winsdk) + media keys (pywin32)
  * macOS   - AppleScript via `osascript` (talks to the Spotify desktop app)
  * Linux   - MPRIS via `playerctl` (install with your package manager, e.g. `sudo apt install playerctl`)
If the helper isn't available, every function returns False/None and main.py falls back to the Spotify Web API.
"""
import asyncio
import shutil
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    try:
        import win32api
        import win32con
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
    except ImportError:  # Dependencies missing - local control disabled
        win32api = win32con = MediaManager = None

ACTIONS = ("previous", "play_pause", "next")


def _run(cmd, timeout=3):
    """Run a command, return stripped stdout or None on any failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _mac_spotify_running():
    # Checked before any AppleScript: addressing an app that isn't installed pops up a "Where is Spotify?" dialog
    return _run(["pgrep", "-x", "Spotify"]) is not None


# ---------- Currently playing title on this computer ----------

async def _windows_media_title():
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session and session.source_app_user_model_id in ("Chrome", "Spotify.exe"):
        info = await session.try_get_media_properties_async()
        return info.title
    return None


def local_playing_title():
    """Title of the track Spotify is playing on this computer, or None if unknown / not playing here."""
    if IS_WINDOWS:
        if MediaManager is None:
            return None
        try:
            return asyncio.run(_windows_media_title())
        except Exception as e:  # winsdk can raise various COM errors
            print(f"Could not read Windows media session: {e!r}")
            return None
    if IS_MAC:
        if not _mac_spotify_running():
            return None
        return _run(["osascript", "-e", 'tell application "Spotify" to return name of current track']) or None
    if IS_LINUX:
        if not shutil.which("playerctl"):
            return None
        return _run(["playerctl", "--player=spotify", "metadata", "title"]) or None
    return None


def is_playing_locally(track_name):
    title = local_playing_title()
    print(f"Local media title: {title!r}")
    return bool(title) and title == track_name


# ---------- Send play/pause/next/previous on this computer ----------

def send_media_command(action):
    """Control Spotify on this computer. action is one of ACTIONS. Returns True if the command was sent."""
    if action not in ACTIONS:
        raise ValueError(f"Unknown media action: {action}")

    if IS_WINDOWS:
        if win32api is None:
            return False
        key = {"previous": win32con.VK_MEDIA_PREV_TRACK,
               "play_pause": win32con.VK_MEDIA_PLAY_PAUSE,
               "next": win32con.VK_MEDIA_NEXT_TRACK}[action]
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)
        return True
    if IS_MAC:
        if not _mac_spotify_running():
            return False
        command = {"previous": "previous track", "play_pause": "playpause", "next": "next track"}[action]
        return _run(["osascript", "-e", f'tell application "Spotify" to {command}']) is not None
    if IS_LINUX:
        if not shutil.which("playerctl"):
            return False
        command = {"previous": "previous", "play_pause": "play-pause", "next": "next"}[action]
        return _run(["playerctl", "--player=spotify", command]) is not None
    return False


# ---------- Window placement / appearance ----------

def bottom_screen_offset(monitor_height):
    """Pixels reserved at the bottom of the primary screen (taskbar / dock / panel)."""
    if IS_WINDOWS and win32api is not None:
        try:
            work_area = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))["Work"]
            return max(0, monitor_height - work_area[3])
        except Exception:
            return 60
    if IS_MAC:
        return 80  # Typical Dock height
    return 48  # Typical Linux bottom panel; harmless if there is none


def apply_window_transparency(root, color):
    """Make `color` see-through in the window. Only supported by Tk on Windows; no-op elsewhere."""
    if IS_WINDOWS:
        root.wm_attributes("-transparentcolor", color)
