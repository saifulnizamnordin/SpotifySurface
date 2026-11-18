"""Tests for lyrics parsing, LRCLIB lookup, Musixmatch song check and Song.update_info in main.py."""
from unittest import mock

import pytest
import requests

import main


# ---------- parse_lrc ----------

def test_parse_lrc_basic_with_leading_gap_and_trailing_blank():
    lrc = "[00:01.50] Hello\n[00:03.00] World"
    assert main.parse_lrc(lrc, 10000) == [
        [[0, 1500], ""],
        [[1500, 3000], "Hello"],
        [[3000, 10000], "World"],
        [[10000, 10000], ""],
    ]


def test_parse_lrc_no_space_after_timestamp():
    # This format crashed the old parser ("invalid literal for int()")
    result = main.parse_lrc("[00:00.00]Wob gopini den\n[00:04.00]Tefe", 8000)
    assert result[0] == [[0, 4000], "Wob gopini den"]
    assert result[1] == [[4000, 8000], "Tefe"]


@pytest.mark.parametrize("stamp, ms", [("[01:02.5]", 62500), ("[01:02.50]", 62500), ("[01:02.500]", 62500), ("[01:02]", 62000)])
def test_parse_lrc_fraction_formats(stamp, ms):
    result = main.parse_lrc(f"{stamp} line", 100000)
    assert [r for r in result if r[1] == "line"][0][0][0] == ms


def test_parse_lrc_skips_tags_and_garbage():
    lrc = "[ar:Artist]\n[ti:Title]\nnot a lyric\n\n[00:00.00] Only line"
    assert main.parse_lrc(lrc, 5000)[0] == [[0, 5000], "Only line"]


def test_parse_lrc_collapses_double_instrumental():
    lrc = "[00:00.00] A\n[00:01.00] \n[00:02.00] \n[00:03.00] B"
    texts = [line[1] for line in main.parse_lrc(lrc, 5000)]
    assert texts == ["A", "", "B", ""]


def test_parse_lrc_empty_returns_none():
    assert main.parse_lrc("", 1000) is None
    assert main.parse_lrc("no timestamps here", 1000) is None


def test_parse_lrc_unknown_duration_never_goes_backwards():
    result = main.parse_lrc("[00:05.00] Last", 0)
    for (start, end), _ in result:
        assert end >= start


# ---------- Musixmatch decoy detection ----------

@pytest.mark.parametrize("req_artist, req_title, found_artist, found_title, same", [
    ("Manu Pilas", "Bella Ciao - Música Original de la Serie", "Manu Pilas", "Bella Ciao", True),
    ("Manu Pilas", "Bella Ciao - Música Original de la Serie", "Drake", "NOKIA", False),
    ("Manu Pilas", "Bella Ciao", "Drake", "Bella Ciao", False),
    ("Queen", "Bohemian Rhapsody - Remastered 2011", "Queen", "Bohemian Rhapsody", True),
    ("The Weeknd", "Blinding Lights", "The Weeknd", "Save Your Tears", False),
    ("", "", "", "", False),
])
def test_is_same_song(req_artist, req_title, found_artist, found_title, same):
    assert main.is_same_song(req_artist, req_title, found_artist, found_title) is same


# ---------- Song.update_info ----------

def musixmatch_body(track):
    return {"matcher.track.get": {"message": {"body": {"track": track}}}}


def test_update_info_handles_missing_coverart_and_length():
    song = main.Song("Manu Pilas", "Bella Ciao")
    song.duration = 139844
    song.update_info(musixmatch_body({"track_name": "NOKIA", "artist_name": "Drake", "has_subtitles": 1}))
    assert song.coverart_url is None
    assert song.duration == 139844  # kept, since Musixmatch sent no track_length
    assert song.title == "NOKIA" and song.has_synced == 1 and song.is_instrumental == 0


def test_update_info_picks_largest_coverart():
    song = main.Song("a", "b")
    song.update_info(musixmatch_body({"album_coverart_100x100": "small", "album_coverart_800x800": "big", "track_length": 200}))
    assert song.coverart_url == "big"
    assert song.duration == 200000


# ---------- LRCLIB ----------

def response(status, data):
    r = mock.MagicMock(status_code=status)
    r.json.return_value = data
    return r


def bella_ciao():
    song = main.Song("Manu Pilas", "Bella Ciao", album="Bella Ciao")
    song.duration = 139844
    return song


def test_lrclib_exact_match():
    record = {"syncedLyrics": "[00:10.05] Una mattina", "plainLyrics": "Una mattina\n\nmi sono alzato", "instrumental": False}
    with mock.patch.object(main.requests, "get", return_value=response(200, record)) as get:
        result = main.get_lyrics_lrclib(bella_ciao())
    assert get.call_args.kwargs["params"]["duration"] == 140
    assert result["synced_lyrics"][1] == [[10050, 139844], "Una mattina"]
    assert result["lyrics"] == ["Una mattina", "mi sono alzato"]
    assert result["song_info"]["has_synced"] is True


def test_lrclib_falls_back_to_search_and_prefers_close_duration():
    results = [
        {"duration": 300, "syncedLyrics": "[00:00.00] wrong version"},
        {"duration": 140, "syncedLyrics": "[00:00.00] right version"},
    ]
    with mock.patch.object(main.requests, "get", side_effect=[response(404, {}), response(200, results)]):
        result = main.get_lyrics_lrclib(bella_ciao())
    assert result["synced_lyrics"][0][1] == "right version"


def test_lrclib_instrumental():
    with mock.patch.object(main.requests, "get", return_value=response(200, {"instrumental": True})):
        result = main.get_lyrics_lrclib(bella_ciao())
    assert result["song_info"]["is_instrumental"] is True


def test_lrclib_not_found():
    with mock.patch.object(main.requests, "get", side_effect=[response(404, {}), response(200, [])]):
        assert main.get_lyrics_lrclib(bella_ciao()) is None


def test_lrclib_network_error():
    with mock.patch.object(main.requests, "get", side_effect=requests.exceptions.ConnectionError):
        assert main.get_lyrics_lrclib(bella_ciao()) is None


# ---------- get_lyrics source order ----------

def test_get_lyrics_uses_lrclib_first():
    with mock.patch.object(main, "get_lyrics_lrclib", return_value={"ok": True}), \
            mock.patch.object(main, "find_lyrics") as find:
        assert main.get_lyrics(bella_ciao()) == {"ok": True}
    find.assert_not_called()


def test_get_lyrics_rejects_musixmatch_decoy():
    decoy = musixmatch_body({"track_name": "NOKIA", "artist_name": "Drake"})
    with mock.patch.object(main, "get_lyrics_lrclib", return_value=None), \
            mock.patch.object(main, "find_lyrics", return_value=decoy):
        assert main.get_lyrics(bella_ciao()) is None
