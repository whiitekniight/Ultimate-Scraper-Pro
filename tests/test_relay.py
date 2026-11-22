import importlib.util
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from relay.server import create_app
from relay_client import RelayClient, RelayClientError

SETTINGS = {'dev_id': 'private-app-id', 'dev_password': 'private-app-password'}
ACCOUNT = {'id': 'alice', 'maxthreads': '2', 'maxrequestspermin': '60'}


class Reply:
    def __init__(self, data=None, status=200, headers=None, raw=None):
        self.status_code = status
        self.raw = raw if raw is not None else json.dumps(data).encode()
        self.headers = headers or {'Content-Type': 'application/json'}
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()
    def close(self):
        self.closed = True
    def iter_content(self, size):
        yield self.raw


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.upstream = Mock(return_value=Reply({'response': {'ssuser': ACCOUNT}}))
        self.app = create_app(SETTINGS, self.upstream, lambda: self.now)
        self.http = self.app.test_client()

    def login(self):
        result = self.http.post('/v1/session', json={'username': 'alice', 'password': 'personal-password'})
        self.assertEqual(result.status_code, 200)
        return result.json['token']

    def test_login_keeps_developer_credentials_server_side(self):
        token = self.login()
        self.assertEqual(len(token), 43)
        args, kwargs = self.upstream.call_args
        self.assertEqual(args[0], 'https://api.screenscraper.fr/api2/ssuserInfos.php')
        self.assertEqual(kwargs['params']['devpassword'], SETTINGS['dev_password'])
        self.assertFalse(kwargs['allow_redirects'])
        self.assertTrue(kwargs['stream'])

    def test_auth_required_and_unsupported_inputs_rejected(self):
        self.assertEqual(self.http.post('/v1/game', json={}).status_code, 401)
        token = self.login()
        for fields in [{'romnom': 'game', 'devid': 'override'}, {'romnom': 'game', 'url': 'http://127.0.0.1'},
                       {'romnom': 'game', 'crc': 'invalid'}, {'romnom': 'game', 'systemeid': '-1'},
                       {'romnom': 'game', 'romtype': 'other'}]:
            self.assertEqual(self.http.post('/v1/game', json=fields, headers={'Authorization': 'Bearer ' + token}).status_code, 400)

    def test_game_response_and_media_never_return_upstream_credentials(self):
        token = self.login()
        secret_url = 'https://www.screenscraper.fr/image.php?devid=private-app-id&devpassword=private-app-password'
        self.upstream.return_value = Reply({'header': {'url': secret_url}, 'response': {'jeu': {
            'id': '123', 'medias': [{'type': 'box-2D', 'url': secret_url}],
            'description': 'private-app-password personal-password'}}})
        result = self.http.post('/v1/game', json={'romnom': 'game', 'systemeid': '1'}, headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(result.status_code, 200)
        for secret in [SETTINGS['dev_id'], SETTINGS['dev_password'], 'personal-password', 'image.php', 'header']:
            self.assertNotIn(secret, result.text)
        path = result.json['response']['jeu']['medias'][0]['url']
        self.assertTrue(path.startswith('/v1/media/'))
        self.upstream.return_value = Reply(raw=b'picture', headers={'Content-Type': 'image/png', 'Content-Length': '7'})
        media = self.http.get(path)
        self.assertEqual(media.status_code, 200)
        self.assertEqual(media.data, b'picture')
        self.now += 1801
        self.assertEqual(self.http.get(path).status_code, 404)

    def test_no_arbitrary_media_targets(self):
        relay = self.app.extensions['relay']
        for url in ['http://screenscraper.fr/media', 'https://screenscraper.fr.evil.test/',
                    'https://127.0.0.1/', 'https://screenscraper.fr:444/',
                    'https://user:password@screenscraper.fr/']:
            self.assertFalse(relay.media_url_allowed(url))
        self.assertEqual(self.http.get('/v1/media/arbitrary').status_code, 404)

    def test_expired_session(self):
        token = self.login()
        self.now += 1801
        self.assertEqual(self.http.post('/v1/game', json={'romnom': 'game'}, headers={'Authorization': 'Bearer ' + token}).status_code, 401)

    def test_login_rate_limit(self):
        for _ in range(5):
            self.login()
        self.assertEqual(self.http.post('/v1/session', json={'username': 'alice', 'password': 'personal-password'}).status_code, 429)
        self.assertEqual(self.upstream.call_count, 5)

    def test_rejects_oversized_request_and_wrong_account(self):
        self.assertEqual(self.http.post('/v1/session', data='x' * 17000, content_type='application/json').status_code, 413)
        self.upstream.return_value = Reply({'response': {'ssuser': {'id': 'anonymous'}}})
        self.assertEqual(self.http.post('/v1/session', json={'username': 'alice', 'password': 'wrong'}).status_code, 403)

    def test_upstream_errors_do_not_echo_secrets(self):
        for status in [301, 400, 401, 403, 429, 500]:
            self.setUp()
            self.upstream.return_value = Reply(raw=b'private-app-password', status=status)
            result = self.http.post('/v1/session', json={'username': 'alice', 'password': 'personal-password'})
            self.assertGreaterEqual(result.status_code, 400)
            self.assertNotIn('private-app-password', result.text)


class ClientTests(unittest.TestCase):
    def test_https_required(self):
        for url in ['http://nas/', 'https://user:pw@example.test', 'https://example.test?token=abc', 'https://example.test/path']:
            with self.assertRaises(RelayClientError):
                RelayClient(url)
        RelayClient('http://127.0.0.1:18080')

    def test_login_cache_and_expired_server_session_retry(self):
        login = Mock(status_code=200)
        login.json.return_value = {'token': 'token-value', 'account': ACCOUNT, 'expires_in': 1800}
        expired = Mock(status_code=401)
        game = Mock(status_code=200)
        game.json.return_value = {'response': {'jeu': {'medias': [{'url': '/v1/media/abc'}]}}}
        post = Mock(side_effect=[login, expired, login, game])
        client = RelayClient('https://relay.example.test', post)
        cfg = {'ssid': 'alice', 'sspassword': ' spaces&?+# '}
        client.user(cfg)
        client.user(cfg)
        result = client.game(cfg, {'romnom': 'game'})
        self.assertEqual(post.call_count, 4)
        self.assertEqual(post.call_args_list[0].kwargs['json']['password'], cfg['sspassword'])
        self.assertEqual(post.call_args_list[-1].kwargs['headers']['Authorization'], 'Bearer token-value')
        self.assertNotIn('password', post.call_args_list[-1].kwargs['json'])
        self.assertEqual(result['response']['jeu']['medias'][0]['url'], 'https://relay.example.test/v1/media/abc')


if __name__ == '__main__':
    unittest.main()
