"""Build the Windows app without committing application credentials."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import argparse

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(ROOT / 'release'))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='scraper-build-') as folder:
        private = Path(folder)
        spec = f'''
from pathlib import Path
import PySide6
from PyInstaller.utils.hooks import collect_submodules
root = Path({str(ROOT)!r})
a = Analysis([str(root / 'UltimateScraperStudio.py')],
    pathex=[{str(private)!r}, str(root)],
    datas=[(str(root / 'UltimateScraperProv2.0.py'), '.'),
           (str(root / 'console_logos'), 'console_logos'),
           (str(root / 'Gamersicon.png'), '.'),
           (str(root / 'Gamersicon-HD.png'), '.'),
           (str(root / 'studio_logo_hd.ico'), '.'),
           (str(root / 'app_icon.ico'), '.')],
    hiddenimports=['relay_client', 'requests', 'xml.etree.ElementTree',
                   'sqlite3', 'tempfile', 'zlib', 'hashlib', 'ctypes', 'winsound']
                  + collect_submodules('tkinter') + collect_submodules('PIL'),
    excludes=[], noarchive=False)
runtime = list(Path(PySide6.__file__).parent.glob('*140*.dll'))
runtime_map = {{f.name.lower(): str(f) for f in runtime}}
a.binaries = [(dest, runtime_map.get(dest.replace('\\\\', '/').split('/')[-1].lower(), src), kind)
              for dest, src, kind in a.binaries]
existing = {{dest.lower() for dest, _, _ in a.binaries}}
a.binaries += [(f.name, str(f), 'BINARY') for f in runtime if f.name.lower() not in existing]
# Qt uses Windows' ICU API. An unrelated ICU found on the build machine's
# PATH (for example Poppler's library) has incompatible exports under this name.
# Leave the Windows system library to the Windows loader.
a.binaries = [(dest, src, kind) for dest, src, kind in a.binaries
              if dest.replace('\\\\', '/').split('/')[-1].lower() not in ('icuuc.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='Ultimate-Scraper-Pro-Studio', console=False,
          debug=False, strip=False, upx=False,
          icon=str(root / 'studio_logo_hd.ico'))
'''
        spec_path = private / 'PublicStudio.spec'
        spec_path.write_text(spec, encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                        '--distpath', str(Path(args.output).resolve()),
                        '--workpath', str(ROOT / 'build'), str(spec_path)], check=True)


if __name__ == '__main__':
    main()
