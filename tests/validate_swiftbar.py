#!/usr/bin/env python3
"""Validate the plugin output without a real Tailscale installation.

Runs `tailnet.10s.py` against `tests/fake-tailscale` and checks the SwiftBar 2.x
output format plus the compact status semantics. Exit code 0 = OK.
"""

import base64
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "tailnet.10s.py")
FAKE_TS = os.path.join(ROOT, "tests", "fake-tailscale")

ALLOWED_PARAMS = {
    "color", "sfimage", "sfcolor", "bash", "terminal", "href",
    "refresh", "tooltip", "length", "templateimage", "width", "height",
} | {f"param{i}" for i in range(1, 11)}
ALLOWED_STATUS = {"direct", "relay", "peer-relay", "idle", "-", "offline"}
DEVICE_ICONS = ("💻", "🖥️", "📱", "❓")


def parse_line(line):
    if line == "---":
        return 0, True, "---"
    work, level = line, 0
    while work.startswith("--"):
        work = work[2:]
        level += 1
        if work == "---":
            break
    return level, work == "---", work.strip()


def parse_params(work):
    idx = work.find("|")
    if idx < 0:
        return work.strip(), {}
    title = work[:idx].rstrip()
    rest = work[idx + 1:].strip()
    params, i, chars = {}, 0, list(rest)
    while i < len(chars):
        while i < len(chars) and chars[i] in " \t":
            i += 1
        if i >= len(chars):
            break
        start = i
        while i < len(chars) and chars[i] != "=":
            i += 1
        if i >= len(chars) or chars[i] != "=":
            break
        key = "".join(chars[start:i]).strip().lower()
        i += 1
        while i < len(chars) and chars[i] in " \t":
            i += 1
        val = ""
        if i < len(chars) and chars[i] in "\"'":
            q = chars[i]
            i += 1
            while i < len(chars) and chars[i] != q:
                val += chars[i]
                i += 1
            i += 1
        else:
            s = i
            while i < len(chars) and chars[i] not in " \t":
                i += 1
            val = "".join(chars[s:i])
        params[key] = val
    return title, params


def run_plugin():
    env = dict(os.environ)
    env.update(
        {
            "TAILNET_TS_BIN": FAKE_TS,
            "TAILNET_LANG": "en",
            "TAILNET_KEEPALIVE": "0",
            "TAILNET_CONTROL_URL": "",
            "SWIFTBAR_PLUGIN_DATA_PATH": tempfile.mkdtemp(prefix="tailnet-test-"),
        }
    )
    proc = subprocess.run(
        [sys.executable, PLUGIN], cwd=ROOT, env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, f"plugin exited {proc.returncode}:\n{proc.stderr}"
    assert not proc.stderr.strip(), f"unexpected stderr:\n{proc.stderr}"
    return proc.stdout


def main():
    out = run_plugin()
    lines = [l for l in out.splitlines() if l]
    idx = next(i for i, l in enumerate(lines) if l.startswith("---"))
    header, body = lines[:idx], lines[idx:]
    assert len(header) == 1, f"header must be exactly 1 title line, got {header}"

    title, tparams = parse_params(header[0])
    assert title == "4/5", f"expected title 4/5 for the fixture, got {title!r}"
    b64 = tparams.get("templateimage", "")
    assert b64, "title is missing the inline tailscale icon (templateImage)"
    assert base64.b64decode(b64)[:5] == b"%PDF-", "templateImage is not a PDF"

    stack, roots, children, statuses = [], [], [], []
    for line in body:
        level, is_sep, work = parse_line(line)
        if is_sep:
            stack = [(0, "---")]
            continue
        name, params = parse_params(work)
        assert name, f"empty title: {line!r}"
        unknown = set(params) - ALLOWED_PARAMS
        assert not unknown, f"unknown params {unknown}: {line!r}"
        while stack and stack[-1][0] >= level:
            stack.pop()
        if level == 0:
            roots.append(name)
        else:
            assert stack and stack[-1][0] == level - 1, f"submenu without parent: {line!r}"
            children.append(name)
        stack.append((level, name))
        if level == 0 and name.startswith(DEVICE_ICONS):
            status = name.rsplit("· ", 1)[-1].strip()
            statuses.append(status)
            assert status in ALLOWED_STATUS, f"unexpected status {status!r} in {line!r}"
            assert "tx " not in name and "rx " not in name, f"tx/rx leaked: {line!r}"

    assert len(roots) >= 5, f"too few root items: {roots}"
    assert {"direct", "relay", "idle", "offline"} <= set(statuses), (
        f"fixture should exercise all states, got {statuses}"
    )
    joined = "\n".join(lines)
    assert "headscale.example.com" in joined, "control URL not detected from prefs"
    assert "param1=-c" in joined, "Refresh item should ping peers first"

    print("VALIDATION OK")
    print(f"title: {title}")
    print(f"root items: {len(roots)} | submenu items: {len(children)}")
    print(f"device statuses: {statuses}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
