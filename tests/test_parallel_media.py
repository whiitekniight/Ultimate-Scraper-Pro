from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from test_relay import ACCOUNT, SETTINGS, Reply
from relay.server import create_app


class ParallelMediaTests(unittest.TestCase):
    def test_six_downloads_can_stream_simultaneously(self):
        barrier = threading.Barrier(6)

        class StreamingReply(Reply):
            def iter_content(self, size):
                barrier.wait(timeout=3)
                yield b'picture'

        def upstream(url, **kwargs):
            if url.endswith('ssuserInfos.php'):
                return Reply({'response': {'ssuser': dict(ACCOUNT, maxthreads='6')}})
            return StreamingReply(raw=b'picture', headers={'Content-Type': 'image/png'})

        app = create_app(SETTINGS, upstream, lambda: 1000)
        token = app.test_client().post('/v1/session', json={'username': 'alice', 'password': 'personal-password'}).json['token']
        relay = app.extensions['relay']
        paths = [relay.sanitize('https://www.screenscraper.fr/image.php?id=' + str(i), token, relay.session(token)) for i in range(6)]

        def download(path):
            with app.test_client() as client:
                response = client.get(path)
                return response.status_code, response.data

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(download, paths))
        self.assertEqual(results, [(200, b'picture')] * 6)

    def test_force_download_manual_is_verified_and_served_as_pdf(self):
        def upstream(url, **kwargs):
            if url.endswith('ssuserInfos.php'):
                return Reply({'response': {'ssuser': ACCOUNT}})
            return Reply(raw=b'%PDF-1.7\nfixture', headers={'Content-Type': 'application/force-download; name="manual.pdf"'})
        app = create_app(SETTINGS, upstream, lambda: 1000)
        client = app.test_client()
        token = client.post('/v1/session', json={'username': 'alice', 'password': 'personal-password'}).json['token']
        relay = app.extensions['relay']
        path = relay.sanitize('https://www.screenscraper.fr/manual.php', token, relay.session(token))
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))
