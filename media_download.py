"""Stream media safely to disk, with bounded retries for temporary failures."""
from pathlib import Path
import os
import tempfile
import time
from urllib.parse import urlsplit
import requests


class MediaDownloadError(RuntimeError):
    pass


def download_media(url, output_path, on_retry=None):
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    attempts = 4
    status = None
    for attempt in range(attempts):
        temporary = None
        wait = min(8, 2 ** attempt)
        try:
            is_relay = urlsplit(url).path.startswith('/v1/media/')
            with requests.get(url, timeout=(10, 90), stream=True,
                              allow_redirects=not is_relay) as reply:
                status = reply.status_code
                if status in (429, 500, 502, 503, 504):
                    retry_after = reply.headers.get('Retry-After', '')
                    if retry_after.isdigit():
                        wait = max(1, min(20, int(retry_after)))
                elif status != 200:
                    raise MediaDownloadError(f'Media is unavailable (HTTP {status}). Try this ROM again later.')
                else:
                    fd, name = tempfile.mkstemp(prefix='.scraper-', suffix='.part', dir=destination.parent)
                    temporary = Path(name)
                    received = 0
                    with os.fdopen(fd, 'wb') as handle:
                        for chunk in reply.iter_content(65536):
                            if not chunk:
                                continue
                            received += len(chunk)
                            if received > 512 * 1024 * 1024:
                                raise MediaDownloadError('This media file exceeds the download size limit.')
                            handle.write(chunk)
                    length = reply.headers.get('Content-Length', '')
                    complete = not (length.isdigit() and not reply.headers.get('Content-Encoding') and received != int(length))
                    if received and complete:
                        os.replace(temporary, destination)
                        return
                    # An empty or incomplete transfer must never become a finished file.
                    status = None
        except requests.RequestException:
            status = None
        except OSError:
            raise MediaDownloadError('Could not save the media. Check free disk space and folder permissions.') from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        if attempt + 1 < attempts:
            if on_retry:
                on_retry(attempt + 1, wait)
            time.sleep(wait)
    detail = f' (HTTP {status})' if status else ''
    raise MediaDownloadError(f'Media download did not complete after {attempts} attempts{detail}. Please retry later.')
