"""Restricted ScreenScraper relay. Run one process: sessions stay in RAM only."""
from collections import OrderedDict, deque
from itertools import chain
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import urlsplit, quote, quote_plus

import requests
from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException


class RelayError(Exception):
    def __init__(self, message, status=502):
        self.message, self.status = message, status


@dataclass
class Session:
    username: str
    password: str
    account: dict
    expires: float


class Relay:
    def __init__(self, settings, upstream=None, clock=time.monotonic):
        self.dev_id = settings['dev_id']
        self.dev_password = settings['dev_password']
        if not self.dev_id or not self.dev_password:
            raise RuntimeError('Application credentials must be configured on the server.')
        self.clock = clock
        self.upstream = upstream or requests.get
        self.lock = threading.RLock()
        self.sessions = OrderedDict()
        self.assets = OrderedDict()
        self.rates = OrderedDict()
        self.active = {}
        self.slots = threading.BoundedSemaphore(6)
        self.download_slots = threading.BoundedSemaphore(6)
        self.ttl = 1800

    def cleanup(self):
        now = self.clock()
        for key in [k for k, s in self.sessions.items() if s.expires <= now]:
            del self.sessions[key]
        for key in [k for k, a in self.assets.items() if a[2] <= now or a[0] not in self.sessions]:
            del self.assets[key]
        for key in [k for k, q in self.rates.items() if not q or q[-1] < now - 600]:
            del self.rates[key]

    def rate(self, key, count, window=60):
        with self.lock:
            now = self.clock()
            self.cleanup()
            q = self.rates.setdefault(key, deque())
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= count:
                raise RelayError('Too many requests. Please wait before trying again.', 429)
            q.append(now)
            if len(self.rates) > 10000:
                self.rates.popitem(last=False)

    def account_key(self, username):
        return hashlib.sha256(username.casefold().encode()).hexdigest()

    def parameters(self, username, password):
        return dict(devid=self.dev_id, devpassword=self.dev_password,
                    softname='UltimateScraperPro Relay 1.2.1', output='json',
                    ssid=username, sspassword=password)

    def api(self, endpoint, params, not_found=False):
        if not self.slots.acquire(blocking=False):
            raise RelayError('The scraper service is busy. Please try again shortly.', 503)
        try:
            # Fixed destination and endpoint: clients cannot turn this into a proxy
            # to the NAS, other websites, or arbitrary ScreenScraper API methods.
            with self.upstream('https://api.screenscraper.fr/api2/' + endpoint,
                               params=params, timeout=(8, 45), allow_redirects=False,
                               stream=True) as reply:
                if reply.status_code == 404 and not_found:
                    return None
                if reply.status_code in (400, 401, 403):
                    raise RelayError('ScreenScraper rejected authentication. Check your username and password.', 403)
                if reply.status_code == 429:
                    raise RelayError('ScreenScraper request limit reached. Please wait.', 429)
                if reply.status_code != 200:
                    raise RelayError('ScreenScraper is temporarily unavailable.', 502)
                chunks, size = [], 0
                for chunk in reply.iter_content(65536):
                    size += len(chunk)
                    if size > 8 * 1024 * 1024:
                        raise RelayError('ScreenScraper returned an oversized response.')
                    chunks.append(chunk)
                text = b''.join(chunks).decode('utf-8-sig')
                try:
                    data = json.loads(text)
                except ValueError:
                    data = json.loads(re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text))
                if not isinstance(data, dict) or not isinstance(data.get('response'), dict):
                    raise RelayError('ScreenScraper returned an invalid response.')
                if data.get('error') or data['response'].get('error'):
                    raise RelayError('ScreenScraper rejected the request.', 403)
                # Deliberately discard the API header, which may echo request URLs.
                return data['response']
        except RelayError:
            raise
        except (requests.RequestException, ValueError, UnicodeError):
            raise RelayError('Could not securely retrieve information from ScreenScraper.') from None
        finally:
            self.slots.release()

    def login(self, username, password, ip):
        if not isinstance(username, str) or not isinstance(password, str):
            raise RelayError('Enter your ScreenScraper username and password.', 400)
        username = username.strip()
        if not username or not password or len(username) > 128 or len(password) > 512:
            raise RelayError('Enter a valid ScreenScraper username and password.', 400)
        self.rate(('login-ip', ip), 10)
        self.rate(('login-user', self.account_key(username)), 5)
        response = self.api('ssuserInfos.php', self.parameters(username, password))
        account = response.get('ssuser')
        if not isinstance(account, dict) or str(account.get('id', '')).casefold() != username.casefold():
            raise RelayError('ScreenScraper did not validate this account. Use your username rather than your email address.', 403)
        def number(key, default):
            try:
                return int(account.get(key, default))
            except (ValueError, TypeError):
                return default
        safe = {'id': str(account['id']), 'niveau': str(account.get('niveau', '0')),
                'maxthreads': max(1, min(6, number('maxthreads', 1))),
                'requeststoday': max(0, number('requeststoday', 0)),
                'maxrequestsperday': max(0, number('maxrequestsperday', 10000)),
                'maxrequestspermin': max(1, min(120, number('maxrequestspermin', 60) or 60))}
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.cleanup()
            # Bound account/session memory without evicting unrelated users.
            same_user = [k for k, s in self.sessions.items() if s.username.casefold() == username.casefold()]
            for k in same_user[:-3]:
                del self.sessions[k]
            if len(self.sessions) >= 2048:
                raise RelayError('The scraper service is busy. Please try again later.', 503)
            self.sessions[token] = Session(username, password, safe, self.clock() + self.ttl)
        return dict(token=token, expires_in=self.ttl, account=safe)

    def session(self, token):
        with self.lock:
            self.cleanup()
            session = self.sessions.get(token)
            if not session:
                raise RelayError('Your session expired. Please validate your account again.', 401)
            return session

    def media_url_allowed(self, url):
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or '').lower()
            return (parsed.scheme == 'https' and not parsed.username and not parsed.password
                    and parsed.port in (None, 443)
                    and (host == 'screenscraper.fr' or host.endswith('.screenscraper.fr')))
        except ValueError:
            return False

    def sanitize(self, value, token, session):
        if isinstance(value, dict):
            return {k: self.sanitize(v, token, session) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(v, token, session) for v in value]
        if not isinstance(value, str):
            return value
        if self.media_url_allowed(value):
            with self.lock:
                key = secrets.token_urlsafe(32)
                self.assets[key] = (token, value, session.expires)
                while len(self.assets) > 20000:
                    self.assets.popitem(last=False)
            # An opaque, expiring capability. No upstream URL or API credentials.
            return '/v1/media/' + key
        # Discard any unsupported URL that contains authentication parameters.
        if value.lower().startswith(('http:', 'https:')) and any(
                x in value.lower() for x in ('devid=', 'devpassword=', 'sspassword=')):
            return ''
        for secret in (self.dev_id, self.dev_password, session.password):
            if secret:
                for variant in {secret, quote(secret, safe=''), quote_plus(secret)}:
                    value = value.replace(variant, '[redacted]')
        return value

    def game(self, token, fields):
        session = self.session(token)
        allowed = {'romnom', 'systemeid', 'romtype', 'crc', 'md5', 'sha1', 'romtaille'}
        if not isinstance(fields, dict) or set(fields) - allowed:
            raise RelayError('Unsupported game search parameters.', 400)
        if not fields.get('romnom') or not isinstance(fields['romnom'], str) or len(fields['romnom']) > 512:
            raise RelayError('A valid ROM name is required.', 400)
        if not re.fullmatch(r'\d{1,5}', str(fields.get('systemeid', '0'))):
            raise RelayError('Invalid system identifier.', 400)
        for key, length in [('crc', 8), ('md5', 32), ('sha1', 40)]:
            if key in fields and not re.fullmatch('[0-9a-fA-F]{' + str(length) + '}', str(fields[key])):
                raise RelayError('Invalid ROM hash.', 400)
        if 'romtaille' in fields and (not str(fields['romtaille']).isdigit() or len(str(fields['romtaille'])) > 14):
            raise RelayError('Invalid ROM size.', 400)
        if fields.get('romtype', 'rom') != 'rom':
            raise RelayError('Unsupported search type.', 400)
        identity = self.account_key(session.username)
        self.rate(('game', identity), session.account['maxrequestspermin'])
        with self.lock:
            if self.active.get(identity, 0) >= session.account['maxthreads']:
                raise RelayError('Your account already has its allowed searches running.', 429)
            self.active[identity] = self.active.get(identity, 0) + 1
        try:
            params = self.parameters(session.username, session.password)
            params.update(fields)
            response = self.api('jeuInfos.php', params, not_found=True)
            if response is None:
                return None
            return self.sanitize(response.get('jeu'), token, session)
        finally:
            with self.lock:
                self.active[identity] -= 1
                if not self.active[identity]:
                    del self.active[identity]

    def media(self, key, ip):
        with self.lock:
            self.cleanup()
            asset = self.assets.get(key)
        if not asset:
            raise RelayError('This media link has expired. Search for the game again.', 404)
        token, url, _ = asset
        session = self.session(token)
        self.rate(('media', self.account_key(session.username)), 300)
        self.rate(('media-ip', ip), 400)
        if not self.download_slots.acquire(timeout=5):
            raise RelayError('Media downloads are busy. Please try again shortly.', 503)
        reply = None
        try:
            reply = self.upstream(url, timeout=(8, 60), allow_redirects=False, stream=True)
            if reply.status_code == 429:
                raise RelayError('ScreenScraper request limit reached. Please wait.', 429)
            if reply.status_code != 200:
                raise RelayError('ScreenScraper could not supply this media.', 502)
            content_type = reply.headers.get('Content-Type', '').split(';')[0].strip().lower()
            stream = reply.iter_content(65536)
            first_chunk = next(stream, b'')
            if not first_chunk:
                raise RelayError('ScreenScraper returned an empty media file.')
            if content_type in ('application/force-download', 'application/x-download', 'application/download', 'application/x-pdf'):
                if not first_chunk.lstrip().startswith(b'%PDF-'):
                    raise RelayError('ScreenScraper returned an unsupported media response.')
                content_type = 'application/pdf'
            if not (content_type.startswith(('image/', 'video/', 'audio/')) or content_type in ('application/pdf', 'application/octet-stream')):
                raise RelayError('ScreenScraper returned an unsupported media response.')
            limit = 512 * 1024 * 1024
            if int(reply.headers.get('Content-Length', '0')) > limit:
                raise RelayError('This media file exceeds the download limit.', 413)
        except Exception as exc:
            if reply is not None:
                reply.close()
            self.download_slots.release()
            if isinstance(exc, RelayError):
                raise
            raise RelayError('Could not securely download media from ScreenScraper.') from None
        finished = False
        finish_lock = threading.Lock()
        def finish():
            nonlocal finished
            with finish_lock:
                if not finished:
                    finished = True
                    reply.close()
                    self.download_slots.release()
        def chunks():
            size = 0
            try:
                for chunk in chain((first_chunk,), stream):
                    size += len(chunk)
                    if size > limit:
                        raise RuntimeError('Media exceeded the download size limit.')
                    yield chunk
            except requests.RequestException:
                raise RuntimeError('Media stream was interrupted.') from None
            finally:
                finish()
        headers = {'Content-Type': content_type}
        if not reply.headers.get('Content-Encoding') and reply.headers.get('Content-Length', '').isdigit():
            headers['Content-Length'] = reply.headers['Content-Length']
        response = Response(chunks(), headers=headers)
        response.call_on_close(finish)
        return response


def create_app(settings=None, upstream=None, clock=time.monotonic):
    if settings is None:
        settings = json.loads(Path(os.environ.get('RELAY_SECRETS_FILE', '/run/secrets/screenscraper.json')).read_text())
    relay = Relay(settings, upstream, clock)
    if clock is time.monotonic:
        def expire_idle_sessions():
            while True:
                time.sleep(10)
                with relay.lock:
                    relay.cleanup()
        threading.Thread(target=expire_idle_sessions, daemon=True,
                         name='relay-session-cleanup').start()
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16384
    app.extensions['relay'] = relay

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc, RelayError):
            message, status = exc.message, exc.status
        elif isinstance(exc, HTTPException):
            message, status = 'Invalid relay request.', exc.code
        else:
            # Never log exceptions: request objects and URLs may contain secrets.
            message, status = 'The scraper service could not complete this request.', 500
        response = jsonify(error=message)
        if status in (429, 503):
            response.headers['Retry-After'] = '2'
        return response, status

    def ip():
        # Trust this only when the origin is reachable exclusively by our tunnel.
        if os.environ.get('RELAY_TRUST_CLOUDFLARE') == '1':
            return request.headers.get('CF-Connecting-IP', request.remote_addr or 'unknown')
        return request.remote_addr or 'unknown'

    @app.get('/health')
    def health():
        return jsonify(status='ok', service='ultimate-scraper-relay', version='1.2.1')

    @app.post('/v1/session')
    def login():
        body = request.get_json()
        if not isinstance(body, dict) or set(body) != {'username', 'password'}:
            raise RelayError('Provide your ScreenScraper username and password.', 400)
        return jsonify(relay.login(body['username'], body['password'], ip()))

    @app.post('/v1/game')
    def game():
        authorization = request.headers.get('Authorization', '')
        if not authorization.startswith('Bearer '):
            raise RelayError('Account validation is required.', 401)
        found = relay.game(authorization[7:], request.get_json())
        if not found:
            return jsonify(error='Game not found.'), 404
        return jsonify(response={'jeu': found})

    @app.get('/v1/media/<key>')
    def media(key):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', key):
            raise RelayError('Invalid media link.', 404)
        return relay.media(key, ip())

    return app


if __name__ == '__main__':
    from waitress import serve
    serve(create_app(), host=os.environ.get('RELAY_BIND', '127.0.0.1'),
          port=int(os.environ.get('RELAY_PORT', '8080')), threads=18,
          connection_limit=64, channel_timeout=60,
          max_request_body_size=16384, max_request_header_size=16384,
          expose_tracebacks=False, ident='ScraperRelay')
