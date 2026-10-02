"""Fetch an approved badge image for the local champion-card canvas."""
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException

ALLOWED_HOSTS = {
    'flagcdn.com', 'raw.githubusercontent.com', 'upload.wikimedia.org',
    'thumb.wikimedia.org', 'crests.football-data.org', 'cdn.sportmonks.com',
    'www.thesportsdb.com', 'seeklogo.com', 'images.seeklogo.com',
}
ALLOWED_TYPES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml'}
MAX_BYTES = 2_000_000


def checked_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        valid = (len(url) <= 1200 and parts.scheme == 'https'
                 and parts.hostname in ALLOWED_HOSTS and parts.port in (None, 443)
                 and not parts.username and not parts.password and not parts.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(422, 'Origine stemma non consentita.')
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_badge_image(url: str) -> tuple[bytes, str]:
    checked_url(url)
    opener = build_opener(SafeRedirect())
    try:
        with opener.open(Request(url, headers={'User-Agent': 'SuperbaPortal/1.0 (champion-card)'}), timeout=7) as response:
            media_type = response.headers.get_content_type().lower()
            if media_type not in ALLOWED_TYPES:
                raise HTTPException(415, 'Il file non è un’immagine supportata.')
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise HTTPException(413, 'Lo stemma supera la dimensione consentita.')
            return body, media_type
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(502, 'Stemma esterno non disponibile.') from error
