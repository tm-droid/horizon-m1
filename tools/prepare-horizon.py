#!/usr/bin/env python3
"""Stage a hash-pinned official ARM64 launcher without executing it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import shlex
import shutil
import stat
import subprocess
import urllib.parse
import urllib.request
import zipfile


def extract_archive(archive, destination):
    """Extract regular files only, into a fresh private directory."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Installation destination must be fresh")
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        if len(entries) > 5000 or sum(i.file_size for i in entries) > 300 * 1024 ** 2:
            raise ValueError("Launcher archive exceeds staging limits")
        seen = set()
        for item in entries:
            name = item.filename
            path = PurePosixPath(name)
            key = name.rstrip("/").casefold()
            if (not name or path.is_absolute() or any(p in ("", ".", "..") for p in name.rstrip("/").split("/"))
                    or "\\" in name or ":" in name or "\x00" in name or key in seen):
                raise ValueError(f"Unsafe launcher archive entry: {name!r}")
            seen.add(key)
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("Launcher archive contains a symlink or special file")
        destination.mkdir(mode=0o700)
        try:
            for item in entries:
                target = destination.joinpath(*PurePosixPath(item.filename).parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output)
                target.chmod(0o755 if (item.external_attr >> 16) & 0o111 else 0o644)
        except BaseException:
            shutil.rmtree(destination)
            raise


def prepare(plan_path, root):
    plan = json.loads(plan_path.read_text())
    artifact = plan["launcher"]
    url = urllib.parse.urlparse(artifact["url"])
    expected = artifact["expected_sha256"]
    size = artifact["expected_size"]
    if (url.scheme != "https" or url.netloc != "github.com" or
            not url.path.startswith("/horizon-rust/horizon/releases/download/") or
            len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected) or
            not 0 < size <= 50 * 1024 ** 2):
        raise ValueError("Invalid pinned official launcher artifact")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    downloads = root / "downloads"
    downloads.mkdir(exist_ok=True)
    archive = downloads / "horizon-launcher-macos-arm64.zip"
    destination = root / "launcher-app"
    if destination.exists() or destination.is_symlink():
        raise ValueError("Launcher is already staged; existing installation is never overwritten")
    if not archive.exists():
        partial = archive.with_suffix(".part")
        try:
            request = urllib.request.Request(artifact["url"], headers={"User-Agent": "Tanush-Horizon-Preparation/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response, partial.open("xb") as output:
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > size:
                        raise ValueError("Download exceeded pinned size")
                    output.write(chunk)
            partial.rename(archive)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size != size:
        raise ValueError("Launcher archive is not the pinned regular file/size")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Launcher size/SHA256 does not match publisher metadata")
    extract_archive(archive, destination)
    apps = list(destination.glob("*.app"))
    if len(apps) != 1:
        raise ValueError("Expected exactly one official app bundle")
    info = plistlib.loads((apps[0] / "Contents/Info.plist").read_bytes())
    executable_name = info["CFBundleExecutable"]
    if (not isinstance(executable_name, str) or executable_name in ("", ".", "..") or
            Path(executable_name).name != executable_name):
        raise ValueError("Invalid app executable name")
    binary = apps[0] / "Contents/MacOS" / executable_name
    if binary.is_symlink() or not binary.is_file():
        raise ValueError("App executable must be a regular file")
    architecture = subprocess.run(["/usr/bin/file", "-b", str(binary)], check=True, capture_output=True, text=True).stdout.strip()
    if "arm64" not in architecture or "Mach-O" not in architecture:
        raise ValueError(f"Unexpected launcher architecture: {architecture}")
    binary.chmod(0o755)
    names = {"HORIZON_LAUNCHER_HOME", "HORIZON_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME"}
    if set(plan["environment_relative_paths"]) != names or plan["environment_literals"] != {"HORIZON_LAUNCHER_NO_SELF_UPDATE": "1"}:
        raise ValueError("Unexpected isolation environment")
    environment = {}
    for key, relative in plan["environment_relative_paths"].items():
        path = (root / relative).resolve()
        if path == root or root not in path.parents:
            raise ValueError("Isolation data directory escapes staging root")
        path.mkdir(parents=True, exist_ok=True)
        environment[key] = str(path)
    environment.update(plan["environment_literals"])
    command = "exec /usr/bin/env " + " ".join(shlex.quote(f"{key}={value}") for key, value in sorted(environment.items())) + " " + shlex.quote(str(binary)) + ' "$@"\n'
    wrapper = root / "launch-isolated.command"
    with wrapper.open("x") as stream:
        stream.write("#!/bin/zsh\nset -eu\n" + command)
    wrapper.chmod(0o755)
    record = {"schema": 1, "status": "launcher-prepared-not-launched", "launcher": artifact,
              "download_sha256": actual, "download_size": size, "app": str(apps[0]),
              "binary": str(binary), "architecture": architecture, "environment": environment,
              "wrapper": str(wrapper), "executed_launcher": False, "executed_game": False,
              "game_assets_prepared": False, "native_pilot_installed": False,
              "research_revision": plan["research_horizon_revision"],
              "note": "Launcher release differs from the converter source pin; game/native compatibility remains unverified."}
    (root / "installation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("status", "app", "download_sha256")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("docs/horizon-converter/install-plan.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/horizon-runtime"))
    args = parser.parse_args()
    prepare(args.plan, args.output)
