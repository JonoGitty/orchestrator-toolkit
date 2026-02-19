#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import imaplib
import email
from email.header import decode_header
from typing import List, Tuple, Optional

try:
    import keyring  # type: ignore
except Exception:  # pragma: no cover
    keyring = None  # type: ignore


SERVICE_NS = "ai_orchestrator"


def _set_secret(kind: str, alias: str, secret: str) -> None:
    if not keyring:
        raise RuntimeError("keyring not available; cannot store secret securely")
    keyring.set_password(SERVICE_NS, f"{kind}:{alias}", secret)


def _get_secret(kind: str, alias: str) -> Optional[str]:
    if not keyring:
        return None
    return keyring.get_password(SERVICE_NS, f"{kind}:{alias}")


# ---------------- Email (IMAP) ----------------
def setup_email(alias: str, server: str, username: str, password: str) -> None:
    """Store IMAP credentials in keyring; test login."""
    # Test login
    M = imaplib.IMAP4_SSL(server)
    try:
        M.login(username, password)
        M.logout()
    except Exception:
        try:
            M.logout()
        except Exception:
            pass
        raise
    # Store
    _set_secret("email_user", alias, username)
    _set_secret("email_host", alias, server)
    _set_secret("email_pass", alias, password)


def _imap_connect(alias: str) -> imaplib.IMAP4_SSL:
    host = _get_secret("email_host", alias) or ""
    user = _get_secret("email_user", alias) or ""
    pwd = _get_secret("email_pass", alias) or ""
    if not (host and user and pwd):
        raise RuntimeError(f"Email alias '{alias}' not configured. Run /email setup {alias}")
    M = imaplib.IMAP4_SSL(host)
    M.login(user, pwd)
    return M


def list_inbox(alias: str, limit: int = 10) -> List[Tuple[str, str, str]]:
    """Return a list of (date, from, subject) for the latest N messages."""
    M = _imap_connect(alias)
    try:
        M.select("INBOX")
        typ, data = M.search(None, "ALL")
        if typ != 'OK':
            return []
        ids = data[0].split()
        ids = ids[-limit:]
        out: List[Tuple[str,str,str]] = []
        for msgid in reversed(ids):
            typ, msg_data = M.fetch(msgid, '(RFC822.HEADER)')
            if typ != 'OK' or not msg_data:
                continue
            raw = msg_data[0][1]
            hdr = email.message_from_bytes(raw)
            subj = _decode_header(hdr.get('Subject', ''))
            frm = _decode_header(hdr.get('From', ''))
            date = hdr.get('Date', '')
            out.append((date, frm, subj))
        return out
    finally:
        try:
            M.logout()
        except Exception:
            pass


def _decode_header(value: str) -> str:
    try:
        parts = decode_header(value)
        out = []
        for val, enc in parts:
            if isinstance(val, bytes):
                out.append(val.decode(enc or 'utf-8', errors='ignore'))
            else:
                out.append(val)
        return ''.join(out)
    except Exception:
        return value


# ---------------- Calendar (CalDAV) ----------------
def setup_caldav(alias: str, url: str, username: str, password: str) -> None:
    """Store CalDAV credentials and verify connectivity."""
    from caldav import DAVClient  # lazy import
    client = DAVClient(url, username=username, password=password)
    principal = client.principal()
    _ = principal.calendars()  # fetch to verify
    _set_secret("cal_url", alias, url)
    _set_secret("cal_user", alias, username)
    _set_secret("cal_pass", alias, password)


def _cal_principal(alias: str):
    from caldav import DAVClient
    url = _get_secret("cal_url", alias) or ""
    user = _get_secret("cal_user", alias) or ""
    pwd = _get_secret("cal_pass", alias) or ""
    if not (url and user and pwd):
        raise RuntimeError(f"Calendar alias '{alias}' not configured. Run /calendar setup {alias}")
    client = DAVClient(url, username=user, password=pwd)
    return client.principal()


def list_events(alias: str, days: int = 1) -> List[str]:
    """List upcoming events within 'days' from now. Returns human-readable lines."""
    principal = _cal_principal(alias)
    calendars = principal.calendars()
    if not calendars:
        return []
    cal = calendars[0]
    start = dt.datetime.now(dt.timezone.utc)
    end = start + dt.timedelta(days=days)
    events = cal.date_search(start, end)
    lines: List[str] = []
    for ev in events:
        try:
            vcal = ev.vobject_instance
            for comp in vcal.vevent_list:
                summ = str(getattr(comp, 'summary', 'untitled'))
                dtstart = getattr(comp, 'dtstart', None)
                d = str(dtstart.value) if dtstart else ''
                lines.append(f"{d}  {summ}")
        except Exception:
            pass
    return lines
