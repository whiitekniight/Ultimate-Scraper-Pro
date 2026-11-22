# Ultimate Scraper pro Studio 1.1.0

Windows artwork, video, manual and metadata scraper for retro game collections.

## Download and start

Download **Ultimate-Scraper-Pro-Studio-v1.1.0.zip** from
[Releases](https://github.com/whiitekniight/Ultimate-Scraper-Pro/releases/latest),
extract it, and run **Ultimate-Scraper-Pro-Studio.exe**. Python is not required.

Open **Accounts**, enter **your own ScreenScraper username and password**, and
select **Validate**. Official Windows binaries include application API access;
users do not need developer credentials. Choose your ROM folder and output folder,
then use **Test one ROM** before starting a batch. The app observes your account's
reported thread limit.

## Changes in 1.1.0

- Restored application authentication missing from the previous public binary.
- Uses ScreenScraper's documented HTTPS API address for login and game lookup.
- Reports connection, authentication, rate-limit and service failures instead of
  incorrectly treating them as games missing from the database.
- Preserves ROM filenames for hash searches, with original-name and cleaned-name
  fallbacks. Supports special characters in account passwords.
- Includes the Studio interface and console artwork.
- Starts without the author's account, saved folders, profiles or settings.

## Privacy and application credentials

Personal login and settings are never shipped. Each user's settings are saved in
`%LOCALAPPDATA%\UltimateScraperPro\settings.json`; the public app does not import
settings from the author's personal Studio folder or the legacy scraper config.
Passwords are saved locally in that file: treat it as private and do not share it.
Login requests use HTTPS, do not follow redirects, and do not log credentials,
request URLs, response bodies or complete account records.

Developer credentials are excluded from this repository and injected into official
Windows builds during packaging. A desktop binary cannot keep an embedded secret
safe from a determined person who inspects or modifies it. Packaging is not a
security boundary. Keeping application credentials truly private requires a
server-side service with authentication, request limits and monitoring.

EmuMovies is optional and requires your own authorized application API key through
`EMUMOVIES_API_KEY`, plus your own EmuMovies login. No third-party application key
or personal media repository is bundled.

## Run or build from source

Install Python 3.12 and run `py -3.12 -m pip install -r requirements.txt`.
Set `SCREENSCRAPER_DEV_ID` and `SCREENSCRAPER_DEV_PASSWORD` to your approved
application credentials in your local environment, then run
`py -3.12 UltimateScraperStudio.py` or `build_exe.bat`.

Obtain application access through the [ScreenScraper team](https://www.screenscraper.fr/webapi2.php).
Do not commit developer credentials, personal config files, logs, or build folders.

Run regression checks with `py -3.12 -m unittest discover -s tests -v`.
