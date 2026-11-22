# Ultimate Scraper pro Studio 1.2.0

A Windows scraper for retro game artwork, videos, manuals and metadata.

## Use the app

Download the official Windows ZIP from [Releases](https://github.com/whiitekniight/Ultimate-Scraper-Pro/releases), extract it, and run **Ultimate-Scraper-Pro-Studio.exe**.
Open **Accounts**, enter your own ScreenScraper **username** and password, and select **Validate**. Choose your ROM/output folders and try **Test one ROM** before starting a batch.

## Server connection and privacy

Starting with 1.2.0, the app uses a restricted HTTPS relay. **ScreenScraper developer credentials are not in the Windows app, its source, or its download.** They are configured only on the operator's server.

Your ScreenScraper username and password are sent over HTTPS to the relay to validate your account and make requests on your behalf. The relay keeps them in memory for at most 30 minutes and does not persist them or log request bodies. Restarting the relay discards its sessions. The client renews expired sessions automatically.

The relay forwards only supported login, game lookup and media operations to ScreenScraper. It enforces request and concurrency limits, discards upstream request headers, and replaces ScreenScraper media URLs with random, expiring relay links. Download links do not expose developer credentials.

Personal settings are not shipped. Your own settings are saved in `%LOCALAPPDATA%\UltimateScraperPro\settings.json`. This local file includes your own account password; keep it private.

The service must be online for ScreenScraper scraping and downloads to work. The app reports service outages and rate limits. A modified client cannot retrieve the developer password from the relay, although compromised server administration could expose it. Previously distributed copies of developer credentials must be revoked at ScreenScraper; moving them to a server does not invalidate old copies.

Optional EmuMovies access still requires your own authorized application API key through `EMUMOVIES_API_KEY` and your own EmuMovies login.

## Build from source

Install Python 3.12 and `py -3.12 -m pip install -r requirements.txt`, then run `py -3.12 UltimateScraperStudio.py` or `build_exe.bat`.
No developer credentials are required or accepted by the desktop build.

The relay address is configured in `relay_client.py`. `SCREENSCRAPER_RELAY_URL` can override it for testing. HTTPS is mandatory except for local loopback development tests.

## Self-host the relay

See [relay/README.md](relay/README.md). Server dependencies are separate from the desktop requirements, and the server is not bundled into the Windows executable.

Run relay regression tests after installing `relay/requirements.txt`:

```
py -3.12 -m unittest discover -s tests -v
```
