import os
import sys
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import requests
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageTk
import urllib.request
import io
import ctypes
try:
    import winsound
except ImportError:
    winsound = None

import zlib
import hashlib

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller EXE.
    When running as EXE, PyInstaller extracts files to a temp folder.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running as normal Python script
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def calculate_file_hashes(filepath, max_size_mb=100):
    """
    Calculate CRC, MD5, SHA1 for a file.
    For disc images (ISO, CHD, etc.), always read full file.
    For other ROMs, limit to max_size_mb for speed.
    Returns dict with 'crc', 'md5', 'sha1', 'size'
    """
    try:
        file_size = os.path.getsize(filepath)
        
        # For disc images, always read the full file (ScreenScraper needs accurate hash)
        ext = os.path.splitext(filepath)[1].lower()
        disc_formats = {'.iso', '.chd', '.cdi', '.gdi', '.cue', '.bin', '.img'}
        
        if ext in disc_formats:
            read_size = file_size  # Full file for disc images
        else:
            # For other ROMs, limit size for speed
            max_bytes = max_size_mb * 1024 * 1024
            read_size = min(file_size, max_bytes)
        
        crc_val = 0
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        
        with open(filepath, 'rb') as f:
            # Read in chunks
            chunk_size = 8192
            bytes_read = 0
            
            while bytes_read < read_size:
                chunk = f.read(min(chunk_size, read_size - bytes_read))
                if not chunk:
                    break
                
                crc_val = zlib.crc32(chunk, crc_val)
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                bytes_read += len(chunk)
        
        # CRC needs to be unsigned 32-bit
        crc_val = crc_val & 0xFFFFFFFF
        
        return {
            'crc': f"{crc_val:08X}",
            'md5': md5_hash.hexdigest().upper(),
            'sha1': sha1_hash.hexdigest().upper(),
            'size': file_size
        }
    except Exception as e:
        print(f"Error calculating hashes for {filepath}: {e}")
        return None




# ---------- COMPLETE SCREENSCRAPER SYSTEM DATABASE ----------
BRAND_INFO = {
    "00": {"color": "#999999", "brand": "Various", "name": "CHIP-8"},
    "1": {"color": "#0089CF", "brand": "Sega", "name": "MEGADRIVE MSU"},
    "2": {"color": "#0089CF", "brand": "Sega", "name": "SEGA MASTER SYSTEM"},
    "3": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Entertainment System"},
    "4": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO SNES-SFC"},
    "6": {"color": "#FF0000", "brand": "Arcade", "name": "CAPCOM PLAY SYSTEM"},
    "7": {"color": "#FF0000", "brand": "Arcade", "name": "Capcom Play System Ii"},
    "8": {"color": "#FF0000", "brand": "Arcade", "name": "Capcom Play System Iii"},
    "9": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO GAME BOY"},
    "10": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Game Boy Color"},
    "11": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Virtual Boy"},
    "12": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Game Boy Advance"},
    "13": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO GAMECUBE"},
    "14": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO 64"},
    "15": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO DS"},
    "16": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO WII"},
    "17": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO 3DS"},
    "18": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO WII U"},
    "19": {"color": "#0089CF", "brand": "Sega", "name": "SEGA 32X"},
    "20": {"color": "#0089CF", "brand": "Sega", "name": "MEGA CD"},
    "21": {"color": "#0089CF", "brand": "Sega", "name": "SEGA GAME GEAR"},
    "22": {"color": "#0089CF", "brand": "Sega", "name": "SEGA SATURN"},
    "23": {"color": "#0089CF", "brand": "Sega", "name": "SEGA DREAMCAST"},
    "25": {"color": "#FF6600", "brand": "SNK", "name": "SNK NEO GEO POCKET"},
    "26": {"color": "#E4002B", "brand": "Atari", "name": "ATARI 2600"},
    "27": {"color": "#E4002B", "brand": "Atari", "name": "ATARI JAGUAR"},
    "28": {"color": "#E4002B", "brand": "Atari", "name": "ATARI LYNX"},
    "29": {"color": "#999999", "brand": "Various", "name": "The 3Do Company - 3Do"},
    "30": {"color": "#999999", "brand": "Various", "name": "NOKIA N-GAGE"},
    "31": {"color": "#FF6600", "brand": "NEC", "name": "PCENGINE"},
    "32": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT XBOX"},
    "33": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT XBOX 360"},
    "34": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT XBOX ONE"},
    "35": {"color": "#FF0000", "brand": "Arcade", "name": "Another_Arcade_Emulator"},
    "36": {"color": "#999999", "brand": "Various", "name": "ACORN ATOM"},
    "37": {"color": "#999999", "brand": "Various", "name": "Bbc Microcomputer System"},
    "39": {"color": "#E4002B", "brand": "Atari", "name": "Atari_2600_Supercharger"},
    "40": {"color": "#E4002B", "brand": "Atari", "name": "ATARI 5200"},
    "41": {"color": "#E4002B", "brand": "Atari", "name": "ATARI 7800"},
    "42": {"color": "#E4002B", "brand": "Atari", "name": "Atari St-Ste-Tt-Falcon"},
    "43": {"color": "#E4002B", "brand": "Atari", "name": "ATARI 800"},
    "44": {"color": "#999999", "brand": "Various", "name": "BALLY ASTROCADE"},
    "45": {"color": "#FF6600", "brand": "Bandai", "name": "WONDERSWAN"},
    "46": {"color": "#FF6600", "brand": "Bandai", "name": "Bandai Wonderswan-Color"},
    "47": {"color": "#FF0000", "brand": "Arcade", "name": "CAVE3RD"},
    "48": {"color": "#999999", "brand": "Various", "name": "COLECOVISION"},
    "49": {"color": "#FF0000", "brand": "Arcade", "name": "DAPHNE"},
    "50": {"color": "#999999", "brand": "Various", "name": "COREGRAFX"},
    "52": {"color": "#999999", "brand": "Various", "name": "GAME & WATCH"},
    "53": {"color": "#0089CF", "brand": "Sega", "name": "SAMMY ATOMISWAVE"},
    "54": {"color": "#0089CF", "brand": "Sega", "name": "SEGA MODEL 2"},
    "55": {"color": "#0089CF", "brand": "Sega", "name": "SEGA MODEL 3"},
    "56": {"color": "#0089CF", "brand": "Sega", "name": "Sega Atomiswave Naomi"},
    "57": {"color": "#003087", "brand": "Sony", "name": "SONY PLAYSTATION"},
    "58": {"color": "#003087", "brand": "Sony", "name": "SONY PLAYSTATION 2"},
    "59": {"color": "#003087", "brand": "Sony", "name": "SONY PLAYSTATION 3"},
    "60": {"color": "#003087", "brand": "Sony", "name": "SONY PLAYSTATION 4"},
    "61": {"color": "#003087", "brand": "Sony", "name": "Sony Playstation Portable"},
    "62": {"color": "#003087", "brand": "Sony", "name": "Sony Playstation Vita"},
    "63": {"color": "#999999", "brand": "Various", "name": "ANDROID"},
    "64": {"color": "#5B4638", "brand": "Commodore", "name": "COMMODORE AMIGA"},
    "65": {"color": "#999999", "brand": "Various", "name": "AMSTRAD CPC"},
    "66": {"color": "#5B4638", "brand": "Commodore", "name": "COMMODORE 64"},
    "67": {"color": "#999999", "brand": "Various", "name": "Epoch Super Cassette Vision"},
    "68": {"color": "#FF6600", "brand": "SNK", "name": "SNK NEO GEO MVS"},
    "69": {"color": "#0089CF", "brand": "Sega", "name": "SEGA ST-V"},
    "70": {"color": "#FF6600", "brand": "SNK", "name": "SNK NEO GEO CD"},
    "72": {"color": "#FF6600", "brand": "NEC", "name": "NEC PC-FX"},
    "73": {"color": "#5B4638", "brand": "Commodore", "name": "COMMODORE VIC-20"},
    "74": {"color": "#999999", "brand": "Various", "name": "CASIO PV-1000"},
    "75": {"color": "#FF0000", "brand": "Tiger", "name": "LCD GAMES"},
    "76": {"color": "#999999", "brand": "Various", "name": "Sinclair Zx Spectrum"},
    "77": {"color": "#999999", "brand": "Various", "name": "SINCLAIR ZX 81"},
    "78": {"color": "#999999", "brand": "Various", "name": "Entex Adventure Vision"},
    "79": {"color": "#999999", "brand": "Various", "name": "SHARP X68000"},
    "80": {"color": "#999999", "brand": "Various", "name": "FAIRCHILD CHANNEL F"},
    "81": {"color": "#999999", "brand": "Various", "name": "WOW ACTION MAX"},
    "82": {"color": "#FF6600", "brand": "SNK", "name": "Snk Neo Geo Pocket - Color"},
    "83": {"color": "#999999", "brand": "Various", "name": "AAMBER PEGASUS"},
    "84": {"color": "#999999", "brand": "Various", "name": "ACORN ARCHIMEDES"},
    "85": {"color": "#999999", "brand": "Various", "name": "ACORN ELECTRON"},
    "86": {"color": "#999999", "brand": "Various", "name": "APPLE II"},
    "87": {"color": "#999999", "brand": "Various", "name": "AMSTRAD GX4000"},
    "88": {"color": "#E4002B", "brand": "Atari", "name": "CAMPUTERS LYNX"},
    "89": {"color": "#999999", "brand": "Various", "name": "COLECO ADAM"},
    "90": {"color": "#999999", "brand": "Various", "name": "Mega Duck - Cougar Boy"},
    "91": {"color": "#999999", "brand": "Various", "name": "DRAGON 32-64"},
    "92": {"color": "#999999", "brand": "Various", "name": "Eaca Eg2000 Colour Genie"},
    "93": {"color": "#999999", "brand": "Various", "name": "ELEKTRONIKA BK"},
    "94": {"color": "#999999", "brand": "Various", "name": "Emerson Arcadia 2001"},
    "95": {"color": "#999999", "brand": "Various", "name": "Epoch Game Pocket Computer"},
    "96": {"color": "#999999", "brand": "Various", "name": "EXELVISION EXL 100"},
    "97": {"color": "#999999", "brand": "Various", "name": "FUJITSU FM-7"},
    "98": {"color": "#999999", "brand": "Various", "name": "CASIO LOOPY"},
    "99": {"color": "#5B4638", "brand": "Commodore", "name": "COMMODORE PLUS 4"},
    "100": {"color": "#999999", "brand": "Various", "name": "FUNTECH SUPER ACAN"},
    "101": {"color": "#999999", "brand": "Various", "name": "GP32"},
    "102": {"color": "#999999", "brand": "Various", "name": "GCE VECTREX"},
    "103": {"color": "#999999", "brand": "Various", "name": "HARTUNG GAME MASTER"},
    "104": {"color": "#999999", "brand": "Various", "name": "MAGNAVOX ODYSSEY 2"},
    "105": {"color": "#FF6600", "brand": "NEC", "name": "Nec Pc Engine Supergrafx"},
    "106": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Famicom Disk System"},
    "107": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Satellaview"},
    "108": {"color": "#999999", "brand": "Various", "name": "SUFAMI_TURBO"},
    "109": {"color": "#0089CF", "brand": "Sega", "name": "SEGA SG-1000"},
    "110": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO_POWER"},
    "111": {"color": "#5B4638", "brand": "Commodore", "name": "AMIGA1000"},
    "111": {"color": "#5B4638", "brand": "Commodore", "name": "AMIGA4000"},
    "112": {"color": "#FF0000", "brand": "Arcade", "name": "TAITO TYPE X"},
    "113": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT - MSX"},
    "114": {"color": "#FF6600", "brand": "NEC", "name": "NEC - PC ENGINE CD"},
    "115": {"color": "#999999", "brand": "Various", "name": "Mattel - Intellivision"},
    "116": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT - MSX2"},
    "117": {"color": "#107C10", "brand": "Microsoft", "name": "MICROSOFT MSX2+"},
    "118": {"color": "#999999", "brand": "Various", "name": "MSX TURBO R"},
    "119": {"color": "#E60012", "brand": "Nintendo", "name": "GBA_E-READER"},
    "120": {"color": "#999999", "brand": "Various", "name": "SOCRATES"},
    "121": {"color": "#999999", "brand": "Various", "name": "GAME.COM"},
    "122": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO 64DD"},
    "123": {"color": "#999999", "brand": "Various", "name": "RESIDUALVM"},
    "124": {"color": "#999999", "brand": "Various", "name": "RADIO-86RK MIKROSHA"},
    "125": {"color": "#999999", "brand": "Various", "name": "PECOM_64"},
    "126": {"color": "#999999", "brand": "Various", "name": "JUPITER ACE"},
    "127": {"color": "#999999", "brand": "Various", "name": "SGB"},
    "128": {"color": "#999999", "brand": "Various", "name": "SUPER_GAME_BOY_2"},
    "129": {"color": "#5B4638", "brand": "Commodore", "name": "COMMODORE CDTV"},
    "130": {"color": "#5B4638", "brand": "Commodore", "name": "Commodore Amiga Cd32"},
    "131": {"color": "#999999", "brand": "Various", "name": "ORIC ATMOS"},
    "133": {"color": "#999999", "brand": "Various", "name": "PHILIPS CD-I"},
    "134": {"color": "#5B4638", "brand": "Commodore", "name": "AMIGA_CD"},
    "135": {"color": "#107C10", "brand": "Microsoft", "name": "MS-DOS"},
    "136": {"color": "#107C10", "brand": "Microsoft", "name": "WINDOWS 3.X"},
    "137": {"color": "#999999", "brand": "Various", "name": "PC_WIN9X"},
    "138": {"color": "#999999", "brand": "Various", "name": "AGS"},
    "139": {"color": "#5B4638", "brand": "Commodore", "name": "AMIGA_CD32_(HACK)"},
    "140": {"color": "#999999", "brand": "Various", "name": "MO5"},
    "141": {"color": "#999999", "brand": "Various", "name": "THOMSON MO5"},
    "142": {"color": "#FF6600", "brand": "SNK", "name": "SNK NEO GEO"},
    "143": {"color": "#999999", "brand": "Various", "name": "PINBALL_FX2"},
    "144": {"color": "#999999", "brand": "Various", "name": "Trs-80 Color Computer"},
    "145": {"color": "#999999", "brand": "Various", "name": "LINUX"},
    "146": {"color": "#999999", "brand": "Various", "name": "APPLE MAC OS"},
    "147": {"color": "#0089CF", "brand": "Sega", "name": "SEGA_CLASSICS"},
    "148": {"color": "#999999", "brand": "Various", "name": "IREM_CLASSICS"},
    "149": {"color": "#999999", "brand": "Various", "name": "SETA"},
    "150": {"color": "#FF0000", "brand": "Arcade", "name": "MIDWAY_CLASSICS"},
    "151": {"color": "#FF0000", "brand": "Arcade", "name": "CAPCOM_CLASSICS"},
    "152": {"color": "#999999", "brand": "Various", "name": "EIGHTING_RAIZING"},
    "153": {"color": "#999999", "brand": "Various", "name": "TECMO"},
    "154": {"color": "#FF6600", "brand": "SNK", "name": "SNK_CLASSICS"},
    "155": {"color": "#FF0000", "brand": "Arcade", "name": "NAMCO2X6"},
    "156": {"color": "#FF0000", "brand": "Arcade", "name": "NAMCO SYSTEM 22"},
    "157": {"color": "#FF0000", "brand": "Arcade", "name": "TAITO_CLASSICS"},
    "158": {"color": "#FF0000", "brand": "Arcade", "name": "KONAMI_CLASSICS"},
    "159": {"color": "#999999", "brand": "Various", "name": "JALECO"},
    "160": {"color": "#E4002B", "brand": "Atari", "name": "ATARI_CLASSICS"},
    "161": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO_CLASSICS"},
    "162": {"color": "#999999", "brand": "Various", "name": "DATA_EAST_CLASSICS"},
    "163": {"color": "#999999", "brand": "Various", "name": "NMK"},
    "164": {"color": "#999999", "brand": "Various", "name": "SAMMY_CLASSICS"},
    "165": {"color": "#999999", "brand": "Various", "name": "EXIDY"},
    "166": {"color": "#999999", "brand": "Various", "name": "ACCLAIM"},
    "167": {"color": "#999999", "brand": "Various", "name": "PSIKYO"},
    "169": {"color": "#999999", "brand": "Various", "name": "TECHNOS"},
    "170": {"color": "#999999", "brand": "Various", "name": "ALG"},
    "171": {"color": "#E4002B", "brand": "Atari", "name": "ATARI JAGUAR CD"},
    "172": {"color": "#003087", "brand": "Sony", "name": "SONY PSP MINIS"},
    "173": {"color": "#999999", "brand": "Various", "name": "DYNAX"},
    "174": {"color": "#999999", "brand": "Various", "name": "KANEKO"},
    "175": {"color": "#999999", "brand": "Various", "name": "VIDEO_SYSTEM_CO."},
    "176": {"color": "#999999", "brand": "Various", "name": "IGS"},
    "177": {"color": "#999999", "brand": "Various", "name": "COMAD"},
    "178": {"color": "#999999", "brand": "Various", "name": "AMCOE"},
    "179": {"color": "#999999", "brand": "Various", "name": "CENTURY_ELECTRONICS"},
    "180": {"color": "#999999", "brand": "Various", "name": "NICHIBUTSU"},
    "181": {"color": "#999999", "brand": "Various", "name": "VISCO"},
    "182": {"color": "#999999", "brand": "Various", "name": "ALPHA_DENSHI_CO."},
    "183": {"color": "#999999", "brand": "Various", "name": "COLECO"},
    "184": {"color": "#999999", "brand": "Various", "name": "PLAYCHOICE"},
    "185": {"color": "#999999", "brand": "Various", "name": "ATLUS"},
    "186": {"color": "#999999", "brand": "Various", "name": "BANPRESTO"},
    "187": {"color": "#999999", "brand": "Various", "name": "SEMICOM"},
    "188": {"color": "#999999", "brand": "Various", "name": "UNIVERSAL"},
    "189": {"color": "#999999", "brand": "Various", "name": "MITCHELL"},
    "190": {"color": "#999999", "brand": "Various", "name": "SEIBU_KAIHATSU"},
    "191": {"color": "#999999", "brand": "Various", "name": "TOAPLAN"},
    "192": {"color": "#999999", "brand": "Various", "name": "CINEMATRONICS"},
    "193": {"color": "#999999", "brand": "Various", "name": "Incredible_Technologies"},
    "194": {"color": "#999999", "brand": "Various", "name": "GAELCO"},
    "195": {"color": "#999999", "brand": "Various", "name": "MEGA-TECH"},
    "196": {"color": "#999999", "brand": "Various", "name": "MEGA-PLAY"},
    "197": {"color": "#999999", "brand": "Various", "name": "FLIPPER"},
    "198": {"color": "#999999", "brand": "Various", "name": "VISUAL_PINBALL"},
    "199": {"color": "#999999", "brand": "Various", "name": "FPINBALL"},
    "200": {"color": "#FF0000", "brand": "Arcade", "name": "THE_PINBALL_ARCADE"},
    "201": {"color": "#999999", "brand": "Various", "name": "PINBALL_FX3"},
    "202": {"color": "#E60012", "brand": "Nintendo", "name": "Super Nintendo Entertainment System - Mario Hacks"},
    "203": {"color": "#0089CF", "brand": "Sega", "name": "Megadrive_-_Sonic_The_Hedgehog_2_Hacks"},
    "205": {"color": "#999999", "brand": "Various", "name": "Texas Instruments Ti 99/4A"},
    "206": {"color": "#999999", "brand": "Various", "name": "LUTRO"},
    "207": {"color": "#999999", "brand": "Various", "name": "WATARA SUPERVISION"},
    "208": {"color": "#FF6600", "brand": "NEC", "name": "NEC PC98"},
    "210": {"color": "#E60012", "brand": "Nintendo", "name": "Super Nintendo Msu-1"},
    "211": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Pokemon Mini"},
    "213": {"color": "#999999", "brand": "Various", "name": "MGT SAM COUPÉ"},
    "214": {"color": "#999999", "brand": "Various", "name": "MUGEN"},
    "216": {"color": "#999999", "brand": "Various", "name": "UZEBOX"},
    "217": {"color": "#999999", "brand": "Various", "name": "APPLE IIGS"},
    "218": {"color": "#999999", "brand": "Various", "name": "SPECTRAVIDEO"},
    "219": {"color": "#999999", "brand": "Various", "name": "PALM"},
    "220": {"color": "#999999", "brand": "Various", "name": "SHARP X1"},
    "221": {"color": "#FF6600", "brand": "NEC", "name": "Nec Pc-8000 - Pc-8800 Series"},
    "222": {"color": "#999999", "brand": "Various", "name": "TIC80"},
    "223": {"color": "#999999", "brand": "Various", "name": "SOLARUS"},
    "225": {"color": "#E60012", "brand": "Nintendo", "name": "NINTENDO SWITCH"},
    "227": {"color": "#0089CF", "brand": "Sega", "name": "NAOMIGD"},
    "230": {"color": "#0089CF", "brand": "Sega", "name": "SEGA NAOMI 2"},
    "231": {"color": "#999999", "brand": "Various", "name": "EASYRPG"},
    "234": {"color": "#999999", "brand": "Various", "name": "PICO-8"},
    "237": {"color": "#999999", "brand": "Various", "name": "PCV2"},
    "241": {"color": "#999999", "brand": "Various", "name": "CREATIVISION"},
    "244": {"color": "#999999", "brand": "Various", "name": "LOWRES NX"},
    "250": {"color": "#0089CF", "brand": "Sega", "name": "SEGA PICO"},
    "253": {"color": "#999999", "brand": "Various", "name": "FMTMARTY"},
    "261": {"color": "#999999", "brand": "Various", "name": "VG5000"},
    "262": {"color": "#999999", "brand": "Various", "name": "WASM-4"},
    "263": {"color": "#999999", "brand": "Various", "name": "ARDUBOY"},
    "266": {"color": "#999999", "brand": "Various", "name": "GAMATE"},
    "269": {"color": "#999999", "brand": "Various", "name": "TEKNOPARROT"},
    "272": {"color": "#999999", "brand": "Various", "name": "VIRCON32"},
    "275": {"color": "#999999", "brand": "Various", "name": "VOXATRON"},
    "278": {"color": "#E60012", "brand": "Nintendo", "name": "Nintendo Entertainment System - Mario Hacks"},
    "287": {"color": "#999999", "brand": "Various", "name": "P2000T"},
}


def get_brand_info(system_id):
    return BRAND_INFO.get(str(system_id), {"color": "#718096", "brand": "Unknown", "name": "UNKNOWN"})


# ---------- CONSOLE LOGO IMAGES WITH CACHING ----------
import tempfile
import hashlib

# Create a cache directory in temp
LOGO_CACHE_DIR = os.path.join(tempfile.gettempdir(), "scraper_logos")
os.makedirs(LOGO_CACHE_DIR, exist_ok=True)

# Local logos folder support
# Handle both regular Python and PyInstaller bundled EXE
if getattr(sys, 'frozen', False):
    # Running as bundled EXE - logos are in temp folder extracted by PyInstaller
    LOCAL_LOGOS_FOLDER = get_resource_path("console_logos")
else:
    # Running as normal Python script - use local folder
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOCAL_LOGOS_FOLDER = os.path.join(BASE_DIR, "console_logos")
    # Only create folder when running as script
    os.makedirs(LOCAL_LOGOS_FOLDER, exist_ok=True)



# Logo URLs from multiple sources
LOGO_SOURCES = {
    # Using gamesdatabase.org console logo images
    "atari2600": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_2600/logo/big/Atari_2600_01.jpg",
    "atari5200": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_5200/logo/big/Atari_5200_01.jpg",
    "atari7800": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_7800/logo/big/Atari_7800_01.jpg",
    "atarijaguar": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_Jaguar/logo/big/Atari_Jaguar_01.jpg",
    "atarijaguarcd": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_Jaguar_CD/logo/big/Atari_Jaguar_CD_01.jpg",
    "atarilynx": "https://www.gamesdatabase.org/Media/SYSTEM/Atari_Lynx/logo/big/Atari_Lynx_01.jpg",
    
    "nes": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_NES/logo/big/Nintendo_NES_01.jpg",
    "snes": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_SNES/logo/big/Nintendo_SNES_01.jpg",
    "sfc": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Super_Famicom/logo/big/Nintendo_Super_Famicom_01.jpg",
    "fds": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Famicom_Disk_System/logo/big/Nintendo_Famicom_Disk_System_01.jpg",
    "n64": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_N64/logo/big/Nintendo_N64_01.jpg",
    "gamecube": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_GameCube/logo/big/Nintendo_GameCube_01.jpg",
    "wii": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Wii/logo/big/Nintendo_Wii_01.jpg",
    "gameboy": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Game_Boy/logo/big/Nintendo_Game_Boy_01.jpg",
    "gameboycolor": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Game_Boy_Color/logo/big/Nintendo_Game_Boy_Color_01.jpg",
    "gameboyadvance": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_Game_Boy_Advance/logo/big/Nintendo_Game_Boy_Advance_01.jpg",
    "ds": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_DS/logo/big/Nintendo_DS_01.jpg",
    "3ds": "https://www.gamesdatabase.org/Media/SYSTEM/Nintendo_3DS/logo/big/Nintendo_3DS_01.jpg",
    
    "ps1": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_Playstation/logo/big/Sony_Playstation_01.jpg",
    "ps2": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_Playstation_2/logo/big/Sony_Playstation_2_01.jpg",
    "ps3": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_Playstation_3/logo/big/Sony_Playstation_3_01.jpg",
    "ps4": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_Playstation_4/logo/big/Sony_Playstation_4_01.jpg",
    "psp": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_PSP/logo/big/Sony_PSP_01.jpg",
    "psvita": "https://www.gamesdatabase.org/Media/SYSTEM/Sony_Playstation_Vita/logo/big/Sony_Playstation_Vita_01.jpg",
    
    "genesis": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_Genesis/logo/big/Sega_Genesis_01.jpg",
    "mastersystem": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_Master_System/logo/big/Sega_Master_System_01.jpg",
    "saturn": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_Saturn/logo/big/Sega_Saturn_01.jpg",
    "dreamcast": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_Dreamcast/logo/big/Sega_Dreamcast_01.jpg",
    "gamegear": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_Game_Gear/logo/big/Sega_Game_Gear_01.jpg",
    "sega32x": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_32X/logo/big/Sega_32X_01.jpg",
    "segacd": "https://www.gamesdatabase.org/Media/SYSTEM/Sega_CD/logo/big/Sega_CD_01.jpg",
    
    "xbox": "https://www.gamesdatabase.org/Media/SYSTEM/Microsoft_Xbox/logo/big/Microsoft_Xbox_01.jpg",
    "xbox360": "https://www.gamesdatabase.org/Media/SYSTEM/Microsoft_Xbox_360/logo/big/Microsoft_Xbox_360_01.jpg",
    
    "neogeo": "https://www.gamesdatabase.org/Media/SYSTEM/SNK_Neo_Geo/logo/big/SNK_Neo_Geo_01.jpg",
    "ngp": "https://www.gamesdatabase.org/Media/SYSTEM/SNK_Neo_Geo_Pocket/logo/big/SNK_Neo_Geo_Pocket_01.jpg",
    "ngpc": "https://www.gamesdatabase.org/Media/SYSTEM/SNK_Neo_Geo_Pocket_Color/logo/big/SNK_Neo_Geo_Pocket_Color_01.jpg",
}

SYSTEM_TO_LOGO = {
    "26": "atari2600", "40": "atari5200", "41": "atari7800", "43": "atari800",
    "27": "atarijaguar", "171": "atarijaguarcd", "28": "lynx", "42": "atarist", "88": "camplynx",
    "214": "openbor", "118": "msxturbor",
    "75": "lcdgames",

    "3": "nes", "4": "snes", "14": "n64", "106": "fds", "107": "sfc",
    "13": "gamecube", "16": "wii", "18": "wiiu",
    "9": "gameboy", "10": "gbc", "12": "gameboyadvance",
    "15": "ds", "17": "3ds", "103": "gmaster",

    "57": "ps1", "58": "ps2", "59": "ps3", "60": "ps4",
    "61": "psp", "62": "psvita",
    "81": "actionmax",
    "78": "advision",
    "65": "amstradcpc",
    "84": "archimedes",
    "263": "arduboy",
    "44": "astrocade", "45": "wswan", "46": "wswanc",
    "36": "atom", "207": "supervision",
    "53": "atomiswave",
    "37": "bbcmicro",
    "266": "gamate",
    "194": "gaelco",
    "85": "electron", "121": "gamecom",
    
    "1": "genesis", "2": "mastersystem",
    "20": "megacd", "21": "gamegear",
    "22": "saturn", "23": "dreamcast",
    "109": "sg1000", "222": "tic80",
    "19": "sega32x",
    "56": "naomi",
    "230": "naomi2",
    "54": "model2",
    "55": "model3",
    "89": "adam", 
    "64": "amiga500",
    "111": "amiga1200", "111": "amiga4000",
    "134": "amigacd32", "129": "amigacdtv",
    "168": "apfm1000",

    "32": "xbox", "33": "xbox360",
    "29": "3do",
    "49": "daphne",
    "135": "dos",
    "91": "dragon32",
    "75": "fbneo",
    "97": "fm7",
    "253": "fmtowns",
    "52": "gameandwatch",
    "138": "windows",
    "101": "gp32", "69": "segastv",
    
    "113": "msx1",
    "80": "channelf",
    "94": "arcadia",
    "73": "c16",
    "73": "c20",
    "66": "c64",
    "66": "c128", "99": "cplus4",
    "47": "cave", "48": "colecovision",
    "241": "crvision", "241": "cvision", "241": "creativision",

    "142": "neogeo",
    "70": "neogeocd",
    "143": "neogeocd",
    "25": "ngp", "82": "ngpc",
    "6": "cps1",
    "7": "cps2",
    "8": "cps3", "76": "zxs",
    
    "31": "pcengine",
    "114": "pcenginecd",
    "105": "supergrafx",    # Optional if you have it

    # 🍏 Apple
    "86": "apple2",
    "87": "apple2gs",

    # 🕹 Odyssey² / Videopac
    "104": "odyssey2",
    "75": "mame",
}

def download_logo(brand_name):
    """Download logo from gamesdatabase.org"""
    if brand_name not in LOGO_SOURCES:
        return None
    
    cache_path = os.path.join(LOGO_CACHE_DIR, f"{brand_name}.jpg")
    
    # Check cache first
    if os.path.exists(cache_path):
        try:
            return Image.open(cache_path)
        except:
            pass
    
    # Download from gamesdatabase.org
    try:
        url = LOGO_SOURCES[brand_name]
        with urllib.request.urlopen(url, timeout=5) as response:
            logo_data = response.read()
        
        logo_img = Image.open(io.BytesIO(logo_data))
        logo_img.save(cache_path, "JPEG")
        return logo_img
    except:
        return None

def get_logo_for_system(system_id, system_key):
    """Get logo: tries local folder first, then downloads"""

    brand = system_key   # ← THIS IS THE FIX

    print(f"[LOGO DEBUG] System ID: {system_id} -> Brand: {brand}")
    print(f"[LOGO DEBUG] Looking in folder: {LOCAL_LOGOS_FOLDER}")

    # 1. Try local logos folder first
    for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
        local_path = os.path.join(LOCAL_LOGOS_FOLDER, f"{brand}{ext}")
        print(f"[LOGO DEBUG] Checking: {local_path} - Exists: {os.path.exists(local_path)}")
        if os.path.exists(local_path):
            try:
                print(f"[LOGO DEBUG] ✓ Loading local logo: {local_path}")
                return Image.open(local_path)
            except Exception as e:
                print(f"[LOGO DEBUG] ✗ Failed to load {local_path}: {e}")

    # 2. Optional fallback to ID-based logo (if you want)
    fallback = SYSTEM_TO_LOGO.get(str(system_id))
    if fallback:
        for ext in ['.png', '.jpg', '.jpeg']:
            local_path = os.path.join(LOCAL_LOGOS_FOLDER, f"{fallback}{ext}")
            if os.path.exists(local_path):
                return Image.open(local_path)

    print(f"[LOGO DEBUG] No local logo found for {brand}")
    return None

# Developer credentials live only on the relay server, never in this client.
from relay_client import RelayClient, RelayClientError
SOFTNAME = "UltimateScraperPro 1.2.0"
APP_VERSION = "1.2.0"
_relay_client = None

def relay_client():
    global _relay_client
    if _relay_client is None:
        _relay_client = RelayClient()
    return _relay_client

CONFIG_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "UltimateScraperPro", "settings.json")

# ========== GITHUB FALLBACK MEDIA ==========
GITHUB_MEDIA_BASE = ""  # No personal media repository in public builds.

SYSTEM_TO_GITHUB_FOLDER = {
    # add systems here as you want
    "17": "3ds",
    "113": "msx1",
}

# ========== FRONTEND FOLDER PROFILES ==========
FRONTEND_PROFILES = {
    "retrobat": {
        "name": "RetroBat / Batocera / EmulationStation",
        "patterns": {
            "box2d": "images/{GAME}-thumb.png",
            "box3d": "images/{GAME}-box3d.png",
            "screenshot": "images/{GAME}-image.png",
            "screenshottitle": "images/{GAME}-screenshottitle.png",
            "logo": "images/{GAME}-logo.png",
            "marquee": "images/{GAME}-marquee.png",
            "fanart": "images/{GAME}-fanart.png",
            "boxback": "images/{GAME}-boxback.png",
            "cartridge": "images/{GAME}-cartridge.png",
            "video": "videos/{GAME}-video.mp4",
            "manual": "manuals/{GAME}.pdf",
        }
    },
    "launchbox": {
        "name": "LaunchBox / BigBox",
        "patterns": {
            "box2d": "Box - Front/{GAME}.png",
            "box3d": "Box - 3D/{GAME}.png",
            "screenshot": "Screenshot - Gameplay/{GAME}.png",
            "screenshottitle": "Screenshot - Game Title/{GAME}.png",
            "logo": "Clear Logo/{GAME}.png",
            "marquee": "Arcade - Marquee/{GAME}.png",
            "fanart": "Fanart - Background/{GAME}.jpg",
            "boxback": "Box - Back/{GAME}.png",
            "cartridge": "Cart - Front/{GAME}.png",
            "video": "videos/{GAME}.mp4",
            "manual": "Manuals/{GAME}.pdf",
        }
    }
}




# ---------- EXTENSION MAPPING FOR images/, videos/ AND manuals/ SUBFOLDERS ----------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov"}
MANUAL_EXTS = {".pdf", ".chm"}

# Boot filenames we treat specially for disc/folder-based systems
BOOT_FILENAMES = {"EBOOT.BIN", "DEFAULT.XBE", "DEFAULT.XEX"}


def get_media_target_path(output_folder: str, rel_path: str) -> str:
    rel_path_norm = rel_path.replace("\\", "/")

    if "/" in rel_path_norm:
        return os.path.join(output_folder, *rel_path_norm.split("/"))

    name = rel_path_norm
    ext = os.path.splitext(name)[1].lower()

    if ext in IMAGE_EXTS:
        base = os.path.join(output_folder, "images")
    elif ext in VIDEO_EXTS:
        base = os.path.join(output_folder, "videos")
    elif ext in MANUAL_EXTS:
        base = os.path.join(output_folder, "manuals")
    else:
        base = output_folder

    return os.path.join(base, name)


# ---------- SIMPLE SYSTEM AUTO-DETECT (FROM FOLDER NAME) ----------

SYSTEM_KEYWORD_MAP = {
    "3do": {"id": "29", "name": "3DO", "icon": "3do.png"},
    "3do interactive multiplayer": {"id": "29", "name": "3Do Interactive Multiplayer", "icon": "3do_interactive_multiplayer.png"},
    "3ds": {"id": "17", "name": "3DS", "icon": "3ds.png"},
    "64dd": {"id": "122", "name": "64Dd", "icon": "64dd.png"},
    "a2600": {"id": "26", "name": "A2600", "icon": "a2600.png"},
    "a2k1": {"id": "94", "name": "A2K1", "icon": "a2k1.png"},
    "a5200": {"id": "40", "name": "A5200", "icon": "a5200.png"},
    "a7800": {"id": "41", "name": "A7800", "icon": "a7800.png"},
    "a800": {"id": "43", "name": "A800", "icon": "a800.png"},
    "aamber pegasus": {"id": "83", "name": "Aamber Pegasus", "icon": "aamber_pegasus.png"},
    "aamber_pegasus": {"id": "83", "name": "Aamber_Pegasus", "icon": "aamber_pegasus.png"},
    "acclaim": {"id": "166", "name": "Acclaim", "icon": "acclaim.png"},
    "ace4000": {"id": "126", "name": "Ace4000", "icon": "ace4000.png"},
    "acorn archimedes": {"id": "84", "name": "Acorn Archimedes", "icon": "acorn_archimedes.png"},
    "acorn atom": {"id": "36", "name": "Acorn Atom", "icon": "acorn_atom.png"},
    "acorn electron": {"id": "85", "name": "Acorn Electron", "icon": "acorn_electron.png"},
    "action_max": {"id": "81", "name": "Action_Max", "icon": "action_max.png"},
    "actionmax": {"id": "81", "name": "Actionmax", "icon": "actionmax.png"},
    "adam": {"id": "89", "name": "Adam", "icon": "adam.png"},
    "adventure_vision": {"id": "78", "name": "Adventure_Vision", "icon": "adventure_vision.png"},
    "advision": {"id": "78", "name": "Advision", "icon": "advision.png"},
    "ags": {"id": "138", "name": "Ags", "icon": "ags.png"},
    "alg": {"id": "170", "name": "Alg", "icon": "alg.png"},
    "alpha_denshi_co.": {"id": "182", "name": "Alpha_Denshi_Co.", "icon": "alpha_denshi_co..png"},
    "amazon": {"id": "138", "name": "Amazon", "icon": "amazon.png"},
    "amcoe": {"id": "178", "name": "Amcoe", "icon": "amcoe.png"},
    "american_laser_games": {"id": "170", "name": "American_Laser_Games", "icon": "american_laser_games.png"},
    "amiga": {"id": "64", "name": "Amiga", "icon": "amiga.png"},
    "amiga1000": {"id": "111", "name": "Amiga 1000", "icon": "amiga1000.png"},
    "amiga1200": {"id": "111", "name": "Amiga 1200", "icon": "amiga1200.png"},
    "amiga3000": {"id": "111", "name": "Amiga 3000", "icon": "amiga3000.png"},
    "amiga4000": {"id": "111", "name": "Amiga 4000", "icon": "amiga4000.png"},
    "amiga500": {"id": "64", "name": "Amiga 500", "icon": "amiga500.png"},
    "amiga500p": {"id": "64", "name": "Amiga500P", "icon": "amiga500p.png"},
    "amiga600": {"id": "64", "name": "Amiga600", "icon": "amiga600.png"},
    "amiga_cd": {"id": "134", "name": "Amiga_Cd", "icon": "amiga_cd.png"},
    "amiga_cd32_(hack)": {"id": "139", "name": "Amiga_Cd32_(Hack)", "icon": "amiga_cd32_(hack).png"},
    "amigacd32": {"id": "130", "name": "Amiga CD32", "icon": "Amiga CD32.png"},
    "amigacdtv": {"id": "129", "name": "Amiga CDTV", "icon": "amigacdtv.png"},
    "apfm1000": {"id": "168", "name": "APFM 1000", "icon": "apfm1000.png"},
    "amstrad": {"id": "65", "name": "Amstrad", "icon": "amstrad.png"},
    "amstrad cpc": {"id": "65", "name": "Amstrad CPC", "icon": "amstrad_cpc.png"},
    "amstrad gx4000": {"id": "87", "name": "Amstrad GX4000", "icon": "amstrad_gx4000.png"},
    "amstradcpc": {"id": "65", "name": "Amstrad CPC", "icon": "amstradcpc.png"},
    "android": {"id": "63", "name": "Android", "icon": "android.png"},
    "another_arcade_emulator": {"id": "35", "name": "Another_Arcade_Emulator", "icon": "another_arcade_emulator.png"},
    "apple ii": {"id": "86", "name": "Apple II", "icon": "apple_ii.png"},
    "apple iigs": {"id": "217", "name": "Apple IIGS", "icon": "apple_iigs.png"},
    "apple mac os": {"id": "146", "name": "Apple Mac OS", "icon": "apple_mac_os.png"},
    "apple2": {"id": "86", "name": "Apple 2", "icon": "apple2.png"},
    "apple2gs": {"id": "217", "name": "Apple2Gs", "icon": "apple2gs.png"},
    "arcade": {"id": "75", "name": "Arcade", "icon": "arcade.png"},
    "arcade_classics": {"id": "75", "name": "Arcade_Classics", "icon": "arcade_classics.png"},
    "arcadia": {"id": "94", "name": "Arcadia", "icon": "arcadia.png"},
    "arcadia_2001": {"id": "94", "name": "Arcadia_2001", "icon": "arcadia_2001.png"},
    "archimede": {"id": "84", "name": "Archimede", "icon": "archimede.png"},
    "archimedes": {"id": "84", "name": "Archimedes", "icon": "archimedes.png"},
    "arduboy": {"id": "263", "name": "Arduboy", "icon": "arduboy.png"},
    "astrocade": {"id": "44", "name": "Astrocade", "icon": "astrocade.png"},
    "astrocde": {"id": "44", "name": "Astrocde", "icon": "astrocde.png"},
    "atari": {"id": "26", "name": "Atari", "icon": "atari.png"},
    "atari 2600": {"id": "26", "name": "Atari 2600", "icon": "atari_2600.png"},
    "atari 5200": {"id": "40", "name": "Atari 5200", "icon": "atari_5200.png"},
    "atari 7800": {"id": "41", "name": "Atari 7800", "icon": "atari_7800.png"},
    "atari 800": {"id": "43", "name": "Atari 800", "icon": "atari_800.png"},
    "atari jaguar": {"id": "27", "name": "Atari Jaguar", "icon": "atari_jaguar.png"},
    "atari jaguar cd": {"id": "171", "name": "Atari Jaguar CD", "icon": "atari_jaguar_cd.png"},
    "atari lynx": {"id": "28", "name": "Atari Lynx", "icon": "atari_lynx.png"},
    "atari st": {"id": "42", "name": "Atari ST", "icon": "atari_st.png"},
    "atari st-ste-tt-falcon": {"id": "42", "name": "Atari ST-STE-TT-Falcon", "icon": "atari_st_ste_tt_falcon.png"},
    "atari2600": {"id": "26", "name": "Atari 2600", "icon": "atari2600.png"},
    "atari5200": {"id": "40", "name": "Atari 5200", "icon": "atari5200.png"},
    "atari7800": {"id": "41", "name": "Atari 7800", "icon": "atari7800.png"},
    "atari800": {"id": "43", "name": "Atari 800", "icon": "atari800.png"},
    "atari8bits": {"id": "43", "name": "Atari8Bits", "icon": "atari8bits.png"},
    "atari_2600_supercharger": {"id": "39", "name": "Atari_2600_Supercharger", "icon": "atari_2600_supercharger.png"},
    "atari_classics": {"id": "160", "name": "Atari_Classics", "icon": "atari_classics.png"},
    "atari_xe": {"id": "43", "name": "Atari_Xe", "icon": "atari_xe.png"},
    "atarijaguar": {"id": "27", "name": "Atarijaguar", "icon": "atarijaguar.png"},
    "atarijaguarcd": {"id": "171", "name": "Atarijaguarcd", "icon": "atarijaguarcd.png"},
    "atarilynx": {"id": "28", "name": "Atarilynx", "icon": "atarilynx.png"},
    "atarist": {"id": "42", "name": "AtariST", "icon": "atarist.png"},
    "atarixegs": {"id": "43", "name": "Atarixegs", "icon": "atarixegs.png"},
    "atlus": {"id": "185", "name": "Atlus", "icon": "atlus.png"},
    "atom": {"id": "36", "name": "Atom", "icon": "atom.png"},
    "atomiswave": {"id": "53", "name": "Atomiswave", "icon": "atomiswave.png"},
    "bally astrocade": {"id": "44", "name": "Bally Astrocade", "icon": "bally_astrocade.png"},
    "bandai wonderswan-color": {"id": "46", "name": "Bandai WonderSwan-Color", "icon": "bandai_wonderswan_color.png"},
    "banpresto": {"id": "186", "name": "Banpresto", "icon": "banpresto.png"},
    "bbc": {"id": "37", "name": "Bbc", "icon": "bbc.png"},
    "bbc microcomputer system": {"id": "37", "name": "BBC Microcomputer System", "icon": "bbc_microcomputer_system.png"},
    "bbc_micro": {"id": "37", "name": "Bbc_Micro", "icon": "bbc_micro.png"},
    "bbcmicro": {"id": "37", "name": "BBC Micro", "icon": "bbcmicro.png"},
    "bk": {"id": "93", "name": "Bk", "icon": "bk.png"},
    "c128": {"id": "66", "name": "Commodore 128", "icon": "c128.png"},
    "c16": {"id": "73", "name": "Commodore 16", "icon": "c16.png"},
    "c20": {"id": "73", "name": "Commodore VIC-20", "icon": "c20.png"},
    "c64": {"id": "66", "name": "Commodore 64", "icon": "c64.png"},
    "camplynx": {"id": "88", "name": "Camplynx", "icon": "camplynx.png"},
    "camputers lynx": {"id": "88", "name": "Camputers Lynx", "icon": "camputers_lynx.png"},
    "camputers_lynx": {"id": "88", "name": "Camputers_Lynx", "icon": "camputers_lynx.png"},
    "cannonball": {"id": "75", "name": "Cannonball", "icon": "cannonball.png"},
    "capcom play system": {"id": "6", "name": "Capcom Play System", "icon": "capcom_play_system.png"},
    "capcom play system ii": {"id": "7", "name": "Capcom Play System II", "icon": "capcom_play_system_ii.png"},
    "capcom play system iii": {"id": "8", "name": "Capcom Play System III", "icon": "capcom_play_system_iii.png"},
    "capcom_classics": {"id": "151", "name": "Capcom_Classics", "icon": "capcom_classics.png"},
    "capcom_play_system": {"id": "6", "name": "Capcom_Play_System", "icon": "capcom_play_system.png"},
    "capcom_play_system_2": {"id": "7", "name": "Capcom_Play_System_2", "icon": "capcom_play_system_2.png"},
    "capcom_play_system_3": {"id": "8", "name": "Capcom_Play_System_3", "icon": "capcom_play_system_3.png"},
    "casio loopy": {"id": "98", "name": "Casio Loopy", "icon": "casio_loopy.png"},
    "casio pv-1000": {"id": "74", "name": "Casio PV-1000", "icon": "casio_pv_1000.png"},
    "cave": {"id": "47", "name": "Cave", "icon": "cave.png"},
    "cave3rd": {"id": "47", "name": "Cave3Rd", "icon": "cave3rd.png"},
    "cavestory": {"id": "135", "name": "Cavestory", "icon": "cavestory.png"},
    "cd-i": {"id": "133", "name": "Cd-I", "icon": "cd_i.png"},
    "cd32": {"id": "130", "name": "Cd32", "icon": "cd32.png"},
    "cdi": {"id": "133", "name": "Philips CD-I", "icon": "cdi.png"},
    "cdimono1": {"id": "133", "name": "Cdimono1", "icon": "cdimono1.png"},
    "century_electronics": {"id": "179", "name": "Century_Electronics", "icon": "century_electronics.png"},
    "cg2000": {"id": "92", "name": "Cg2000", "icon": "cg2000.png"},
    "chailove": {"id": "138", "name": "Chailove", "icon": "chailove.png"},
    "channel-f": {"id": "80", "name": "Channel-F", "icon": "channel_f.png"},
    "channel_f": {"id": "80", "name": "Channel_F", "icon": "channel_f.png"},
    "channelf": {"id": "80", "name": "Channelf", "icon": "channelf.png"},
    "chihiro": {"id": "75", "name": "Chihiro", "icon": "chihiro.png"},
    "chip-8": {"id": "00", "name": "CHIP-8", "icon": "chip_8.png"},
    "cinematronics": {"id": "192", "name": "Cinematronics", "icon": "cinematronics.png"},
    "coco": {"id": "144", "name": "Coco", "icon": "coco.png"},
    "coco3": {"id": "144", "name": "Coco3", "icon": "coco3.png"},
    "coleco": {"id": "183", "name": "Coleco", "icon": "coleco.png"},
    "coleco adam": {"id": "89", "name": "Coleco ADAM", "icon": "coleco_adam.png"},
    "colecovision": {"id": "48", "name": "Colecovision", "icon": "colecovision.png"},
    "comad": {"id": "177", "name": "Comad", "icon": "comad.png"},
    "commodore": {"id": "66", "name": "Commodore", "icon": "commodore.png"},
    "commodore 64": {"id": "66", "name": "Commodore 64", "icon": "commodore_64.png"},
    "commodore amiga": {"id": "64", "name": "Commodore Amiga", "icon": "commodore_amiga.png"},
    "commodore amiga cd32": {"id": "130", "name": "Commodore Amiga CD32", "icon": "commodore_amiga_cd32.png"},
    "commodore c128": {"id": "66", "name": "Commodore C128", "icon": "commodore_c128.png"},
    "commodore c64": {"id": "66", "name": "Commodore C64", "icon": "commodore_c64.png"},
    "commodore cbm-ii": {"id": "66", "name": "Commodore CBM-II", "icon": "commodore_cbm_ii.png"},
    "commodore cdtv": {"id": "129", "name": "Commodore CDTV", "icon": "commodore_cdtv.png"},
    "commodore pet": {"id": "66", "name": "Commodore PET", "icon": "commodore_pet.png"},
    "commodore plus 4": {"id": "99", "name": "Commodore Plus 4", "icon": "commodore_plus_4.png"},
    "commodore vic-20": {"id": "73", "name": "Commodore VIC-20", "icon": "commodore_vic_20.png"},
    "consolearcade": {"id": "75", "name": "Consolearcade", "icon": "consolearcade.png"},
    "coregrafx": {"id": "50", "name": "Coregrafx", "icon": "coregrafx.png"},
    "cougar_boy": {"id": "90", "name": "Cougar_Boy", "icon": "cougar_boy.png"},
    "cpc": {"id": "65", "name": "Cpc", "icon": "cpc.png"},
    "cplus4": {"id": "99", "name": "Commodore Plus 4", "icon": "cplus4.png"},
    "cps1": {"id": "6", "name": "Capcom Play System I", "icon": "cps1.png"},
    "cps2": {"id": "7", "name": "Capcom Play System II", "icon": "cps2.png"},
    "cps3": {"id": "8", "name": "Capcom Play System III", "icon": "cps3.png"},
    "creativision": {"id": "241", "name": "Creativision", "icon": "creativision.png"},
    "crvision": {"id": "241", "name": "Crvision", "icon": "crvision.png"},
    "cvision": {"id": "241", "name": "Cvision", "icon": "cvision.png"},
    "daphne": {"id": "49", "name": "Daphne", "icon": "daphne.png"},
    "data_east_classics": {"id": "162", "name": "Data_East_Classics", "icon": "data_east_classics.png"},
    "dinothawr": {"id": "63", "name": "Dinothawr", "icon": "dinothawr.png"},
    "doom": {"id": "135", "name": "Doom", "icon": "doom.png"},
    "dos": {"id": "135", "name": "DOS", "icon": "dos.png"},
    "dragon": {"id": "91", "name": "Dragon", "icon": "dragon.png"},
    "dragon 32-64": {"id": "91", "name": "Dragon 32-64", "icon": "dragon_32_64.png"},
    "dragon32": {"id": "91", "name": "Dragon 32", "icon": "dragon32.png"},
    "dreamcast": {"id": "23", "name": "Dreamcast", "icon": "dreamcast.png"},
    "ds": {"id": "15", "name": "Ds", "icon": "ds.png"},
    "dynax": {"id": "173", "name": "Dynax", "icon": "dynax.png"},
    "eaca eg2000 colour genie": {"id": "92", "name": "EACA EG2000 Colour Genie", "icon": "eaca_eg2000_colour_genie.png"},
    "eagames": {"id": "138", "name": "Eagames", "icon": "eagames.png"},
    "easyrpg": {"id": "231", "name": "Easyrpg", "icon": "easyrpg.png"},
    "ecv": {"id": "67", "name": "Ecv", "icon": "ecv.png"},
    "ecwolf": {"id": "135", "name": "Ecwolf", "icon": "ecwolf.png"},
    "eduke32": {"id": "138", "name": "Eduke32", "icon": "eduke32.png"},
    "eg2000_colour_genie": {"id": "92", "name": "Eg2000_Colour_Genie", "icon": "eg2000_colour_genie.png"},
    "eighthundred": {"id": "43", "name": "Eighthundred", "icon": "eighthundred.png"},
    "eighting_raizing": {"id": "152", "name": "Eighting_Raizing", "icon": "eighting_raizing.png"},
    "electron": {"id": "85", "name": "Electron", "icon": "electron.png"},
    "elektronika bk": {"id": "93", "name": "Elektronika BK", "icon": "elektronika_bk.png"},
    "emerson arcadia 2001": {"id": "94", "name": "Emerson Arcadia 2001", "icon": "emerson_arcadia_2001.png"},
    "enterprise": {"id": "76", "name": "Enterprise", "icon": "enterprise.png"},
    "entex adventure vision": {"id": "78", "name": "Entex Adventure Vision", "icon": "entex_adventure_vision.png"},
    "ep128": {"id": "76", "name": "Ep128", "icon": "ep128.png"},
    "ep64": {"id": "76", "name": "Ep64", "icon": "ep64.png"},
    "epic": {"id": "138", "name": "Epic", "icon": "epic.png"},
    "epoch game pocket computer": {"id": "95", "name": "Epoch Game Pocket Computer", "icon": "epoch_game_pocket_computer.png"},
    "epoch super cassette vision": {"id": "67", "name": "Epoch Super Cassette Vision", "icon": "epoch_super_cassette_vision.png"},
    "exelvision exl 100": {"id": "96", "name": "Exelvision EXL 100", "icon": "exelvision_exl_100.png"},
    "exidy": {"id": "165", "name": "Exidy", "icon": "exidy.png"},
    "exl100": {"id": "96", "name": "Exl100", "icon": "exl100.png"},
    "exl_100": {"id": "96", "name": "Exl_100", "icon": "exl_100.png"},
    "fairchild": {"id": "80", "name": "Fairchild", "icon": "fairchild.png"},
    "fairchild channel f": {"id": "80", "name": "Fairchild Channel F", "icon": "fairchild_channel_f.png"},
    "fairchild channelf": {"id": "80", "name": "Fairchild ChannelF", "icon": "fairchild_channelf.png"},
    "famicom": {"id": "3", "name": "Famicom", "icon": "famicom.png"},
    "family_computer": {"id": "3", "name": "Family_Computer", "icon": "family_computer.png"},
    "famiri_konpyuta_disuku_shisutemu": {"id": "106", "name": "Famiri_Konpyuta_Disuku_Shisutemu", "icon": "famiri_konpyuta_disuku_shisutemu.png"},
    "fba": {"id": "75", "name": "Fba", "icon": "fba.png"},
    "fba2012": {"id": "75", "name": "Fba2012", "icon": "fba2012.png"},
    "fba_libretro": {"id": "75", "name": "Fba_Libretro", "icon": "fba_libretro.png"},
    "fbneo": {"id": "75", "name": "FBNEO", "icon": "fbneo.png"},
    "fc": {"id": "3", "name": "Fc", "icon": "fc.png"},
    "fds": {"id": "106", "name": "Famicom Disk System", "icon": "fds.png"},
    "flash": {"id": "63", "name": "Flash", "icon": "flash.png"},
    "flipper": {"id": "197", "name": "Flipper", "icon": "flipper.png"},
    "fm-7": {"id": "97", "name": "Fm-7", "icon": "fm_7.png"},
    "fm7": {"id": "97", "name": "FM7", "icon": "fm7.png"},
    "fmtmarty": {"id": "253", "name": "Fmtmarty", "icon": "fmtmarty.png"},
    "fmtowns": {"id": "253", "name": "FM Towns", "icon": "fmtowns.png"},
    "fpinball": {"id": "199", "name": "Fpinball", "icon": "fpinball.png"},
    "fujitsu fm-7": {"id": "97", "name": "Fujitsu FM-7", "icon": "fujitsu_fm_7.png"},
    "funtech super acan": {"id": "100", "name": "Funtech Super Acan", "icon": "funtech_super_acan.png"},
    "future_pinball": {"id": "199", "name": "Future_Pinball", "icon": "future_pinball.png"},
    "gaelco": {"id": "194", "name": "Gaelco", "icon": "gaelco.png"},
    "gamate": {"id": "266", "name": "Gamate", "icon": "gamate.png"},
    "game & watch": {"id": "52", "name": "Game & Watch", "icon": "game_&_watch.png"},
    "game.com": {"id": "121", "name": "Game.Com", "icon": "game.com.png"},
    "game_master": {"id": "103", "name": "Game_Master", "icon": "game_master.png"},
    "game_pocket_computer": {"id": "95", "name": "Game_Pocket_Computer", "icon": "game_pocket_computer.png"},
    "gameandwatch": {"id": "52", "name": "Game & Watch", "icon": "gameandwatch.png"},
    "gamecom": {"id": "121", "name": "Gamecom", "icon": "gamecom.png"},
    "gamecube": {"id": "13", "name": "Gamecube", "icon": "gamecube.png"},
    "gamegear": {"id": "21", "name": "Game Gear", "icon": "gamegear.png"},
    "gamepock": {"id": "95", "name": "Gamepock", "icon": "gamepock.png"},
    "gb": {"id": "9", "name": "Game Boy", "icon": "gb.png"},
    "gb2players": {"id": "9", "name": "Gb2Players", "icon": "gb2players.png"},
    "gba": {"id": "12", "name": "Game Boy Advance", "icon": "gba.png"},
    "gba_e-reader": {"id": "119", "name": "Gba_E-Reader", "icon": "gba_e_reader.png"},
    "gbc": {"id": "10", "name": "Game Boy Color", "icon": "gbc.png"},
    "gc": {"id": "13", "name": "Gc", "icon": "gc.png"},
    "gce vectrex": {"id": "102", "name": "GCE Vectrex", "icon": "gce_vectrex.png"},
    "gce-vectrex": {"id": "102", "name": "GCE-Vectrex", "icon": "gce_vectrex.png"},
    "genesis": {"id": "1", "name": "Genesis", "icon": "genesis.png"},
    "gg": {"id": "21", "name": "Gg", "icon": "gg.png"},
    "gmaster": {"id": "103", "name": "Game Master", "icon": "gmaster.png"},
    "gog": {"id": "138", "name": "Gog", "icon": "gog.png"},
    "gp32": {"id": "101", "name": "GP32", "icon": "gp32.png"},
    "gw": {"id": "52", "name": "Gw", "icon": "gw.png"},
    "gx4000": {"id": "87", "name": "GX4000", "icon": "gx4000.png"},
    "handheld electronic - game and watch": {"id": "52", "name": "Handheld Electronic - Game and Watch", "icon": "handheld_electronic___game_and_watch.png"},
    "hartung game master": {"id": "103", "name": "Hartung Game Master", "icon": "hartung_game_master.png"},
    "hbmame": {"id": "75", "name": "Hbmame", "icon": "hbmame.png"},
    "hikaru": {"id": "75", "name": "Hikaru", "icon": "hikaru.png"},
    "igs": {"id": "176", "name": "Igs", "icon": "igs.png"},
    "incredible_technologies": {"id": "193", "name": "Incredible_Technologies", "icon": "incredible_technologies.png"},
    "intellivision": {"id": "115", "name": "Intellivision", "icon": "intellivision.png"},
    "irem_classics": {"id": "148", "name": "Irem_Classics", "icon": "irem_classics.png"},
    "jaguar": {"id": "27", "name": "Jaguar", "icon": "jaguar.png"},
    "jaguar_cd": {"id": "171", "name": "Jaguar_Cd", "icon": "jaguar_cd.png"},
    "jaguarcd": {"id": "171", "name": "Jaguar CD", "icon": "Jaguar CD.png"},
    "jaleco": {"id": "159", "name": "Jaleco", "icon": "jaleco.png"},
    "java j2me": {"id": "00", "name": "Java J2ME", "icon": "java_j2me.png"},
    "jupace": {"id": "126", "name": "Jupace", "icon": "jupace.png"},
    "jupiter ace": {"id": "126", "name": "Jupiter Ace", "icon": "jupiter_ace.png"},
    "jupiter_ace": {"id": "126", "name": "Jupiter_Ace", "icon": "jupiter_ace.png"},
    "kaneko": {"id": "174", "name": "Kaneko", "icon": "kaneko.png"},
    "konami_classics": {"id": "158", "name": "Konami_Classics", "icon": "konami_classics.png"},
    "laserdisc": {"id": "49", "name": "Laserdisc", "icon": "laserdisc.png"},
    "lcdgames": {"id": "75", "name": "LCD Games", "icon": "LCD Games.png"},
    "lindbergh": {"id": "75", "name": "Lindbergh", "icon": "lindbergh.png"},
    "linux": {"id": "145", "name": "Linux", "icon": "linux.png"},
    "loopy": {"id": "98", "name": "Loopy", "icon": "loopy.png"},
    "love2d": {"id": "00", "name": "Love2D", "icon": "love2d.png"},
    "lowres nx": {"id": "244", "name": "Lowres NX", "icon": "lowres_nx.png"},
    "lowresnx": {"id": "244", "name": "Lowresnx", "icon": "lowresnx.png"},
    "lua engine": {"id": "00", "name": "Lua Engine", "icon": "lua_engine.png"},
    "lutro": {"id": "206", "name": "Lutro", "icon": "lutro.png"},
    "lynx": {"id": "28", "name": "Lynx", "icon": "lynx.png"},
    "mac": {"id": "146", "name": "Mac", "icon": "mac.png"},
    "mac_os": {"id": "146", "name": "Mac_Os", "icon": "mac_os.png"},
    "macintosh": {"id": "146", "name": "Macintosh", "icon": "macintosh.png"},
    "magnavox odyssey 2": {"id": "104", "name": "Magnavox Odyssey 2", "icon": "magnavox_odyssey_2.png"},
    "mame": {"id": "75", "name": "MAME", "icon": "mame.png"},
    "mame-advmame": {"id": "75", "name": "Mame-Advmame", "icon": "mame_advmame.png"},
    "mame-libretro": {"id": "75", "name": "Mame-Libretro", "icon": "mame_libretro.png"},
    "mame-mame4all": {"id": "75", "name": "Mame-Mame4All", "icon": "mame_mame4all.png"},
    "mame2000": {"id": "75", "name": "Mame2000", "icon": "mame2000.png"},
    "mame2003": {"id": "75", "name": "Mame2003", "icon": "mame2003.png"},
    "mastersystem": {"id": "2", "name": "Mastersystem", "icon": "mastersystem.png"},
    "mattel - intellivision": {"id": "115", "name": "Mattel - Intellivision", "icon": "mattel___intellivision.png"},
    "mattel intellivision": {"id": "115", "name": "Mattel Intellivision", "icon": "mattel_intellivision.png"},
    "md": {"id": "1", "name": "Md", "icon": "md.png"},
    "mdcd": {"id": "20", "name": "Mdcd", "icon": "mdcd.png"},
    "mega duck": {"id": "90", "name": "Mega Duck", "icon": "mega_duck.png"},
    "mega duck - cougar boy": {"id": "90", "name": "Mega Duck - Cougar Boy", "icon": "mega_duck___cougar_boy.png"},
    "mega-cd": {"id": "20", "name": "Mega-Cd", "icon": "mega_cd.png"},
    "mega-play": {"id": "196", "name": "Mega-Play", "icon": "mega_play.png"},
    "mega-tech": {"id": "195", "name": "Mega-Tech", "icon": "mega_tech.png"},
    "mega_duck": {"id": "90", "name": "Mega_Duck", "icon": "mega_duck.png"},
    "megacd": {"id": "20", "name": "Mega CD", "icon": "megacd.png"},
    "megacdjp": {"id": "20", "name": "Megacdjp", "icon": "megacdjp.png"},
    "megadrive": {"id": "1", "name": "Megadrive", "icon": "megadrive.png"},
    "megadrive msu": {"id": "1", "name": "Megadrive MSU", "icon": "megadrive_msu.png"},
    "megadrive-msu": {"id": "1", "name": "Megadrive-Msu", "icon": "megadrive_msu.png"},
    "megadrive_-_sonic_the_hedgehog_2_hacks": {"id": "203", "name": "Megadrive_-_Sonic_The_Hedgehog_2_Hacks", "icon": "megadrive___sonic_the_hedgehog_2_hacks.png"},
    "megadrive_32x": {"id": "19", "name": "Megadrive_32X", "icon": "megadrive_32x.png"},
    "megadrivejp": {"id": "1", "name": "Megadrivejp", "icon": "megadrivejp.png"},
    "megaduck": {"id": "90", "name": "Megaduck", "icon": "megaduck.png"},
    "mess": {"id": "75", "name": "Mess", "icon": "mess.png"},
    "mgt sam coupé": {"id": "213", "name": "MGT SAM Coupé", "icon": "mgt_sam_coupé.png"},
    "microsoft - msx": {"id": "113", "name": "Microsoft - MSX", "icon": "microsoft___msx.png"},
    "microsoft - msx2": {"id": "116", "name": "Microsoft - MSX2", "icon": "microsoft___msx2.png"},
    "microsoft msx": {"id": "113", "name": "Microsoft MSX", "icon": "microsoft_msx.png"},
    "microsoft msx2": {"id": "116", "name": "Microsoft MSX2", "icon": "microsoft_msx2.png"},
    "microsoft msx2+": {"id": "117", "name": "Microsoft MSX2+", "icon": "microsoft_msx2+.png"},
    "microsoft xbox": {"id": "32", "name": "Microsoft Xbox", "icon": "microsoft_xbox.png"},
    "microsoft xbox 360": {"id": "33", "name": "Microsoft Xbox 360", "icon": "microsoft_xbox_360.png"},
    "microsoft xbox one": {"id": "34", "name": "Microsoft Xbox One", "icon": "microsoft_xbox_one.png"},
    "midway_classics": {"id": "150", "name": "Midway_Classics", "icon": "midway_classics.png"},
    "mikrosha": {"id": "124", "name": "Mikrosha", "icon": "mikrosha.png"},
    "mitchell": {"id": "189", "name": "Mitchell", "icon": "mitchell.png"},
    "mo5": {"id": "140", "name": "Mo5", "icon": "mo5.png"},
    "model2": {"id": "54", "name": "Model 2", "icon": "model2.png"},
    "model3": {"id": "55", "name": "Model 3", "icon": "model3.png"},
    "moonlight": {"id": "135", "name": "Moonlight", "icon": "moonlight.png"},
    "moto": {"id": "141", "name": "Moto", "icon": "moto.png"},
    "ms": {"id": "2", "name": "Ms", "icon": "ms.png"},
    "ms-dos": {"id": "135", "name": "MS-DOS", "icon": "ms_dos.png"},
    "msx": {"id": "113", "name": "Msx", "icon": "msx.png"},
    "msx1": {"id": "113", "name": "MSX1", "icon": "msx1.png"},
    "msx2": {"id": "116", "name": "MSX2", "icon": "msx2.png"},
    "msx2+": {"id": "117", "name": "MSX2+", "icon": "msx2+.png"},
    "msx_r_turbo": {"id": "118", "name": "Msx_R_Turbo", "icon": "msx_r_turbo.png"},
    "msxturbor": {"id": "118", "name": "MSX Turbo R", "icon": "msxturbor.png"},
    "mtx": {"id": "75", "name": "Mtx", "icon": "mtx.png"},
    "mtx512": {"id": "75", "name": "Mtx512", "icon": "mtx512.png"},
    "mugen": {"id": "214", "name": "Mugen", "icon": "mugen.png"},
    "multivision": {"id": "109", "name": "Multivision", "icon": "multivision.png"},
    "mv": {"id": "00", "name": "Mv", "icon": "mv.png"},
    "n-gage": {"id": "30", "name": "N-Gage", "icon": "n_gage.png"},
    "n3ds": {"id": "17", "name": "N3Ds", "icon": "n3ds.png"},
    "n64": {"id": "14", "name": "N64", "icon": "n64.png"},
    "n64dd": {"id": "122", "name": "N64DD", "icon": "n64dd.png"},
    "namco system 22": {"id": "156", "name": "Namco System 22", "icon": "namco_system_22.png"},
    "namco2x6": {"id": "155", "name": "Namco2X6", "icon": "namco2x6.png"},
    "namco3xx": {"id": "155", "name": "Namco3Xx", "icon": "namco3xx.png"},
    "namco_classics": {"id": "155", "name": "Namco_Classics", "icon": "namco_classics.png"},
    "namco_system_22": {"id": "156", "name": "Namco_System_22", "icon": "namco_system_22.png"},
    "naomi": {"id": "56", "name": "Naomi", "icon": "naomi.png"},
    "naomi2": {"id": "230", "name": "Naomi 2", "icon": "naomi2.png"},
    "naomigd": {"id": "227", "name": "Naomigd", "icon": "naomigd.png"},
    "nds": {"id": "15", "name": "NDS", "icon": "nds.png"},
    "nec - pc engine cd": {"id": "114", "name": "NEC - PC Engine CD", "icon": "nec___pc_engine_cd.png"},
    "nec - turbografx cd": {"id": "114", "name": "NEC - TurboGrafx CD", "icon": "nec___turbografx_cd.png"},
    "nec pc engine": {"id": "31", "name": "PC Engine", "icon": "nec_pc_engine.png"},
    "nec pc engine cd": {"id": "114", "name": "NEC PC Engine CD", "icon": "nec_pc_engine_cd.png"},
    "nec pc engine supergrafx": {"id": "105", "name": "NEC PC Engine SuperGrafx", "icon": "nec_pc_engine_supergrafx.png"},
    "nec pc engine-cd": {"id": "114", "name": "NEC PC Engine-CD", "icon": "nec_pc_engine_cd.png"},
    "nec pc-8000 - pc-8800 series": {"id": "221", "name": "NEC PC-8000 - PC-8800 series", "icon": "nec_pc_8000___pc_8800_series.png"},
    "nec pc-fx": {"id": "72", "name": "NEC PC-FX", "icon": "nec_pc_fx.png"},
    "nec pc98": {"id": "208", "name": "NEC PC98", "icon": "nec_pc98.png"},
    "nec turbografx-16": {"id": "31", "name": "NEC TurboGrafx-16", "icon": "nec_turbografx_16.png"},
    "neo-geo_cd": {"id": "70", "name": "Neo-Geo_Cd", "icon": "neo_geo_cd.png"},
    "neo-geo_mvs": {"id": "68", "name": "Neo-Geo_Mvs", "icon": "neo_geo_mvs.png"},
    "neocd": {"id": "70", "name": "Neocd", "icon": "neocd.png"},
    "neogeo": {"id": "142", "name": "Neo Geo", "icon": "neogeo.png"},
    "neogeo64": {"id": "142", "name": "Neogeo64", "icon": "neogeo64.png"},
    "neogeocd": {"id": "70", "name": "Neo Geo CD", "icon": "neogeocd.png"},
    "neogeocdjp": {"id": "70", "name": "Neogeocdjp", "icon": "neogeocdjp.png"},
    "neogeomini": {"id": "142", "name": "Neogeomini", "icon": "neogeomini.png"},
    "neogeox": {"id": "142", "name": "Neogeox", "icon": "neogeox.png"},
    "nes": {"id": "3", "name": "NES", "icon": "nes.png"},
    "nesmini": {"id": "3", "name": "Nesmini", "icon": "nesmini.png"},
    "ngage": {"id": "30", "name": "Ngage", "icon": "ngage.png"},
    "ngp": {"id": "25", "name": "NGP", "icon": "ngp.png"},
    "ngpc": {"id": "82", "name": "NGPC", "icon": "ngpc.png"},
    "nichibutsu": {"id": "180", "name": "Nichibutsu", "icon": "nichibutsu.png"},
    "nintendo 3ds": {"id": "17", "name": "Nintendo 3DS", "icon": "nintendo_3ds.png"},
    "nintendo 64": {"id": "14", "name": "Nintendo 64", "icon": "nintendo_64.png"},
    "nintendo 64dd": {"id": "122", "name": "Nintendo 64DD", "icon": "nintendo_64dd.png"},
    "nintendo ds": {"id": "15", "name": "Nintendo DS", "icon": "nintendo_ds.png"},
    "nintendo entertainment system": {"id": "3", "name": "Nintendo Entertainment System", "icon": "nintendo_entertainment_system.png"},
    "nintendo entertainment system - mario hacks": {"id": "278", "name": "Nintendo Entertainment System - Mario Hacks", "icon": "nintendo_entertainment_system___mario_hacks.png"},
    "nintendo famicom disk system": {"id": "106", "name": "Nintendo Famicom Disk System", "icon": "nintendo_famicom_disk_system.png"},
    "nintendo game boy": {"id": "9", "name": "Nintendo Game Boy", "icon": "nintendo_game_boy.png"},
    "nintendo game boy advance": {"id": "12", "name": "Nintendo Game Boy Advance", "icon": "nintendo_game_boy_advance.png"},
    "nintendo game boy color": {"id": "10", "name": "Nintendo Game Boy Color", "icon": "nintendo_game_boy_color.png"},
    "nintendo gamecube": {"id": "13", "name": "Nintendo GameCube", "icon": "nintendo_gamecube.png"},
    "nintendo n64": {"id": "14", "name": "Nintendo N64", "icon": "nintendo_n64.png"},
    "nintendo nes-famicom": {"id": "3", "name": "Nintendo NES-Famicom", "icon": "nintendo_nes_famicom.png"},
    "nintendo pokemon mini": {"id": "211", "name": "Nintendo Pokemon Mini", "icon": "nintendo_pokemon_mini.png"},
    "nintendo satellaview": {"id": "107", "name": "Nintendo Satellaview", "icon": "nintendo_satellaview.png"},
    "nintendo snes-sfc": {"id": "4", "name": "Nintendo SNES-SFC", "icon": "nintendo_snes_sfc.png"},
    "nintendo switch": {"id": "225", "name": "Nintendo Switch", "icon": "nintendo_switch.png"},
    "nintendo virtual boy": {"id": "11", "name": "Nintendo Virtual Boy", "icon": "nintendo_virtual_boy.png"},
    "nintendo wii": {"id": "16", "name": "Nintendo Wii", "icon": "nintendo_wii.png"},
    "nintendo wii u": {"id": "18", "name": "Nintendo Wii U", "icon": "nintendo_wii_u.png"},
    "nintendo_64dd": {"id": "122", "name": "Nintendo_64Dd", "icon": "nintendo_64dd.png"},
    "nintendo_classics": {"id": "161", "name": "Nintendo_Classics", "icon": "nintendo_classics.png"},
    "nintendo_power": {"id": "110", "name": "Nintendo_Power", "icon": "nintendo_power.png"},
    "nmk": {"id": "163", "name": "Nmk", "icon": "nmk.png"},
    "nokia n-gage": {"id": "30", "name": "Nokia N-Gage", "icon": "nokia_n_gage.png"},
    "np2pi": {"id": "208", "name": "Np2Pi", "icon": "np2pi.png"},
    "o2em": {"id": "104", "name": "O2EM", "icon": "o2em.png"},
    "odyssey": {"id": "104", "name": "Odyssey", "icon": "odyssey.png"},
    "odyssey2": {"id": "104", "name": "Odyssey2", "icon": "odyssey2.png"},
    "onscripter": {"id": "00", "name": "Onscripter", "icon": "onscripter.png"},
    "openbor": {"id": "214", "name": "OpenBOR", "icon": "openbor.png"},
    "oric": {"id": "131", "name": "Oric", "icon": "oric.png"},
    "oric atmos": {"id": "131", "name": "Oric Atmos", "icon": "oric_atmos.png"},
    "oricatmos": {"id": "131", "name": "Oricatmos", "icon": "oricatmos.png"},
    "p2000t": {"id": "287", "name": "P2000T", "icon": "p2000t.png"},
    "palm": {"id": "219", "name": "Palm", "icon": "palm.png"},
    "panasonic": {"id": "29", "name": "Panasonic", "icon": "panasonic.png"},
    "pc": {"id": "135", "name": "Pc", "icon": "pc.png"},
    "pc engine supergrafx": {"id": "105", "name": "PC Engine SuperGrafx", "icon": "pc_engine_supergrafx.png"},
    "pc-fx": {"id": "72", "name": "Pc-Fx", "icon": "pc_fx.png"},
    "pc88": {"id": "221", "name": "PC88", "icon": "pc88.png"},
    "pc98": {"id": "208", "name": "PC98", "icon": "pc98.png"},
    "pc_engine": {"id": "31", "name": "Pc_Engine", "icon": "pc_engine.png"},
    "pc_win3.xx": {"id": "136", "name": "Pc_Win3.Xx", "icon": "pc_win3.xx.png"},
    "pc_win9x": {"id": "137", "name": "Pc_Win9X", "icon": "pc_win9x.png"},
    "pc_windows": {"id": "138", "name": "Pc_Windows", "icon": "pc_windows.png"},
    "pcarcade": {"id": "75", "name": "Pcarcade", "icon": "pcarcade.png"},
    "pce": {"id": "31", "name": "Pce", "icon": "pce.png"},
    "pce-cd": {"id": "114", "name": "Pce-Cd", "icon": "pce_cd.png"},
    "pceightyeight": {"id": "221", "name": "Pceightyeight", "icon": "pceightyeight.png"},
    "pcengine": {"id": "31", "name": "PC Engine", "icon": "pcengine.png"},
    "pcenginecd": {"id": "114", "name": "PC Engine CD", "icon": "pcenginecd.png"},
    "pcfx": {"id": "72", "name": "PCFX", "icon": "pcfx.png"},
    "pcninetyeight": {"id": "208", "name": "Pcninetyeight", "icon": "pcninetyeight.png"},
    "pcv2": {"id": "237", "name": "Pcv2", "icon": "pcv2.png"},
    "pdark": {"id": "14", "name": "Pdark", "icon": "pdark.png"},
    "pecom_64": {"id": "125", "name": "Pecom_64", "icon": "pecom_64.png"},
    "pet": {"id": "73", "name": "PET", "icon": "pet.png"},
    "philips cd-i": {"id": "133", "name": "Philips CD-i", "icon": "philips_cd_i.png"},
    "philips cdi": {"id": "133", "name": "Philips CDi", "icon": "philips_cdi.png"},
    "pico": {"id": "234", "name": "Pico", "icon": "pico.png"},
    "pico-8": {"id": "234", "name": "PICO-8", "icon": "pico_8.png"},
    "pico8": {"id": "234", "name": "Pico8", "icon": "pico8.png"},
    "piece": {"id": "00", "name": "Piece", "icon": "piece.png"},
    "pinball": {"id": "197", "name": "Pinball", "icon": "pinball.png"},
    "pinball_fx2": {"id": "143", "name": "Pinball_Fx2", "icon": "pinball_fx2.png"},
    "pinball_fx3": {"id": "201", "name": "Pinball_Fx3", "icon": "pinball_fx3.png"},
    "pinballfx": {"id": "143", "name": "Pinballfx", "icon": "pinballfx.png"},
    "pinballfx2": {"id": "143", "name": "Pinballfx2", "icon": "pinballfx2.png"},
    "pinballfx3": {"id": "201", "name": "Pinballfx3", "icon": "pinballfx3.png"},
    "pinballm": {"id": "138", "name": "Pinballm", "icon": "pinballm.png"},
    "playchoice": {"id": "184", "name": "Playchoice", "icon": "playchoice.png"},
    "playstation_3": {"id": "59", "name": "Playstation_3", "icon": "playstation_3.png"},
    "playstation_minis": {"id": "172", "name": "Playstation_Minis", "icon": "playstation_minis.png"},
    "plus4": {"id": "99", "name": "Plus4", "icon": "plus4.png"},
    "poke": {"id": "211", "name": "Poke", "icon": "poke.png"},
    "pokemini": {"id": "211", "name": "Pokemini", "icon": "pokemini.png"},
    "pokemonmini": {"id": "211", "name": "Pokemonmini", "icon": "pokemonmini.png"},
    "port": {"id": "290", "name": "Port", "icon": "port.png"},
    "prboom": {"id": "135", "name": "Prboom", "icon": "prboom.png"},
    "ps": {"id": "57", "name": "Ps", "icon": "ps.png"},
    "ps1": {"id": "57", "name": "Playstation", "icon": "ps1.png"},
    "ps2": {"id": "58", "name": "Playstation 2", "icon": "ps2.png"},
    "ps3": {"id": "59", "name": "Playstation 3", "icon": "ps3.png"},
    "ps_vita": {"id": "62", "name": "Ps_Vita", "icon": "ps_vita.png"},
    "psikyo": {"id": "167", "name": "Psikyo", "icon": "psikyo.png"},
    "psp": {"id": "61", "name": "PSP", "icon": "psp.png"},
    "pspminis": {"id": "61", "name": "Pspminis", "icon": "pspminis.png"},
    "psvita": {"id": "62", "name": "PS Vista", "icon": "psvita.png"},
    "psx": {"id": "57", "name": "Playstation", "icon": "psx.png"},
    "psxmini": {"id": "57", "name": "Psxmini", "icon": "psxmini.png"},
    "puzzlescript": {"id": "00", "name": "Puzzlescript", "icon": "puzzlescript.png"},
    "pv-1000": {"id": "74", "name": "Pv-1000", "icon": "pv_1000.png"},
    "pv1000": {"id": "74", "name": "PV1000", "icon": "pv1000.png"},
    "quake": {"id": "135", "name": "Quake", "icon": "quake.png"},
    "radio-86rk mikrosha": {"id": "124", "name": "Radio-86RK Mikrosha", "icon": "radio_86rk_mikrosha.png"},
    "reminiscence": {"id": "138", "name": "Reminiscence", "icon": "reminiscence.png"},
    "residualvm": {"id": "123", "name": "Residualvm", "icon": "residualvm.png"},
    "rpg maker 2000 - 2003": {"id": "00", "name": "RPG Maker 2000 - 2003", "icon": "rpg_maker_2000___2003.png"},
    "samcoupe": {"id": "213", "name": "Samcoupe", "icon": "samcoupe.png"},
    "sameduck": {"id": "90", "name": "Sameduck", "icon": "sameduck.png"},
    "sammy atomiswave": {"id": "53", "name": "Sammy Atomiswave", "icon": "sammy_atomiswave.png"},
    "sammy_classics": {"id": "164", "name": "Sammy_Classics", "icon": "sammy_classics.png"},
    "satellaview": {"id": "107", "name": "Satellaview", "icon": "satellaview.png"},
    "saturn": {"id": "22", "name": "Saturn", "icon": "saturn.png"},
    "saturnjp": {"id": "22", "name": "Saturnjp", "icon": "saturnjp.png"},
    "scummvm": {"id": "123", "name": "Scummvm", "icon": "scummvm.png"},
    "scv": {"id": "67", "name": "Scv", "icon": "scv.png"},
    "sdlpop": {"id": "135", "name": "Sdlpop", "icon": "sdlpop.png"},
    "sega 32x": {"id": "19", "name": "Sega 32X", "icon": "sega_32x.png"},
    "sega atomiswave naomi": {"id": "56", "name": "Sega Atomiswave Naomi", "icon": "sega_atomiswave_naomi.png"},
    "sega cd": {"id": "20", "name": "Sega CD", "icon": "sega_cd.png"},
    "sega dreamcast": {"id": "23", "name": "Sega Dreamcast", "icon": "sega_dreamcast.png"},
    "sega game gear": {"id": "21", "name": "Sega Game Gear", "icon": "sega_game_gear.png"},
    "sega genesis": {"id": "1", "name": "Sega Genesis", "icon": "sega_genesis.png"},
    "sega master system": {"id": "2", "name": "Sega Master System", "icon": "sega_master_system.png"},
    "sega mega cd - sega cd": {"id": "20", "name": "Sega Mega CD - Sega CD", "icon": "sega_mega_cd___sega_cd.png"},
    "sega mega drive - genesis": {"id": "1", "name": "Sega Mega Drive - Genesis", "icon": "sega_mega_drive___genesis.png"},
    "sega model 2": {"id": "54", "name": "Sega Model 2", "icon": "sega_model_2.png"},
    "sega model 3": {"id": "55", "name": "Sega Model 3", "icon": "sega_model_3.png"},
    "sega naomi": {"id": "56", "name": "Sega Naomi", "icon": "sega_naomi.png"},
    "sega naomi 2": {"id": "230", "name": "Sega Naomi 2", "icon": "sega_naomi_2.png"},
    "sega pico": {"id": "250", "name": "Sega Pico", "icon": "sega_pico.png"},
    "sega saturn": {"id": "22", "name": "Sega Saturn", "icon": "sega_saturn.png"},
    "sega sg-1000": {"id": "109", "name": "Sega SG-1000", "icon": "sega_sg_1000.png"},
    "sega st-v": {"id": "69", "name": "Sega ST-V", "icon": "sega_st_v.png"},
    "sega32x": {"id": "19", "name": "Sega32X", "icon": "sega32x.png"},
    "sega32xjp": {"id": "19", "name": "Sega32Xjp", "icon": "sega32xjp.png"},
    "sega32xna": {"id": "19", "name": "Sega32Xna", "icon": "sega32xna.png"},
    "sega_classics": {"id": "147", "name": "Sega_Classics", "icon": "sega_classics.png"},
    "sega_st-v": {"id": "69", "name": "Sega_St-V", "icon": "sega_st_v.png"},
    "segacd": {"id": "20", "name": "Segacd", "icon": "segacd.png"},
    "segapico": {"id": "250", "name": "Segapico", "icon": "segapico.png"},
    "segasgone": {"id": "109", "name": "Segasgone", "icon": "segasgone.png"},
    "seibu_kaihatsu": {"id": "190", "name": "Seibu_Kaihatsu", "icon": "seibu_kaihatsu.png"},
    "semicom": {"id": "187", "name": "Semicom", "icon": "semicom.png"},
    "seta": {"id": "149", "name": "Seta", "icon": "seta.png"},
    "sfc": {"id": "4", "name": "Super Famicom Computer", "icon": "sfc.png"},
    "sg-1000": {"id": "109", "name": "Sg-1000", "icon": "sg_1000.png"},
    "sg1000": {"id": "109", "name": "SG1000", "icon": "sg1000.png"},
    "sgb": {"id": "127", "name": "Sgb", "icon": "sgb.png"},
    "sgfx": {"id": "105", "name": "Sgfx", "icon": "sgfx.png"},
    "sharp x1": {"id": "220", "name": "Sharp X1", "icon": "sharp_x1.png"},
    "sharp x68000": {"id": "79", "name": "Sharp X68000", "icon": "sharp_x68000.png"},
    "sharpx1": {"id": "220", "name": "Sharpx1", "icon": "sharpx1.png"},
    "shmups": {"id": "75", "name": "Shmups", "icon": "shmups.png"},
    "sinclair": {"id": "76", "name": "Sinclair", "icon": "sinclair.png"},
    "sinclair zx 81": {"id": "77", "name": "Sinclair ZX 81", "icon": "sinclair_zx_81.png"},
    "sinclair zx spectrum": {"id": "76", "name": "Sinclair ZX Spectrum", "icon": "sinclair_zx_spectrum.png"},
    "sinclair zx-81": {"id": "77", "name": "Sinclair ZX-81", "icon": "sinclair_zx_81.png"},
    "singe": {"id": "49", "name": "Singe", "icon": "singe.png"},
    "sms": {"id": "2", "name": "Sms", "icon": "sms.png"},
    "snes": {"id": "4", "name": "SNES", "icon": "snes.png"},
    "snes-hacks": {"id": "202", "name": "Snes-Hacks", "icon": "snes_hacks.png"},
    "snes-msu1": {"id": "210", "name": "Snes-Msu1", "icon": "snes_msu1.png"},
    "snes_-_super_mario_world_hacks": {"id": "202", "name": "Snes_-_Super_Mario_World_Hacks", "icon": "snes___super_mario_world_hacks.png"},
    "snescd": {"id": "210", "name": "Snescd", "icon": "snescd.png"},
    "snesmini": {"id": "4", "name": "Snesmini", "icon": "snesmini.png"},
    "snesmsu1": {"id": "210", "name": "Snesmsu1", "icon": "snesmsu1.png"},
    "snesna": {"id": "4", "name": "Snesna", "icon": "snesna.png"},
    "snk neo geo": {"id": "142", "name": "SNK Neo Geo", "icon": "snk_neo_geo.png"},
    "snk neo geo cd": {"id": "70", "name": "SNK Neo Geo CD", "icon": "snk_neo_geo_cd.png"},
    "snk neo geo mvs": {"id": "68", "name": "SNK Neo Geo MVS", "icon": "snk_neo_geo_mvs.png"},
    "snk neo geo pocket": {"id": "25", "name": "SNK Neo Geo Pocket", "icon": "snk_neo_geo_pocket.png"},
    "snk neo geo pocket - color": {"id": "82", "name": "SNK Neo Geo Pocket - Color", "icon": "snk_neo_geo_pocket___color.png"},
    "snk neo geo pocket color": {"id": "82", "name": "SNK Neo Geo Pocket Color", "icon": "snk_neo_geo_pocket_color.png"},
    "snk_classics": {"id": "154", "name": "Snk_Classics", "icon": "snk_classics.png"},
    "socrates": {"id": "120", "name": "Socrates", "icon": "socrates.png"},
    "solarus": {"id": "223", "name": "Solarus", "icon": "solarus.png"},
    "sony playstation": {"id": "57", "name": "Sony Playstation", "icon": "sony_playstation.png"},
    "sony playstation 2": {"id": "58", "name": "Sony Playstation 2", "icon": "sony_playstation_2.png"},
    "sony playstation 3": {"id": "59", "name": "Sony Playstation 3", "icon": "sony_playstation_3.png"},
    "sony playstation 4": {"id": "60", "name": "Sony Playstation 4", "icon": "sony_playstation_4.png"},
    "sony playstation portable": {"id": "61", "name": "Sony Playstation Portable", "icon": "sony_playstation_portable.png"},
    "sony playstation vita": {"id": "62", "name": "Sony Playstation Vita", "icon": "sony_playstation_vita.png"},
    "sony psp": {"id": "61", "name": "Sony PSP", "icon": "sony_psp.png"},
    "sony psp minis": {"id": "172", "name": "Sony PSP Minis", "icon": "sony_psp_minis.png"},
    "spectravideo": {"id": "218", "name": "Spectravideo", "icon": "spectravideo.png"},
    "steam": {"id": "138", "name": "Steam", "icon": "steam.png"},
    "stv": {"id": "69", "name": "Sega STV", "icon": "stv.png"},
    "sufami": {"id": "108", "name": "Sufami", "icon": "sufami.png"},
    "sufami_turbo": {"id": "108", "name": "Sufami_Turbo", "icon": "sufami_turbo.png"},
    "super nintendo entertainment system": {"id": "4", "name": "Super Nintendo Entertainment System", "icon": "super_nintendo_entertainment_system.png"},
    "super nintendo entertainment system - mario hacks": {"id": "202", "name": "Super Nintendo Entertainment System - Mario Hacks", "icon": "super_nintendo_entertainment_system___mario_hacks.png"},
    "super nintendo msu-1": {"id": "210", "name": "Super Nintendo MSU-1", "icon": "super_nintendo_msu_1.png"},
    "super_a'can": {"id": "100", "name": "Super_A'Can", "icon": "super_a'can.png"},
    "super_cassette_vision": {"id": "67", "name": "Super_Cassette_Vision", "icon": "super_cassette_vision.png"},
    "super_game_boy": {"id": "127", "name": "Super_Game_Boy", "icon": "super_game_boy.png"},
    "super_game_boy_2": {"id": "128", "name": "Super_Game_Boy_2", "icon": "super_game_boy_2.png"},
    "supergrafx": {"id": "105", "name": "Supergrafx", "icon": "supergrafx.png"},
    "supervision": {"id": "207", "name": "Watara Supervision", "icon": "supervision.png"},
    "supracan": {"id": "100", "name": "Supracan", "icon": "supracan.png"},
    "switch": {"id": "225", "name": "Switch", "icon": "switch.png"},
    "switch2": {"id": "225", "name": "Switch2", "icon": "switch2.png"},
    "taito type x": {"id": "112", "name": "Taito Type X", "icon": "taito_type_x.png"},
    "taito_classics": {"id": "157", "name": "Taito_Classics", "icon": "taito_classics.png"},
    "tanodragon": {"id": "91", "name": "Tanodragon", "icon": "tanodragon.png"},
    "technos": {"id": "169", "name": "Technos", "icon": "technos.png"},
    "tecmo": {"id": "153", "name": "Tecmo", "icon": "tecmo.png"},
    "teknoparrot": {"id": "269", "name": "Teknoparrot", "icon": "teknoparrot.png"},
    "texas instruments ti 99/4a": {"id": "205", "name": "Texas Instruments TI 99/4A", "icon": "texas_instruments_ti_99/4a.png"},
    "texas instruments ti-83": {"id": "205", "name": "Texas Instruments TI-83", "icon": "texas_instruments_ti_83.png"},
    "tg-cd": {"id": "114", "name": "Tg-Cd", "icon": "tg_cd.png"},
    "tg16": {"id": "31", "name": "Tg16", "icon": "tg16.png"},
    "the 3do company - 3do": {"id": "29", "name": "The 3DO Company - 3DO", "icon": "the_3do_company___3do.png"},
    "the_pinball_arcade": {"id": "200", "name": "The_Pinball_Arcade", "icon": "the_pinball_arcade.png"},
    "theforceengine": {"id": "138", "name": "Theforceengine", "icon": "theforceengine.png"},
    "thirtytwox": {"id": "19", "name": "Thirtytwox", "icon": "thirtytwox.png"},
    "thomson": {"id": "141", "name": "Thomson", "icon": "thomson.png"},
    "thomson mo5": {"id": "141", "name": "Thomson MO5", "icon": "thomson_mo5.png"},
    "thomson to7": {"id": "141", "name": "Thomson TO7", "icon": "thomson_to7.png"},
    "threedo": {"id": "29", "name": "Threedo", "icon": "threedo.png"},
    "ti99": {"id": "205", "name": "Ti99", "icon": "ti99.png"},
    "ti994a": {"id": "205", "name": "Ti994A", "icon": "ti994a.png"},
    "tic": {"id": "205", "name": "Tic", "icon": "tic.png"},
    "tic-80": {"id": "205", "name": "TIC-80", "icon": "tic_80.png"},
    "tic80": {"id": "222", "name": "TIC-80", "icon": "tic80.png"},
    "tiger": {"id": "121", "name": "Tiger", "icon": "tiger.png"},
    "tigerlcd": {"id": "121", "name": "Tigerlcd", "icon": "tigerlcd.png"},
    "to7": {"id": "141", "name": "To7", "icon": "to7.png"},
    "to8": {"id": "141", "name": "To8", "icon": "to8.png"},
    "toaplan": {"id": "191", "name": "Toaplan", "icon": "toaplan.png"},
    "triforce": {"id": "75", "name": "Triforce", "icon": "triforce.png"},
    "trs-80": {"id": "144", "name": "Trs-80", "icon": "trs_80.png"},
    "trs-80 color computer": {"id": "144", "name": "TRS-80 Color Computer", "icon": "trs_80_color_computer.png"},
    "trs80coco": {"id": "144", "name": "Trs80Coco", "icon": "trs80coco.png"},
    "turbografx": {"id": "31", "name": "Turbografx", "icon": "turbografx.png"},
    "turbografx-16": {"id": "31", "name": "Turbografx-16", "icon": "turbografx_16.png"},
    "turbografxcd": {"id": "31", "name": "Turbografxcd", "icon": "turbografxcd.png"},
    "tvc": {"id": "00", "name": "Tvc", "icon": "tvc.png"},
    "type-x": {"id": "112", "name": "Type-X", "icon": "type_x.png"},
    "typex": {"id": "112", "name": "Typex", "icon": "typex.png"},
    "tyrquake": {"id": "135", "name": "Tyrquake", "icon": "tyrquake.png"},
    "universal": {"id": "188", "name": "Universal", "icon": "universal.png"},
    "uzebox": {"id": "216", "name": "Uzebox", "icon": "uzebox.png"},
    "v.smile": {"id": "120", "name": "V.Smile", "icon": "v.smile.png"},
    "vb": {"id": "11", "name": "Vb", "icon": "vb.png"},
    "vectrex": {"id": "102", "name": "Vectrex", "icon": "vectrex.png"},
    "vg5000": {"id": "261", "name": "Vg5000", "icon": "vg5000.png"},
    "vg5k": {"id": "261", "name": "VG5K", "icon": "vg5k.png"},
    "vgmplay": {"id": "75", "name": "Vgmplay", "icon": "vgmplay.png"},
    "vic-20": {"id": "73", "name": "Vic-20", "icon": "vic_20.png"},
    "vic20": {"id": "73", "name": "Vic20", "icon": "vic20.png"},
    "video_system_co.": {"id": "175", "name": "Video_System_Co.", "icon": "video_system_co..png"},
    "videopac": {"id": "104", "name": "Videopac", "icon": "videopac.png"},
    "videopacplus": {"id": "104", "name": "Videopacplus", "icon": "videopacplus.png"},
    "vircon32": {"id": "272", "name": "Vircon32", "icon": "vircon32.png"},
    "virtualboy": {"id": "11", "name": "Virtualboy", "icon": "virtualboy.png"},
    "visco": {"id": "181", "name": "Visco", "icon": "visco.png"},
    "visual_pinball": {"id": "198", "name": "Visual_Pinball", "icon": "visual_pinball.png"},
    "vmac": {"id": "00", "name": "Vmac", "icon": "vmac.png"},
    "voxatron": {"id": "275", "name": "Voxatron", "icon": "voxatron.png"},
    "vpinball": {"id": "198", "name": "Vpinball", "icon": "vpinball.png"},
    "vsmile": {"id": "120", "name": "Vsmile", "icon": "vsmile.png"},
    "wasm-4": {"id": "262", "name": "WASM-4", "icon": "wasm_4.png"},
    "wasm4": {"id": "262", "name": "Wasm4", "icon": "wasm4.png"},
    "watara supervision": {"id": "207", "name": "Watara Supervision", "icon": "watara_supervision.png"},
    "watara_supervision": {"id": "207", "name": "Watara_Supervision", "icon": "watara_supervision.png"},
    "wii": {"id": "16", "name": "Wii", "icon": "wii.png"},
    "wiiu": {"id": "18", "name": "Wii U", "icon": "wiiu.png"},
    "windows": {"id": "138", "name": "Windows", "icon": "windows.png"},
    "windows 3.x": {"id": "136", "name": "Windows 3.X", "icon": "windows_3.x.png"},
    "wolf": {"id": "00", "name": "Wolf", "icon": "wolf.png"},
    "wonderswan": {"id": "45", "name": "Wonderswan", "icon": "wonderswan.png"},
    "wonderswan color": {"id": "46", "name": "WonderSwan Color", "icon": "wonderswan_color.png"},
    "wonderswancolor": {"id": "46", "name": "Wonderswancolor", "icon": "wonderswancolor.png"},
    "wow action max": {"id": "81", "name": "WoW Action Max", "icon": "wow_action_max.png"},
    "ws": {"id": "46", "name": "Ws", "icon": "ws.png"},
    "wswan": {"id": "45", "name": "WonderSwan", "icon": "wswan.png"},
    "wswanc": {"id": "46", "name": "WonderSwan Color", "icon": "wswanc.png"},
    "x1": {"id": "220", "name": "X1", "icon": "x1.png"},
    "x360": {"id": "33", "name": "X360", "icon": "x360.png"},
    "x68000": {"id": "79", "name": "X68000", "icon": "x68000.png"},
    "xash3d_fwgs": {"id": "135", "name": "Xash3D_Fwgs", "icon": "xash3d_fwgs.png"},
    "xbla": {"id": "32", "name": "Xbla", "icon": "xbla.png"},
    "xbox": {"id": "32", "name": "Xbox", "icon": "xbox.png"},
    "xbox360": {"id": "33", "name": "Xbox 360", "icon": "xbox360.png"},
    "xegs": {"id": "43", "name": "Xegs", "icon": "xegs.png"},
    "xone": {"id": "220", "name": "Xone", "icon": "xone.png"},
    "zaccariapinball": {"id": "138", "name": "Zaccariapinball", "icon": "zaccariapinball.png"},
    "zinc": {"id": "75", "name": "Zinc", "icon": "zinc.png"},
    "zx81": {"id": "77", "name": "Zx81", "icon": "zx81.png"},
    "zxeightyone": {"id": "77", "name": "Zxeightyone", "icon": "zxeightyone.png"},
    "zxnext": {"id": "76", "name": "Zxnext", "icon": "zxnext.png"},
    "zxs": {"id": "76", "name": "ZX Spectrum", "icon": "zxs.png"},
}


def get_system_info(folder_name: str):
    """Returns system info dict for a given folder name."""
    folder_lower = folder_name.lower()
    
    if folder_lower in SYSTEM_KEYWORD_MAP:
        info = SYSTEM_KEYWORD_MAP[folder_lower].copy()
        info["folder"] = folder_name
        return info
    
    for keyword, info in SYSTEM_KEYWORD_MAP.items():
        if keyword in folder_lower:
            result = info.copy()
            result["folder"] = folder_name
            return result
    
    return {
        "id": "0",
        "name": folder_name.title(),
        "icon": "MAME.png",
        "folder": folder_name
    }


# Helper function to get system info by folder name
def get_system_info(folder_name: str):
    """
    Returns system info dict for a given folder name.
    Returns None if not found.
    """
    folder_lower = folder_name.lower()
    
    # Direct match
    if folder_lower in SYSTEM_KEYWORD_MAP:
        info = SYSTEM_KEYWORD_MAP[folder_lower].copy()
        info["folder"] = folder_name
        return info
    
    # Partial match
    for keyword, info in SYSTEM_KEYWORD_MAP.items():
        if keyword in folder_lower:
            result = info.copy()
            result["folder"] = folder_name
            return result
    
    # No match - return generic
    return {
        "id": "0",
        "name": folder_name.title(),
        "icon": "MAME.png",
        "folder": folder_name
    }
    
from urllib.parse import quote

def fetch_github_media(game_name, system_id):
    if not GITHUB_MEDIA_BASE:
        return None
    system_folder = SYSTEM_TO_GITHUB_FOLDER.get(str(system_id))
    if not system_folder:
        return None

    base = f"{GITHUB_MEDIA_BASE}/{system_folder}"
    safe_name = quote(make_safe_filename(game_name))

    media_map = {
        "box2d":      f"{base}/box/{safe_name}.png",
        "logo":       f"{base}/logo/{safe_name}.png",
        "screenshot": f"{base}/screenshot/{safe_name}.png",
        "videos":      f"{base}/videos/{safe_name}.mp4",
        "manual":     f"{base}/manual/{safe_name}.pdf",
    }

    found = {}
    for media_type, url in media_map.items():
        try:
            r = requests.head(url, timeout=5)
            if r.status_code == 200:
                found[media_type] = url
        except:
            pass

    return found if found else None



def autodetect_system_id_from_folder(rom_folder: str) -> str:
    """Auto-detect system ID from folder name using new system database"""
    folder_name = os.path.basename(os.path.normpath(rom_folder))
    system_info = get_system_info(folder_name)
    if system_info:
        return system_info["id"]
    return ""


# ---------- PRESETS ----------

OUTPUT_PRESETS = {
    "RetroBat-style": {
        "description": "RetroBat naming: images/, Video/, manuals/",
        "patterns": {
            "box2d": "images/{GAME}-thumb.png",
            "box3d": "images/{GAME}-box3d.png",
            "boxback": "images/{GAME}-boxback.png",
            "boxside": "images/{GAME}-boxside.png",
            "screenshot": "images/{GAME}-image.png",
            "screenshottitle": "images/{GAME}-titleshot.png",
            "logo": "images/{GAME}-logo.png",
            "marquee": "images/{GAME}-marquee.png",
            "fanart": "images/{GAME}-fanart.png",
            "cartridge": "images/{GAME}-cartridge.png",
            "mix": "images/{GAME}-mix.png",
            "video": "videos/{GAME}-video.mp4",
            "manual": "manuals/{GAME}.pdf",
        },
    },
    "LaunchBox-style": {
        "description": "LaunchBox folders: Box - Front/, Clear Logo/, Video/, etc.",
        "patterns": {
            "box2d": "Box - Front/{GAME}.png",
            "box3d": "Box - 3D/{GAME}.png",
            "boxback": "Box - Back/{GAME}.png",
            "boxside": "Box - Spine/{GAME}.png",
            "screenshot": "Screenshot - Gameplay/{GAME}.png",
            "screenshottitle": "Screenshot - Game Title/{GAME}.png",
            "logo": "Clear Logo/{GAME}.png",
            "marquee": "Arcade - Marquee/{GAME}.png",
            "fanart": "Fanart - Background/{GAME}.jpg",
            "cartridge": "Cart - Front/{GAME}.png",
            "mix": "Box - Front/{GAME}.png",
            "video": "videos/{GAME}.mp4",
            "manual": "Manuals/{GAME}.pdf",
        },
    },
    "Recalbox/ES-style": {
        "description": "Everything under images/, manuals/ and single mp4 per game",
        "patterns": {
            "box2d": "images/{GAME}.png",
            "box3d": "images/{GAME}_3d.png",
            "boxback": "images/{GAME}_back.png",
            "boxside": "images/{GAME}_side.png",
            "screenshot": "images/{GAME}_screen.png",
            "screenshottitle": "images/{GAME}_title.png",
            "logo": "images/{GAME}_logo.png",
            "marquee": "images/{GAME}_marquee.png",
            "fanart": "images/{GAME}_fanart.png",
            "cartridge": "images/{GAME}_cartridge.png",
            "mix": "images/{GAME}_mix.png",
            "video": "images/{GAME}.mp4",
            "manual": "manuals/{GAME}.pdf",
        },
    },
    "Custom": {
        "description": "Define your own patterns for every media type.",
        "patterns": {
            "box2d": "images/{GAME}-thumb.png",
            "box3d": "{GAME}-box3d.png",
            "boxback": "{GAME}-boxback.png",
            "boxside": "{GAME}-boxside.png",
            "screenshot": "{GAME}-image.png",
            "screenshottitle": "{GAME}-titleshot.png",
            "logo": "{GAME}-logo.png",
            "marquee": "{GAME}-marquee.png",
            "fanart": "{GAME}-fanart.png",
            "cartridge": "{GAME}-cartridge.png",
            "mix": "{GAME}-mix.png",
            "video": "{GAME}-video.mp4",
            "manual": "manuals/{GAME}.pdf",
        },
    },
}

# ---------- DEFAULT CONFIG ----------

DEFAULT_MEDIA_TOGGLES = {
    "box2d": True,
    "box3d": True,
    "boxback": True,
    "boxside": True,
    "screenshot": True,
    "screenshottitle": True,
    "logo": True,
    "marquee": True,
    "fanart": True,
    "cartridge": True,
    "mix": True,
    "video": True,
    "manual": True,
}

# ---------- SCREEN SCRAPER MEDIA MAP ----------
SCREEN_SCRAPER_MEDIA_MAP = {
    "box2d": ["box-2D"],
    "box3d": ["box-3D"],
    "boxback": ["box-2D-back"],
    "boxside": ["box-2D-side"],
    "marquee": ["wheel"],
    "cartridge": ["support-2D", "support-3D"],
    "screenshot": ["ss"],
    "screenshottitle": ["sstitle"],
    "logo": ["wheel"],
    "fanart": ["fanart"],
    "mix": ["mixrbv2", "mixrbv1"],
    "video": ["video"],
    "manual": ["manuel"],
}

DEFAULT_CONFIG = {
    "ssid": "",
    "sspassword": "",
    "dark_mode": True,
    "last_rom_folder": "",
    "last_output_folder": "",
    "last_system_id": "",
    "last_system_name": "",
    "output_preset": "RetroBat-style",
    "custom_patterns": OUTPUT_PRESETS["Custom"]["patterns"],
    "max_threads": 4,
    "generate_gamelist": True,
    "media_toggles": DEFAULT_MEDIA_TOGGLES,
    "profiles": {},
    "finish_sound_file": "",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(data)

            if "custom_patterns" not in cfg:
                cfg["custom_patterns"] = OUTPUT_PRESETS["Custom"]["patterns"].copy()
            if "max_threads" not in cfg:
                cfg["max_threads"] = 4
            if "generate_gamelist" not in cfg:
                cfg["generate_gamelist"] = True
            if "media_toggles" not in cfg:
                cfg["media_toggles"] = DEFAULT_MEDIA_TOGGLES.copy()
            else:
                # make sure all keys exist
                mt = DEFAULT_MEDIA_TOGGLES.copy()
                mt.update(cfg["media_toggles"])
                cfg["media_toggles"] = mt
            if "profiles" not in cfg:
                cfg["profiles"] = {}
            if "finish_sound_file" not in cfg:
                cfg["finish_sound_file"] = ""

            # 🔒 Disable ALL custom media everywhere
            cfg["custom_media_url"] = ""

            return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in cfg.items() if not k.startswith("_")}, f, indent=2)
    except Exception:
        # silently ignore (no noisy Permission denied spam)
        pass


# ---------- LAUNCHBOX DATABASE FALLBACK ----------
import sqlite3

# LaunchBox image CDN base URL
LAUNCHBOX_IMAGE_CDN = "https://images.launchbox-app.com/"

# Map ScreenScraper system IDs to LaunchBox platform names
# Based on BRAND_INFO ScreenScraper system IDs
SCREENSCRAPER_TO_LAUNCHBOX_PLATFORM = {
    # Sega
    "1": "Sega Genesis",           # Megadrive MSU
    "2": "Sega Master System",
    "19": "Sega 32X",
    "20": "Sega CD",               # Mega CD
    "21": "Sega Game Gear",
    "22": "Sega Saturn",
    "23": "Sega Dreamcast",
    "53": "Arcade",                # Atomiswave
    "54": "Sega Model 2",
    "55": "Sega Model 3",
    "56": "Arcade",                # Naomi
    "69": "Arcade",                # Sega ST-V
    "109": "Sega SG-1000",

    # Nintendo
    "3": "Nintendo Entertainment System",
    "4": "Super Nintendo Entertainment System",
    "9": "Nintendo Game Boy",
    "10": "Nintendo Game Boy Color",
    "11": "Nintendo Virtual Boy",
    "12": "Nintendo Game Boy Advance",
    "13": "Nintendo GameCube",
    "14": "Nintendo 64",
    "15": "Nintendo DS",
    "16": "Nintendo Wii",
    "17": "Nintendo 3DS",
    "18": "Nintendo Wii U",
    "106": "Nintendo Famicom Disk System",
    "122": "Nintendo 64DD",
    "225": "Nintendo Switch",

    # Sony
    "57": "Sony Playstation",
    "58": "Sony Playstation 2",
    "59": "Sony Playstation 3",
    "60": "Sony Playstation 4",
    "61": "Sony PSP",
    "62": "Sony Playstation Vita",

    # Microsoft
    "32": "Microsoft Xbox",
    "33": "Microsoft Xbox 360",
    "34": "Microsoft Xbox One",
    "113": "MSX",
    "116": "MSX2",
    "117": "MSX2",                  # MSX2+
    "135": "MS-DOS",

    # Atari
    "26": "Atari 2600",
    "27": "Atari Jaguar",
    "28": "Atari Lynx",
    "40": "Atari 5200",
    "41": "Atari 7800",
    "42": "Atari ST",
    "43": "Atari 800",             # This is the fix!

    # SNK
    "25": "SNK Neo Geo Pocket",
    "68": "SNK Neo Geo AES",       # MVS
    "70": "SNK Neo Geo CD",
    "82": "SNK Neo Geo Pocket Color",
    "142": "SNK Neo Geo AES",

    # NEC
    "31": "NEC TurboGrafx-16",     # PC Engine
    "72": "NEC PC-FX",
    "105": "NEC PC Engine SuperGrafx",
    "114": "NEC TurboGrafx-CD",    # PC Engine CD

    # Commodore
    "64": "Commodore Amiga",
    "66": "Commodore 64",
    "73": "Commodore VIC-20",
    "99": "Commodore Plus 4",
    "129": "Commodore CDTV",
    "130": "Commodore Amiga CD32",

    # Bandai
    "45": "WonderSwan",
    "46": "WonderSwan Color",

    # Other systems
    "29": "3DO Interactive Multiplayer",
    "44": "Bally Astrocade",
    "48": "ColecoVision",
    "49": "Arcade",                # Daphne
    "65": "Amstrad CPC",
    "76": "Sinclair ZX Spectrum",
    "77": "Sinclair ZX81",
    "79": "Sharp X68000",
    "80": "Fairchild Channel F",
    "86": "Apple II",
    "87": "Amstrad GX4000",
    "94": "Emerson Arcadia 2001",
    "102": "Vectrex",
    "104": "Magnavox Odyssey 2",
    "115": "Mattel Intellivision",
    "133": "Philips CD-i",
    "168": "APF Imagination Machine",  # APF M1000
    "89": "Coleco ADAM",              # Coleco Adam computer

    # Arcade systems
    "6": "Arcade",                 # CPS1
    "7": "Arcade",                 # CPS2
    "8": "Arcade",                 # CPS3
    "35": "Arcade",
    "47": "Arcade",                # Cave
    "75": "Arcade",                # LCD Games
    "112": "Arcade",               # Taito Type X
}

# Map our media types to LaunchBox image types (with region preference)
MEDIA_TO_LAUNCHBOX_IMAGE_TYPE = {
    "box2d": ["Box - Front", "Box - Front - Reconstructed"],
    "box3d": ["Box - 3D"],
    "boxback": ["Box - Back", "Box - Back - Reconstructed"],
    "boxside": ["Box - Spine"],
    "screenshot": ["Screenshot - Gameplay"],
    "screenshottitle": ["Screenshot - Game Title"],
    "logo": ["Clear Logo"],
    "marquee": ["Clear Logo", "Arcade - Marquee"],
    "fanart": ["Fanart - Background", "Fanart - Box - Front"],
    "cartridge": ["Cart - Front", "Cart - 3D", "Disc"],
    "mix": ["Box - Front"],  # No direct equivalent, fall back to box
}

# Preferred regions for LaunchBox (in priority order)
LAUNCHBOX_PREFERRED_REGIONS = [
    "North America",
    "United States",
    "World",
    "Europe",
    "United Kingdom",
    "",  # Empty region (often default/universal)
]


def get_launchbox_db_path():
    """
    Try to find the LaunchBox metadata database.
    Checks common install locations and config.
    """
    # Try to load from config first
    cfg = load_config()
    custom_path = cfg.get("launchbox_path", "")
    if custom_path:
        db_path = os.path.join(custom_path, "Metadata", "LaunchBox.Metadata.db")
        if os.path.exists(db_path):
            return db_path

    # Common install locations
    common_paths = [
        r"E:\LaunchBox",
        r"C:\LaunchBox",
        r"D:\LaunchBox",
        r"C:\Program Files\LaunchBox",
        r"C:\Program Files (x86)\LaunchBox",
        os.path.expanduser(r"~\LaunchBox"),
    ]

    for base_path in common_paths:
        db_path = os.path.join(base_path, "Metadata", "LaunchBox.Metadata.db")
        if os.path.exists(db_path):
            return db_path

    return None


def search_launchbox_game(game_name, platform_name, db_path=None):
    """
    Search for a game in the LaunchBox database.

    Args:
        game_name: Name of the game to search for
        platform_name: LaunchBox platform name (e.g., "Nintendo Switch")
        db_path: Optional path to database, auto-detected if None

    Returns:
        dict with game info or None if not found
    """
    if db_path is None:
        db_path = get_launchbox_db_path()

    if not db_path or not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Clean the game name for searching
        clean_name = re.sub(r'\s*\(.*?\)', '', game_name).strip()  # Remove (USA), (World), etc.
        clean_name = re.sub(r'\s*\[.*?\]', '', clean_name).strip()  # Remove [!], [b], etc.

        # Also create a normalized version for fuzzy matching
        # Replace common separators with wildcards for SQL LIKE
        normalized = clean_name
        normalized = re.sub(r'[:\-–—]', '%', normalized)  # Colons and dashes become wildcards
        normalized = re.sub(r'\s+', '%', normalized)  # Spaces become wildcards
        normalized = re.sub(r'%+', '%', normalized)  # Collapse multiple wildcards

        # Try exact match first
        cursor.execute('''
            SELECT DatabaseID, Name, Platform, Overview, Genres, Developer, Publisher,
                   ReleaseDate, ReleaseYear, MaxPlayers, CommunityRating
            FROM Games
            WHERE Platform = ? AND (Name = ? OR CompareName = ?)
            LIMIT 1
        ''', (platform_name, clean_name, clean_name.lower()))

        row = cursor.fetchone()

        # If no exact match, try LIKE search with original name
        if not row:
            search_pattern = f"%{clean_name}%"
            cursor.execute('''
                SELECT DatabaseID, Name, Platform, Overview, Genres, Developer, Publisher,
                       ReleaseDate, ReleaseYear, MaxPlayers, CommunityRating
                FROM Games
                WHERE Platform = ? AND (Name LIKE ? OR CompareName LIKE ?)
                ORDER BY
                    CASE WHEN Name = ? THEN 0
                         WHEN Name LIKE ? THEN 1
                         ELSE 2 END,
                    LENGTH(Name)
                LIMIT 1
            ''', (platform_name, search_pattern, search_pattern.lower(), clean_name, clean_name + "%"))

            row = cursor.fetchone()

        # If still no match, try fuzzy search with normalized name (handles "Zelda - Breath" vs "Zelda: Breath")
        if not row and normalized != clean_name:
            fuzzy_pattern = f"%{normalized}%"
            cursor.execute('''
                SELECT DatabaseID, Name, Platform, Overview, Genres, Developer, Publisher,
                       ReleaseDate, ReleaseYear, MaxPlayers, CommunityRating
                FROM Games
                WHERE Platform = ? AND (Name LIKE ? OR CompareName LIKE ?)
                ORDER BY LENGTH(Name)
                LIMIT 1
            ''', (platform_name, fuzzy_pattern, fuzzy_pattern.lower()))

            row = cursor.fetchone()

        conn.close()

        if row:
            return {
                "database_id": row["DatabaseID"],
                "name": row["Name"],
                "platform": row["Platform"],
                "overview": row["Overview"],
                "genres": row["Genres"],
                "developer": row["Developer"],
                "publisher": row["Publisher"],
                "release_date": row["ReleaseDate"],
                "release_year": row["ReleaseYear"],
                "max_players": row["MaxPlayers"],
                "rating": row["CommunityRating"],
            }

        return None

    except Exception as e:
        print(f"[LaunchBox] Database search error: {e}")
        return None


def get_launchbox_image_url(database_id, media_type, db_path=None):
    """
    Get the CDN URL for a game's image from LaunchBox.

    Args:
        database_id: LaunchBox game database ID
        media_type: Our media type (box2d, logo, screenshot, etc.)
        db_path: Optional path to database

    Returns:
        Image URL string or None
    """
    if db_path is None:
        db_path = get_launchbox_db_path()

    if not db_path or not os.path.exists(db_path):
        return None

    lb_image_types = MEDIA_TO_LAUNCHBOX_IMAGE_TYPE.get(media_type, [])
    if not lb_image_types:
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Build query for multiple image types
        placeholders = ','.join('?' * len(lb_image_types))

        # Get all matching images
        cursor.execute(f'''
            SELECT FileName, Type, Region
            FROM GameImages
            WHERE DatabaseId = ? AND Type IN ({placeholders})
        ''', [database_id] + lb_image_types)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # Sort by region preference and image type preference
        def sort_key(row):
            filename, img_type, region = row

            # Region priority
            try:
                region_priority = LAUNCHBOX_PREFERRED_REGIONS.index(region or "")
            except ValueError:
                region_priority = 999  # Non-preferred region

            # Image type priority (prefer first in our list)
            try:
                type_priority = lb_image_types.index(img_type)
            except ValueError:
                type_priority = 999

            return (type_priority, region_priority)

        rows.sort(key=sort_key)
        best_match = rows[0]

        return LAUNCHBOX_IMAGE_CDN + best_match[0]

    except Exception as e:
        print(f"[LaunchBox] Image lookup error: {e}")
        return None


def get_all_launchbox_images(database_id, db_path=None):
    """
    Get all available image URLs for a game from LaunchBox.

    Args:
        database_id: LaunchBox game database ID
        db_path: Optional path to database

    Returns:
        dict mapping our media types to URLs
    """
    images = {}

    for media_type in MEDIA_TO_LAUNCHBOX_IMAGE_TYPE.keys():
        url = get_launchbox_image_url(database_id, media_type, db_path)
        if url:
            images[media_type] = url

    return images


def convert_launchbox_to_metadata(lb_game):
    """
    Convert LaunchBox game info to our standard metadata format.

    Args:
        lb_game: dict from search_launchbox_game()

    Returns:
        dict in same format as extract_metadata_from_ss()
    """
    if not lb_game:
        return None

    meta = {
        "desc": lb_game.get("overview"),
        "rating": None,
        "releasedate": None,
        "genre": lb_game.get("genres"),
        "players": None,
        "region": None,
        "publisher": lb_game.get("publisher"),
        "developer": lb_game.get("developer"),
    }

    # Convert rating (LaunchBox uses 0-5 scale, we use 0-1)
    if lb_game.get("rating"):
        try:
            meta["rating"] = str(round(float(lb_game["rating"]) / 5.0, 2))
        except (ValueError, TypeError):
            pass

    # Convert release date
    if lb_game.get("release_date"):
        try:
            # LaunchBox format varies, try to parse
            date_str = lb_game["release_date"]
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            # Convert to EmulationStation format (YYYYMMDD)
            parts = date_str.split("-")
            if len(parts) == 3:
                meta["releasedate"] = f"{parts[0]}{parts[1]}{parts[2]}T000000"
        except:
            pass
    elif lb_game.get("release_year"):
        meta["releasedate"] = f"{lb_game['release_year']}0101T000000"

    # Convert players
    if lb_game.get("max_players"):
        meta["players"] = str(lb_game["max_players"])

    return meta


# ---------- EMUMOVIES API FALLBACK ----------

import xml.etree.ElementTree as EmuMoviesET
import time

# EmuMovies API configuration
EMUMOVIES_API_BASE = "https://api.gamesdbase.com/"
EMUMOVIES_API_KEY = os.environ.get("EMUMOVIES_API_KEY", "")

# EmuMovies session cache
_emumovies_session = {
    "token": None,
    "expires": 0,
}

# Map ScreenScraper system IDs to EmuMovies system lookup names
SCREENSCRAPER_TO_EMUMOVIES_SYSTEM = {
    # Nintendo
    "3": "Nintendo_NES",
    "4": "Nintendo_SNES",
    "9": "Nintendo_Game_Boy",
    "10": "Nintendo_Game_Boy_Color",
    "11": "Nintendo_Virtual_Boy",
    "12": "Nintendo_Game_Boy_Advance",
    "13": "Nintendo_GameCube",
    "14": "Nintendo_N64",
    "15": "Nintendo_DS",
    "16": "Nintendo_Wii",
    "17": "Nintendo_3DS",
    "18": "Nintendo_Wii_U",
    "106": "Nintendo_Famicom_Disk_System",
    "225": "Nintendo_Switch",

    # Sega
    "1": "Sega_Genesis",
    "2": "Sega_Master_System",
    "19": "Sega_32X",
    "20": "Sega_CD",
    "21": "Sega_Game_Gear",
    "22": "Sega_Saturn",
    "23": "Sega_Dreamcast",
    "109": "Sega_SG_1000",

    # Sony
    "57": "Sony_Playstation",
    "58": "Sony_Playstation_2",
    "59": "Sony_Playstation_3",
    "61": "Sony_PSP",
    "62": "Sony_Playstation_Vita",

    # Atari
    "26": "Atari_2600",
    "27": "Atari_Jaguar",
    "28": "Atari_Lynx",
    "40": "Atari_5200",
    "41": "Atari_7800",
    "42": "Atari_ST",
    "43": "Atari_8_bit",  # Atari 800

    # NEC
    "31": "NEC_TurboGrafx_16",
    "114": "NEC_TurboGrafx_CD",

    # SNK
    "142": "SNK_Neo_Geo_AES",
    "70": "SNK_Neo_Geo_CD",
    "82": "SNK_Neo_Geo_Pocket_Color",

    # Other
    "29": "3DO",
    "48": "Colecovision",
    "102": "GCE_Vectrex",
    "104": "Magnavox_Odyssey_2",
    "115": "Mattel_Intellivision",
    "66": "Commodore_64",
    "64": "Commodore_Amiga",
    "168": "APF_Imagination_Machine",
}

# Map our media types to EmuMovies media types
MEDIA_TO_EMUMOVIES_TYPE = {
    "box2d": ["Box"],
    "box3d": ["Box_3D"],
    "boxback": ["BoxBack"],
    "boxside": ["Box_Spine"],
    "screenshot": ["Snap"],
    "screenshottitle": ["Title"],
    "logo": ["Logos"],
    "marquee": ["Marquee", "Logos"],
    "fanart": ["Background"],
    "cartridge": ["Cart", "Cart_3D", "Disc"],
    "video": ["Video_MP4_HI_QUAL", "Video_MP4_HD", "Video_MP4"],
}


def emumovies_login(username, password):
    """
    Login to EmuMovies API and get session token.
    Caches the session for 9 minutes.
    """
    global _emumovies_session
    if not EMUMOVIES_API_KEY or not username or not password:
        return None

    # Check if we have a valid cached session
    if _emumovies_session["token"] and time.time() < _emumovies_session["expires"]:
        return _emumovies_session["token"]

    try:
        url = f"{EMUMOVIES_API_BASE}login.aspx?user={username}&api={password}&product={EMUMOVIES_API_KEY}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        # Parse XML response
        root = EmuMoviesET.fromstring(resp.text)
        result = root.find("Result")

        if result is not None and result.get("Success") == "True":
            session_token = result.get("Session")
            # Cache for 9 minutes (tokens expire after 10)
            _emumovies_session["token"] = session_token
            _emumovies_session["expires"] = time.time() + (9 * 60)
            return session_token
        else:
            error_msg = result.get("MSG", "Unknown error") if result is not None else "No response"
            print("[EmuMovies] Login failed.")
            return None

    except Exception as e:
        print("[EmuMovies] Login request failed.")
        return None


def emumovies_search(session_token, game_name, system_lookup, media_type):
    """
    Search EmuMovies for a game's media.

    Args:
        session_token: Valid session token from login
        game_name: Name of the game to search
        system_lookup: EmuMovies system lookup name (e.g., "Nintendo_NES")
        media_type: EmuMovies media type (e.g., "Video_MP4_HI_QUAL")

    Returns:
        URL string or None
    """
    if not session_token:
        return None

    try:
        from urllib.parse import quote
        encoded_name = quote(game_name)

        url = f"{EMUMOVIES_API_BASE}search.aspx?search={encoded_name}&system={system_lookup}&media={media_type}&sessionid={session_token}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        # Parse XML response
        root = EmuMoviesET.fromstring(resp.text)
        result = root.find("Result")

        if result is not None and result.get("Found") == "True":
            return result.get("URL")
        return None

    except Exception as e:
        print("[EmuMovies] Search request failed.")
        return None


def get_emumovies_media_url(cfg, game_name, system_id, media_type):
    """
    Get media URL from EmuMovies for a game.

    Args:
        cfg: Config dict with EmuMovies credentials
        game_name: Name of the game
        system_id: ScreenScraper system ID
        media_type: Our media type (box2d, logo, video, etc.)

    Returns:
        URL string or None
    """
    username = cfg.get("emumovies_user", "").strip()
    password = cfg.get("emumovies_pass", "").strip()

    if not username or not password:
        return None

    # Get EmuMovies system name
    em_system = SCREENSCRAPER_TO_EMUMOVIES_SYSTEM.get(str(system_id))
    if not em_system:
        return None

    # Get EmuMovies media types for our media type
    em_media_types = MEDIA_TO_EMUMOVIES_TYPE.get(media_type, [])
    if not em_media_types:
        return None

    # Login (uses cached session if valid)
    session = emumovies_login(username, password)
    if not session:
        return None

    # Clean game name for search
    clean_name = re.sub(r'\s*\(.*?\)', '', game_name).strip()
    clean_name = re.sub(r'\s*\[.*?\]', '', clean_name).strip()

    # Try each media type until we find one
    for em_media in em_media_types:
        url = emumovies_search(session, clean_name, em_system, em_media)
        if url:
            return url

    return None


def get_all_emumovies_media(cfg, game_name, system_id):
    """
    Get all available media URLs from EmuMovies for a game.

    Args:
        cfg: Config dict with EmuMovies credentials
        game_name: Name of the game
        system_id: ScreenScraper system ID

    Returns:
        dict mapping our media types to URLs
    """
    username = cfg.get("emumovies_user", "").strip()
    password = cfg.get("emumovies_pass", "").strip()

    if not username or not password:
        return {}

    # Get EmuMovies system name
    em_system = SCREENSCRAPER_TO_EMUMOVIES_SYSTEM.get(str(system_id))
    if not em_system:
        return {}

    # Login (uses cached session if valid)
    session = emumovies_login(username, password)
    if not session:
        return {}

    # Clean game name for search
    clean_name = re.sub(r'\s*\(.*?\)', '', game_name).strip()
    clean_name = re.sub(r'\s*\[.*?\]', '', clean_name).strip()

    results = {}
    for media_type, em_media_types in MEDIA_TO_EMUMOVIES_TYPE.items():
        for em_media in em_media_types:
            url = emumovies_search(session, clean_name, em_system, em_media)
            if url:
                results[media_type] = url
                break  # Got this media type, move to next

    return results


# ---------- SCREENSCRAPER API HELPERS ----------

class ScreenScraperError(RuntimeError):
    """Safe, user-facing failure; never includes request URLs or credentials."""


def _screenscraper_params(cfg):
    if not cfg.get("ssid", "").strip() or not cfg.get("sspassword", ""):
        raise ScreenScraperError("Enter your own ScreenScraper username and password in Accounts, then select Validate.")
    return {"ssid": cfg["ssid"].strip(), "sspassword": cfg["sspassword"]}


def _screenscraper_request(endpoint, params, allow_not_found=False):
    try:
        cfg = {key: params[key] for key in ("ssid", "sspassword")}
        if endpoint == "ssuserInfos.php":
            return relay_client().user(cfg)
        if endpoint == "jeuInfos.php":
            fields = {k: v for k, v in params.items() if k not in ("ssid", "sspassword")}
            return relay_client().game(cfg, fields)
        raise ScreenScraperError("Unsupported scraper operation.")
    except RelayClientError as exc:
        raise ScreenScraperError(str(exc)) from None


def fetch_screenscraper_user_info(cfg):
    cfg.pop("_screenscraper_error", None)
    try:
        data = _screenscraper_request("ssuserInfos.php", _screenscraper_params(cfg))
        user = data["response"].get("ssuser")
        if not isinstance(user, dict) or not user.get("id"):
            raise ScreenScraperError("ScreenScraper did not confirm your account. Check your username and password.")
        def number(key, default):
            try:
                return int(user.get(key, default))
            except (TypeError, ValueError):
                return default
        return {"id": user["id"], "nom": cfg["ssid"].strip(),
                "niveau": user.get("niveau", "0"), "contribution": user.get("contribution", "0"),
                "maxthreads": max(1, number("maxthreads", 1)),
                "requeststoday": number("requeststoday", 0),
                "maxrequestsperday": number("maxrequestsperday", 10000),
                "requestsperday": user.get("requestsperday", "0"),
                "maxrequestspermin": user.get("maxrequestspermin", "0"),
                "visites": user.get("visites", "0")}
    except ScreenScraperError as exc:
        cfg["_screenscraper_error"] = str(exc)
        return None


def compute_file_hashes(path, chunk_size=65536):
    """
    Compute CRC32, MD5, SHA1 and file size for ScreenScraper.
    Returns dict: {crc, md5, sha1, romtaille}
    """
    crc32_val = 0
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    total_size = 0

    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            crc32_val = zlib.crc32(chunk, crc32_val)
            md5.update(chunk)
            sha1.update(chunk)

    # CRC32 must be 8-char lowercase hex
    crc_hex = f"{crc32_val & 0xFFFFFFFF:08x}"

    return {
        "crc": crc_hex,
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "romtaille": total_size,
    }


def _parse_jeu_from_json(data):
    """
    Helper to pull the first 'jeu' entry out of ScreenScraper's JSON.
    """
    if not isinstance(data, dict):
        return None
    resp = data.get("response", {})
    jeu_list = resp.get("jeu", [])
    if isinstance(jeu_list, dict):
        return jeu_list
    if isinstance(jeu_list, list) and jeu_list:
        return jeu_list[0]
    return None



def fetch_game_info(cfg, rom_name, system_id, rom_path=None):
    params = _screenscraper_params(cfg)
    params.update(systemeid=str(system_id or "0"), romtype="rom")
    if rom_path and os.path.isfile(rom_path):
        hashed = dict(params, romnom=os.path.basename(rom_path))
        hashed.update(compute_file_hashes(rom_path))
        data = _screenscraper_request("jeuInfos.php", hashed, allow_not_found=True)
        game = _parse_jeu_from_json(data)
        if game:
            return game
    # Preserve the original name first; regions and extensions can help matching.
    original = rom_name or ""
    clean = re.sub(r"\s*\(.*?\)", "", original).strip()
    names = [original, clean]
    if str(system_id) == "84" or clean.startswith("!"):
        names.append(clean.replace("!", "").strip())
    for name in dict.fromkeys(names):
        if not name:
            continue
        data = _screenscraper_request("jeuInfos.php", dict(params, romnom=name), allow_not_found=True)
        game = _parse_jeu_from_json(data)
        if game:
            return game
    return None


def pick_media_url(medias, desired_types, preferred_regions=None):
    """
    Pick media URL with region preference support.

    Args:
        medias: Media data from ScreenScraper API
        desired_types: List of media types to look for (e.g., ["wheel", "logo"])
        preferred_regions: Optional list of region codes in priority order.
                          Default: ["us", "wor", "eu", "ss"] - prioritizes English regions
                          Use None to disable region filtering (first match wins)
    """
    if not medias:
        return None

    if isinstance(medias, list):
        media_entries = medias
    elif isinstance(medias, dict):
        media_entries = medias.get("media", [])
        if isinstance(media_entries, dict):
            media_entries = [media_entries]
    else:
        return None

    if not isinstance(media_entries, list):
        return None

    # Default region preference: US, World, Europe, ScreenScraper default
    # This avoids Japanese (jp) and other non-English logos
    if preferred_regions is None:
        preferred_regions = ["us", "wor", "eu", "ss"]

    for d_type in desired_types:
        # First pass: look for matches with preferred regions (in priority order)
        for region in preferred_regions:
            for m in media_entries:
                if not isinstance(m, dict):
                    continue
                if m.get("type") == d_type:
                    media_region = m.get("region", "").lower()
                    if media_region == region:
                        return m.get("url2") or m.get("url") or m.get("original")

        # Second pass: if no preferred region found, take any non-Japanese match
        for m in media_entries:
            if not isinstance(m, dict):
                continue
            if m.get("type") == d_type:
                media_region = m.get("region", "").lower()
                # Skip Japanese region to avoid Japanese text on logos
                if media_region not in ("jp", "ja"):
                    return m.get("url2") or m.get("url") or m.get("original")

        # Final fallback: take whatever is available (even Japanese)
        for m in media_entries:
            if not isinstance(m, dict):
                continue
            if m.get("type") == d_type:
                return m.get("url2") or m.get("url") or m.get("original")

    return None


def download_binary(url, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        raise ScreenScraperError("Media download failed. Check the service and try again.") from None
    with open(output_path, "wb") as f:
        f.write(resp.content)


# ---------- METADATA HELPERS FOR GAMELIST ----------

def clean_display_name(rom_name: str) -> str:
    name = rom_name
    # Remove all (Year), (Publisher), (Region), (Disc X), etc.
    name = re.sub(r'\s*\([^)]*\)', '', name)
    # Remove all [!], [a], [b1], [BIOS], etc.
    name = re.sub(r'\s*\[[^\]]*\]', '', name)
    # Remove version strings like v1.002, v2, v1.0a
    name = re.sub(r'\s+v\d+[\d.]*[a-zA-Z]?(?=\s|$)', '', name)
    # Collapse multiple spaces and strip
    name = re.sub(r'\s+', ' ', name).strip()
    return name
    
    
def make_safe_filename(name: str) -> str:
    """
    Turn a ScreenScraper title into a Windows-safe filename.
    """
    # Strip leading/trailing spaces
    name = name.strip()

    # Remove characters Windows hates:  \ / : * ? " < > |
    name = re.sub(r'[<>:"/\\|?*]', '', name)

    # Replace newlines with spaces
    name = name.replace("\n", " ").replace("\r", " ")

    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)

    # Optional: limit length a bit so things don't get crazy
    if len(name) > 120:
        name = name[:120].rstrip()

    return name


def pick_lang_entry(block: dict, keys=("en", "us", "wor", "eu")):
    """
    ScreenScraper uses language/region codes as keys.
    Each sub-entry is usually a dict with 'text' or 'texte'.
    """
    if not isinstance(block, dict):
        return None
    for lang in keys:
        val = block.get(lang)
        if isinstance(val, dict):
            txt = val.get("text") or val.get("nom") or val.get("texte")
            if txt:
                return txt
    # fall back to first dict
    for val in block.values():
        if isinstance(val, dict):
            txt = val.get("text") or val.get("nom") or val.get("texte")
            if txt:
                return txt
    return None


def extract_metadata_from_ss(game_info: dict):
    """Return dict with name/desc/rating/releasedate/publisher/developer/genre/players/region."""
    meta = {
        "name": None,
        "desc": None,
        "rating": None,
        "releasedate": None,
        "genre": None,
        "players": None,
        "region": None,
        "publisher": None,
        "developer": None,
    }

    if not game_info:
        return meta

    # ---------- helpers ----------

    def find_long_string(obj, min_len=80):
        """
        Walk dicts/lists and return the first string >= min_len chars.
        """
        if isinstance(obj, str):
            s = obj.strip()
            if len(s) >= min_len:
                return s
        elif isinstance(obj, dict):
            for v in obj.values():
                s = find_long_string(v, min_len)
                if s:
                    return s
        elif isinstance(obj, list):
            for v in obj:
                s = find_long_string(v, min_len)
                if s:
                    return s
        return None

    def pick_lang_entry_any(obj, keys=("us", "en", "wor", "eu", "fr", "jp")):
        """
        More aggressive picker that understands:
        - dict of language codes  -> { "en": { "text": ... }, ... }
        - list of those dicts     -> [ { "en": {...} }, { "fr": {...} } ]
        - list/dict with 'langue' + 'text' (ScreenScraper style)
        """
        # 1) dict-of-langs or single dict with 'langue'
        if isinstance(obj, dict):
            # Try classic dict-of-langs format first
            txt = pick_lang_entry(obj, keys=keys)
            if txt:
                return txt

            # Then try "langue" + "text"
            lang = obj.get("langue")
            val = obj.get("text") or obj.get("nom") or obj.get("texte")
            if val:
                if (not lang) or (lang in keys):
                    return val

        # 2) list of dicts (very common in synopsis/genres/dates)
        if isinstance(obj, list):
            # Prefer matching by 'langue' field if present
            for lang in keys:
                for item in obj:
                    if isinstance(item, dict):
                        if item.get("langue") == lang:
                            val = item.get("text") or item.get("nom") or item.get("texte")
                            if val:
                                return val

            # Fallback: run pick_lang_entry on each dict
            for item in obj:
                if isinstance(item, dict):
                    txt = pick_lang_entry(item, keys=keys)
                    if txt:
                        return txt

            # Last resort: first dict's 'text' / 'nom' / 'texte'
            for item in obj:
                if isinstance(item, dict):
                    val = item.get("text") or item.get("nom") or item.get("texte")
                    if val:
                        return val

        return None

    def is_human_name(s: str) -> bool:
        """
        Return True if string looks like a real name/word (has any letter),
        not just digits like '48621'.
        """
        if not isinstance(s, str):
            return False
        s = s.strip()
        if not s:
            return False
        # reject pure digits
        if s.isdigit():
            return False
        # accept if there's at least one letter
        return any(ch.isalpha() for ch in s)

    # -------- GAME NAME --------
    noms = game_info.get("noms")
    if noms:
        txt_name = pick_lang_entry_any(noms, keys=("us", "wor", "en", "eu", "fr", "jp"))
        if txt_name and isinstance(txt_name, str) and txt_name.strip():
            meta["name"] = txt_name.strip()

    # -------- DESCRIPTION / SYNOPSIS --------
    synopsis = game_info.get("synopsis")

    # 1) Try language-aware helper first
    if synopsis:
        meta["desc"] = pick_lang_entry_any(synopsis, keys=("us", "en", "wor", "eu", "fr", "jp"))

    # 2) If still nothing, look for long text inside synopsis
    if not meta["desc"] and synopsis:
        s = find_long_string(synopsis, min_len=60)
        if s:
            meta["desc"] = s

    # 3) As a last resort, scan the *whole* game_info for a long string
    if not meta["desc"]:
        s = find_long_string(game_info, min_len=60)
        if s:
            meta["desc"] = s

    # -------- RATING --------
    note = game_info.get("note")
    txt = None
    if isinstance(note, dict):
        txt = note.get("text") or note.get("note")
    elif isinstance(note, (str, int, float)):
        txt = str(note)
    if txt:
        try:
            val = float(txt)
            meta["rating"] = str(round(val / 20.0, 2))  # EmulationStation expects 0..1
        except Exception:
            pass

    # -------- RELEASE DATE --------
    dates = game_info.get("dates")
    date_text = None
    if dates:
        date_text = pick_lang_entry_any(dates, keys=("us", "eu", "wor", "jp", "en"))
    if date_text:
        clean = re.sub(r"[^\d]", "", date_text)
        if len(clean) == 8:
            meta["releasedate"] = clean + "T000000"

    # -------- PUBLISHER --------
    editeur = game_info.get("editeur")
    if editeur:
        txt_pub = pick_lang_entry_any(editeur, keys=("us", "en", "wor", "eu", "fr", "jp"))
        if txt_pub and is_human_name(txt_pub):
            meta["publisher"] = txt_pub

    # -------- DEVELOPER --------
    developpeur = game_info.get("developpeur")
    if developpeur:
        txt_dev = pick_lang_entry_any(developpeur, keys=("us", "en", "wor", "eu", "fr", "jp"))
        if txt_dev and is_human_name(txt_dev):
            meta["developer"] = txt_dev

    # -------- GENRE --------
    genres = game_info.get("genres")
    if genres:
        txt_genre = pick_lang_entry_any(genres, keys=("us", "en", "wor", "eu", "fr", "jp"))
        if txt_genre and is_human_name(txt_genre):
            meta["genre"] = txt_genre

    # -------- PLAYERS --------
    joueurs = game_info.get("joueurs")
    if isinstance(joueurs, dict):
        txt = joueurs.get("text") or joueurs.get("min") or joueurs.get("max")
        if not txt:
            txt = pick_lang_entry_any(joueurs, keys=("us", "en", "wor", "eu", "fr", "jp"))
        if txt:
            meta["players"] = str(txt)
    elif isinstance(joueurs, list):
        for j in joueurs:
            if isinstance(j, dict):
                txt = j.get("text") or j.get("min") or j.get("max")
                if txt:
                    meta["players"] = str(txt)
                    break

    # -------- REGION --------
    regions = game_info.get("regions")
    if isinstance(regions, dict):
        for key in regions.keys():
            meta["region"] = key.lower()
            break
    elif isinstance(regions, list):
        for r in regions:
            if isinstance(r, dict):
                for key in r.keys():
                    if isinstance(key, str) and key:
                        meta["region"] = key.lower()
                        break
                if meta["region"]:
                    break

    return meta


# ---------- ROM DISCOVERY (FILES + FOLDER-BASED ROMS) ----------

def discover_roms(rom_folder: str):
    """
    Return list of (logical_name, full_path_to_bootfile_or_rom).

    - For flat ROMs: logical_name = filename without extension, path = file.
    - For folder ROMs (PS3, 360, Wii U, etc.): logical_name = top folder, path = boot file inside it.
    """
    allowed_ext = {
        # Archives / general
        ".zip", ".7z",

        # Common ROM / disc formats
        ".nes", ".smc", ".sfc", ".ciso",
        ".bin", ".rom", ".iso", ".cue", ".chd", ".img",
        ".gdi",        # Dreamcast GD-ROMs
        ".cdi",        # DiscJuggler images (common Dreamcast rip)
        ".chd",        # Compressed disc images (if you use them)

        ".gba", ".gbc", ".gb", ".mgw", ".min", ".psvita", ".vpk",
        ".n64", ".z64", ".v64", "ndd", ".v32", ".vb", ".vboy",
        ".md", ".gen", ".sms", ".gg", ".wasm", ".ws",
        ".wav", ".cas", ".dmk", ".jvc", ".os9", ".vdk",
        ".d88", ".u88", ".a0", ".b0", ".wsc", ".mds",
        ".crt", ".b64", ".d81", ".t64", ".ccc",
        ".nso", ".nro", ".nca", ".xci", ".nsp", ".kip",
        ".adf", ".uae", ".ipf", ".dms", ".adz", ".lha", ".rp9",
        ".uae", ".hdf",
        
        # Portables
        ".ngage", ".symbian", ".id", ".vec", ".gam", ".bstone",
        
        # OpenBORE
        ".pak", ".tzx", ".tap", ".z80", ".rzx", ".scl", ".trd", ".p",
        
        # Capcom
        ".fba", ".sv", ".rpk", ".z80", ".scl", ".trd", ".cpr",
        
        # Arduboy
        ".hex", ".libretro", ".easyrpg", ".lbd", ".squashfs",
        ".tgc", ".cpc", ".sna", ".cdt", ".voc", 
        
        # Sharp
        ".2hd", ".88d", ".d88", ".dim", ".dup", ".hdf", ".hdm", ".xdf",
        
        # Atari
        ".lnx", ".st", ".fig", ".bs", ".tic", ".msa", ".stx", ".ipf ", ".gemdos",
        
        # Windows
        ".exe", ".bat", ".cmd", ".lnk", ".game", ".url", ".pc", ".win",
        ".windows", ".wine", ".wsquashfs", ".p8", ".ps4",
        
        # Nintendo optical
        ".xci", ".nsp", ".wbfs", ".gcm", ".cso",
        ".rvz",          # GameCube (Dolphin)
        ".3ds", ".cia",  # Nintendo 3DS
        ".ngp", ".ngc", ".wad", ".wia", ".json",

        # Apple II disks
        ".dsk", ".cas", ".fd", ".sap", ".k7", ".m7", ".m5", ".qd",

        # Wii U formats
        ".wud", ".wux", ".wua",  # full images
        ".rpx",                  # extracted (Cemu style in code/ folder)
        
        # ... existing extensions ...
        ".adf", ".apd", ".jfd", ".hfe", ".arc", ".bas"
        ".ssd", ".prg", ".col", ".d64", ".m3u",
        ".t77", ".mfi", ".dfi", ".hfe", ".mfm", ".td0", ".imd",
        ".d77", ".d88", ".1dd", ".cqm", ".cqi", 
        ".d98", ".98d", ".fdi", ".fdd", ".2hd", ".tfd", ".d88", 
        ".88d", ".hdm", ".xdf", ".dup", ".hdi", ".thd", ".nhd", ".hdd",
        ".hdn", ".pce", ".wad", ".ccd", ".toc",
        
        # MSX
        ".ri", ".mx1", ".mx2", ".ogv", ".sg", ".sc",
        ".sub", 
}

    ARDUBOY_EXTS = {".hex"}

    roms = []

    if not os.path.isdir(rom_folder):
        return roms

    entries = os.listdir(rom_folder)
    for entry in entries:
        full = os.path.join(rom_folder, entry)

        # --- plain files directly in the folder ---
        if os.path.isfile(full):
            ext = os.path.splitext(entry)[1].lower()
            if ext in allowed_ext:
                logical = os.path.splitext(entry)[0]
                roms.append((logical, full))

        # --- folder-based games (PS3, 360, Wii U, Dreamcast, etc.) ---
        elif os.path.isdir(full):
            boot_path = None
            for root, dirs, files in os.walk(full):
                for fname in files:
                    upper = fname.upper()
                    lower = fname.lower()
                    ext = os.path.splitext(fname)[1].lower()

                    # Check for boot files OR any allowed ROM extension
                    if upper in BOOT_FILENAMES or lower.endswith(".rpx") or ext in allowed_ext:
                        boot_path = os.path.join(root, fname)
                        break
                if boot_path:
                    break

            if boot_path:
                # use the top-level folder name as the logical game name
                roms.append((entry, boot_path))

    # De-duplicate by full_path (in case something was picked twice)
    seen = set()
    unique_roms = []
    for logical, full in roms:
        if full not in seen:
            seen.add(full)
            unique_roms.append((logical, full))

    return unique_roms


def guess_query_name(logical_name: str, full_path: str, system_id: str) -> str:
    base = os.path.basename(full_path)
    upper_base = base.upper()

    # Special handling for Acorn Archimedes (System 84)
    if str(system_id) == "84":
        # Remove the extension but keep the '!' if it exists
        name_no_ext = os.path.splitext(base)[0]
        # ScreenScraper often indexes these without the '!' in the searchable title
        return name_no_ext.replace("!", "").strip()

    # Your existing boot-file logic for PS3/Xbox 360/etc.
    if upper_base in BOOT_FILENAMES:
        cur = os.path.dirname(full_path)
        game_name = None
        generic_names = {"usrdir", "ps3_game", "system", "bin", "binaries"}

        while True:
            parent, folder = os.path.split(cur)
            if not folder: break
            if folder.lower() not in generic_names:
                game_name = os.path.splitext(folder)[0]
                break
            cur = parent
        return game_name or logical_name or base

    return logical_name or base


# ---------- GAME LIST (RETROBAT-STYLE) GENERATOR ----------

def generate_gamelist_xml(cfg, rom_folder: str, output_folder: str,
                          system_id: str, system_name: str, patterns: dict,
                          log_queue=None, metadata_cache=None):
    """
    Build / overwrite a RetroBat-style gamelist.xml using media filenames
    AND metadata that was ALREADY fetched during scraping.

    Uses discover_roms() so we support:
      - flat ROM files
      - ROMs in subfolders (PS3, Xbox 360, etc.)

    For folder-based / disc systems we write <path> to the TOP-LEVEL GAME FOLDER,
    not the inner boot file (EBOOT.BIN / default.xex / default.xbe).
    """

    rom_entries = discover_roms(rom_folder)

    if not rom_entries:
        if log_queue:
            log_queue.put("[GAMELIST] No ROM files/folders found. Nothing to write.\n")
        return

    # Root + provider
    root = ET.Element("gameList")

    provider = ET.SubElement(root, "provider")
    ET.SubElement(provider, "system").text = (system_name or "").lower()
    ET.SubElement(provider, "software").text = "ScreenScraper Artwork Scraper"
    ET.SubElement(provider, "web").text = "https://www.screenscraper.fr"

    tag_map = {
        "image": "box2d",            # main IMAGE field = 2D box (-thumb)
        "thumbnail": "box2d",
        "boxart": "box2d",
        "screenshot": "screenshot",  # -image
        "titleshot": "screenshottitle",
        "boxback": "boxback",
        "fanart": "fanart",
        "cartridge": "cartridge",
        "video": "video",
        "logo": "logo",
        "marquee": "marquee",
    }

    for (logical_name, full_path) in rom_entries:
        # relative path from rom_folder
        rel = os.path.relpath(full_path, rom_folder).replace("\\", "/")

        # If it lives in a subfolder (disc-style), use the top-level folder as the ROM path
        if "/" in rel:
            top_folder = rel.split("/")[0]
            rom_path_text = f"./{top_folder}"
            rom_name = top_folder
        else:
            top_folder = None
            rom_path_text = f"./{rel}"
            rom_name, _ext = os.path.splitext(rel)

        # ---- metadata from CACHE ONLY (no new web calls) ----
        meta = {}
        if metadata_cache:
            candidate_keys = [
                rel,
                os.path.basename(full_path),
                rom_name,
            ]
            if top_folder:
                candidate_keys.append(top_folder)

            for k in candidate_keys:
                if k in metadata_cache:
                    meta = metadata_cache[k]
                    break

        # Use ScreenScraper's clean title if available, else strip extras from filename
        display_name = meta.get("name") or clean_display_name(rom_name)

        game_el = ET.SubElement(root, "game")
        ET.SubElement(game_el, "path").text = rom_path_text
        ET.SubElement(game_el, "name").text = display_name

        if meta.get("desc"):
            ET.SubElement(game_el, "desc").text = meta["desc"]
        if meta.get("rating"):
            ET.SubElement(game_el, "rating").text = meta["rating"]
        if meta.get("releasedate"):
            ET.SubElement(game_el, "releasedate").text = meta["releasedate"]
        if meta.get("publisher"):
            ET.SubElement(game_el, "publisher").text = meta["publisher"]
        if meta.get("developer"):
            ET.SubElement(game_el, "developer").text = meta["developer"]
        if meta.get("genre"):
            ET.SubElement(game_el, "genre").text = meta["genre"]
        if meta.get("players"):
            ET.SubElement(game_el, "players").text = meta["players"]

        # language / region
        ET.SubElement(game_el, "lang").text = "en"
        if meta.get("region"):
            ET.SubElement(game_el, "region").text = meta["region"]

        # ---- media paths from patterns ----
        vars_for_pattern = {
            "rom_name": rom_name,
            "title": display_name,
            "system": system_name or "",
            "GAME": rom_name,  # Alias for {GAME} placeholder
            "SYSTEM": system_name or "",  # Alias for {SYSTEM} placeholder
        }

        for tag, key in tag_map.items():
            pattern = patterns.get(key, "")
            if not pattern:
                continue

            try:
                rel_media = pattern.format(**vars_for_pattern)
            except KeyError:
                continue

            abs_media = get_media_target_path(output_folder, rel_media)
            if not os.path.exists(abs_media):
                continue

            rel_from_rom = "./" + os.path.relpath(abs_media, rom_folder).replace("\\", "/")
            ET.SubElement(game_el, tag).text = rel_from_rom

    # Safe write: temp file + replace
    out_path = os.path.join(rom_folder, "gamelist.xml")
    tmp_path = out_path + ".tmp"

    tree = ET.ElementTree(root)
    tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
    os.replace(tmp_path, out_path)

    if log_queue:
        log_queue.put(f"[GAMELIST] written to {out_path}\n")


# ---------- SCRAPER WORKER ----------

# ---------- SCRAPER WORKER ----------

def scrape_worker(cfg, rom_folder, output_folder, system_id, system_name,
                  preset_name, patterns, log_queue, progress_queue, stop_flag,
                  max_threads, metadata_cache=None,
                  enabled_media_keys=None, stats=None, stats_lock=None,
                  single_rom=None):
    """
    Main scraping worker.

    Supports:
      - ROMs directly in rom_folder
      - ROMs inside subfolders (disc-based systems, etc.)
    """

    # Discover ROMs (flat + subfolders)
    rom_entries = discover_roms(rom_folder)

    # If we're in "Test 1 ROM" mode, restrict to that one (by logical name or basename)
    if single_rom:
        target = single_rom.lower()
        rom_entries = [
            (logical, full)
            for (logical, full) in rom_entries
            if logical.lower() == target or os.path.basename(full).lower() == target
        ]

    total = len(rom_entries)
    if stats is not None and stats_lock is not None:
        with stats_lock:
            stats["total_roms"] = total
            stats["processed"] = 0
            stats["downloaded"] = 0
            stats["skipped"] = 0
            stats["no_media"] = 0
            stats["errors"] = 0

    if total == 0:
        log_queue.put("No ROM files found in folder.\n")
        progress_queue.put(("done", 0, 0))
        return

    if single_rom:
        log_queue.put(f"Found 1 ROM to process (test mode): {single_rom}\n")
    else:
        log_queue.put(f"Found {total} ROM(s) to process.\n")
    log_queue.put(f"Using {max_threads} thread(s).\n")

    media_mapping = {
        "box2d": ["box-2D", "box"],
        "box3d": ["box-3D"],
        "boxback": ["box-2D-back", "boxback"],
        "boxside": ["box-2D-side", "boxside"],
        "screenshot": ["screen", "screenshot", "screen-normalized", "ingame", "ss"],
        "screenshottitle": ["sstitle", "screenshottitle", "titleshot"],
        "logo": ["wheel", "logo"],
        "marquee": ["marquee"],
        "fanart": ["fanart", "background"],
        "cartridge": ["support-cartridge", "cartridge"],
        "mix": ["mix", "support"],
        "video": ["video-normalized", "video", "video-1080p", "video-720p", "video-origin"],
        "manual": ["manuel"],
    }

    if enabled_media_keys is None:
        enabled_media_keys = list(media_mapping.keys())
    enabled_media = set(enabled_media_keys)
    # --- FORCE ENABLE screenshottitle (safety fix) ---
    enabled_media.add("screenshottitle")

    completed = {"value": 0}
    counter_lock = threading.Lock()
    meta_lock = threading.Lock()

    def stats_inc(key, amount=1):
        if stats is not None and stats_lock is not None:
            with stats_lock:
                stats[key] = stats.get(key, 0) + amount
                
        

    def process_one(idx, logical_name, full_path):
        github_media = None

        # If stop requested before we even start this ROM, bail
        if stop_flag["stop"]:
            return

        rom_basename = os.path.basename(full_path)
        rom_name = logical_name or os.path.splitext(rom_basename)[0]

        prefix = "[TEST]" if single_rom else f"[{idx}/{total}]"

        query_name = guess_query_name(logical_name, full_path, system_id)
        log_queue.put(f"{prefix} {rom_basename} -> querying ScreenScraper as '{query_name}'...\n")

        # ---------------- ScreenScraper lookup ----------------
        try:
            if stop_flag["stop"]:
                return
            game_info = fetch_game_info(cfg, query_name, system_id, full_path)
        except ScreenScraperError as e:
            log_queue.put(f"  ERROR: {e}\n")
            stats_inc("errors")
            stats_inc("processed")
            return
        except Exception:
            log_queue.put("  ERROR: Failed to fetch game information.\n")
            stats_inc("errors")
            stats_inc("processed")
            return

        # Prepare LaunchBox fallback data (used for missing media even if ScreenScraper found the game)
        launchbox_fallback = False
        launchbox_game = None
        launchbox_images = {}

        # Try to find game in LaunchBox (for fallback on missing media)
        lb_platform = SCREENSCRAPER_TO_LAUNCHBOX_PLATFORM.get(str(system_id))
        if lb_platform:
            try:
                launchbox_game = search_launchbox_game(query_name, lb_platform)
                if launchbox_game:
                    launchbox_images = get_all_launchbox_images(launchbox_game["database_id"])
            except Exception as e:
                pass  # Silent fail for LaunchBox lookup

        # If no game info found in ScreenScraper, use LaunchBox as primary
        if not game_info:
            log_queue.put("  Not found in ScreenScraper, trying LaunchBox...\n")

            if launchbox_game:
                launchbox_fallback = True
                log_queue.put(f"  Found in LaunchBox: {launchbox_game['name']}\n")
            else:
                log_queue.put("  Not found in any database.\n")
                stats_inc("no_media")
                stats_inc("processed")
                return

        # ---------------- Extract metadata ----------------
        try:
            if launchbox_fallback:
                meta = convert_launchbox_to_metadata(launchbox_game)
            else:
                meta = extract_metadata_from_ss(game_info)

            if metadata_cache is not None and meta:
                with meta_lock:
                    rel_key = os.path.relpath(full_path, rom_folder).replace("\\", "/")
                    metadata_cache[rel_key] = meta
                    metadata_cache[rom_name] = meta
                    metadata_cache[rom_basename] = meta
        except Exception as e:
            log_queue.put(f"  ERROR extracting metadata: {e}\n")
            stats_inc("errors")
            stats_inc("processed")
            return

        if stop_flag["stop"]:
            return

        # ---------------- Media download loop ----------------
        medias = game_info.get("medias", {}) if game_info else {}
        title = clean_display_name(rom_name)

        vars_for_pattern = {
            "rom_name": rom_name,
            "title": title,
            "system": system_name or "",
            "GAME": rom_name,
            "SYSTEM": system_name or "",
        }

        any_media_found = False

        for media_key, desired_types in media_mapping.items():

            # ScreenScraper actual key
            ss_key = "screenshottitle" if media_key == "screentitleshot" else media_key

            if media_key not in enabled_media:
                log_queue.put(f"  {media_key}: disabled by toggle, skipping.\n")
                continue

            pattern = patterns.get(media_key)
            if not pattern:
                continue

            try:
                rel_path = pattern.format(**vars_for_pattern)
            except Exception as e:
                log_queue.put(f"  Pattern error for {media_key}: {e}\n")
                continue

            out_path = get_media_target_path(output_folder, rel_path)

            if os.path.exists(out_path):
                log_queue.put(f"  {media_key}: exists, skipping\n")
                stats_inc("skipped")
                any_media_found = True
                continue

            media_url = pick_media_url(
                medias,
                SCREEN_SCRAPER_MEDIA_MAP.get(media_key, [])
            )

            # If ScreenScraper doesn't have the media, try LaunchBox
            media_source = "ScreenScraper"
            if not media_url and launchbox_images:
                media_url = launchbox_images.get(media_key)
                if media_url:
                    media_source = "LaunchBox"

            # If still no media, try EmuMovies (especially good for videos)
            if not media_url:
                em_url = get_emumovies_media_url(cfg, query_name, system_id, media_key)
                if em_url:
                    media_url = em_url
                    media_source = "EmuMovies"

            if not media_url:
                log_queue.put(f"  {media_key}: no media found.\n")
                continue

            try:
                log_queue.put(f"  {media_key}: downloading from {media_source}\n")
                download_binary(media_url, out_path)
                stats_inc("downloaded")
                any_media_found = True
            except Exception as e:
                log_queue.put(f"  {media_key}: ERROR downloading: {e}\n")
                stats_inc("errors")

        if not any_media_found:
            stats_inc("no_media")

        stats_inc("processed")

        # ---------- SINGLE-THREAD MODE ----------
    if max_threads <= 1:
        idx = 0
        for logical_name, full_path in rom_entries:
            if stop_flag["stop"]:
                log_queue.put("Scraping interrupted by user (single-thread mode).\n")
                break

            idx += 1
            process_one(idx, logical_name, full_path)

            with counter_lock:
                completed["value"] += 1
                done = completed["value"]
            progress_queue.put(("progress", done, total))

        # Always send 'done' so UI unlocks, even if stopped early
        progress_queue.put(("done", completed["value"], total))
        return

    # ---------- MULTI-THREAD MODE ----------
    task_queue = queue.Queue()
    for idx, (logical_name, full_path) in enumerate(rom_entries, start=1):
        task_queue.put((idx, logical_name, full_path))

    def worker():
        while True:
            if stop_flag["stop"]:
                break
            try:
                idx, logical_name, full_path = task_queue.get_nowait()
            except queue.Empty:
                break
            if stop_flag["stop"]:
                break

            process_one(idx, logical_name, full_path)

            with counter_lock:
                completed["value"] += 1
                done = completed["value"]
            progress_queue.put(("progress", done, total))

    threads = []
    for _ in range(max_threads):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    if stop_flag["stop"]:
        log_queue.put("Scraping interrupted by user (multi-thread mode).\n")

    # Always send 'done' so the GUI re-enables Start and tries gamelist if enabled
    progress_queue.put(("done", completed["value"], total))

# ---------- GUI CLASS ----------

# Retain the original source entry point for existing users.
if __name__ == "__main__":
    import runpy
    runpy.run_path(os.path.join(os.path.dirname(__file__), "UltimateScraperStudio.py"), run_name="__main__")
