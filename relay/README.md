# ScreenScraper relay

Use a single Waitress process with 12 threads. Sessions and media capabilities live only in memory, so multiple independent workers must not be used without a shared session store.

## Configuration

Create a private JSON file outside this repository containing `dev_id` and `dev_password`, populated with your own approved ScreenScraper application credentials. Do not copy personal scraper settings to the server.

Set `RELAY_SECRETS_FILE` to that file and run `python server.py` after installing `requirements.txt`. The default listen address is loopback, port 8080. Docker deployments can set `RELAY_BIND=0.0.0.0` within a dedicated container network, without publishing a host port.

Run the application as a non-root user. Mount app code and the credential file read-only. Do not mount the Docker socket, ROM libraries, NAS root, other services, or unrelated shares. Use a read-only root filesystem, a limited temporary filesystem, resource limits, no additional Linux capabilities, and restart protection.

Place an HTTPS tunnel or reverse proxy in front of it. `RELAY_TRUST_CLOUDFLARE=1` is allowed only when the origin can be reached exclusively by the trusted Cloudflare connector; otherwise leave it unset so clients cannot spoof the IP used for request limits. Do not log POST bodies, Authorization headers, upstream query strings, or full media capability URLs.

## API

- `GET /health`: minimal liveness response; no account or host information.
- `POST /v1/session`: JSON `username` and `password`; returns a short-lived bearer token and a limited account summary.
- `POST /v1/game`: bearer authentication plus allowlisted ROM name/system/hash fields; returns game metadata with opaque media links. Arbitrary URL parameters and developer credential overrides are rejected.
- `GET /v1/media/<capability>`: forwards only an approved upstream HTTPS media link. Links expire with their account session. Redirects and unsupported media content types are rejected.

User sessions expire after 30 minutes. Login limits apply per account and source IP. Game concurrency and request limits apply to the ScreenScraper account across all its sessions, with global service limits as well. Memory, body sizes, upstream responses and media sizes are bounded. Sessions are lost on restart and the client revalidates automatically.

This protects the developer secret from client extraction, not from a compromised NAS or operator account. Keep the host and container images updated. Revoke any credentials shipped in older desktop releases after migration. Confirm that your ScreenScraper application authorization covers your deployment and shared egress IP.
