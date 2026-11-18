"""Tests for Spotify token refresh (main.py), local playback control and get_refresh_token.py."""
from unittest import mock

import pytest

import get_refresh_token
import main


def response(status, data, reason="OK"):
    r = mock.MagicMock(status_code=status, reason=reason, content=b"x")
    r.json.return_value = data
    return r


@pytest.fixture(autouse=True)
def spotify_globals(monkeypatch):
    # main.py normally sets these in its __main__ block
    monkeypatch.setattr(main, "spotify_refresh_token", "refresh", raising=False)
    monkeypatch.setattr(main, "spotify_base64_token", "base64", raising=False)


# ---------- spotifyapi_refresh_token ----------

def test_refresh_returns_access_token():
    with mock.patch.object(main.requests, "post", return_value=response(200, {"access_token": "abc"})):
        assert main.spotifyapi_refresh_token() == "abc"


def test_refresh_revoked_token_exits_with_message(capsys):
    revoked = response(400, {"error": "invalid_grant", "error_description": "Refresh token revoked"}, "Bad Request")
    with mock.patch.object(main.requests, "post", return_value=revoked), pytest.raises(SystemExit) as exc:
        main.spotifyapi_refresh_token()
    assert exc.value.code == 1
    assert "Refresh token revoked" in capsys.readouterr().out


def test_refresh_retries_after_connection_error():
    with mock.patch.object(main.requests, "post",
                           side_effect=[main.requests.exceptions.ConnectionError, response(200, {"access_token": "abc"})]), \
            mock.patch.object(main.time, "sleep") as sleep:
        assert main.spotifyapi_refresh_token() == "abc"
    sleep.assert_called_once_with(10)


# ---------- control_locally (play/pause/next/previous without Premium) ----------

def test_control_locally_when_playing_on_this_device(monkeypatch):
    monkeypatch.setattr(main, "track_info", {"track_name": "Bella Ciao"}, raising=False)
    with mock.patch.object(main.platform_support, "is_playing_locally", return_value=True), \
            mock.patch.object(main.platform_support, "send_media_command", return_value=True) as send:
        assert main.control_locally("next") is True
    send.assert_called_once_with("next")


def test_control_locally_falls_back_to_web_api(monkeypatch):
    monkeypatch.setattr(main, "track_info", {"track_name": "Bella Ciao"}, raising=False)
    with mock.patch.object(main.platform_support, "is_playing_locally", return_value=False), \
            mock.patch.object(main.platform_support, "send_media_command") as send:
        assert main.control_locally("next") is False
    send.assert_not_called()


def test_control_locally_without_track(monkeypatch):
    monkeypatch.setattr(main, "track_info", None, raising=False)
    assert main.control_locally("play_pause") is False


# ---------- get_refresh_token.py ----------

def test_save_refresh_token_replaces_existing_line(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SPOTIFY_REFRESH_TOKEN=old\nSPOTIFY_BASE64_TOKEN=keep\n", encoding="utf-8")
    monkeypatch.setattr(get_refresh_token, "ENV_PATH", env)
    get_refresh_token.save_refresh_token("new")
    assert env.read_text(encoding="utf-8") == "SPOTIFY_REFRESH_TOKEN=new\nSPOTIFY_BASE64_TOKEN=keep\n"


def test_save_refresh_token_appends_when_missing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("MUSIXMATCH_TOKEN=x\n", encoding="utf-8")
    monkeypatch.setattr(get_refresh_token, "ENV_PATH", env)
    get_refresh_token.save_refresh_token("new")
    assert env.read_text(encoding="utf-8") == "MUSIXMATCH_TOKEN=x\nSPOTIFY_REFRESH_TOKEN=new\n"


def test_save_refresh_token_creates_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    monkeypatch.setattr(get_refresh_token, "ENV_PATH", env)
    get_refresh_token.save_refresh_token("new")
    assert env.read_text(encoding="utf-8") == "SPOTIFY_REFRESH_TOKEN=new\n"


def test_capture_code_by_paste_parses_redirect_url(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "https://kampung.xyz/?code=CODE123&state=STATE")
    assert get_refresh_token.capture_code_by_paste() == {"code": "CODE123", "state": "STATE"}
