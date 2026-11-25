from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import requests
import media_download


class DownloadReply:
    def __init__(self, status=200, chunks=None, headers=None):
        self.status_code = status
        self.headers = headers or {}
        self.chunks = chunks if chunks is not None else [b'complete']
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
    def iter_content(self, size):
        for item in self.chunks:
            if isinstance(item, Exception):
                raise item
            yield item


class MediaDownloadTests(unittest.TestCase):
    def test_busy_and_rate_limit_are_retried_and_closed(self):
        replies = [DownloadReply(503, headers={'Retry-After': '2'}), DownloadReply(429), DownloadReply()]
        with tempfile.TemporaryDirectory() as tmp, patch.object(media_download.requests, 'get', side_effect=replies), patch.object(media_download.time, 'sleep') as sleep:
            path = Path(tmp) / 'art.png'
            media_download.download_media('https://relay.example/v1/media/token', path)
            self.assertEqual(path.read_bytes(), b'complete')
            self.assertEqual(sleep.call_count, 2)
            self.assertTrue(all(reply.closed for reply in replies))

    def test_interrupted_transfer_retries_without_leaving_partial_file(self):
        interrupted = DownloadReply(chunks=[b'incomplete', requests.ConnectionError('credential-bearing URL')])
        with tempfile.TemporaryDirectory() as tmp, patch.object(media_download.requests, 'get', side_effect=[interrupted, DownloadReply()]), patch.object(media_download.time, 'sleep'):
            path = Path(tmp) / 'manual.pdf'
            media_download.download_media('https://relay.example/v1/media/token', path)
            self.assertEqual(path.read_bytes(), b'complete')
            self.assertEqual(list(Path(tmp).glob('*.part')), [])

    def test_failed_transfers_preserve_existing_file_and_hide_request_details(self):
        replies = [DownloadReply(chunks=[b'bad', requests.ConnectionError('SECRET')]) for _ in range(4)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(media_download.requests, 'get', side_effect=replies), patch.object(media_download.time, 'sleep'):
            path = Path(tmp) / 'art.png'; path.write_bytes(b'previous good file')
            with self.assertRaises(media_download.MediaDownloadError) as raised:
                media_download.download_media('https://relay.example/v1/media/token', path)
            self.assertNotIn('SECRET', str(raised.exception))
            self.assertEqual(path.read_bytes(), b'previous good file')
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_short_or_empty_body_is_not_saved_as_complete(self):
        for chunks in [[b'short'], []]:
            replies = [DownloadReply(chunks=chunks, headers={'Content-Length': '100'}) for _ in range(4)]
            with self.subTest(chunks=chunks), tempfile.TemporaryDirectory() as tmp, patch.object(media_download.requests, 'get', side_effect=replies), patch.object(media_download.time, 'sleep'):
                path = Path(tmp) / 'video.mp4'
                with self.assertRaises(media_download.MediaDownloadError):
                    media_download.download_media('https://relay.example/v1/media/token', path)
                self.assertFalse(path.exists())
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_permanent_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(media_download.requests, 'get', return_value=DownloadReply(404)) as get, patch.object(media_download.time, 'sleep') as sleep:
            with self.assertRaisesRegex(media_download.MediaDownloadError, 'HTTP 404'):
                media_download.download_media('https://relay.example/v1/media/token', Path(tmp) / 'manual.pdf')
            self.assertEqual(get.call_count, 1)
            sleep.assert_not_called()
