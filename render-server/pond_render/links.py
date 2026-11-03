"""Short, permanent links to stored render files.

A file link is <public url>/s/<code>/<file name>, and a 3D viewer link is <public url>/v/<code>.
The code packs the render id (its UTC timestamp and random suffix) with a keyed hash of the id
and file name, so links need no storage and cannot be guessed or edited to reach another file.
Opening a link redirects to a freshly signed storage URL, so links never expire.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)
MAC_LEN = 6
ID_RE = re.compile(r"^(\d{8}-\d{6})-([0-9a-f]{4})$")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
CODE_RE = re.compile(r"^[0-9A-Za-z]{%d,24}$" % (MAC_LEN + 1))
VIEWER_FILE = "model.glb"


def _b62(n: int) -> str:
    out = ""
    while True:
        n, r = divmod(n, 62)
        out = ALPHABET[r] + out
        if n == 0:
            return out


def _unb62(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 62 + ALPHABET.index(ch)
    return n


class ShortLinks:
    def __init__(self, secret: str, base_url: str):
        self.key = hmac.new(secret.encode(), b"pond short links v1", hashlib.sha256).digest()
        self.base = base_url.rstrip("/")

    def _mac(self, render_id: str, name: str) -> str:
        digest = hmac.new(self.key, f"{render_id}/{name}".encode(), hashlib.sha256).digest()
        return _b62(int.from_bytes(digest[:8], "big")).rjust(11, "0")[:MAC_LEN]

    def code(self, render_id: str, name: str) -> str | None:
        m = ID_RE.match(render_id)
        if not m or not NAME_RE.match(name):
            return None
        stamp = datetime.strptime(m[1], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        seconds = int((stamp - EPOCH).total_seconds())
        if seconds < 0:
            return None
        return _b62(seconds * 65536 + int(m[2], 16)) + self._mac(render_id, name)

    def file_url(self, render_id: str, name: str) -> str | None:
        code = self.code(render_id, name)
        return f"{self.base}/s/{code}/{name}" if code else None

    def viewer_url(self, render_id: str) -> str | None:
        code = self.code(render_id, VIEWER_FILE)
        return f"{self.base}/v/{code}" if code else None

    def resolve(self, code: str, name: str) -> str | None:
        """The render id a link points at, or None if the code is malformed or was not made by us."""
        if not CODE_RE.match(code) or not NAME_RE.match(name):
            return None
        body, mac = code[:-MAC_LEN], code[-MAC_LEN:]
        seconds, suffix = divmod(_unb62(body), 65536)
        try:
            stamp = EPOCH + timedelta(seconds=seconds)
        except OverflowError:
            return None
        render_id = f"{stamp:%Y%m%d-%H%M%S}-{suffix:04x}"
        return render_id if hmac.compare_digest(mac, self._mac(render_id, name)) else None
