import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engine', ROOT / 'UltimateScraperProv2.0.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def response(code=200, payload=None, text=''):
    result = Mock(status_code=code, text=text)
    if payload is None:
        result.json.side_effect = ValueError('not JSON')
    else:
        result.json.return_value = payload
    return result


class ScreenScraperTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {'ssid': 'test-user', 'sspassword': ' spaces &?+# '}
        self.credentials = patch.multiple(engine, DEV_ID='test-app', DEV_PASSWORD='test-app-secret')
        self.credentials.start()
        self.addCleanup(self.credentials.stop)

    def test_missing_developer_credentials_never_sends_request(self):
        with patch.object(engine, 'DEV_ID', ''), patch.object(engine.requests, 'get') as get:
            self.assertIsNone(engine.fetch_screenscraper_user_info(self.cfg))
            self.assertIn('Application API credentials', self.cfg['_screenscraper_error'])
            get.assert_not_called()

    def test_login_transport_and_no_account_logging(self):
        reply = response(payload={'response': {'ssuser': {'id': 'test-user', 'maxthreads': '2'}}})
        with patch.object(engine.requests, 'get', return_value=reply) as get, redirect_stdout(io.StringIO()) as output:
            info = engine.fetch_screenscraper_user_info(self.cfg)
        self.assertEqual(info['maxthreads'], 2)
        args, kwargs = get.call_args
        self.assertEqual(args[0], 'https://api.screenscraper.fr/api2/ssuserInfos.php')
        self.assertEqual(kwargs['params']['sspassword'], self.cfg['sspassword'])
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(output.getvalue(), '')

    def test_http_errors_never_include_response_body_or_credentials(self):
        for status in [301, 400, 401, 403, 429, 503]:
            with self.subTest(status=status), patch.object(engine.requests, 'get', return_value=response(status, text='test-app-secret')):
                self.assertIsNone(engine.fetch_screenscraper_user_info(self.cfg))
                self.assertNotIn('test-app-secret', self.cfg['_screenscraper_error'])

    def test_network_errors_never_expose_url(self):
        for exc in [requests.Timeout('secret URL'), requests.ConnectionError('secret URL')]:
            with patch.object(engine.requests, 'get', side_effect=exc):
                self.assertIsNone(engine.fetch_screenscraper_user_info(self.cfg))
                self.assertNotIn('secret URL', self.cfg['_screenscraper_error'])

    def test_malformed_and_api_errors(self):
        for reply in [response(text='bad test-app-secret'), response(payload={'response': {'error': 'test-app-secret'}}), response(payload=[]), response(payload={'response': {'ssuser': {}}})]:
            with patch.object(engine.requests, 'get', return_value=reply):
                self.assertIsNone(engine.fetch_screenscraper_user_info(self.cfg))
                self.assertNotIn('test-app-secret', self.cfg['_screenscraper_error'])

    def test_game_name_fallback(self):
        found = {'id': '1'}
        with patch.object(engine.requests, 'get', side_effect=[response(404), response(payload={'response': {'jeu': [found]}})]) as get:
            self.assertEqual(engine.fetch_game_info(self.cfg, '!Game (Europe)', '84'), found)
        self.assertEqual([c.kwargs['params']['romnom'] for c in get.call_args_list], ['!Game (Europe)', '!Game'])

    def test_hash_lookup_and_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'fixture.bin'
            rom.write_bytes(b'fixture')
            with patch.object(engine.requests, 'get', return_value=response(payload={'response': {'jeu': {'id': '2'}}})) as get:
                self.assertEqual(engine.fetch_game_info(self.cfg, 'fixture', '1', str(rom))['id'], '2')
            params = get.call_args.kwargs['params']
            self.assertEqual(params['romnom'], 'fixture.bin')
            self.assertEqual(params['romtaille'], 7)
            self.assertEqual(len(params['crc']), 8)
        with patch.object(engine.requests, 'get', return_value=response(404)):
            self.assertIsNone(engine.fetch_game_info(self.cfg, 'unknown', '1'))

    def test_auth_failure_does_not_become_game_not_found(self):
        with patch.object(engine.requests, 'get', return_value=response(403)) as get:
            with self.assertRaises(engine.ScreenScraperError):
                engine.fetch_game_info(self.cfg, 'Game', '1')
            self.assertEqual(get.call_count, 1)

    def test_transient_errors_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'CONFIG_FILE', str(Path(tmp) / 'app' / 'settings.json')):
            engine.save_config(dict(self.cfg, _screenscraper_error='temporary'))
            saved = json.loads(Path(engine.CONFIG_FILE).read_text())
            self.assertNotIn('_screenscraper_error', saved)


if __name__ == '__main__':
    unittest.main()
