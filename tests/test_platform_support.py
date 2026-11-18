"""Tests for platform_support.py.

Each OS branch is tested on every runner by faking the platform flags and mocking the OS tools,
plus a few "real" tests that only run on their native OS.
"""
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

import platform_support as ps


def fake_platform(name):
    """Patch the IS_* flags so the module behaves as if running on `name`."""
    return mock.patch.multiple(ps, IS_WINDOWS=name == "windows", IS_MAC=name == "mac", IS_LINUX=name == "linux")


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


# ---------- Platform detection ----------

def test_exactly_one_platform_flag_matches_current_os():
    assert [ps.IS_WINDOWS, ps.IS_MAC, ps.IS_LINUX].count(True) == 1
    assert ps.IS_WINDOWS == (sys.platform == "win32")
    assert ps.IS_MAC == (sys.platform == "darwin")
    assert ps.IS_LINUX == sys.platform.startswith("linux")


def test_unknown_action_raises():
    with pytest.raises(ValueError):
        ps.send_media_command("rewind")


# ---------- Linux (playerctl) ----------

@pytest.mark.parametrize("action, expected_arg", [("previous", "previous"), ("play_pause", "play-pause"), ("next", "next")])
def test_linux_send_command_uses_playerctl(action, expected_arg):
    with fake_platform("linux"), mock.patch.object(ps.shutil, "which", return_value="/usr/bin/playerctl"), \
            mock.patch.object(ps.subprocess, "run", return_value=completed()) as run:
        assert ps.send_media_command(action) is True
    assert run.call_args[0][0] == ["playerctl", "--player=spotify", expected_arg]


def test_linux_title_from_playerctl():
    with fake_platform("linux"), mock.patch.object(ps.shutil, "which", return_value="/usr/bin/playerctl"), \
            mock.patch.object(ps.subprocess, "run", return_value=completed("Bella Ciao\n")):
        assert ps.local_playing_title() == "Bella Ciao"


def test_linux_without_playerctl_falls_back():
    with fake_platform("linux"), mock.patch.object(ps.shutil, "which", return_value=None), \
            mock.patch.object(ps.subprocess, "run") as run:
        assert ps.local_playing_title() is None
        assert ps.send_media_command("next") is False
    run.assert_not_called()


def test_linux_spotify_not_running_returns_none():
    with fake_platform("linux"), mock.patch.object(ps.shutil, "which", return_value="/usr/bin/playerctl"), \
            mock.patch.object(ps.subprocess, "run", return_value=completed("", returncode=1)):
        assert ps.local_playing_title() is None
        assert ps.send_media_command("next") is False


# ---------- macOS (osascript) ----------

@pytest.mark.parametrize("action, expected", [("previous", "previous track"), ("play_pause", "playpause"), ("next", "next track")])
def test_mac_send_command_uses_osascript(action, expected):
    with fake_platform("mac"), mock.patch.object(ps.subprocess, "run", return_value=completed()) as run:
        assert ps.send_media_command(action) is True
    cmd = run.call_args[0][0]
    assert cmd[:2] == ["osascript", "-e"]
    assert cmd[2] == f'tell application "Spotify" to {expected}'


def test_mac_title_from_osascript():
    with fake_platform("mac"), mock.patch.object(ps.subprocess, "run", return_value=completed("Bella Ciao\n")):
        assert ps.local_playing_title() == "Bella Ciao"


def test_mac_osascript_missing_falls_back():
    with fake_platform("mac"), mock.patch.object(ps.subprocess, "run", side_effect=FileNotFoundError):
        assert ps.local_playing_title() is None
        assert ps.send_media_command("play_pause") is False


def test_mac_spotify_not_running_skips_applescript():
    with fake_platform("mac"), mock.patch.object(ps.subprocess, "run", return_value=completed("", returncode=1)) as run:
        assert ps.local_playing_title() is None
        assert ps.send_media_command("next") is False
    assert all(call[0][0][0] == "pgrep" for call in run.call_args_list)  # osascript never called


def test_command_timeout_falls_back():
    with fake_platform("mac"), mock.patch.object(ps.subprocess, "run", side_effect=subprocess.TimeoutExpired("osascript", 3)):
        assert ps.send_media_command("next") is False


# ---------- Windows (pywin32 / winsdk) ----------

def fake_win32():
    win32con = SimpleNamespace(VK_MEDIA_PREV_TRACK=0xB1, VK_MEDIA_PLAY_PAUSE=0xB3, VK_MEDIA_NEXT_TRACK=0xB0, KEYEVENTF_EXTENDEDKEY=1)
    return mock.MagicMock(), win32con


@pytest.mark.parametrize("action, key", [("previous", 0xB1), ("play_pause", 0xB3), ("next", 0xB0)])
def test_windows_send_command_presses_media_key(action, key):
    win32api, win32con = fake_win32()
    with fake_platform("windows"), mock.patch.object(ps, "win32api", win32api, create=True), \
            mock.patch.object(ps, "win32con", win32con, create=True):
        assert ps.send_media_command(action) is True
    win32api.keybd_event.assert_called_once_with(key, 0, 1, 0)


def test_windows_without_pywin32_falls_back():
    with fake_platform("windows"), mock.patch.object(ps, "win32api", None, create=True), \
            mock.patch.object(ps, "MediaManager", None, create=True):
        assert ps.send_media_command("next") is False
        assert ps.local_playing_title() is None


def test_windows_media_session_error_is_caught():
    async def boom():
        raise OSError("COM failure")

    with fake_platform("windows"), mock.patch.object(ps, "MediaManager", object(), create=True), \
            mock.patch.object(ps, "_windows_media_title", boom):
        assert ps.local_playing_title() is None


def test_windows_taskbar_offset_from_work_area():
    win32api, _ = fake_win32()
    win32api.GetMonitorInfo.return_value = {"Work": (0, 0, 1920, 1032)}
    with fake_platform("windows"), mock.patch.object(ps, "win32api", win32api, create=True):
        assert ps.bottom_screen_offset(1080) == 48


def test_windows_taskbar_offset_fallback_on_error():
    win32api, _ = fake_win32()
    win32api.MonitorFromPoint.side_effect = RuntimeError
    with fake_platform("windows"), mock.patch.object(ps, "win32api", win32api, create=True):
        assert ps.bottom_screen_offset(1080) == 60


# ---------- Shared behaviour ----------

def test_is_playing_locally_compares_titles():
    with mock.patch.object(ps, "local_playing_title", return_value="Bella Ciao"):
        assert ps.is_playing_locally("Bella Ciao") is True
        assert ps.is_playing_locally("NOKIA") is False
    with mock.patch.object(ps, "local_playing_title", return_value=None):
        assert ps.is_playing_locally("Bella Ciao") is False


@pytest.mark.parametrize("name, expected", [("mac", 80), ("linux", 48)])
def test_non_windows_offsets(name, expected):
    with fake_platform(name):
        assert ps.bottom_screen_offset(1080) == expected


@pytest.mark.parametrize("name, called", [("windows", True), ("mac", False), ("linux", False)])
def test_transparency_only_applied_on_windows(name, called):
    root = mock.MagicMock()
    with fake_platform(name):
        ps.apply_window_transparency(root, "grey")
    assert root.wm_attributes.called is called


# ---------- Real, unmocked calls on the native OS (Spotify isn't running on CI) ----------

def test_native_calls_do_not_crash():
    title = ps.local_playing_title()
    assert title is None or isinstance(title, str)
    assert isinstance(ps.bottom_screen_offset(1080), int)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_windows_dependencies_installed():
    assert ps.win32api is not None and ps.MediaManager is not None
