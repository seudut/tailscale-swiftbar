# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); versions follow
the plugin's `<xbar.version>`.

## [1.14.0] - 2026-10-26

Initial public release.

### Added
- Automatic background keepalive: every 60s (`TAILNET_KEEPALIVE`) the plugin
  pings all online peers in the background so direct paths stay warm and the
  status does not fall back to `-` / `idle`. Set to `0` to disable.
- Portable `install.sh` (works from a checkout, a release zip, or `curl | sh`).
- Test suite (`tests/`) with a fake `tailscale` CLI and a SwiftBar output
  validator; GitHub Actions CI and tag-triggered release workflow.
- Dynamic Headscale control URL read from `tailscale debug prefs` (no
  hard-coded server address); `TAILNET_CONTROL_URL` still overrides it.
- MIT license, changelog, contributing guide.

### Changed
- Docs and preview images use generic example hostnames/IPs
  (`headscale.example.com`, `tailnet.example.com`, `192.168.1.x`).

### Removed
- Inline `last seen` text on offline rows (the exact timestamp is shown in the
  device submenu), `tx/rx` counters, OS name text, and direct-address /
  DERP-region details from the compact status column.

## [1.13.0] - 2026-10-26
- Offline rows show only `offline`; exact `last seen` timestamp moved to the submenu.

## [1.12.0] - 2026-10-26
- Final colors: `offline` gray (de-emphasized), `idle` / `-` default text color.

## [1.11.0] - 2026-10-26
- Experiment: swapped offline/idle colors (reverted in 1.12).

## [1.10.0] - 2026-10-25
- Compactly show only the status keyword: `direct` / `relay` / `peer-relay` /
  `idle` / `-` / `offline`; hide direct address, DERP region and `tx/rx`.

## [1.9.0] - 2026-10-25
- Hide `tx/rx` traffic counters from device rows.

## [1.8.0] - 2026-10-25
- Manual Refresh now pings all online peers in parallel before refreshing.

## [1.7.0] - 2026-10-25
- Status classification now matches the last column of `tailscale status`
  (`Online` / `Active` / `CurAddr` / `Relay` / `PeerRelay` / `TxBytes` / `RxBytes`),
  fixing same-LAN idle peers being misreported as `relay`.

## [1.6.0] - 2026-10-25
- Device icons switched from SF Symbols to OS emoji (fixes root-level menu icons
  not rendering on macOS 26); OS name text removed.

## [1.5.0] - 2026-10-25
- Self row: drop `This Mac` label, keep `・💻` marker + hostname.

## [1.4.0] - 2026-10-25
- OS emoji icons (💻 / 🖥️ / 📱).

## [1.3.0] - 2026-10-25
- Menu bar icon: Tailscale dot mark (inline 18×18 vector PDF template image) +
  online/total count.
- `・` prefix on the self row.

## [1.2.0] - 2026-10-25
- Connection colors: direct green / relay orange / offline gray.
- Menu text i18n following the system language (`TAILNET_LANG=en|zh`).

## [1.1.0] - 2026-10-25
- Fix SwiftBar 2.x body format (no `--` prefix on body items).

## [1.0.0] - 2026-10-25
- Initial plugin: device list, online state, SSH / Screen Sharing / Ping / Copy IP.
