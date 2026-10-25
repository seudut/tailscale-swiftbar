#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <xbar.title>Tailnet Status</xbar.title>
# <xbar.version>v1.14</xbar.version>
# <xbar.author>peng</xbar.author>
# <xbar.desc>Show tailnet devices with the same connection status text as `tailscale status` (Tailscale dot icon + online count); auto keepalive and manual Refresh ping peers first; SSH / Screen Sharing / Ping / Copy IP actions.</xbar.desc>
# <xbar.dependencies>python3,tailscale</xbar.dependencies>
# <xbar.abouturl>https://github.com/seudut/tailscale-swiftbar</xbar.abouturl>
# <swiftbar.runInBash>false</swiftbar.runInBash>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
#
# Data source: local tailscaled unix socket (`tailscale status --json`).
# No sudo, no network requests. Refresh interval comes from the file name
# (tailnet.10s.py = every 10 seconds).
#
# SwiftBar 2.x output format:
#   - first line is the menu bar title; first "---" separates header from body
#   - body lines are plain "title | params" (NO "--" prefix; a "--" prefix
#     means "submenu of the previous item")
#   - submenu items use "-- title | params"; deeper levels use "----"
#   - "---" is a menu separator
#
# Config (override with same-named env vars):
#   TAILNET_SSH_USER      default: current user
#   TAILNET_CONTROL_URL   control URL (default: read from `tailscale debug prefs`)
#   TAILNET_TS_BIN        default: auto-detect Homebrew tailscale
#   TAILNET_LANG          "auto" (system language) | "en" | "zh"
#   TAILNET_KEEPALIVE     seconds between background keepalive pings (default 60, 0=off)
#
# Colors: direct = green, relayed = orange, offline = gray (light,dark pairs).

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------- config ----------------
TS_CANDIDATES = [
    "/opt/homebrew/bin/tailscale",
    "/opt/homebrew/opt/tailscale/bin/tailscale",
    "/usr/local/bin/tailscale",
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
]
TS = os.environ.get("TAILNET_TS_BIN") or next(
    (p for p in TS_CANDIDATES if os.path.exists(p)), TS_CANDIDATES[0]
)
SSH_USER = (
    os.environ.get("TAILNET_SSH_USER")
    or os.environ.get("USER")
    or os.environ.get("LOGNAME")
    or "peng"
)
CONTROL_URL_OVERRIDE = os.environ.get("TAILNET_CONTROL_URL", "").strip()
KEEPALIVE_SECONDS = int(os.environ.get("TAILNET_KEEPALIVE", "60") or 0)  # 0 disables
DATA_DIR = (
    os.environ.get("SWIFTBAR_PLUGIN_DATA_PATH")
    or os.path.join(os.path.expanduser("~"), ".cache", "tailnet-status")
)
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 8

LANG_PREF = "auto"  # auto | en | zh

COLOR_DIRECT = "#1B7F37,#30D158"   # green (light,dark)
COLOR_RELAY = "#A15C00,#FF9F0A"    # orange (light,dark)
COLOR_OFFLINE = "#6E6E73,#98989D"  # gray (light,dark)

# 18x18 矢量 PDF：Tailscale 官方点阵 T 标记（templateImage，菜单栏自动适配黑白）
TS_ICON_B64 = (
    "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5"
    "cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVu"
    "dCAyIDAgUiAvTWVkaWFCb3ggWzAgMCAxOC4wIDE4LjBdIC9SZXNvdXJjZXMgPDwgL0V4dEdTdGF0ZSA8PCAvR1MxIDUgMCBS"
    "ID4+ID4+IC9Db250ZW50cyA0IDAgUiA+PgplbmRvYmoKNCAwIG9iago8PCAvTGVuZ3RoIDE5NjkgPj4Kc3RyZWFtCnEKMCBn"
    "IDUuMDAwMCA5LjAwMDAgbSA1LjAwMDAgMTAuMTA0NiAzLjg5NTQgMTEuMDAwMCAzLjAwMDAgMTEuMDAwMCBjIDEuODk1NCAx"
    "MS4wMDAwIDEuMDAwMCA5Ljg5NTQgMS4wMDAwIDkuMDAwMCBjIDEuMDAwMCA3Ljg5NTQgMi4xMDQ2IDcuMDAwMCAzLjAwMDAg"
    "Ny4wMDAwIGMgNC4xMDQ2IDcuMDAwMCA1LjAwMDAgOC4xMDQ2IDUuMDAwMCA5LjAwMDAgYyBoIGYKMCBnIDExLjAwMDAgOS4w"
    "MDAwIG0gMTEuMDAwMCAxMC4xMDQ2IDkuODk1NCAxMS4wMDAwIDkuMDAwMCAxMS4wMDAwIGMgNy44OTU0IDExLjAwMDAgNy4w"
    "MDAwIDkuODk1NCA3LjAwMDAgOS4wMDAwIGMgNy4wMDAwIDcuODk1NCA4LjEwNDYgNy4wMDAwIDkuMDAwMCA3LjAwMDAgYyAx"
    "MC4xMDQ2IDcuMDAwMCAxMS4wMDAwIDguMTA0NiAxMS4wMDAwIDkuMDAwMCBjIGggZgowIGcgMTcuMDAwMCA5LjAwMDAgbSAx"
    "Ny4wMDAwIDEwLjEwNDYgMTUuODk1NCAxMS4wMDAwIDE1LjAwMDAgMTEuMDAwMCBjIDEzLjg5NTQgMTEuMDAwMCAxMy4wMDAw"
    "IDkuODk1NCAxMy4wMDAwIDkuMDAwMCBjIDEzLjAwMDAgNy44OTU0IDE0LjEwNDYgNy4wMDAwIDE1LjAwMDAgNy4wMDAwIGMg"
    "MTYuMTA0NiA3LjAwMDAgMTcuMDAwMCA4LjEwNDYgMTcuMDAwMCA5LjAwMDAgYyBoIGYKMCBnIDExLjAwMDAgMy4wMDAwIG0g"
    "MTEuMDAwMCA0LjEwNDYgOS44OTU0IDUuMDAwMCA5LjAwMDAgNS4wMDAwIGMgNy44OTU0IDUuMDAwMCA3LjAwMDAgMy44OTU0"
    "IDcuMDAwMCAzLjAwMDAgYyA3LjAwMDAgMS44OTU0IDguMTA0NiAxLjAwMDAgOS4wMDAwIDEuMDAwMCBjIDEwLjEwNDYgMS4w"
    "MDAwIDExLjAwMDAgMi4xMDQ2IDExLjAwMDAgMy4wMDAwIGMgaCBmCnEgL0dTMSBncyAwIGcgNS4wMDAwIDMuMDAwMCBtIDUu"
    "MDAwMCA0LjEwNDYgMy44OTU0IDUuMDAwMCAzLjAwMDAgNS4wMDAwIGMgMS44OTU0IDUuMDAwMCAxLjAwMDAgMy44OTU0IDEu"
    "MDAwMCAzLjAwMDAgYyAxLjAwMDAgMS44OTU0IDIuMTA0NiAxLjAwMDAgMy4wMDAwIDEuMDAwMCBjIDQuMTA0NiAxLjAwMDAg"
    "NS4wMDAwIDIuMTA0NiA1LjAwMDAgMy4wMDAwIGMgaCBmIFEKcSAvR1MxIGdzIDAgZyAxNy4wMDAwIDMuMDAwMCBtIDE3LjAw"
    "MDAgNC4xMDQ2IDE1Ljg5NTQgNS4wMDAwIDE1LjAwMDAgNS4wMDAwIGMgMTMuODk1NCA1LjAwMDAgMTMuMDAwMCAzLjg5NTQg"
    "MTMuMDAwMCAzLjAwMDAgYyAxMy4wMDAwIDEuODk1NCAxNC4xMDQ2IDEuMDAwMCAxNS4wMDAwIDEuMDAwMCBjIDE2LjEwNDYg"
    "MS4wMDAwIDE3LjAwMDAgMi4xMDQ2IDE3LjAwMDAgMy4wMDAwIGMgaCBmIFEKcSAvR1MxIGdzIDAgZyA1LjAwMDAgMTUuMDAw"
    "MCBtIDUuMDAwMCAxNi4xMDQ2IDMuODk1NCAxNy4wMDAwIDMuMDAwMCAxNy4wMDAwIGMgMS44OTU0IDE3LjAwMDAgMS4wMDAw"
    "IDE1Ljg5NTQgMS4wMDAwIDE1LjAwMDAgYyAxLjAwMDAgMTMuODk1NCAyLjEwNDYgMTMuMDAwMCAzLjAwMDAgMTMuMDAwMCBj"
    "IDQuMTA0NiAxMy4wMDAwIDUuMDAwMCAxNC4xMDQ2IDUuMDAwMCAxNS4wMDAwIGMgaCBmIFEKcSAvR1MxIGdzIDAgZyAxMS4w"
    "MDAwIDE1LjAwMDAgbSAxMS4wMDAwIDE2LjEwNDYgOS44OTU0IDE3LjAwMDAgOS4wMDAwIDE3LjAwMDAgYyA3Ljg5NTQgMTcu"
    "MDAwMCA3LjAwMDAgMTUuODk1NCA3LjAwMDAgMTUuMDAwMCBjIDcuMDAwMCAxMy44OTU0IDguMTA0NiAxMy4wMDAwIDkuMDAw"
    "MCAxMy4wMDAwIGMgMTAuMTA0NiAxMy4wMDAwIDExLjAwMDAgMTQuMTA0NiAxMS4wMDAwIDE1LjAwMDAgYyBoIGYgUQpxIC9H"
    "UzEgZ3MgMCBnIDE3LjAwMDAgMTUuMDAwMCBtIDE3LjAwMDAgMTYuMTA0NiAxNS44OTU0IDE3LjAwMDAgMTUuMDAwMCAxNy4w"
    "MDAwIGMgMTMuODk1NCAxNy4wMDAwIDEzLjAwMDAgMTUuODk1NCAxMy4wMDAwIDE1LjAwMDAgYyAxMy4wMDAwIDEzLjg5NTQg"
    "MTQuMTA0NiAxMy4wMDAwIDE1LjAwMDAgMTMuMDAwMCBjIDE2LjEwNDYgMTMuMDAwMCAxNy4wMDAwIDE0LjEwNDYgMTcuMDAw"
    "MCAxNS4wMDAwIGMgaCBmIFEKUQplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0V4dEdTdGF0ZSAvY2EgMC40"
    "ID4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAw"
    "MDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIG4gCjAwMDAwMDAyNDkgMDAwMDAgbiAKMDAwMDAwMjI2OSAwMDAwMCBuIAp0cmFp"
    "bGVyCjw8IC9TaXplIDYgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjIzMTUKJSVFT0YK"
)

OS_EMOJI = {
    "macOS": "💻",
    "linux": "🖥️",
    "iOS": "📱",
    "iPadOS": "📱",
    "android": "📱",
    "windows": "🖥️",
}
OS_EMOJI_FALLBACK = "❓"

STRINGS = {
    "en": {
        "title": "{online}/{total}",
        "online": "online",
        "offline": "offline",
        "direct": "direct",
        "relay": "relay",
        "relay_region": "relay region",
        "conn_addr": "connection",
        "last_seen": "last seen",
        "screen_sharing": "Screen Sharing",
        "ssh": "SSH",
        "ping": "Ping",
        "copy_ip": "Copy IP",
        "dns": "DNS",
        "ip": "IP",
        "tailnet": "Tailnet",
        "headscale": "Headscale",
        "full_status": "Full status",
        "refresh": "Refresh",
        "refresh_tip": "Ping all peers, then refresh",
        "open_plugin_dir": "Open plugin folder",
        "retry": "Retry",
        "run_status": "Run tailscale status in Terminal",
        "run_short": "Open in Terminal",
        "err_ts_not_found": "⚠︎ tailscale not found",
        "err_ts_not_found_detail": "tailscale executable not found",
        "err_tried": "Tried",
        "err_no_response": "⚠︎ tailscaled not responding",
        "err_timeout": "tailscale status --json timed out after {secs}s",
        "err_not_connected": "⚠︎ not connected to tailscaled",
        "err_nonzero": "tailscale status returned a non-zero exit code",
        "err_parse": "⚠︎ failed to parse status",
        "err_parse_detail": "tailscale status --json returned invalid JSON",
        "err_plugin": "⚠︎ plugin error",
        "open_login": "Open login URL",
        "state": "State",
        "ago_just_now": "just now",
        "ago_minutes": "{n} min ago",
        "ago_hours": "{n} h ago",
        "ago_days": "{n} d ago",
        "unavailable": "unavailable",
        "hint_idle": "no active connection (traffic will try to establish a direct path)",
    },
    "zh": {
        "title": "{online}/{total}",
        "online": "在线",
        "offline": "离线",
        "direct": "直连",
        "relay": "中继",
        "relay_region": "中继区域",
        "conn_addr": "连接地址",
        "last_seen": "最近在线",
        "screen_sharing": "屏幕共享",
        "ssh": "SSH",
        "ping": "Ping",
        "copy_ip": "复制 IP",
        "dns": "DNS",
        "ip": "IP",
        "tailnet": "Tailnet",
        "headscale": "Headscale",
        "full_status": "完整状态",
        "refresh": "刷新",
        "refresh_tip": "先 ping 所有设备，再刷新",
        "open_plugin_dir": "打开插件目录",
        "retry": "重试",
        "run_status": "在终端运行 tailscale status",
        "run_short": "在终端查看",
        "err_ts_not_found": "⚠︎ 找不到 tailscale",
        "err_ts_not_found_detail": "未找到 tailscale 可执行文件",
        "err_tried": "尝试过",
        "err_no_response": "⚠︎ tailscaled 无响应",
        "err_timeout": "tailscale status --json 超过 {secs}s 未返回",
        "err_not_connected": "⚠︎ 未连接到 tailscaled",
        "err_nonzero": "tailscale status 返回非 0 退出码",
        "err_parse": "⚠︎ 状态解析失败",
        "err_parse_detail": "tailscale status --json 输出不是合法 JSON",
        "err_plugin": "⚠︎ 插件异常",
        "open_login": "打开登录链接",
        "state": "状态",
        "ago_just_now": "刚刚",
        "ago_minutes": "{n} 分钟前",
        "ago_hours": "{n} 小时前",
        "ago_days": "{n} 天前",
        "unavailable": "不可用",
        "hint_idle": "当前无活动连接（有流量时会尝试建立直连）",
    },
}


# ---------------- helpers ----------------
def run(cmd, timeout=TIMEOUT):
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True
    )


def detect_system_language():
    """Pick zh only when the primary system language is Chinese; fall back to env."""
    try:
        proc = run(["/usr/bin/defaults", "read", "-g", "AppleLanguages"], timeout=3)
        if proc.returncode == 0:
            m = re.search(r'"([^"]+)"', proc.stdout)
            if m:
                first = m.group(1).lower()
                return "zh" if first.startswith("zh") else "en"
    except Exception:
        pass
    env = (os.environ.get("LANG") or os.environ.get("LC_ALL") or "").lower()
    return "zh" if env.startswith("zh") else "en"


def pick_language():
    pref = (os.environ.get("TAILNET_LANG") or LANG_PREF).strip().lower()
    if pref in ("en", "zh"):
        return pref
    return detect_system_language()


T = STRINGS[pick_language()]


def clean(text, limit=110):
    if not text:
        return ""
    t = str(text).replace("\r", " ").replace("\n", " ").replace("|", "／")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    return t


def emit(lines):
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def error_menu(title_key, details):
    lines = [
        f"{clean(T[title_key])} | sfimage=exclamationmark.triangle.fill color=red",
        "---",
    ]
    for d in details[:4]:
        if d:
            lines.append(f"{clean(d)} | color={COLOR_OFFLINE}")
    lines += [
        f'{T["retry"]} | refresh=true sfimage=arrow.clockwise',
        f'{T["run_status"]} | bash={TS} param1=status terminal=true sfimage=terminal',
        f'{T["open_plugin_dir"]} | bash=/usr/bin/open param1="{PLUGIN_DIR}" terminal=false sfimage=folder',
    ]
    emit(lines)
    sys.exit(0)


def short_name(dns, host):
    n = (dns or "").rstrip(".")
    if n:
        return n.split(".")[0]
    return host or "?"


def fqdn(dns):
    return (dns or "").rstrip(".")


def parse_last_seen(value):
    """Parse RFC3339 LastSeen (nanoseconds / Z / +08:00)."""
    if not value:
        return None
    s = str(value).strip()
    if s.startswith("0001-") or s == "0":
        return None
    s = s.replace("Z", "+00:00")
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(.*)$", s)
    if not m:
        return None
    base, frac, tz = m.groups()
    frac = (frac or "")[:7]
    try:
        return datetime.fromisoformat(base + frac + (tz or ""))
    except ValueError:
        return None


def ago_text(dt):
    if dt is None:
        return ""
    try:
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    except Exception:
        return ""
    sec = int(delta.total_seconds())
    if sec < 60:
        return T["ago_just_now"]
    if sec < 3600:
        return T["ago_minutes"].format(n=sec // 60)
    if sec < 86400:
        return T["ago_hours"].format(n=sec // 3600)
    return T["ago_days"].format(n=sec // 86400)


def first_ip(addrs):
    for a in addrs or []:
        if "." in a:
            return a
    return (addrs or [""])[0]


# ---- compact status label (classification mirrors `tailscale status`) ----
def cli_status_text(p):
    """Compact status label (same classification as `tailscale status`, but only the keyword).

    direct / relay / peer-relay / idle / - / offline
    The direct address, DERP region name and inline "last seen" are intentionally hidden;
    offline devices show the exact last-seen timestamp as a submenu item instead.
    """
    if not p["online"]:
        return "offline"
    if not p["active"]:
        return "idle" if (p["tx"] or p["rx"]) else "-"
    if p["cur_addr"]:
        return "direct"
    if p["relay"] and not p["peer_relay"]:
        return "relay"
    if p["peer_relay"]:
        return "peer-relay"
    return "active"


def conn_kind(p):
    if not p["online"]:
        return "offline"
    if not p["active"]:
        return "idle"
    if p["cur_addr"]:
        return "direct"
    if p["relay"] and not p["peer_relay"]:
        return "relay"
    if p["peer_relay"]:
        return "peer"
    return "active"


def conn_color(kind):
    if kind == "direct":
        return COLOR_DIRECT
    if kind in ("relay", "peer"):
        return COLOR_RELAY
    if kind == "offline":
        # really unreachable: de-emphasize with gray
        return COLOR_OFFLINE
    # idle / '-' (online, just no active path): keep the normal text color
    return ""


def pick_emoji(os_name):
    return OS_EMOJI.get(os_name, OS_EMOJI_FALLBACK)


def control_url():
    """Headscale control URL: env override, else tailscaled prefs, else empty."""
    if CONTROL_URL_OVERRIDE:
        return CONTROL_URL_OVERRIDE
    try:
        proc = run([TS, "debug", "prefs"], timeout=4)
        if proc.returncode == 0:
            data = json.loads(proc.stdout or "{}")
            return (data.get("ControlURL") or "").rstrip("/")
    except Exception:
        pass
    return ""


def maybe_keepalive(online_dns):
    """Every KEEPALIVE_SECONDS, fire-and-forget parallel `tailscale ping` to all
    online peers so direct paths stay warm (status stays 'direct' instead of
    falling back to '-' / 'idle'). Background only; 0 disables."""
    if KEEPALIVE_SECONDS <= 0 or not online_dns:
        return
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        stamp = os.path.join(DATA_DIR, "last-keepalive")
        now = time.time()
        try:
            with open(stamp, "r", encoding="utf-8") as f:
                last = float((f.read() or "0").strip())
        except Exception:
            last = 0.0
        if now - last < KEEPALIVE_SECONDS:
            return
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(str(int(now)))
        pings = " & ".join(
            f"{TS} ping -c 1 --timeout=1s {shlex.quote(h)} >/dev/null 2>&1"
            for h in online_dns
        )
        subprocess.Popen(
            ["/bin/sh", "-c", pings + " & wait"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


# ---------------- main ----------------
def main():
    try:
        proc = run([TS, "status", "--json"])
    except FileNotFoundError:
        error_menu(
            "err_ts_not_found",
            [T["err_ts_not_found_detail"], f'{T["err_tried"]}: ' + ", ".join(TS_CANDIDATES)],
        )
        return
    except subprocess.TimeoutExpired:
        error_menu("err_no_response", [T["err_timeout"].format(secs=TIMEOUT)])
        return

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        error_menu("err_not_connected", msg or [T["err_nonzero"]])
        return

    try:
        data = json.loads(proc.stdout or "{}")
    except Exception:
        error_menu("err_parse", [T["err_parse_detail"]])
        return

    backend = data.get("BackendState") or "Unknown"
    selfp = data.get("Self") or {}
    peers = data.get("Peer") or {}
    suffix = (data.get("MagicDNSSuffix") or "").rstrip(".")

    if backend != "Running":
        lines = [
            f"⚠︎ {clean(backend)} | sfimage=exclamationmark.triangle.fill color=red",
            "---",
        ]
        auth_url = (data.get("AuthURL") or "").strip()
        if auth_url:
            lines.append(f'{T["open_login"]} | href={auth_url} sfimage=lock.open')
        lines.append(f'{T["state"]}: {clean(backend)} | color={COLOR_OFFLINE}')
        lines += [
            f'{T["retry"]} | refresh=true sfimage=arrow.clockwise',
            f'{T["run_short"]} | bash={TS} param1=status terminal=true sfimage=terminal',
        ]
        emit(lines)
        return

    self_online = bool(selfp.get("Online", True))
    self_name = short_name(selfp.get("DNSName"), selfp.get("HostName"))
    self_dns = fqdn(selfp.get("DNSName"))
    self_ip = first_ip(selfp.get("TailscaleIPs"))

    peer_list = []
    for p in peers.values():
        os_name = p.get("OS") or "?"
        name = short_name(p.get("DNSName"), p.get("HostName"))
        peer_list.append(
            {
                "name": name,
                "dns": fqdn(p.get("DNSName")),
                "ip": first_ip(p.get("TailscaleIPs")),
                "os": os_name,
                "online": bool(p.get("Online")),
                "last_seen": parse_last_seen(p.get("LastSeen")),
                "cur_addr": p.get("CurAddr") or "",
                "relay": p.get("Relay") or "",
                "exit_node": bool(p.get("ExitNode")),
                "exit_node_option": bool(p.get("ExitNodeOption")),
                "active": bool(p.get("Active")),
                "peer_relay": p.get("PeerRelay") or "",
                "tx": p.get("TxBytes") or 0,
                "rx": p.get("RxBytes") or 0,
            }
        )

    peers_sorted = sorted(
        peer_list, key=lambda x: (0 if x["online"] else 1, x["name"].lower())
    )
    online_dns = [p["dns"] for p in peers_sorted if p["online"] and p["dns"]]
    maybe_keepalive(online_dns)
    total = 1 + len(peers_sorted)
    online = (1 if self_online else 0) + sum(1 for p in peers_sorted if p["online"])

    base_title = T["title"].format(online=online, total=total)
    if online == total:
        title = f"{base_title} | templateImage={TS_ICON_B64} color={COLOR_DIRECT}"
    else:
        title = f"{base_title} | templateImage={TS_ICON_B64}"

    lines = [title, "---"]

    # ---- this Mac ----
    self_emoji = pick_emoji(selfp.get("OS") or "macOS")
    self_state = T["online"] if self_online else T["offline"]
    self_color = COLOR_DIRECT if self_online else COLOR_OFFLINE
    lines.append(
        f'・{self_emoji} {clean(self_name)} ({clean(self_ip)}) · {self_state}'
        f" | color={self_color}"
    )
    if self_dns:
        lines.append(f'-- {T["dns"]}: {clean(self_dns)} | color={COLOR_OFFLINE}')
    lines.append(f'-- {T["ip"]}: {clean(self_ip)} | color={COLOR_OFFLINE}')
    if suffix:
        lines.append(f'-- {T["tailnet"]}: {clean(suffix)} | color={COLOR_OFFLINE}')

    # ---- peers ----
    for p in peers_sorted:
        emoji = pick_emoji(p["os"])
        kind = conn_kind(p)
        status_text = clean(cli_status_text(p), 90)
        color = conn_color(kind)
        line = f"{emoji} {clean(p['name'])} ({clean(p['ip'])}) · {status_text}"
        if color:
            line += f" | color={color}"
        lines.append(line)
        if p["online"]:
            if p["dns"]:
                lines.append(f'-- {T["dns"]}: {clean(p["dns"])} | color={COLOR_OFFLINE}')
            if p["os"] == "macOS" and p["dns"]:
                lines.append(
                    f'-- {T["screen_sharing"]} | bash=/usr/bin/open param1=vnc://{p["dns"]}'
                    f" terminal=false sfimage=display"
                )
            if p["os"] in ("macOS", "linux") and p["dns"]:
                lines.append(
                    f'-- {T["ssh"]} | bash=/usr/bin/ssh param1={SSH_USER}@{p["dns"]}'
                    f" terminal=true sfimage=terminal"
                )
            if p["dns"]:
                lines.append(
                    f'-- {T["ping"]} | bash={TS} param1=ping param2=-c param3=3 param4={p["dns"]}'
                    f" terminal=true sfimage=waveform.path.ecg"
                )
            lines.append(
                f'-- {T["copy_ip"]} | bash=/bin/sh param1=-c param2="printf %s {p["ip"]} | pbcopy"'
                f" terminal=false sfimage=doc.on.doc"
            )
            if kind == "idle":
                lines.append(f'-- {T["hint_idle"]} | color={COLOR_OFFLINE}')
        else:
            if p["last_seen"] is not None:
                local = p["last_seen"].astimezone().strftime("%Y-%m-%d %H:%M")
                lines.append(f'-- {T["last_seen"]}: {local} | color={COLOR_OFFLINE}')

    # ---- footer ----
    lines.append("---")
    ctrl = control_url()
    if ctrl:
        lines.append(
            f'{T["headscale"]}: {clean(ctrl)} | href={ctrl}'
            f" sfimage=lock.shield color={COLOR_OFFLINE}"
        )
    lines.append(f'{T["full_status"]} | bash={TS} param1=status terminal=true sfimage=terminal')
    # Manual refresh: ping every online peer in parallel first (this triggers
    # NAT traversal / path discovery), then ask SwiftBar to rerun the plugin so
    # the status column reflects the freshly established paths.
    if online_dns:
        pings = " & ".join(
            f"{TS} ping -c 1 --timeout=1s {shlex.quote(h)} >/dev/null 2>&1"
            for h in online_dns
        )
        probe_cmd = pings + " & wait"
        lines.append(
            f'{T["refresh"]} | bash=/bin/sh param1=-c param2="{probe_cmd}"'
            f" terminal=false refresh=true sfimage=arrow.clockwise"
            f' tooltip="{clean(T["refresh_tip"])}"'
        )
    else:
        lines.append(f'{T["refresh"]} | refresh=true sfimage=arrow.clockwise')
    lines.append(
        f'{T["open_plugin_dir"]} | bash=/usr/bin/open param1="{PLUGIN_DIR}" terminal=false sfimage=folder'
    )

    emit(lines)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error_menu("err_plugin", [repr(exc)])
