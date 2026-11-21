# Security

## Reporting a problem

Report security problems privately through
[GitHub's private advisory form](https://github.com/tm-droid/horizon-m1/security/advisories/new),
not as a public issue. Expect an answer within a few days. Fixes ship as a new Horizon M1 build.

## What the installer does

- The one-line install (`install.sh`, also served as `https://tm-droid.github.io/horizon-m1/i`) asks the GitHub API
  for the latest release, downloads `Horizon-M1.zip` over HTTPS and stops unless its SHA-256 matches the digest
  GitHub computed when the file was uploaded. Then it runs `Install Horizon M1.command` from the zip.
- The installer writes only to `/Applications/Horizon.app`, `~/Applications/Horizon M1.app`,
  `~/Library/Application Support/horizon-launcher` and `~/Library/Application Support/horizon`. It needs no
  administrator password and changes no system settings.
- For offline play without a Microsoft account it can download Minecraft 26.3 from Mojang's public servers;
  every file is checked against the SHA-1 Mojang lists.
- The Horizon M1 app checks `releases/latest/download/horizon-m1.json` at most once a day and updates only
  after you click Update, by running the same one-line install. `touch
  ~/Library/Application\ Support/horizon-launcher/horizon-m1/no-updates` turns the check off.
- Builds are signed ad hoc, not notarized by Apple. Files fetched with `curl` carry no quarantine flag, so
  macOS shows no warning for them.

## Supported versions

Only the latest release gets fixes.
