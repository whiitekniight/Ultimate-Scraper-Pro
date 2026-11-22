"""Client for the restricted relay. No ScreenScraper developer credentials."""
import hashlib
import os
import threading
import time
from urllib.parse import urlsplit

import requests

DEFAULT_RELAY_URL = 'https://scraper.greenstreemlabs.com'


class RelayClientError(RuntimeError):
    pass


class RelayClient:
    def __init__(self, base_url=None, post=None, clock=time.monotonic):
        self.base_url = (base_url or os.environ.get('SCREENSCRAPER_RELAY_URL') or DEFAULT_RELAY_URL).rstrip('/')
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost'))
                or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/')):
            raise RelayClientError('The scraper service requires a secure HTTPS address.')
        self.post = post or requests.post
        self.clock = clock
        self.lock = threading.RLock()
        self.cached = {}

    def json_request(self, path, payload, token=None, not_found=False):
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        try:
            reply = self.post(self.base_url + path, json=payload, headers=headers,
                              timeout=(10, 60), allow_redirects=False)
        except requests.RequestException:
            raise RelayClientError('Could not securely connect to the scraper service. Please try again shortly.') from None
        if reply.status_code == 404 and not_found:
            return None
        if reply.status_code != 200:
            messages = {400: 'The scraper service rejected the request. Check your settings.',
                        401: 'Your scraper session expired. Validate your account again.',
                        403: 'ScreenScraper rejected your login. Use your ScreenScraper username and password.',
                        429: 'The request limit was reached. Wait a little before trying again.',
                        503: 'The scraper service is busy. Please try again shortly.'}
            error = RelayClientError(messages.get(reply.status_code, 'The scraper service is temporarily unavailable.'))
            error.status = reply.status_code
            raise error
        try:
            data = reply.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except ValueError:
            raise RelayClientError('The scraper service returned an unreadable response.') from None

    def session(self, cfg, refresh=False):
        username = cfg.get('ssid', '').strip()
        password = cfg.get('sspassword', '')
        if not username or not password:
            raise RelayClientError('Enter your ScreenScraper username and password in Accounts, then select Validate.')
        key = hashlib.sha256((username + '\0' + password).encode()).hexdigest()
        # Single-flight login prevents parallel ROM workers making login storms.
        with self.lock:
            now = self.clock()
            self.cached = {k: v for k, v in self.cached.items() if v['expires'] > now}
            if key in self.cached and not refresh:
                return self.cached[key]
            data = self.json_request('/v1/session', {'username': username, 'password': password})
            if not isinstance(data.get('token'), str) or not isinstance(data.get('account'), dict):
                raise RelayClientError('The scraper service did not validate your account.')
            try:
                ttl = max(1, min(1800, int(data.get('expires_in', 1800))))
            except (TypeError, ValueError):
                raise RelayClientError('The scraper service returned an invalid session.') from None
            session = {'token': data['token'], 'account': data['account'],
                       'expires': now + max(1, ttl - 30)}
            if len(self.cached) >= 32:
                self.cached.clear()
            self.cached[key] = session
            return session

    def absolute_media(self, value):
        if isinstance(value, dict):
            return {k: self.absolute_media(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.absolute_media(v) for v in value]
        if isinstance(value, str) and value.startswith('/v1/media/'):
            return self.base_url + value
        return value

    def user(self, cfg):
        # A successful cached session is sufficient until it nears expiration.
        return {'response': {'ssuser': self.session(cfg)['account']}}

    def game(self, cfg, fields):
        for attempt in range(2):
            session = self.session(cfg, refresh=bool(attempt))
            try:
                data = self.json_request('/v1/game', fields, session['token'], not_found=True)
                return self.absolute_media(data) if data else None
            except RelayClientError as exc:
                if getattr(exc, 'status', None) != 401 or attempt:
                    raise
