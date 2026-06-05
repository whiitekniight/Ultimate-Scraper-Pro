# Ultimate Scraper pro

Ultimate Scraper pro is a Windows app for scraping retro game artwork, videos,
manuals, metadata, and `gamelist.xml` files.

## Download

Prebuilt Windows downloads are available on the Releases page:

https://github.com/whiitekniight/Ultimate-Scraper-Pro/releases

The repository contains the source code used to build the EXE. The EXE itself is
published as a release asset so users can download it without installing Python.

## Features

- Download box art, screenshots, logos, videos, manuals, fanart, and metadata.
- Build `gamelist.xml` files for RetroBat, EmulationStation-style folders, and
  other frontends.
- Choose output folders and customize output image filename patterns.
- Save reusable system profiles.
- Auto-detect platforms from ROM folders.
- Test one ROM before scraping a full folder.
- Choose exactly which media types to download.

## Build From Source

Install Python, then run:

```bat
pip install -r requirements.txt
build_exe.bat
```

The build script creates the Windows EXE using PyInstaller.

## Developer/API Credentials

Private developer credentials are not included in this repository.

Before running or building from source, set your own local environment variables:

```bat
set SCREENSCRAPER_DEV_ID=your_dev_id
set SCREENSCRAPER_DEV_PASSWORD=your_dev_password
set SCREENSCRAPER_SOFTNAME=your_softname
set EMUMOVIES_API_KEY=your_emumovies_api_key
```

Users still enter their own ScreenScraper and EmuMovies account credentials in
the app UI. Those user credentials are saved locally on their own PC.

## Privacy

User settings and ScreenScraper login details are saved locally on the user's own
PC in a config file outside this repository. That config file is not included in
this repo or in the release download.
