<br>
<div align="center">
  <img src="https://i.imgur.com/qvdqtsc.png" alt="Logo" width="150" height="150">

  <h3 align="center">Spotify Surface</h3>

  <p align="center">
    A minimalistic window with lyrics synced to Spotify<br>on the surface of your screen
    <br>
    <br>
    <a href="#usage-and-features">Usage and Features</a>
    ·
    <a href="https://github.com/PureAspiration/SpotifySurface/issues">Report Bug</a>
    ·
    <a href="https://github.com/PureAspiration/SpotifySurface/issues">Request Feature</a>
  </p>
</div>

---

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li><a href="#usage-and-features">Usage and Features</a></li>
    <li><a href="#installationdownloading">Installation/Downloading</a></li>
    <li>
      <a href="#setup">Setup</a>
      <ul>
        <li><a href="#tokens-and-environment-variables">Tokens and Environment Variables</a></li>
        <li><a href="#spotify-tokens">Spotify Tokens</a></li>
        <li><a href="#lyrics-sources">Lyrics Sources</a></li>
        <li><a href="#musixmatch-token">Musixmatch Token</a></li>
      </ul>
    </li>
    <li><a href="#running">Running</a></li>
    <li><a href="#troubleshooting">Troubleshooting</a></li>
    <li><a href="#running-the-tests">Running the Tests</a></li>
    <li><a href="#acknowledgments-and-credits">Acknowledgments and Credits</a></li>
    <li><a href="#developer">Developer</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

---

## About
A minimalistic window that shows you the current song playing on Spotify with synced lyrics.<br>
The application is non-distracting with all the information you need about the song you are listening to.
This window is pinned to the top of the screen for all your lyrics needs.
<br>

## Usage and Features
<strong>Synced Lyrics</strong><br>
Lyrics are shown at the center of the interface, with a following rectangle.<br>
<img src="https://i.imgur.com/3fp5ObV.gif" alt="Synced Lyrics Demo" height=200>

<strong>Automatic Lyric Scrolling</strong><br>
The lyrics scroll down automatically.<br>
But what if you want to read the lyrics? Then just scroll.<br>
Once you're done, just click the follow button, and the lyrics will scroll automatically once again.<br>
<img src="https://i.imgur.com/sSYJV18.gif" alt="Automatic Lyric Scrolling Demo" height=200>

<strong>Live Lyrics Fetching</strong><br>
The application searches for lyrics immediately after you change songs on Spotify.<br>
<img src="https://i.imgur.com/f0GOJy4.gif" alt="Logo" height=200>

<strong>Quick Access Controls *</strong><br>
With the quick access controls, you can play/pause, skip, return, shuffle, and repeat songs with the click of a singular button.<br>
&ast; Note that some of these functions require Spotify Premium to work. If you do not have Spotify Premium, the play/pause, skip, and return buttons will control the Spotify app directly when it is playing on the same computer (Windows: media keys, macOS: AppleScript, Linux: `playerctl`).<br>
<img src="https://i.imgur.com/3fp5ObV.gif" alt="Quick Access Controls Demo" height=200>

<strong>Window Dragging, Resize, and Alignment Lock</strong><br>
The window can be dragged and resized like a normal window, but when dragging the window near the side of the screen, the window locks and aligns to the side or at the taskbar.<br>
<img src="https://i.imgur.com/i6Pao1A.gif" alt="Window Dragging and Alignment Lock Demo" height=200>

<br><br>

---

## Installation/Downloading
Requirements:
* **Windows 10/11, macOS or Linux**<br>
  Windows and Linux are tested in CI. macOS support is written but **not yet tested on a real Mac** (only with mocked tests, see [Running the Tests](#running-the-tests)) - please [report](https://github.com/PureAspiration/SpotifySurface/issues) any problems.
* **Python 3.10** (the version the pinned dependencies and CI tests use)
* A Spotify account (some playback controls need Spotify Premium, see above)

Steps:
* Clone or download this repo
* Install the required dependencies with pip command:
```pip install -r requirements.txt```
(`pywin32` and `winsdk` are installed on Windows only.)

Extra steps per platform:

| Platform | Notes |
|---|---|
| Windows | Nothing extra. |
| macOS | Use the Python from [python.org](https://www.python.org/downloads/) or `brew install python-tk@3.10` so Tkinter is included. The first time you use the playback buttons without Premium, macOS asks to allow your terminal to control Spotify - click **OK**. |
| Linux | Install Tkinter, e.g. `sudo apt install python3-tk`. For playback buttons without Premium, install `playerctl` (`sudo apt install playerctl`). |
<br>

## Setup
#### Tokens and Environment Variables
The tokens below are read from environment variables.

To do this, create a file named `.env` in your folder containing the `main.py` file.

In the file, enter the following, replacing `<TOKEN>` with your respective token.
```
SPOTIFY_REFRESH_TOKEN=<TOKEN>   # refresh_token
SPOTIFY_BASE64_TOKEN=<TOKEN>    # base64_encode(client_id:client_secret)
MUSIXMATCH_TOKEN=<TOKEN>        # optional, see "Musixmatch Token"
```
`.env` is listed in `.gitignore` - never commit it, it contains your Spotify client secret.
<br>

#### Spotify Tokens
**1. Create a Spotify app**
* Go to the Spotify Developer [Dashboard](https://developer.spotify.com/dashboard) and click **Create app**.
* Fill in the App name and App description.
* Under **Redirect URIs** add exactly `http://127.0.0.1:8888/callback`.<br>
  Spotify no longer accepts `localhost` - use `127.0.0.1`. No trailing slash.
* Tick **Web API**, agree to the terms and save.
* Open the app's **Settings**. Copy the **Client ID** and click **View client secret** to copy the **Client Secret**.

**2. Create `SPOTIFY_BASE64_TOKEN`**

This is `client_id:client_secret` encoded in Base64. In PowerShell:
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("<client_id>:<client_secret>"))
```
Put the output into `SPOTIFY_BASE64_TOKEN=` in `.env`.

> If you have several Spotify apps, make sure the Client ID you encode belongs to the app whose Redirect URIs you set up.
> A Redirect URI added to a different app gives `INVALID_CLIENT: Invalid redirect URI` / `redirect_uri: Not matching configuration`.

**3. Get `SPOTIFY_REFRESH_TOKEN` (automatic)**

With `SPOTIFY_BASE64_TOKEN` saved in `.env`, run:
```
python get_refresh_token.py
```
A browser tab opens. Log in and approve, and the script saves the new refresh token into `.env` for you.

To use a different redirect URI that is already registered on your app, pass it as an argument:
```
python get_refresh_token.py https://your-redirect-uri.example
```
For a non-`127.0.0.1` redirect, the script asks you to paste the URL your browser lands on after approving.

**Refresh tokens expire.** The dashboard shows "Refresh Token Lifetime: 180 days", and Spotify may also revoke a token earlier
(e.g. if you remove the app's access or reset the client secret). When that happens, `main.py` stops with
`Spotify token refresh failed: Refresh token revoked` - just run `python get_refresh_token.py` again.

<details>
  <summary>Manual method (without the script)</summary>

Visit this link, replacing `{client_id}` and `{redirect_uri}` (URL-encoded):
```
https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=playlist-modify-public%20playlist-modify-private%20user-modify-playback-state%20user-read-playback-state
```
After authorizing and agreeing, you will see a URL like `https://your-redirect-uri/?code=xxxxxxx`. Copy the **code** from the URL.

Now run this curl command and replace all the required values:
```
curl -H "Authorization: Basic {SPOTIFY_BASE64_TOKEN}" -d grant_type=authorization_code -d code={code} -d redirect_uri={redirect_uri} https://accounts.spotify.com/api/token
```
Copy the value of `refresh_token` from the JSON response into `SPOTIFY_REFRESH_TOKEN=` in `.env`.
The code can only be used once and expires after a few minutes.
</details>
<br>

#### Lyrics Sources
Lyrics are looked up in this order:
1. **[LRCLIB](https://lrclib.net)** - free and open, no token needed. Matched by artist, title, album and song length. Provides synced and plain lyrics.
2. **Musixmatch** - only used when LRCLIB has no lyrics for the song. Needs a working token (see below).

If Musixmatch returns a different song than the one playing, the result is ignored and a warning is printed.
This protects against a blocked Musixmatch token, which returns a fake song with gibberish lyrics instead of an error.
<br>

#### Musixmatch Token
The Musixmatch token is **optional** - LRCLIB is used first. You may remove the `MUSIXMATCH_TOKEN` variable from the `.env` file if you do not have a Musixmatch token.<br>
Do not leave the variable unfilled.

Keep in mind that the default token provided may not work 100% of the time and is likely rate limited or blocked.

In order to get a new Musixmatch token, follow steps 1 - 5 with the guide [here](https://spicetify.app/docs/faq#sometimes-popup-lyrics-andor-lyrics-plus-seem-to-not-work).
<br><br>

---

## Running
Start Spotify and play a song, then run:
```
python main.py
```
The window shows the current song and its lyrics. Window position and settings are saved to `api_data.json` (created automatically, ignored by git).
<br>

## Troubleshooting
| Problem | Cause / Fix |
|---|---|
| `Spotify token refresh failed: Refresh token revoked` (or `invalid_grant`) | The refresh token expired or was revoked. Run `python get_refresh_token.py`. |
| `Spotify token refresh failed: Invalid client` | `SPOTIFY_BASE64_TOKEN` is wrong or the client secret was reset. Rebuild it (Setup step 2). |
| Browser shows `redirect_uri: Not matching configuration` | The redirect URI is not registered on **the app whose Client ID is in `SPOTIFY_BASE64_TOKEN`**. Add it to that app and click **Save**. |
| Lyrics are gibberish or belong to another song | Old versions used a blocked Musixmatch token. Update to the current version (LRCLIB first + song check), or get a new Musixmatch token. |
| `Failed to find song` / no lyrics shown | The song isn't on LRCLIB and Musixmatch failed. Try again later or get a new Musixmatch token. |
| App works for you but not for others | New Spotify apps are in **Development mode**: only users added under the app's **User Management** tab can log in. |
| Linux: play/pause/skip do nothing without Premium | Install `playerctl` and check `playerctl --player=spotify status` works. |
| Linux: `ModuleNotFoundError: No module named 'tkinter'` | `sudo apt install python3-tk` (or your distro's equivalent). |
<br>

## Running the Tests
```
pip install -r requirements-dev.txt
pytest
```
The tests mock Spotify, LRCLIB, Musixmatch and the OS media tools, so no tokens or running Spotify app are needed.
GitHub Actions ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) runs them on Windows and Linux for every pull request and push to `master`.
macOS has no CI runner (GitHub's macOS runners are scarce and queue for a long time); its code paths are tested on the other runners with mocked `osascript`/`pgrep`.
<br>

---

## Acknowledgments and Credits
* [`MxLRC` by fashni](https://github.com/fashni/MxLRC)
* [LRCLIB](https://lrclib.net/)
* [Musixmatch](https://www.musixmatch.com/)
<br>

## Developer
This project was developed by [`PureAspiration`](https://github.com/PureAspiration).
<br>

## License
Distributed under the MIT License. See [`LICENSE`](./LICENSE.md) for more information.
<br><br>
