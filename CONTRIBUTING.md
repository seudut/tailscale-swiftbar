# Contributing

Thanks for taking a look! This plugin is a single Python script driving a
SwiftBar menu. Keep changes small and testable.

## Layout

| Path | Purpose |
|---|---|
| `tailnet.10s.py` | The plugin (run directly by SwiftBar; no dependencies beyond `python3`). |
| `install.sh` | Copies the plugin into the SwiftBar plugin folder (no sudo). |
| `tests/validate_swiftbar.py` | Runs the plugin against a fake `tailscale` CLI and validates the output format/semantics. |
| `tests/fake-tailscale` | Fake CLI used by tests (returns `tests/fixtures/status.json`). |
| `.github/workflows/` | CI (syntax + format validation) and tag-based release packaging. |

## Local checks

```sh
python3 -m py_compile tailnet.10s.py
python3 tests/validate_swiftbar.py
sh -n install.sh
```

The validator sets `TAILNET_TS_BIN=tests/fake-tailscale`, `TAILNET_LANG=en` and
`TAILNET_KEEPALIVE=0`, then asserts:

- first line is the menu bar title and contains the inline Tailscale icon
  (`templateImage`, a base64 PDF)
- body items use SwiftBar 2.x format: plain titles, `--` for submenus, `---`
  separators; no unknown parameters
- status keywords are limited to `direct` / `relay` / `peer-relay` / `idle` /
  `-` / `offline`
- device rows do not contain `tx`/`rx` counters

## Style

- Python 3.9+ (runs on the system `python3`), standard library only.
- Keep menu output deterministic for a given `tailscale status --json` snapshot.
- No network calls in the plugin; only local `tailscale` CLI + JSON parsing.
- Status classification must stay aligned with `cmd/tailscale/cli/status.go`
  (`printPS`) for the matching Tailscale version; the public UI only shows the
  compact keyword.

## Releases

1. Update `# <xbar.version>` in `tailnet.10s.py` and `CHANGELOG.md`.
2. Run the local checks above.
3. Commit, tag `vX.Y` and push both:
   `git push origin main && git push origin vX.Y`
4. The `Release` workflow packages `tailnet.10s.py`, `install.sh`, docs and
   creates a GitHub Release with the zip attached.
