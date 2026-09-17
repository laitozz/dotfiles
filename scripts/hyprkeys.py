#!/usr/bin/env python3
"""
hyprkeys — extract every Hyprland keybind and visualize it.

    hyprkeys list                 coloured table in the terminal
    hyprkeys rofi                 command palette: pick a bind → it is dispatched
    hyprkeys html --open          interactive keyboard map in your browser
    hyprkeys md                   markdown cheatsheet
    hyprkeys json                 machine-readable dump
    hyprkeys overlaps             chords that trigger more than one dispatcher

Bind sources (--source):
    auto      read the config (Lua or hyprlang, see below) and, when Hyprland is
              running, merge in `hyprctl binds -j` (descriptions, Lua callback ids)
    hyprctl   only the live table. NOTE: for Lua configs Hyprland reports every
              bind as dispatcher "__lua" with an opaque number — useless alone.
    config    only the config files.

Config formats:
    hyprland.lua   (Hyprland >= 0.55) the config is *executed* by a Lua runtime
                   (lua5.4 / lua / luajit in PATH, or the `lupa` Python module)
                   with a fake `hl` that records every hl.bind() instead of
                   registering it. `require`, string concatenation, loops,
                   hl.define_submap, hl.unbind and {description=...} all work.
                   Lua-function dispatchers are dry-run with hl.dispatch /
                   hl.exec_cmd / os.execute / io.popen sandboxed to recording,
                   and their source snippet is captured.
    hyprland.conf  (<= 0.54) parsed: `source =`, $variables, submaps, bind
                   flags, bindd descriptions, unbind, comments → descriptions.

Only the Python standard library is required. rofi/fuzzel/wofi are optional.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

MOD_ORDER = ["SUPER", "CTRL", "ALT", "SHIFT", "CAPS", "MOD2", "MOD3", "MOD5"]
MOD_LABEL = {"SUPER": "Super", "CTRL": "Ctrl", "ALT": "Alt", "SHIFT": "Shift",
             "CAPS": "Caps", "MOD2": "Mod2", "MOD3": "Mod3", "MOD5": "Mod5"}
# hyprctl modmask bits
MOD_BITS = [(1, "SHIFT"), (2, "CAPS"), (4, "CTRL"), (8, "ALT"),
            (16, "MOD2"), (32, "MOD3"), (64, "SUPER"), (128, "MOD5")]

FLAG_NAMES = {
    "l": "locked", "r": "release", "o": "long-press", "e": "repeat",
    "n": "non-consuming", "m": "mouse", "t": "transparent", "i": "ignore-mods",
    "s": "separate", "d": "described", "p": "bypass-inhibitor", "c": "click",
    "g": "drag",
}


@dataclass
class Bind:
    mods: list[str]
    key: str
    dispatcher: str
    arg: str = ""
    flags: str = ""
    submap: str = ""
    description: str = ""
    group: str = ""
    source: str = ""
    mouse: bool = False
    expr: str = ""      # Lua expression that re-creates the dispatcher (hl.dsp.exec_cmd("firefox"))
    lua_id: str = ""    # Lua registry id reported by hyprctl for __lua binds
    code: str = ""      # source snippet of a Lua-function dispatcher

    # ---- derived helpers -------------------------------------------------- #
    @property
    def chord(self) -> str:
        parts = [MOD_LABEL.get(m, m) for m in sorted(self.mods, key=MOD_ORDER.index)]
        parts.append(pretty_key(self.key))
        return " + ".join(parts)

    @property
    def layer(self) -> str:
        """Modifier combination as a stable string, e.g. 'SUPER+SHIFT' or ''."""
        return "+".join(sorted(self.mods, key=MOD_ORDER.index))

    @property
    def action(self) -> str:
        return f"{self.dispatcher} {self.arg}".strip()

    @property
    def category(self) -> str:
        return categorize(self)

    def identity(self) -> tuple:
        return (self.submap, self.layer, self.key.lower())

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(chord=self.chord, layer=self.layer, action=self.action,
                 category=self.category, key_label=pretty_key(self.key))
        return d


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #

def parse_mods(text: str) -> list[str]:
    """Hyprland matches modifier names as case-insensitive substrings, so
    'SUPER SHIFT', 'SUPER_SHIFT' and 'SUPERSHIFT' are all the same thing."""
    t = text.upper()
    mods = []
    if "SHIFT" in t:
        mods.append("SHIFT")
    if "CAPS" in t:
        mods.append("CAPS")
    if "CTRL" in t or "CONTROL" in t:
        mods.append("CTRL")
    if "ALT" in t:
        mods.append("ALT")
    if "MOD2" in t:
        mods.append("MOD2")
    if "MOD3" in t:
        mods.append("MOD3")
    if "SUPER" in t or "WIN" in t or "LOGO" in t or "MOD4" in t:
        mods.append("SUPER")
    if "MOD5" in t:
        mods.append("MOD5")
    return sorted(set(mods), key=MOD_ORDER.index)


def mods_from_mask(mask: int) -> list[str]:
    return sorted([name for bit, name in MOD_BITS if mask & bit], key=MOD_ORDER.index)


KEY_PRETTY = {
    "return": "Enter", "backspace": "Backspace", "space": "Space", "escape": "Esc",
    "tab": "Tab", "grave": "`", "minus": "-", "equal": "=", "bracketleft": "[",
    "bracketright": "]", "backslash": "\\", "semicolon": ";", "apostrophe": "'",
    "comma": ",", "period": ".", "slash": "/", "less": "<", "plus": "+",
    "section": "§", "acute": "´", "aring": "å", "adiaeresis": "ä",
    "odiaeresis": "ö", "dead_diaeresis": "¨", "prior": "PgUp", "next": "PgDn",
    "up": "↑", "down": "↓", "left": "←", "right": "→", "print": "PrtSc",
    "delete": "Del", "insert": "Ins", "home": "Home", "end": "End",
    "mouse:272": "LMB", "mouse:273": "RMB", "mouse:274": "MMB",
    "mouse:275": "Mouse4", "mouse:276": "Mouse5",
    "mouse_up": "Scroll↑", "mouse_down": "Scroll↓",
    "xf86audioraisevolume": "Vol+", "xf86audiolowervolume": "Vol−",
    "xf86audiomute": "Mute", "xf86audiomicmute": "MicMute",
    "xf86audioplay": "Play/Pause", "xf86audiopause": "Pause",
    "xf86audionext": "Next track", "xf86audioprev": "Prev track",
    "xf86monbrightnessup": "Bright+", "xf86monbrightnessdown": "Bright−",
    "xf86calculator": "Calc", "xf86explorer": "Explorer", "xf86mail": "Mail",
    "xf86homepage": "Home page", "xf86search": "Search", "xf86tools": "Tools",
    "xf86poweroff": "Power", "xf86sleep": "Sleep", "xf86wlan": "WLAN",
    "xf86display": "Display", "xf86keyboardbrightnessup": "KbdLight+",
    "xf86keyboardbrightnessdown": "KbdLight−", "catchall": "(any key)",
}


def pretty_key(key: str) -> str:
    k = key.lower()
    if k in KEY_PRETTY:
        return KEY_PRETTY[k]
    if k.startswith("kp_"):
        return "Num " + key[3:]
    if k.startswith("code:"):
        return f"key#{key[5:]}"
    if len(key) == 1:
        return key.upper()
    return key


EXEC_MEDIA_RE = re.compile(
    r"\b(wpctl|pamixer|pactl|amixer|playerctl|brightnessctl|light|ddcutil|swayosd)\b")
WINDOW_DISPATCHERS = {
    "killactive", "closewindow", "togglefloating", "setfloating", "settiled",
    "fullscreen", "fullscreenstate", "fakefullscreen", "pin", "movewindow",
    "resizewindow", "movefocus", "swapwindow", "cyclenext", "focuswindow",
    "centerwindow", "resizeactive", "moveactive", "resizewindowpixel",
    "movewindowpixel", "togglesplit", "swapsplit", "pseudo", "alterzorder",
    "togglegroup", "changegroupactive", "moveintogroup", "moveoutofgroup",
    "lockgroups", "lockactivegroup", "movewindoworgroup", "movegroupwindow",
    "denywindowfromgroup", "setignoregrouplock", "bringactivetotop",
    "focusurgentorlast", "focuscurrentorlast", "togglespecialworkspace",
    "toggleopaque", "tagwindow", "swapnext", "layoutmsg", "forcerendererreload",
}
WORKSPACE_DISPATCHERS = {
    "workspace", "movetoworkspace", "movetoworkspacesilent", "renameworkspace",
    "focusworkspaceoncurrentmonitor", "movecurrentworkspacetomonitor",
    "moveworkspacetomonitor", "swapactiveworkspaces", "focusmonitor",
    "togglespecialworkspace",
}


def categorize(b: Bind) -> str:
    d = b.dispatcher.lower()
    is_exec = d in ("exec", "execr", "exec_cmd", "exec_raw", "call")
    if b.key.lower().startswith("xf86") or (is_exec and EXEC_MEDIA_RE.search(b.arg)):
        return "media"
    if d == "lua":
        return "script"
    if is_exec or d in ("global", "sendshortcut", "pass", "send_shortcut", "send_key_state"):
        return "launch"
    if d == "submap":
        return "submap"
    if d in WORKSPACE_DISPATCHERS or d.startswith("workspace.") or (d == "focus" and "workspace" in b.arg):
        return "workspace"
    if d in WINDOW_DISPATCHERS or b.mouse or d.startswith(("window.", "group.")) or d == "focus":
        return "window"
    return "system"


# --------------------------------------------------------------------------- #
# Source 1: hyprctl
# --------------------------------------------------------------------------- #

def hyprland_running() -> bool:
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) and shutil.which("hyprctl") is not None


def binds_from_hyprctl() -> list[Bind]:
    out = subprocess.run(["hyprctl", "binds", "-j"], check=True, capture_output=True, text=True).stdout
    binds = []
    for e in json.loads(out):
        key = e.get("key") or ""
        if not key and e.get("keycode"):
            key = f"code:{e['keycode']}"
        if e.get("catch_all"):
            key = "catchall"
        flags = "".join(c for c, cond in (
            ("l", e.get("locked")), ("r", e.get("release")), ("e", e.get("repeat")),
            ("n", e.get("non_consuming")), ("m", e.get("mouse")), ("o", e.get("longPress")),
        ) if cond)
        binds.append(Bind(
            mods=mods_from_mask(int(e.get("modmask", 0))),
            key=key,
            dispatcher=e.get("dispatcher", ""),
            arg=e.get("arg", ""),
            flags=flags,
            submap=e.get("submap", "") or "",
            description=e.get("description", "") or "",
            source="hyprctl",
            mouse=bool(e.get("mouse")),
        ))
    return binds


# --------------------------------------------------------------------------- #
# Source 2: hyprlang config parser
# --------------------------------------------------------------------------- #

BIND_RE = re.compile(r"^(bind[a-z]*|unbind)$")
VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
GROUP_COMMENT_RE = re.compile(r"^#{1,}\s*[-=#~*]{2,}\s*(.*?)\s*[-=#~*]*\s*$|^##+\s*(.+?)\s*$")


class ConfigParser:
    def __init__(self):
        self.vars: dict[str, str] = {}
        self.binds: list[Bind] = []
        self.warnings: list[str] = []
        self.files: list[str] = []
        self._seen: set[str] = set()

    # -- public ------------------------------------------------------------- #
    def parse(self, path: Path) -> list[Bind]:
        self._parse_file(path.expanduser().resolve())
        # late variable resolution (hyprlang allows forward references)
        for b in self.binds:
            b.key = self._subst(b.key)
            b.arg = self._subst(b.arg)
            b.dispatcher = self._subst(b.dispatcher)
        return self.binds

    # -- internals ---------------------------------------------------------- #
    def _subst(self, text: str) -> str:
        def rep(m):
            return self.vars.get(m.group(1), m.group(0))
        prev = None
        for _ in range(10):  # variables may reference variables
            if prev == text:
                break
            prev, text = text, VAR_RE.sub(rep, text)
        return text

    @staticmethod
    def _split_comment(line: str) -> tuple[str, str]:
        """Split at the first '#' that is not part of '##' (hyprlang escape)."""
        i, n = 0, len(line)
        while i < n:
            if line[i] == "#":
                if i + 1 < n and line[i + 1] == "#":
                    i += 2
                    continue
                return line[:i], line[i + 1:].strip()
            i += 1
        return line, ""

    def _parse_file(self, path: Path):
        key = str(path)
        if key in self._seen:
            return
        self._seen.add(key)
        if not path.is_file():
            self.warnings.append(f"missing file: {path}")
            return
        self.files.append(key)
        submap = ""
        group = ""
        pending_comments: list[str] = []
        pending_is_group = False
        comment_after_blank = True  # file start counts as "after a blank line"
        prev_blank = True

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        def is_bind_line(i: int) -> bool:
            if i >= len(lines):
                return False
            s = lines[i].strip()
            return bool(BIND_RE.match(s.partition("=")[0].strip())) if "=" in s else False

        for lineno, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                # a comment block followed by a blank line is a section header
                if pending_comments:
                    group = " ".join(pending_comments)
                pending_comments, pending_is_group = [], False
                prev_blank = True
                continue
            if line.startswith("#"):
                m = GROUP_COMMENT_RE.match(line)
                if m:
                    title = (m.group(1) or m.group(2) or "").strip()
                    if title:
                        group = title
                    pending_comments, pending_is_group = [], True
                    prev_blank = False
                    continue
                if not pending_comments:
                    comment_after_blank = prev_blank
                pending_comments.append(line.lstrip("#").strip())
                prev_blank = False
                continue
            prev_blank = False

            code, trailing = self._split_comment(line)
            code = code.strip().replace("##", "#")
            if code in ("}",) or code.endswith("{"):
                pending_comments = []
                continue
            if "=" not in code:
                pending_comments = []
                continue
            k, _, v = code.partition("=")
            k, v = k.strip(), v.strip()

            if k.startswith("$"):
                self.vars[k[1:]] = self._subst(v)
            elif k == "source":
                for target in self._expand_source(v, path.parent):
                    self._parse_file(target)
            elif k == "submap":
                submap = "" if v.lower() == "reset" else v
            elif BIND_RE.match(k):
                desc_from_comments = ""
                if trailing:
                    desc_from_comments = trailing
                if pending_comments and not pending_is_group:
                    # a stand-alone comment heading a run of binds is a group
                    # label; a comment glued above one bind is its description
                    if comment_after_blank and is_bind_line(lineno):  # next line
                        group = " ".join(pending_comments)
                    elif not desc_from_comments:
                        desc_from_comments = " ".join(pending_comments)
                self._handle_bind(k, self._subst(v), submap, group, desc_from_comments,
                                  f"{path}:{lineno}")
            pending_comments, pending_is_group = [], False

    def _expand_source(self, value: str, base: Path) -> list[Path]:
        value = os.path.expandvars(os.path.expanduser(self._subst(value)))
        p = Path(value)
        if not p.is_absolute():
            p = base / p
        matches = sorted(glob.glob(str(p)))
        if not matches:
            self.warnings.append(f"source pattern matched nothing: {value}")
        return [Path(m) for m in matches]

    def _handle_bind(self, keyword: str, value: str, submap: str, group: str,
                     comment_desc: str, source: str):
        if keyword == "unbind":
            parts = [p.strip() for p in value.split(",", 1)]
            if len(parts) == 2:
                mods, key = parse_mods(parts[0]), parts[1].lower()
                before = len(self.binds)
                self.binds = [b for b in self.binds
                              if not (b.submap == submap and b.mods == mods and b.key.lower() == key)]
                if len(self.binds) == before:
                    self.warnings.append(f"{source}: unbind matched nothing ({value})")
            return

        flags = keyword[4:]
        described = "d" in flags
        n_fixed = 4 if described else 3  # mods, key, [desc], dispatcher
        parts = [p.strip() for p in value.split(",", n_fixed)]
        if len(parts) < n_fixed:
            self.warnings.append(f"{source}: could not parse bind '{value}'")
            return
        mods_s, key = parts[0], parts[1]
        desc = parts[2] if described else ""
        dispatcher = parts[3] if described else parts[2]
        arg = parts[n_fixed] if len(parts) > n_fixed else ""
        self.binds.append(Bind(
            mods=parse_mods(mods_s), key=key, dispatcher=dispatcher, arg=arg,
            flags=flags.replace("d", ""), submap=submap,
            description=desc or comment_desc, group=group, source=source,
            mouse="m" in flags,
        ))


# --------------------------------------------------------------------------- #
# Source 3: Lua config (Hyprland >= 0.55) — executed with a recording `hl` stub
# --------------------------------------------------------------------------- #

LUA_HARNESS = r"""
-- hyprkeys harness: runs a Hyprland Lua config with a fake `hl` that records binds.
local CONFIG = HYPRKEYS_CONFIG or (arg and arg[1])
local OUT = HYPRKEYS_OUT or (arg and arg[2])
local DRY_RUN = HYPRKEYS_DRY_RUN
if DRY_RUN == nil then DRY_RUN = not (arg and arg[3] == "0") end
local MAX_CODE_LINES = 40

local records, warnings = {}, {}
local submap_stack = { "" }
local dry = nil      -- list collecting what a bind function dispatches while dry-running
local order = 0
local DISPATCH_MT, PROXY_MT

local function warn(msg) warnings[#warnings + 1] = tostring(msg) end
local function is_dispatcher(v) return type(v) == "table" and getmetatable(v) == DISPATCH_MT end
local function is_proxy(v) return type(v) == "table" and getmetatable(v) == PROXY_MT end

-- Lua-source-ish representation of a value (valid Lua for plain data)
local function repr(v, depth)
    depth = depth or 0
    local t = type(v)
    if t == "string" then
        return (string.format("%q", v):gsub("\\\n", "\\n"))
    elseif t == "number" or t == "boolean" or t == "nil" then
        return tostring(v)
    elseif t == "function" then
        local i = debug.getinfo(v, "S")
        return string.format("<function %s:%d>", i.short_src, i.linedefined)
    elseif t == "table" then
        if is_dispatcher(v) then return rawget(v, "__expr") end
        if is_proxy(v) then return rawget(v, "__path") end
        if depth > 5 then return "{...}" end
        local parts, n = {}, #v
        for i = 1, n do parts[#parts + 1] = repr(v[i], depth + 1) end
        local keys = {}
        for k in pairs(v) do
            if not (type(k) == "number" and k >= 1 and k <= n and k % 1 == 0) then keys[#keys + 1] = k end
        end
        table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
        for _, k in ipairs(keys) do
            local ks = (type(k) == "string" and k:match("^[%a_][%w_]*$")) and k or ("[" .. repr(k, depth + 1) .. "]")
            parts[#parts + 1] = ks .. " = " .. repr(v[k], depth + 1)
        end
        return "{ " .. table.concat(parts, ", ") .. " }"
    end
    return "<" .. t .. ">"
end

-- describe something passed to hl.dispatch / used as a dispatcher
local function describe(d)
    if is_dispatcher(d) then return rawget(d, "__expr") end
    return repr(d)
end

-- generic proxy: any hl.* we don't model. Indexable, callable, comparable, harmless.
local function make_proxy(path, dsp)
    return setmetatable({ __path = path, __dsp = dsp or false }, PROXY_MT)
end
local function empty_iter() return nil end
PROXY_MT = {
    __index = function(self, k)
        if type(k) ~= "string" then return nil end
        return make_proxy(rawget(self, "__path") .. "." .. k, rawget(self, "__dsp"))
    end,
    __call = function(self, ...)
        local path = rawget(self, "__path")
        if rawget(self, "__dsp") then
            local n, args, reprs = select("#", ...), { ... }, {}
            for i = 1, n do reprs[i] = repr(args[i]) end
            return setmetatable({ __path = path, __args = args, __nargs = n,
                                  __expr = path .. "(" .. table.concat(reprs, ", ") .. ")" }, DISPATCH_MT)
        end
        -- while dry-running a bind function, record direct hl.* actions (hl.config, hl.notification.create, ...)
        -- but not queries (hl.get_*, hl.is_*) or method calls on their results
        if dry and path:match("^hl%.[%w_]+$") and not path:match("^hl%.get_") and not path:match("^hl%.is_") then
            local n, reprs = select("#", ...), {}
            for i = 1, n do reprs[i] = repr((select(i, ...))) end
            dry[#dry + 1] = path .. "(" .. table.concat(reprs, ", ") .. ")"
        end
        return make_proxy(path .. "()")
    end,
    __tostring = function(self) return "<" .. rawget(self, "__path") .. ">" end,
    __concat = function(a, b) return tostring(a) .. tostring(b) end,
    __len = function() return 0 end,
    __pairs = function() return empty_iter, nil, nil end,
    __lt = function() return false end,
    __le = function() return false end,
    __unm = function() return 0 end,
    __add = function() return 0 end, __sub = function() return 0 end,
    __mul = function() return 0 end, __div = function() return 0 end,
}
DISPATCH_MT = {
    __tostring = function(self) return rawget(self, "__expr") end,
    __concat = function(a, b) return tostring(a) .. tostring(b) end,
    __call = function(self) if dry then dry[#dry + 1] = rawget(self, "__expr") end return true end,
}

local function read_code(source, first, last)
    if type(source) ~= "string" or source:sub(1, 1) ~= "@" then return nil end
    local f = io.open(source:sub(2), "r")
    if not f then return nil end
    local out, i = {}, 0
    for line in f:lines() do
        i = i + 1
        if i >= first and i <= last then out[#out + 1] = line end
        if i > last then break end
    end
    f:close()
    if #out > MAX_CODE_LINES then
        local cut = {}
        for j = 1, MAX_CODE_LINES do cut[j] = out[j] end
        cut[#cut + 1] = "-- … " .. (#out - MAX_CODE_LINES) .. " more lines"
        out = cut
    end
    -- strip common indentation
    local indent
    for _, l in ipairs(out) do
        if l:match("%S") then
            local ws = l:match("^(%s*)")
            if indent == nil or #ws < #indent then indent = ws end
        end
    end
    if indent and #indent > 0 then
        for j, l in ipairs(out) do out[j] = l:sub(1, #indent) == indent and l:sub(#indent + 1) or l end
    end
    return table.concat(out, "\n")
end

local function fake_file()
    local f = {}
    f.read = function() return nil end
    f.lines = function() return empty_iter end
    f.write = function() return f end
    f.close = function() return true end
    f.flush = function() return f end
    f.seek = function() return 0 end
    f.setvbuf = function() return true end
    return f
end

-- run a bind function with anything that could touch the system replaced by a recorder
local function dry_run(fn)
    local real = { execute = os.execute, popen = io.popen, remove = os.remove, rename = os.rename,
                   exit = os.exit, open = io.open, write = io.write, output = io.output }
    os.execute = function(cmd) dry[#dry + 1] = "os.execute(" .. repr(cmd) .. ")" return true, "exit", 0 end
    io.popen = function(cmd) dry[#dry + 1] = "io.popen(" .. repr(cmd) .. ")" return fake_file() end
    os.remove = function(p) dry[#dry + 1] = "os.remove(" .. repr(p) .. ")" return true end
    os.rename = function(a, b) dry[#dry + 1] = "os.rename(" .. repr(a) .. ", " .. repr(b) .. ")" return true end
    os.exit = function() dry[#dry + 1] = "os.exit()" error("os.exit() during dry run", 0) end
    io.open = function(name, mode)
        mode = mode or "r"
        if mode:find("[wa+]") then dry[#dry + 1] = "io.open(" .. repr(name) .. ", " .. repr(mode) .. ")" return fake_file() end
        return real.open(name, mode)
    end
    io.write = function() end
    io.output = function() return fake_file() end
    dry = {}
    local ok, err = pcall(fn)
    local result = dry
    dry = nil
    os.execute, io.popen, os.remove, os.rename, os.exit = real.execute, real.popen, real.remove, real.rename, real.exit
    io.open, io.write, io.output = real.open, real.write, real.output
    return result, (not ok) and tostring(err) or nil
end

local function norm_keys(keys)
    return tostring(keys):upper():gsub("%s+", "")
end

local hl = {}
hl.dsp = make_proxy("hl.dsp", true)

function hl.bind(keys, dispatcher, opts)
    order = order + 1
    local info = debug.getinfo(2, "Sl")
    local rec = {
        order = order, keys = tostring(keys), submap = submap_stack[#submap_stack],
        src = (info and info.short_src or "?") .. ":" .. (info and info.currentline or 0),
        opts = {}, dynamic = dry ~= nil,
    }
    if type(opts) == "table" then
        for k, v in pairs(opts) do
            if type(k) == "string" then rec.opts[k] = (type(v) == "table") and repr(v) or v end
        end
    end
    if is_dispatcher(dispatcher) then
        rec.kind = "dispatcher"
        rec.path = rawget(dispatcher, "__path")
        rec.expr = rawget(dispatcher, "__expr")
        rec.args = {}
        local args = rawget(dispatcher, "__args")
        for i = 1, rawget(dispatcher, "__nargs") do rec.args[i] = repr(args[i]) end
        if type(args[1]) == "string" then rec.arg1 = args[1] end
    elseif type(dispatcher) == "function" then
        rec.kind = "function"
        local fi = debug.getinfo(dispatcher, "S")
        rec.fn_src = fi.short_src .. ":" .. fi.linedefined
        rec.code = read_code(fi.source, fi.linedefined, fi.lastlinedefined)
        if DRY_RUN and not rec.dynamic then
            rec.dispatches, rec.dry_error = dry_run(dispatcher)
        end
    elseif type(dispatcher) == "string" then
        rec.kind = "string"
        rec.expr = repr(dispatcher)
        rec.arg1 = dispatcher
    else
        rec.kind = "other"
        rec.expr = repr(dispatcher)
    end
    records[#records + 1] = rec
    return make_proxy("hl.bind()")
end

function hl.unbind(keys)
    if type(keys) ~= "string" then warn("hl.unbind with a non-string argument is ignored") return end
    local nk, sm, kept, removed = norm_keys(keys), submap_stack[#submap_stack], {}, 0
    for _, r in ipairs(records) do
        if r.submap == sm and norm_keys(r.keys) == nk then removed = removed + 1 else kept[#kept + 1] = r end
    end
    records = kept
    if removed == 0 then warn("hl.unbind(" .. repr(keys) .. ") matched nothing") end
end

function hl.define_submap(name, ...)
    local fn
    for i = 1, select("#", ...) do
        local a = select(i, ...)
        if type(a) == "function" then fn = a end
    end
    if not fn then warn("hl.define_submap(" .. repr(name) .. ") without a function") return make_proxy("hl.define_submap()") end
    submap_stack[#submap_stack + 1] = tostring(name)
    local ok, err = pcall(fn)
    if not ok then warn("error inside submap " .. repr(name) .. ": " .. tostring(err)) end
    submap_stack[#submap_stack] = nil
    return make_proxy("hl.define_submap()")
end

function hl.dispatch(d) if dry then dry[#dry + 1] = describe(d) end return true end
function hl.exec_cmd(cmd) if dry then dry[#dry + 1] = "hl.dsp.exec_cmd(" .. repr(cmd) .. ")" end return 0 end
function hl.get_current_submap() return submap_stack[#submap_stack] end
function hl.is_key_down() return false end
setmetatable(hl, { __index = function(_, k) return make_proxy("hl." .. k) end })
_G.hl = hl

-- the config's own print() must not pollute stdout (hyprkeys json | jq ...)
local QUIET = HYPRKEYS_QUIET
if QUIET == nil then QUIET = arg and arg[4] == "1" end
print = function(...)
    if QUIET then return end
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    io.stderr:write(table.concat(parts, "\t"), "\n")
end

-- ---------- run the config
if not CONFIG then error("hyprkeys harness: no config path") end
local cfg_dir = CONFIG:match("^(.*)/[^/]*$") or "."
package.path = table.concat({
    cfg_dir .. "/?.lua", cfg_dir .. "/?/init.lua", cfg_dir .. "/lua/?.lua", cfg_dir .. "/lua/?/init.lua", package.path,
}, ";")
local chunk, lerr = loadfile(CONFIG)
if not chunk then
    warn("cannot load " .. CONFIG .. ": " .. tostring(lerr))
else
    local ok, err = pcall(chunk)
    if not ok then warn("config raised an error (binds registered before it are kept): " .. tostring(err)) end
end

-- ---------- minimal JSON encoder
local function json(v)
    local t = type(v)
    if t == "nil" then return "null"
    elseif t == "boolean" then return tostring(v)
    elseif t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if v % 1 == 0 then return string.format("%d", v) end
        return string.format("%.14g", v)
    elseif t == "string" then
        return '"' .. v:gsub('[%c"\\]', function(c)
            local m = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }
            return m[c] or string.format("\\u%04x", c:byte())
        end) .. '"'
    elseif t == "table" then
        if is_dispatcher(v) or is_proxy(v) then return json(repr(v)) end
        if #v > 0 or next(v) == nil then
            local out = {}
            for i = 1, #v do out[i] = json(v[i]) end
            return "[" .. table.concat(out, ",") .. "]"
        end
        local keys = {}
        for k in pairs(v) do keys[#keys + 1] = tostring(k) end
        table.sort(keys)
        local out = {}
        for _, k in ipairs(keys) do out[#out + 1] = json(k) .. ":" .. json(v[k]) end
        return "{" .. table.concat(out, ",") .. "}"
    end
    return json(tostring(v))
end

local payload = json({ binds = records, warnings = warnings, config = CONFIG })
if OUT then
    local f = assert(io.open(OUT, "w"))
    f:write(payload)
    f:close()
else
    io.write(payload)
end
"""

LUA_FLAG_SHORT = {
    "locked": "l", "release": "r", "repeating": "e", "long_press": "o", "non_consuming": "n",
    "mouse": "m", "transparent": "t", "ignore_mods": "i", "click": "c", "drag": "g",
    "submap_universal": "u", "auto_consuming": "a", "dont_inhibit": "p",
}


def find_lua_runtime(preferred: str | None = None) -> tuple[str, str] | None:
    """Returns ('bin', path) or ('lupa', '') or None."""
    if preferred:
        if preferred == "lupa":
            return ("lupa", "")
        return ("bin", preferred)
    for name in ("lua5.4", "lua", "luajit", "lua5.3", "lua5.5", "lua5.1"):
        p = shutil.which(name)
        if p:
            return ("bin", p)
    try:
        import lupa  # noqa: F401
        return ("lupa", "")
    except ImportError:
        return None


def run_lua_harness(cfg: Path, dry_run: bool, runtime: tuple[str, str], quiet: bool = False) -> dict:
    import tempfile
    cfg = cfg.resolve()
    with tempfile.TemporaryDirectory(prefix="hyprkeys-") as tmp:
        out = os.path.join(tmp, "binds.json")
        kind, path = runtime
        if kind == "bin":
            harness = os.path.join(tmp, "harness.lua")
            Path(harness).write_text(LUA_HARNESS, encoding="utf-8")
            res = subprocess.run([path, harness, str(cfg), out, "1" if dry_run else "0", "1" if quiet else "0"],
                                 cwd=cfg.parent, capture_output=True, text=True)
            if res.returncode != 0:
                sys.exit(f"hyprkeys: lua harness failed:\n{res.stderr.strip()}")
            if not quiet and (res.stderr.strip() or res.stdout.strip()):
                print((res.stderr + res.stdout).rstrip(), file=sys.stderr)  # the config's own output
        else:
            from lupa import LuaRuntime
            lua = LuaRuntime(unpack_returned_tuples=True)
            g = lua.globals()
            g.HYPRKEYS_CONFIG, g.HYPRKEYS_OUT, g.HYPRKEYS_DRY_RUN, g.HYPRKEYS_QUIET = str(cfg), out, dry_run, quiet
            cwd = os.getcwd()
            os.chdir(cfg.parent)
            try:
                lua.execute(LUA_HARNESS)
            finally:
                os.chdir(cwd)
        return json.loads(Path(out).read_text(encoding="utf-8"))


def parse_lua_keys(keys: str) -> tuple[list[str], str]:
    """'SUPER + SHIFT + F' → (['SUPER','SHIFT'], 'F'). Tolerates 'SUPER+F' and a literal '+' key."""
    tokens = [t.strip() for t in keys.split("+")]
    if len(tokens) > 1 and tokens[-1] == "":
        tokens = [t for t in tokens[:-1] if t] + ["plus"]
    tokens = [t for t in tokens if t] or ["?"]
    return parse_mods(" ".join(tokens[:-1])), tokens[-1]


def short_expr(expr: str) -> str:
    return expr[len("hl.dsp."):] if expr.startswith("hl.dsp.") else expr


def binds_from_lua(cfg: Path, dry_run: bool = True, runtime_pref: str | None = None,
                   quiet: bool = False) -> list[Bind]:
    runtime = find_lua_runtime(runtime_pref)
    if not runtime:
        sys.exit("hyprkeys: no Lua runtime found. Install lua5.4 (nix: pkgs.lua5_4) or `pip install lupa`.")
    data = run_lua_harness(cfg, dry_run, runtime, quiet)
    binds: list[Bind] = []
    dynamic = 0
    for r in data.get("binds", []):
        if r.get("dynamic"):
            dynamic += 1
            continue
        mods, key = parse_lua_keys(r["keys"])
        opts = r.get("opts") or {}
        if not isinstance(opts, dict):
            opts = {}
        flags = "".join(s for name, s in LUA_FLAG_SHORT.items() if opts.get(name))
        desc = str(opts.get("description") or opts.get("desc") or "")
        kind, expr, code = r.get("kind"), r.get("expr", "") or "", r.get("code") or ""
        if kind == "dispatcher":
            dispatcher = short_expr(r["path"])
            args = r.get("args") or []
            if "arg1" in r:
                arg = r["arg1"] + (", " + ", ".join(args[1:]) if len(args) > 1 else "")
            else:
                arg = ", ".join(args)
        elif kind == "function":
            dispatcher = "lua"
            disp = r.get("dispatches") or []
            if not isinstance(disp, list):
                disp = []
            arg = "; ".join(short_expr(d) for d in disp) or f"function @ {r.get('fn_src', '?')}"
            if r.get("dry_error") and not quiet:
                print(f"hyprkeys: note: dry run of {r.get('fn_src')} stopped early: {r['dry_error']}", file=sys.stderr)
        elif kind == "string":
            dispatcher, arg = "call", r.get("arg1", "")
        else:
            dispatcher, arg = "?", expr
        binds.append(Bind(mods=mods, key=key, dispatcher=dispatcher, arg=arg, flags=flags,
                          submap=r.get("submap", "") or "", description=desc, source=r.get("src", ""),
                          mouse=bool(opts.get("mouse")), expr=expr, code=code))
    if not quiet:
        for w in data.get("warnings", []):
            print(f"hyprkeys: warning: {w}", file=sys.stderr)
        if dynamic:
            print(f"hyprkeys: note: {dynamic} bind(s) are registered dynamically inside other binds and were skipped",
                  file=sys.stderr)
    return binds


# --------------------------------------------------------------------------- #
# Putting the sources together
# --------------------------------------------------------------------------- #

def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    lua = Path(xdg) / "hypr" / "hyprland.lua"
    return lua if lua.exists() else Path(xdg) / "hypr" / "hyprland.conf"


def merge_live(cfg_binds: list[Bind], live: list[Bind], lua: bool) -> list[Bind]:
    """Attach hyprctl facts (Lua callback ids, descriptions) to config binds, in registration order."""
    def key(b: Bind):
        return b.identity() if lua else (*b.identity(), b.dispatcher.lower())
    pool: dict[tuple, list[Bind]] = {}
    for b in live:
        pool.setdefault(key(b), []).append(b)
    for b in cfg_binds:
        cands = pool.get(key(b))
        if cands:
            lb = cands.pop(0)
            b.description = b.description or lb.description
            if lua and lb.dispatcher == "__lua":
                b.lua_id = lb.arg
            b.flags = b.flags or lb.flags
    return cfg_binds


def load_binds(source: str, config: Path | None, quiet: bool = False,
               dry_run: bool = True, lua_runtime: str | None = None) -> list[Bind]:
    cfg = (config or default_config_path()).expanduser()
    is_lua = cfg.suffix == ".lua"
    running = hyprland_running()

    if source == "hyprctl":
        if not running:
            sys.exit("hyprkeys: Hyprland is not running (HYPRLAND_INSTANCE_SIGNATURE unset)")
        return binds_from_hyprctl()

    if not cfg.exists():
        if source == "config" or not running:
            sys.exit(f"hyprkeys: config not found: {cfg}")
        return binds_from_hyprctl()

    if is_lua:
        parsed = binds_from_lua(cfg, dry_run, lua_runtime, quiet)
    else:
        parser = ConfigParser()
        parsed = parser.parse(cfg)
        if not quiet:
            for w in parser.warnings:
                print(f"hyprkeys: warning: {w}", file=sys.stderr)

    if source == "auto" and running:
        try:
            parsed = merge_live(parsed, binds_from_hyprctl(), is_lua)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            if not quiet:
                print(f"hyprkeys: warning: hyprctl failed ({e}), using config only", file=sys.stderr)
    return parsed


# --------------------------------------------------------------------------- #
# Output: terminal
# --------------------------------------------------------------------------- #

CAT_COLORS = {"launch": "32", "window": "34", "workspace": "35", "media": "33",
              "submap": "36", "script": "31", "system": "90"}


def sort_key(b: Bind):
    return (b.submap, MOD_ORDER.index(b.mods[0]) if b.mods else 99, len(b.mods), b.layer,
            pretty_key(b.key).lower())


def cmd_list(binds: list[Bind], args):
    color = sys.stdout.isatty() and not args.no_color

    def c(code, s):
        return f"\033[{code}m{s}\033[0m" if color else s

    width = max((len(b.chord) for b in binds), default=10)
    current = None
    for b in sorted(binds, key=sort_key):
        head = (b.submap or "global", b.layer or "no modifier")
        if head != current:
            current = head
            print()
            title = f"[{head[0]}]  {head[1].replace('+', ' + ')}"
            print(c("1", title))
        flags = f" ({b.flags})" if b.flags else ""
        desc = f"  {c('2', '— ' + b.description)}" if b.description else ""
        print(f"  {c('1;37', b.chord.ljust(width))}  {c(CAT_COLORS[b.category], b.action)}{flags}{desc}")
    print()
    print(c("2", f"{len(binds)} binds, {len({b.submap for b in binds})} submap(s)"))


# --------------------------------------------------------------------------- #
# Output: launcher (rofi / fuzzel / wofi / ...)
# --------------------------------------------------------------------------- #

LAUNCHERS = {
    # name: (argv, returns_index)
    "rofi":   (["rofi", "-dmenu", "-i", "-p", "keys", "-format", "i", "-no-custom"], True),
    "fuzzel": (["fuzzel", "--dmenu", "--index", "--prompt", "keys ❯ "], True),
    "wofi":   (["wofi", "--dmenu", "-i", "-p", "keys"], False),
    "tofi":   (["tofi", "--prompt-text", "keys: "], False),
    "walker": (["walker", "--dmenu"], False),
    "dmenu":  (["dmenu", "-i", "-p", "keys"], False),
}


def cmd_rofi(binds: list[Bind], args):
    name = args.launcher or next((n for n in LAUNCHERS if shutil.which(n)), None)
    if not name:
        sys.exit("hyprkeys: no launcher found (rofi/fuzzel/wofi/tofi/walker/dmenu)")
    argv, returns_index = LAUNCHERS[name]
    if args.launcher_args:
        argv += args.launcher_args

    ordered = sorted(binds, key=sort_key)
    width = max(len(b.chord) for b in ordered)
    lines = []
    for b in ordered:
        sub = f"[{b.submap}] " if b.submap else ""
        what = b.description or b.action
        extra = f"   ⟶ {b.action}" if b.description and args.show_action else ""
        lines.append(f"{sub}{b.chord.ljust(width)}   {what}{extra}")

    res = subprocess.run(argv, input="\n".join(lines) + "\n", capture_output=True, text=True)
    choice = res.stdout.strip()
    if not choice:
        return
    if returns_index:
        idx = int(choice)
    else:
        idx = lines.index(choice) if choice in lines else -1
    if idx < 0:
        return
    b = ordered[idx]
    cmd = dispatch_command(b)
    if args.no_exec:
        print(b.action)
        print("  would run:", " ".join(repr(c) if " " in c else c for c in cmd) if cmd else "(not dispatchable)")
        return
    if b.mouse:
        print(f"hyprkeys: '{b.action}' is a mouse bind, not dispatching", file=sys.stderr)
        return
    if not cmd:
        print(f"hyprkeys: cannot dispatch '{b.action}' — Lua function bind and Hyprland's callback id is unknown "
              "(run inside a Hyprland session so hyprctl can supply it)", file=sys.stderr)
        return
    subprocess.run(cmd)


def dispatch_command(b: Bind) -> list[str] | None:
    """How to trigger this bind from the outside."""
    if b.dispatcher == "lua":
        # a Lua function: only Hyprland's registry reference can run it (undocumented but works)
        return ["hyprctl", "dispatch", f"debug.getregistry()[{b.lua_id}]"] if b.lua_id else None
    if b.expr:
        # `hyprctl dispatch` evaluates Lua dispatcher expressions since 0.55
        return ["hyprctl", "dispatch", b.expr]
    if b.lua_id:
        return ["hyprctl", "dispatch", f"debug.getregistry()[{b.lua_id}]"]
    return ["hyprctl", "dispatch", b.dispatcher, b.arg] if b.arg else ["hyprctl", "dispatch", b.dispatcher]


# --------------------------------------------------------------------------- #
# Output: markdown / json / overlaps
# --------------------------------------------------------------------------- #

def cmd_md(binds: list[Bind], args):
    out = ["# Hyprland keybinds", ""]
    current = None
    for b in sorted(binds, key=sort_key):
        head = b.submap or "global"
        if head != current:
            current = head
            out += [f"## {head}", "", "| Keys | Action | Description |", "|---|---|---|"]
        out.append(f"| `{b.chord}` | `{b.action}` | {b.description} |")
    text = "\n".join(out) + "\n"
    write_or_print(text, args.output)


def cmd_json(binds: list[Bind], args):
    write_or_print(json.dumps([b.to_dict() for b in binds], indent=2, ensure_ascii=False) + "\n", args.output)


def find_overlaps(binds: list[Bind]) -> dict[tuple, list[Bind]]:
    groups: dict[tuple, list[Bind]] = {}
    for b in binds:
        groups.setdefault(b.identity(), []).append(b)
    return {k: v for k, v in groups.items() if len(v) > 1}


def cmd_overlaps(binds: list[Bind], args):
    ov = find_overlaps(binds)
    if not ov:
        print("No chord triggers more than one dispatcher.")
        return
    print("Chords with several dispatchers (Hyprland fires all of them, in order):\n")
    for (submap, _layer, _key), bs in sorted(ov.items()):
        print(f"  {'[' + submap + '] ' if submap else ''}{bs[0].chord}")
        for b in bs:
            print(f"      {b.action:<45} {b.source}")
    print(f"\n{len(ov)} overlapping chord(s)")


def write_or_print(text: str, output: str | None):
    if output and output != "-":
        Path(output).expanduser().write_text(text, encoding="utf-8")
        print(f"hyprkeys: wrote {output}", file=sys.stderr)
    else:
        sys.stdout.write(text)


# --------------------------------------------------------------------------- #
# Output: interactive HTML keyboard map
# --------------------------------------------------------------------------- #

# Physical ISO layout. Each key: (keycode, us_keysym, width_in_units). Gaps: ("", "", w).
KEYBOARD_ROWS = [
    [(9, "Escape", 1), ("", "", 1), (67, "F1", 1), (68, "F2", 1), (69, "F3", 1), (70, "F4", 1),
     ("", "", .5), (71, "F5", 1), (72, "F6", 1), (73, "F7", 1), (74, "F8", 1), ("", "", .5),
     (75, "F9", 1), (76, "F10", 1), (95, "F11", 1), (96, "F12", 1), ("", "", .5),
     (107, "Print", 1), (78, "Scroll_Lock", 1), (127, "Pause", 1)],
    [(49, "grave", 1), (10, "1", 1), (11, "2", 1), (12, "3", 1), (13, "4", 1), (14, "5", 1),
     (15, "6", 1), (16, "7", 1), (17, "8", 1), (18, "9", 1), (19, "0", 1), (20, "minus", 1),
     (21, "equal", 1), (22, "BackSpace", 2), ("", "", .5),
     (118, "Insert", 1), (110, "Home", 1), (112, "Prior", 1)],
    [(23, "Tab", 1.5), (24, "q", 1), (25, "w", 1), (26, "e", 1), (27, "r", 1), (28, "t", 1),
     (29, "y", 1), (30, "u", 1), (31, "i", 1), (32, "o", 1), (33, "p", 1),
     (34, "bracketleft", 1), (35, "bracketright", 1), (51, "backslash", 1.5), ("", "", .5),
     (119, "Delete", 1), (115, "End", 1), (117, "Next", 1)],
    [(66, "Caps_Lock", 1.75), (38, "a", 1), (39, "s", 1), (40, "d", 1), (41, "f", 1),
     (42, "g", 1), (43, "h", 1), (44, "j", 1), (45, "k", 1), (46, "l", 1),
     (47, "semicolon", 1), (48, "apostrophe", 1), (36, "Return", 2.25)],
    [(50, "Shift_L", 1.25), (94, "less", 1), (52, "z", 1), (53, "x", 1), (54, "c", 1),
     (55, "v", 1), (56, "b", 1), (57, "n", 1), (58, "m", 1), (59, "comma", 1),
     (60, "period", 1), (61, "slash", 1), (62, "Shift_R", 2.75), ("", "", 1.5),
     (111, "Up", 1)],
    [(37, "Control_L", 1.25), (133, "Super_L", 1.25), (64, "Alt_L", 1.25), (65, "space", 6.25),
     (108, "Alt_R", 1.25), (134, "Super_R", 1.25), (135, "Menu", 1.25), (105, "Control_R", 1.25),
     ("", "", .5), (113, "Left", 1), (116, "Down", 1), (114, "Right", 1)],
]

# keycode → keysym overrides for non-US layouts (only positions that differ)
LAYOUT_OVERRIDES = {
    "us": {},
    "fi": {49: "section", 20: "plus", 21: "acute", 34: "aring", 35: "dead_diaeresis",
           47: "odiaeresis", 48: "adiaeresis", 51: "apostrophe", 61: "minus"},
    "se": {49: "section", 20: "plus", 21: "acute", 34: "aring", 35: "dead_diaeresis",
           47: "odiaeresis", 48: "adiaeresis", 51: "apostrophe", 61: "minus"},
    "no": {49: "bar", 20: "plus", 21: "backslash", 34: "aring", 35: "dead_diaeresis",
           47: "oslash", 48: "ae", 51: "apostrophe", 61: "minus"},
    "de": {49: "dead_circumflex", 20: "ssharp", 21: "acute", 29: "z", 52: "y",
           34: "udiaeresis", 35: "plus", 47: "odiaeresis", 48: "adiaeresis", 51: "numbersign", 61: "minus"},
    "uk": {49: "grave", 51: "numbersign", 48: "apostrophe"},
}
LAYOUT_OVERRIDES["gb"] = LAYOUT_OVERRIDES["uk"]

KEY_GLYPHS = {"backspace": "⌫", "tab": "⇥", "caps_lock": "Caps", "return": "⏎",
              "shift_l": "⇧", "shift_r": "⇧", "control_l": "Ctrl", "control_r": "Ctrl",
              "super_l": "Super", "super_r": "Super", "alt_l": "Alt", "alt_r": "Alt",
              "menu": "☰", "space": "", "escape": "Esc", "scroll_lock": "ScrLk",
              "dead_circumflex": "^", "ssharp": "ß", "udiaeresis": "ü", "oslash": "ø",
              "ae": "æ", "bar": "|", "numbersign": "#", "print": "PrtSc"}


def detect_layout() -> str:
    if hyprland_running():
        try:
            out = subprocess.run(["hyprctl", "getoption", "input:kb_layout", "-j"],
                                 capture_output=True, text=True, timeout=2).stdout
            val = json.loads(out).get("str", "")
            first = val.split(",")[0].strip().lower()
            if first in LAYOUT_OVERRIDES:
                return first
        except Exception:
            pass
    return "us"


def keyboard_model(layout: str) -> list[list[dict]]:
    ov = LAYOUT_OVERRIDES.get(layout, {})
    rows = []
    for row in KEYBOARD_ROWS:
        r = []
        for code, sym, w in row:
            if code == "":
                r.append({"gap": True, "w": w})
                continue
            sym = ov.get(code, sym)
            label = KEY_GLYPHS.get(sym.lower(), pretty_key(sym))
            r.append({"code": code, "sym": sym.lower(), "label": label, "w": w})
        rows.append(r)
    return rows


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hyprland keymap</title>
<style>
:root{--bg:#0f1115;--panel:#161a22;--key:#1e232d;--key-edge:#2a303c;--fg:#d7dbe3;--dim:#7d8594;
--launch:#4ade80;--window:#60a5fa;--workspace:#c084fc;--media:#fbbf24;--submap:#22d3ee;--script:#fb7185;--system:#9ca3af;--accent:#a78bfa;
--u:52px;--gap:6px}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
code,kbd,.mono{font-family:ui-monospace,"JetBrainsMono Nerd Font","JetBrains Mono",Menlo,Consolas,monospace}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:16px;padding:22px 28px 6px}
header h1{margin:0;font-size:20px;font-weight:600;letter-spacing:.2px}
header .meta{color:var(--dim);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px 28px}
.bar label{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-right:4px}
.chip{border:1px solid var(--key-edge);background:var(--panel);color:var(--fg);border-radius:999px;padding:5px 12px;cursor:pointer;font-size:13px}
.chip:hover{border-color:var(--accent)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#0f1115;font-weight:600}
.chip .n{opacity:.6;font-size:11px;margin-left:4px}
input.search{margin-left:auto;background:var(--panel);border:1px solid var(--key-edge);color:var(--fg);border-radius:8px;padding:7px 12px;min-width:260px;font-size:13px}
input.search:focus{outline:none;border-color:var(--accent)}
.kb-wrap{padding:14px 28px 6px;overflow-x:auto}
.kb{display:inline-flex;flex-direction:column;gap:var(--gap);background:var(--panel);padding:16px;border-radius:14px;border:1px solid var(--key-edge)}
.row{display:flex;gap:var(--gap)}
.key,.gap{height:var(--u);flex:0 0 auto}
.key{position:relative;background:var(--key);border:1px solid var(--key-edge);border-bottom-width:3px;border-radius:7px;
 display:flex;align-items:flex-end;justify-content:flex-start;padding:5px 7px;cursor:default;transition:transform .05s,background .15s;overflow:hidden}
.key .lbl{font-size:12px;color:var(--dim);line-height:1}
.key .act{position:absolute;top:5px;left:7px;right:5px;font-size:10.5px;line-height:1.15;color:#fff;
 overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-word;font-weight:500}
.key.bound{cursor:pointer;border-color:var(--c);background:color-mix(in srgb,var(--c) 22%,var(--key))}
.key.bound .lbl{color:var(--fg)}
.key.bound:hover{transform:translateY(1px);background:color-mix(in srgb,var(--c) 38%,var(--key))}
.key.multi::after{content:attr(data-n);position:absolute;right:4px;top:3px;font-size:9px;background:var(--c);color:#0f1115;border-radius:8px;padding:0 5px;font-weight:700}
.key.dots .act{display:none}
.dots .dotrow{position:absolute;top:6px;left:7px;display:flex;gap:3px}
.dotrow i{width:7px;height:7px;border-radius:50%;display:block}
.key.hit{outline:2px solid #fff;outline-offset:-2px}
.key.dim{opacity:.35}
.extra{margin-top:10px;padding-top:10px;border-top:1px dashed var(--key-edge)}
.extra .row{flex-wrap:wrap}
.extra .key{min-width:calc(var(--u)*1.5)}
.legend{display:flex;gap:14px;flex-wrap:wrap;padding:6px 28px 8px;color:var(--dim);font-size:12px}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px;background:var(--c)}
.legend .hint{margin-left:auto}
#pop{position:fixed;z-index:9;pointer-events:none;background:#0b0d12;border:1px solid var(--key-edge);border-radius:10px;padding:10px 12px;max-width:420px;box-shadow:0 12px 40px #0009;display:none}
#pop.pin{pointer-events:auto}
#pop h4{margin:0 0 6px;font-size:12px;color:var(--dim);font-weight:500}
#pop .b{padding:4px 0;border-top:1px solid #1c212b}
#pop .b:first-of-type{border-top:0}
#pop .b .a{color:#fff;font-weight:500}
#pop .b .d{color:var(--dim);font-size:12px}
#pop .b .s{color:#555c69;font-size:11px}
#pop pre{margin:6px 0 2px;padding:8px 10px;background:#11141b;border:1px solid #1c212b;border-radius:6px;font-size:11px;line-height:1.35;color:#c9d1e0;white-space:pre;overflow:auto;max-height:220px;max-width:100%}
td.desc pre{margin:4px 0 0;font-size:11px;color:#8b93a3;white-space:pre-wrap}
.table{padding:8px 28px 40px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--dim);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.08em;padding:8px 10px;border-bottom:1px solid var(--key-edge);position:sticky;top:0;background:var(--bg)}
td{padding:6px 10px;border-bottom:1px solid #1a1f29;vertical-align:top}
tr.sub td{padding-top:22px;font-weight:600;color:var(--accent);border-bottom:0}
tr.grp td{color:var(--dim);font-size:12px;padding-top:12px;border-bottom:0;text-transform:uppercase;letter-spacing:.06em}
tr.b:hover td{background:#141821}
tr.b{cursor:pointer}
kbd{display:inline-block;background:var(--key);border:1px solid var(--key-edge);border-bottom-width:2px;border-radius:5px;padding:1px 6px;font-size:12px;margin-right:3px}
td.act{color:var(--c)}
td.desc{color:var(--dim)}
td.src{color:#555c69;font-size:11px;white-space:nowrap}
.flag{display:inline-block;font-size:10px;color:var(--dim);border:1px solid var(--key-edge);border-radius:4px;padding:0 4px;margin-left:6px;vertical-align:1px}
.hidden{display:none!important}
@media print{body{background:#fff;color:#000}.bar,.kb-wrap,.legend,#pop{display:none}th{position:static}}
</style></head>
<body>
<header><h1>Hyprland keymap</h1><span class="meta" id="meta"></span></header>
<div class="bar" id="submaps"><label>submap</label></div>
<div class="bar" id="layers"><label>layer</label><input class="search" id="q" placeholder="search binds… (dispatcher, arg, key, description)"></div>
<div class="kb-wrap"><div class="kb" id="kb"></div></div>
<div class="legend" id="legend"></div>
<div id="pop"></div>
<div class="table"><table><thead><tr><th>Keys</th><th>Action</th><th>Description</th><th>Source</th></tr></thead><tbody id="rows"></tbody></table></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const CAT = {launch:'var(--launch)',window:'var(--window)',workspace:'var(--workspace)',media:'var(--media)',submap:'var(--submap)',script:'var(--script)',system:'var(--system)'};
const MODLBL = {SUPER:'Super',CTRL:'Ctrl',ALT:'Alt',SHIFT:'Shift',CAPS:'Caps',MOD2:'Mod2',MOD3:'Mod3',MOD5:'Mod5'};
const state = {submap:'', layer:'ALL', q:''};
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const layerLabel = l => l==='' ? 'no modifier' : l.split('+').map(m=>MODLBL[m]||m).join(' + ');

$('#meta').textContent = `${D.binds.length} binds · source: ${D.source} · layout: ${D.layout} · generated ${D.generated}`;

function bindsFor(){ return D.binds.filter(b => b.submap===state.submap && (state.layer==='ALL' || b.layer===state.layer)); }
function matchesQ(b){ if(!state.q) return true; const q=state.q.toLowerCase();
  return [b.chord,b.action,b.description,b.group,b.key].some(x => (x||'').toLowerCase().includes(q)); }
function keyMatches(b, k){ return b.key.toLowerCase()===k.sym || b.key.toLowerCase()==='code:'+k.code; }

function renderChips(){
  const sm = $('#submaps'); sm.querySelectorAll('.chip').forEach(e=>e.remove());
  const submaps = [...new Set(D.binds.map(b=>b.submap))].sort((a,b)=>(a===''?-1:b===''?1:a.localeCompare(b)));
  for(const s of submaps){ const c=document.createElement('button'); c.className='chip'+(s===state.submap?' on':'');
    c.innerHTML = `${esc(s||'global')}<span class="n">${D.binds.filter(b=>b.submap===s).length}</span>`;
    c.onclick=()=>{state.submap=s; if(!layersIn().includes(state.layer)) state.layer='ALL'; render();}; sm.appendChild(c); }
  const ly = $('#layers'); ly.querySelectorAll('.chip').forEach(e=>e.remove());
  const all=document.createElement('button'); all.className='chip'+(state.layer==='ALL'?' on':''); all.textContent='all layers';
  all.onclick=()=>{state.layer='ALL';render();}; ly.insertBefore(all, $('#q'));
  for(const l of layersIn()){ const c=document.createElement('button'); c.className='chip'+(l===state.layer?' on':'');
    c.innerHTML=`${esc(layerLabel(l))}<span class="n">${D.binds.filter(b=>b.submap===state.submap&&b.layer===l).length}</span>`;
    c.onclick=()=>{state.layer=l;render();}; ly.insertBefore(c, $('#q')); }
}
function layersIn(){ const ls=[...new Set(D.binds.filter(b=>b.submap===state.submap).map(b=>b.layer))];
  return ls.sort((a,b)=>a.split('+').length-b.split('+').length || a.localeCompare(b)); }

function keyEl(k, bs){
  const el=document.createElement('div'); el.className='key'; el.style.width=`calc(var(--u)*${k.w} + var(--gap)*${k.w-1})`;
  el.innerHTML=`<span class="lbl">${esc(k.label)}</span>`;
  if(bs.length){ el.classList.add('bound'); el.style.setProperty('--c', CAT[bs[0].category]);
    if(state.layer==='ALL' && new Set(bs.map(b=>b.layer)).size>1){ el.classList.add('dots');
      const dr=document.createElement('div'); dr.className='dotrow';
      for(const b of bs.slice(0,6)){ const i=document.createElement('i'); i.style.background=CAT[b.category]; dr.appendChild(i);} el.appendChild(dr);
    } else { const a=document.createElement('span'); a.className='act'; a.textContent = bs[0].description || bs[0].action; el.appendChild(a); }
    if(bs.length>1){ el.classList.add('multi'); el.dataset.n=bs.length; }
    if(state.q && !bs.some(matchesQ)) el.classList.add('dim'); else if(state.q) el.classList.add('hit');
    el.onmouseenter=e=>showPop(e, k, bs, false); el.onmousemove=movePop; el.onmouseleave=()=>{ if(!pinned) hidePop(); };
    el.onclick=e=>{ e.stopPropagation(); pinned=!pinned; showPop(e,k,bs,pinned); };
  } else if(state.q){ el.classList.add('dim'); }
  return el;
}
function renderKb(){
  const kb=$('#kb'); kb.innerHTML=''; const bs=bindsFor(); const used=new Set();
  for(const row of D.keyboard){ const r=document.createElement('div'); r.className='row';
    for(const k of row){ if(k.gap){ const g=document.createElement('div'); g.className='gap'; g.style.width=`calc(var(--u)*${k.w} + var(--gap)*${k.w-1})`; r.appendChild(g); continue; }
      const mine=bs.filter(b=>keyMatches(b,k)); mine.forEach(b=>used.add(b)); r.appendChild(keyEl(k, mine)); }
    kb.appendChild(r); }
  const rest=bs.filter(b=>!used.has(b)); if(rest.length){ const ex=document.createElement('div'); ex.className='extra'; const r=document.createElement('div'); r.className='row';
    const byKey={}; for(const b of rest){ (byKey[b.key.toLowerCase()] ||= []).push(b); }
    for(const [sym, list] of Object.entries(byKey).sort()){ r.appendChild(keyEl({sym, code:-1, label:list[0].key_label, w:1.5}, list)); }
    ex.appendChild(r); kb.appendChild(ex); }
}
let pinned=false;
function showPop(e,k,bs,pin){ const p=$('#pop'); p.className=pin?'pin':'';
  p.innerHTML=`<h4>${esc(k.label)} · ${esc(state.submap||'global')}</h4>`+bs.map(b=>`<div class="b"><div class="a"><kbd>${esc(b.chord)}</kbd> ${esc(b.action)}${b.flags?`<span class="flag">${esc(b.flags)}</span>`:''}</div>${b.description?`<div class="d">${esc(b.description)}</div>`:''}${b.code?`<pre>${esc(b.code)}</pre>`:''}<div class="s">${esc(b.source)}</div></div>`).join('');
  p.style.display='block'; movePop(e); }
function movePop(e){ const p=$('#pop'); if(pinned) return; const x=Math.min(e.clientX+14, innerWidth-p.offsetWidth-10), y=Math.min(e.clientY+14, innerHeight-p.offsetHeight-10); p.style.left=x+'px'; p.style.top=y+'px'; }
function hidePop(){ $('#pop').style.display='none'; }
document.addEventListener('click', ()=>{ pinned=false; hidePop(); });

function renderTable(){
  const tb=$('#rows'); tb.innerHTML=''; let sm=null, grp=null;
  const list=D.binds.filter(b=>b.submap===state.submap && (state.layer==='ALL'||b.layer===state.layer) && matchesQ(b));
  for(const b of list){
    if(b.submap!==sm){ sm=b.submap; grp=null; tb.insertAdjacentHTML('beforeend',`<tr class="sub"><td colspan="4">${esc(sm||'global')}</td></tr>`); }
    if(b.group!==grp && b.group){ grp=b.group; tb.insertAdjacentHTML('beforeend',`<tr class="grp"><td colspan="4">${esc(grp)}</td></tr>`); }
    const tr=document.createElement('tr'); tr.className='b';
    tr.innerHTML=`<td class="mono">${b.chord.split(' + ').map(x=>`<kbd>${esc(x)}</kbd>`).join('')}${b.flags?`<span class="flag">${esc(b.flags)}</span>`:''}</td><td class="act mono" style="--c:${CAT[b.category]}">${esc(b.action)}</td><td class="desc">${esc(b.description)}${b.code?`<pre>${esc(b.code)}</pre>`:''}</td><td class="src">${esc(b.source)}</td>`;
    tr.onclick=()=>{ state.layer=b.layer; render(); document.querySelector('.kb-wrap').scrollIntoView({behavior:'smooth'}); };
    tb.appendChild(tr); }
  if(!list.length) tb.innerHTML='<tr><td colspan="4" style="color:var(--dim)">nothing matches</td></tr>';
}
function renderLegend(){ $('#legend').innerHTML = Object.entries(CAT).map(([c,v])=>`<span style="--c:${v}">${c}</span>`).join('')+
  `<span class="hint" style="--c:transparent">hover a key for details · click to pin · hold real modifier keys to switch layer · ⌘/Ctrl+P to print a cheatsheet</span>`; }
function render(){ renderChips(); renderKb(); renderTable(); }
$('#q').addEventListener('input', e=>{ state.q=e.target.value; render(); });

// hold physical modifiers to switch the visible layer (Super is often eaten by the compositor)
const held=new Set(); const KM={Shift:'SHIFT',Control:'CTRL',Alt:'ALT',Meta:'SUPER',OS:'SUPER'};
function heldLayer(){ const order=['SUPER','CTRL','ALT','SHIFT']; return order.filter(m=>held.has(m)).join('+'); }
window.addEventListener('keydown', e=>{ if(e.target.tagName==='INPUT') return; const m=KM[e.key]; if(!m) return; held.add(m);
  const l=heldLayer(); if(layersIn().includes(l)){ state.layer=l; render(); } });
window.addEventListener('keyup', e=>{ const m=KM[e.key]; if(m) held.delete(m); });
window.addEventListener('blur', ()=>held.clear());
// keep groups contiguous in the order they appear in the config; sort by layer/key inside a group
const gOrder={}; D.binds.forEach((b,i)=>{ const k=b.submap+'\0'+b.group; if(!(k in gOrder)) gOrder[k]=i; });
D.binds.sort((a,b)=> (a.submap>b.submap)-(a.submap<b.submap) || gOrder[a.submap+'\0'+a.group]-gOrder[b.submap+'\0'+b.group]
  || a.layer.split('+').length-b.layer.split('+').length || a.layer.localeCompare(b.layer) || a.key_label.localeCompare(b.key_label));
renderLegend(); render();
</script></body></html>
"""


def cmd_html(binds: list[Bind], args):
    import datetime
    layout = args.layout or detect_layout()
    data = {
        "binds": [b.to_dict() for b in binds],
        "keyboard": keyboard_model(layout),
        "layout": layout,
        "source": args.source,
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    # '</' inside JSON would end the script tag early
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = HTML_TEMPLATE.replace("__DATA__", payload)
    out = args.output
    if not out:
        runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
        out = str(Path(runtime) / "hyprkeys.html")
    if out == "-":
        sys.stdout.write(page)
        return
    Path(out).expanduser().write_text(page, encoding="utf-8")
    print(f"hyprkeys: wrote {out}", file=sys.stderr)
    if args.open:
        webbrowser.open(Path(out).expanduser().resolve().as_uri())


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(prog="hyprkeys", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["auto", "hyprctl", "config"], default="auto")
    ap.add_argument("--config", "-c", type=Path,
                    help="hyprland.lua or hyprland.conf (default: $XDG_CONFIG_HOME/hypr/hyprland.lua, else .conf)")
    ap.add_argument("--submap", help="only show binds from this submap ('global' for the root)")
    ap.add_argument("--quiet", "-q", action="store_true", help="suppress warnings")
    ap.add_argument("--no-dry-run", action="store_true",
                    help="Lua: don't execute function dispatchers to discover what they do")
    ap.add_argument("--lua", metavar="RUNTIME", help="Lua interpreter to use (path, or 'lupa'); default: auto-detect")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="table in the terminal")
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("rofi", help="pick a bind in a launcher and dispatch it")
    p.add_argument("--launcher", choices=sorted(LAUNCHERS), help="default: first one found in PATH")
    p.add_argument("--no-exec", action="store_true", help="print the action instead of dispatching it")
    p.add_argument("--show-action", action="store_true", help="show the dispatcher next to descriptions")
    p.add_argument("launcher_args", nargs=argparse.REMAINDER, help="extra args after --, passed to the launcher")
    p.set_defaults(fn=cmd_rofi)

    p = sub.add_parser("html", help="interactive keyboard map")
    p.add_argument("--output", "-o", help="default: $XDG_RUNTIME_DIR/hyprkeys.html ('-' for stdout)")
    p.add_argument("--open", action="store_true", help="open in the default browser")
    p.add_argument("--layout", choices=sorted(LAYOUT_OVERRIDES), help="keyboard layout (default: from input:kb_layout, else us)")
    p.set_defaults(fn=cmd_html)

    p = sub.add_parser("md", help="markdown cheatsheet")
    p.add_argument("--output", "-o")
    p.set_defaults(fn=cmd_md)

    p = sub.add_parser("json", help="JSON dump")
    p.add_argument("--output", "-o")
    p.set_defaults(fn=cmd_json)

    p = sub.add_parser("overlaps", help="chords bound to several dispatchers")
    p.set_defaults(fn=cmd_overlaps)

    args = ap.parse_args(argv)
    if getattr(args, "launcher_args", None) and args.launcher_args[:1] == ["--"]:
        args.launcher_args = args.launcher_args[1:]

    binds = load_binds(args.source, args.config, args.quiet, not args.no_dry_run, args.lua)
    if args.submap is not None:
        want = "" if args.submap == "global" else args.submap
        binds = [b for b in binds if b.submap == want]
    if not binds:
        sys.exit("hyprkeys: no binds found")
    args.fn(binds, args)


if __name__ == "__main__":
    main()
