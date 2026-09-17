#!/usr/bin/env python3
"""wl-define: define or translate the current text selection as a desktop notification.

    English selection      -> dictionary definition(s)
    non-English selection  -> translation to English (+ alternatives for single words)

Reads the Wayland primary selection (the text you highlighted) via wl-paste and
shows the result with notify-send (mako / dunst / swaync), or with hyprctl notify.
Only the Python standard library is used.

Lookups try several free, keyless providers in order and fall back on failure:
    google      Google Translate "gtx" endpoint — detection, translation,
                alternatives and English definitions in a single request
    clients5    Google's dictionary-extension endpoint — detection + translation
    mymemory    api.mymemory.translated.net — detection + translation
    wiktionary  en.wiktionary.org REST — definitions when the others have none

Results are cached for 30 days under $XDG_CACHE_HOME/wl-define so repeated
lookups never touch the network, and a provider that answers HTTP 429/403 is
skipped for 15 minutes instead of being hammered.

Examples:
    wl-define                       # look up the primary selection
    wl-define -c                    # look up the clipboard instead
    wl-define -t kissa              # look up a literal string
    wl-define -t "hyvää huomenta"   # phrases work too (quote them)
    wl-define -t serendipity -b stdout -e -v   # terminal output, examples, provider log
"""

import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

APP_NAME = "wl-define"
VERSION = "1.1"

GOOGLE_GTX_URL = "https://translate.googleapis.com/translate_a/single"
GOOGLE_CLIENTS5_URL = "https://clients5.google.com/translate_a/t"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
WIKTIONARY_URL = "https://en.wiktionary.org/api/rest_v1/page/definition/"

BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
TOOL_UA = "wl-define/%s (Wayland dictionary popup; Python urllib)" % VERSION

HTTP_TIMEOUT = 8              # seconds per request
MAX_CHARS = 500               # longest selection we bother sending
SUMMARY_CHARS = 60            # notification title length cap
CACHE_TTL = 30 * 24 * 3600    # seconds
CACHE_MAX = 2000              # entries
COOLDOWN_SECONDS = 15 * 60    # after an HTTP 429/403 from a provider
DEFAULT_PROVIDERS = "google,clients5,mymemory"
ID_FILE = "wl-define.notify-id"
ICON = "accessories-dictionary"

LANG_NAMES = {
    "af": "Afrikaans", "ar": "Arabic", "bg": "Bulgarian", "bn": "Bengali",
    "ca": "Catalan", "cs": "Czech", "da": "Danish", "de": "German",
    "el": "Greek", "en": "English", "es": "Spanish", "et": "Estonian",
    "fa": "Persian", "fi": "Finnish", "fr": "French", "ga": "Irish",
    "he": "Hebrew", "iw": "Hebrew", "hi": "Hindi", "hr": "Croatian",
    "hu": "Hungarian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
    "ja": "Japanese", "ko": "Korean", "la": "Latin", "lt": "Lithuanian",
    "lv": "Latvian", "nl": "Dutch", "no": "Norwegian", "pl": "Polish",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sk": "Slovak",
    "sl": "Slovenian", "sv": "Swedish", "sw": "Swahili", "th": "Thai",
    "tr": "Turkish", "uk": "Ukrainian", "vi": "Vietnamese",
    "zh": "Chinese", "zh-CN": "Chinese", "zh-TW": "Chinese (Traditional)",
}


class WlDefineError(Exception):
    """Something the user should see as an error notification."""


class ProviderError(Exception):
    """One provider failed; the chain moves on to the next."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------- input

def read_selection(clipboard):
    """Return the primary selection (or clipboard) as text, '' if empty."""
    if shutil.which("wl-paste") is None:
        raise WlDefineError("wl-paste not found — install wl-clipboard")
    cmd = ["wl-paste", "--no-newline", "--type", "text"]
    if not clipboard:
        cmd.append("--primary")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=3)
    except subprocess.TimeoutExpired:
        raise WlDefineError("wl-paste timed out reading the selection")
    if proc.returncode != 0:
        return ""  # "Nothing is copied" / "No selection"
    return proc.stdout.decode("utf-8", "replace")


def normalize(text):
    """Collapse whitespace and trim punctuation that double-click selections drag in."""
    text = " ".join(text.split())
    text = text.strip(" \"'“”‘’«».,;:!?()[]{}")
    return text[:MAX_CHARS]


# ------------------------------------------------------------------------- helpers

def at(seq, index):
    """Safe list index: None when out of range or not a list."""
    if isinstance(seq, list) and -len(seq) <= index < len(seq):
        return seq[index]
    return None


def clean_html(text):
    """Strip tags/entities and collapse whitespace (Wiktionary returns HTML)."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split())


def lang_base(code):
    return (code or "").split("-")[0].lower()


def lang_name(code):
    return LANG_NAMES.get(code) or LANG_NAMES.get(lang_base(code)) or code


def shorten(text, limit=SUMMARY_CHARS):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def empty_result():
    return {
        "detected": "?",
        "translation": "",
        "alternatives": [],   # [(part_of_speech, [alt, ...]), ...]
        "definitions": [],    # [(part_of_speech, [(definition, example), ...]), ...]
    }


def http_get_json(url, user_agent, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError("HTTP %d" % exc.code, status=exc.code)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise ProviderError("timed out")
        raise ProviderError(str(exc.reason))
    except (socket.timeout, TimeoutError):
        raise ProviderError("timed out")
    except (OSError, ValueError) as exc:
        raise ProviderError(str(exc) or exc.__class__.__name__)


# ----------------------------------------------------------------------- providers

def provider_google(text, source, target):
    """Google Translate gtx: detection [2], translation [0], alternatives [1], definitions [12]."""
    params = [("client", "gtx"), ("sl", source), ("tl", target),
              ("dt", "t"), ("dt", "bd"), ("dt", "md"), ("q", text)]
    data = http_get_json(GOOGLE_GTX_URL + "?" + urllib.parse.urlencode(params), BROWSER_UA)
    if not isinstance(data, list):
        raise ProviderError("unexpected response")

    result = empty_result()
    result["detected"] = at(data, 2) if isinstance(at(data, 2), str) else "?"
    result["translation"] = "".join(
        seg[0] for seg in (at(data, 0) or [])
        if isinstance(seg, list) and isinstance(at(seg, 0), str)
    ).strip()

    for entry in at(data, 1) or []:
        pos = at(entry, 0) or ""
        alts = [a for a in (at(entry, 1) or []) if isinstance(a, str)]
        if alts:
            result["alternatives"].append((pos, alts))

    for entry in at(data, 12) or []:
        pos = at(entry, 0) or ""
        defs = []
        for d in at(entry, 1) or []:
            definition = at(d, 0)
            if not isinstance(definition, str):
                continue
            example = at(d, 2)
            example = clean_html(example) if isinstance(example, str) else ""
            defs.append((definition, example))
        if defs:
            result["definitions"].append((pos, defs))
    return result


def provider_clients5(text, source, target):
    """Google dictionary-extension endpoint: [[translation, detected]] — a separate quota."""
    params = {"client": "dict-chrome-ex", "sl": source, "tl": target, "q": text}
    data = http_get_json(GOOGLE_CLIENTS5_URL + "?" + urllib.parse.urlencode(params), BROWSER_UA)
    item = at(data, 0)
    result = empty_result()
    if isinstance(item, list) and isinstance(at(item, 0), str):
        result["translation"] = item[0].strip()
        result["detected"] = at(item, 1) if isinstance(at(item, 1), str) else source
    elif isinstance(item, str):
        result["translation"] = item.strip()
        result["detected"] = source
    else:
        raise ProviderError("unexpected response")
    return result


def provider_mymemory(text, source, target):
    """MyMemory: free anonymous quota, supports autodetect|target language pairs."""
    pair = ("autodetect" if source == "auto" else source) + "|" + target
    params = {"q": text, "langpair": pair}
    data = http_get_json(MYMEMORY_URL + "?" + urllib.parse.urlencode(params), TOOL_UA)
    if not isinstance(data, dict):
        raise ProviderError("unexpected response")
    status = str(data.get("responseStatus", ""))
    result = empty_result()
    if status != "200":
        details = str(data.get("responseDetails") or "").strip()
        if "DISTINCT LANGUAGES" in details.upper():
            # MyMemory detected the text is already in the target language and
            # refuses to "translate" it — report that so definitions take over.
            result["detected"] = target
            result["translation"] = text
            return result
        raise ProviderError(shorten(details, 60) if details else "status %s" % status)
    payload = data.get("responseData") or {}
    result["translation"] = str(payload.get("translatedText") or "").strip()
    detected = payload.get("detectedLanguage")
    result["detected"] = detected.lower() if isinstance(detected, str) and detected \
        else (source if source != "auto" else "?")
    return result


PROVIDERS = {
    "google": provider_google,
    "clients5": provider_clients5,
    "mymemory": provider_mymemory,
}


def wiktionary_definitions(term, lang):
    """Definitions of TERM from the LANG-language section of English Wiktionary."""
    candidates = [term] if term == term.lower() else [term, term.lower()]
    data = None
    for candidate in candidates:
        try:
            data = http_get_json(WIKTIONARY_URL + urllib.parse.quote(candidate, safe=""), TOOL_UA)
            break
        except ProviderError as exc:
            if exc.status != 404:
                raise
    if not isinstance(data, dict):
        return []

    groups = []
    for entry in data.get(lang_base(lang)) or []:
        if not isinstance(entry, dict):
            continue
        pos = str(entry.get("partOfSpeech") or "").lower()
        defs = []
        for d in entry.get("definitions") or []:
            if not isinstance(d, dict):
                continue
            definition = clean_html(str(d.get("definition") or ""))
            if not definition:
                continue
            examples = d.get("parsedExamples") or []
            example = clean_html(str(examples[0].get("example") or "")) \
                if examples and isinstance(examples[0], dict) else ""
            defs.append((definition, example))
        if defs:
            groups.append((pos, defs))
    return groups


# --------------------------------------------------------------- cache & cooldown

def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, APP_NAME)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def save_json(path, data):
    """Best-effort atomic write; the cache is never worth failing a lookup over."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


class Cache:
    def __init__(self, enabled):
        self.enabled = enabled
        self.path = os.path.join(cache_dir(), "cache.json")
        self.data = load_json(self.path, {}) if enabled else {}

    def get(self, key):
        entry = self.data.get(key)
        if isinstance(entry, dict) and time.time() - entry.get("ts", 0) < CACHE_TTL:
            return entry.get("result")
        return None

    def put(self, key, result):
        if not self.enabled:
            return
        now = time.time()
        self.data = {k: v for k, v in self.data.items()
                     if isinstance(v, dict) and now - v.get("ts", 0) < CACHE_TTL}
        self.data[key] = {"ts": now, "result": result}
        if len(self.data) > CACHE_MAX:
            oldest = sorted(self.data, key=lambda k: self.data[k]["ts"])[: len(self.data) - CACHE_MAX]
            for k in oldest:
                del self.data[k]
        save_json(self.path, self.data)


class Cooldown:
    def __init__(self):
        self.path = os.path.join(cache_dir(), "cooldown.json")
        self.data = load_json(self.path, {})

    def remaining(self, name):
        return max(0, self.data.get(name, 0) - time.time())

    def start(self, name):
        self.data[name] = time.time() + COOLDOWN_SECONDS
        save_json(self.path, self.data)


# -------------------------------------------------------------------------- lookup

def same_language(detected, target):
    return detected == target or lang_base(detected) == lang_base(target)


def lookup(text, source, target, providers, use_cache, log):
    """Run the provider chain, supplement with Wiktionary, cache the outcome."""
    cache = Cache(use_cache)
    key = "%s|%s|%s" % (source, target, text.lower())
    hit = cache.get(key)
    if hit:
        log("cache hit")
        return hit

    cooldown = Cooldown()
    errors = []
    result = None
    for name in providers:
        left = cooldown.remaining(name)
        if left:
            errors.append("%s: cooling down (%d min left)" % (name, left // 60 + 1))
            continue
        try:
            log("trying %s" % name)
            result = PROVIDERS[name](text, source, target)
            result["provider"] = name
            break
        except ProviderError as exc:
            log("%s failed: %s" % (name, exc))
            errors.append("%s: %s" % (name, exc))
            if exc.status in (429, 403):
                cooldown.start(name)
    if result is None:
        raise WlDefineError("lookup failed — " + " · ".join(errors))

    detected = result["detected"]
    single_word = " " not in text
    try:
        if same_language(detected, target) and not result["definitions"]:
            log("no definitions from %s, trying wiktionary" % result["provider"])
            result["definitions"] = wiktionary_definitions(text, target)
        elif not same_language(detected, target) and single_word \
                and not result["alternatives"] and detected != "?":
            log("no alternatives from %s, trying wiktionary" % result["provider"])
            glosses = []
            for pos, defs in wiktionary_definitions(text, detected):
                glosses.append((pos, [shorten(d, 50) for d, _ in defs[:3]]))
            result["alternatives"] = glosses[:2]
    except ProviderError as exc:
        log("wiktionary failed: %s" % exc)

    if result["translation"] or result["definitions"]:
        cache.put(key, result)
    return result


# ----------------------------------------------------------------------- rendering

def esc(text):
    """Escape for Pango markup (notify-send bodies)."""
    return html.escape(text, quote=False)


def pick_definitions(groups, max_defs):
    """Round-robin across parts of speech so a noun/verb word shows both."""
    picked = {}  # pos -> [(definition, example), ...], insertion ordered
    total = 0
    depth = 0
    while total < max_defs:
        added = False
        for pos, defs in groups:
            if depth < len(defs) and total < max_defs:
                picked.setdefault(pos, []).append(defs[depth])
                total += 1
                added = True
        if not added:
            break
        depth += 1
    return picked


def render_definitions(word, result, max_defs, with_examples, markup):
    summary = shorten(word)
    lines = []
    number = 1
    for pos, defs in pick_definitions(result["definitions"], max_defs).items():
        if pos:
            lines.append("<i>%s</i>" % esc(pos) if markup else "[%s]" % pos)
        for definition, example in defs:
            lines.append("%d. %s" % (number, esc(definition) if markup else definition))
            if with_examples and example:
                quoted = "“%s”" % example
                lines.append(("   <i>%s</i>" % esc(quoted)) if markup else "   " + quoted)
            number += 1
    return summary, "\n".join(lines)


def render_translation(text, result, target, markup):
    src = lang_name(result["detected"])
    translation = result["translation"]
    single_word = " " not in text

    if single_word:
        summary = "%s  ·  %s" % (shorten(text), src)
    else:
        summary = "%s → %s" % (src, lang_name(target))

    lines = [("<b>%s</b>" % esc(translation)) if markup else translation]

    if single_word:
        for pos, alts in result["alternatives"]:
            extra = [a for a in alts if a.lower() != translation.lower()][:4]
            if extra:
                label = ("<i>%s:</i>" % esc(pos)) if markup else "%s:" % pos
                joined = ", ".join(esc(a) if markup else a for a in extra)
                lines.append("%s %s" % (label, joined))
    return summary, "\n".join(lines)


# --------------------------------------------------------------------- notifying

def id_file_path():
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return os.path.join(base, ID_FILE)


def read_previous_id(path):
    try:
        with open(path) as fh:
            value = fh.read().strip()
    except OSError:
        return 0
    return int(value) if value.isdigit() else 0


def close_notification(notification_id):
    """Ask the daemon to close a notification via org.freedesktop.Notifications.

    Uses whichever D-Bus CLI is around (gdbus from glib, busctl from systemd,
    dbus-send from dbus). Returns False when none is available. Closing an id
    the daemon no longer knows is a harmless no-op.
    """
    if shutil.which("gdbus"):
        cmd = ["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
               "--object-path", "/org/freedesktop/Notifications",
               "--method", "org.freedesktop.Notifications.CloseNotification",
               str(notification_id)]
    elif shutil.which("busctl"):
        cmd = ["busctl", "--user", "call", "org.freedesktop.Notifications",
               "/org/freedesktop/Notifications", "org.freedesktop.Notifications",
               "CloseNotification", "u", str(notification_id)]
    elif shutil.which("dbus-send"):
        cmd = ["dbus-send", "--session", "--type=method_call",
               "--dest=org.freedesktop.Notifications", "/org/freedesktop/Notifications",
               "org.freedesktop.Notifications.CloseNotification",
               "uint32:%d" % notification_id]
    else:
        return False
    try:
        subprocess.run(cmd, capture_output=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return True


def notify_send(summary, body, timeout_ms, urgency, stack=False):
    """notify-send, dismissing the previous wl-define notification first.

    Deliberately not `notify-send -r`: replacing a notification that has already
    expired is treated by several daemons as an update to nothing, so no popup
    appears — which looks like "it only works the first time". Closing the old
    one explicitly and sending a fresh notification works everywhere.
    """
    if shutil.which("notify-send") is None:
        raise WlDefineError("notify-send not found — install libnotify")
    path = id_file_path()
    previous = read_previous_id(path)
    if previous and not stack:
        close_notification(previous)

    cmd = ["notify-send", "-a", APP_NAME, "-i", ICON, "-u", urgency,
           "-t", str(timeout_ms), "-p", "--", summary, body]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Older libnotify without -p: fall back to a plain notification.
        subprocess.run(["notify-send", "-a", APP_NAME, "-i", ICON, "-u", urgency,
                        "-t", str(timeout_ms), "--", summary, body])
        return
    new_id = proc.stdout.strip()
    if new_id.isdigit():
        try:
            with open(path, "w") as fh:
                fh.write(new_id)
        except OSError:
            pass


def hyprctl_notify(summary, body, timeout_ms, urgency):
    """Hyprland's built-in single-line notification."""
    if shutil.which("hyprctl") is None:
        raise WlDefineError("hyprctl not found")
    icon, color = ("3", "rgb(f38ba8)") if urgency == "critical" else ("1", "rgb(89b4fa)")
    flat = " — ".join(part.strip() for part in [summary] + body.split("\n") if part.strip())
    subprocess.run(["hyprctl", "notify", icon, str(timeout_ms), color, flat])


def emit(backend, summary, body, timeout_ms, urgency="normal", stack=False):
    if backend == "notify":
        notify_send(summary, body, timeout_ms, urgency, stack)
    elif backend == "hyprctl":
        hyprctl_notify(summary, body, timeout_ms, urgency)
    else:
        print(summary)
        if body:
            print(body)


def choose_backend(requested):
    if requested != "auto":
        return requested
    if shutil.which("notify-send"):
        return "notify"
    if shutil.which("hyprctl"):
        return "hyprctl"
    return "stdout"


# -------------------------------------------------------------------------- main

def parse_args(argv):
    p = argparse.ArgumentParser(prog=APP_NAME, description=__doc__.split("\n\n")[0])
    p.add_argument("-c", "--clipboard", action="store_true",
                   help="read the clipboard instead of the primary selection")
    p.add_argument("-t", "--text", metavar="TEXT",
                   help="look up TEXT instead of reading a selection")
    p.add_argument("-s", "--source", default="auto", metavar="LANG",
                   help="source language code (default: auto-detect)")
    p.add_argument("-T", "--target", default="en", metavar="LANG",
                   help="target language code (default: en)")
    p.add_argument("-b", "--backend", default="auto",
                   choices=["auto", "notify", "hyprctl", "stdout"],
                   help="how to show the result (default: auto)")
    p.add_argument("-n", "--max-defs", type=int, default=3, metavar="N",
                   help="maximum number of definitions to show (default: 3)")
    p.add_argument("-e", "--examples", action="store_true",
                   help="include an example sentence under each definition")
    p.add_argument("-p", "--providers", default=DEFAULT_PROVIDERS, metavar="LIST",
                   help="comma-separated provider order, from %s (default: %s); "
                        "wiktionary is always used as the definitions fallback"
                        % ("/".join(PROVIDERS), DEFAULT_PROVIDERS))
    p.add_argument("--no-cache", action="store_true",
                   help="bypass the on-disk result cache")
    p.add_argument("--timeout", type=int, default=10000, metavar="MS",
                   help="notification timeout in milliseconds (default: 10000)")
    p.add_argument("--stack", action="store_true",
                   help="let notifications pile up instead of dismissing the previous one")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="log provider attempts and failures to stderr")
    p.add_argument("--version", action="version", version="%s %s" % (APP_NAME, VERSION))
    args = p.parse_args(argv)

    args.providers = [name.strip() for name in args.providers.split(",") if name.strip()]
    unknown = [name for name in args.providers if name not in PROVIDERS]
    if unknown or not args.providers:
        p.error("unknown provider(s): %s (choose from %s)"
                % (", ".join(unknown) or "none given", ", ".join(PROVIDERS)))
    return args


def main(argv=None):
    args = parse_args(argv)
    backend = choose_backend(args.backend)
    markup = backend == "notify"

    def log(message):
        if args.verbose:
            print("%s: %s" % (APP_NAME, message), file=sys.stderr)

    def say(summary, body, urgency="normal"):
        """Plain-text message (escaped for Pango when going through notify-send)."""
        emit(backend, summary, esc(body) if markup else body, args.timeout, urgency, args.stack)

    try:
        raw = args.text if args.text is not None else read_selection(args.clipboard)
        text = normalize(raw)
        if not text:
            say(APP_NAME, "Nothing selected", urgency="low")
            return 1

        result = lookup(text, args.source, args.target, args.providers,
                        not args.no_cache, log)
        detected = result["detected"]
        log("answered by %s (detected %s)" % (result.get("provider", "cache"), detected))

        if same_language(detected, args.target) and result["definitions"]:
            summary, body = render_definitions(text, result, args.max_defs, args.examples, markup)
        elif same_language(detected, args.target):
            say(shorten(text), "No definition found", urgency="low")
            return 1
        elif not result["translation"] or (
            result["translation"].lower() == text.lower() and not result["alternatives"]
        ):
            where = "" if detected in ("?", "") else " (detected %s)" % lang_name(detected)
            say(shorten(text), "No translation or definition found" + where, urgency="low")
            return 1
        else:
            summary, body = render_translation(text, result, args.target, markup)

        emit(backend, summary, body, args.timeout, stack=args.stack)  # already markup-aware
        return 0

    except WlDefineError as exc:
        say(APP_NAME, str(exc), urgency="critical")
        return 1


if __name__ == "__main__":
    sys.exit(main())
