"""
Script to download the latest Windows .exe binaries for:
  - Claude Code (from GitHub releases)
  - OpenCode (from GitHub releases)
  - Codex (from GitHub releases)

Usage:
  python download_binaries.py           # Download all
  python download_binaries.py claude    # Download only Claude
  python download_binaries.py opencode  # Download only OpenCode
  python download_binaries.py codex     # Download only Codex
"""

import argparse
import hashlib
import sys
from pathlib import Path

import requests


def download_file(url: str, output_path: Path, description: str = "") -> bool:
    """Download a file from URL with progress indication."""
    try:
        print(f"Downloading {description or output_path.name}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size:
                    percent = (downloaded / total_size) * 100
                    print(f"\r  Progress: {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)", end="")

        print(f"\n  Downloaded: {output_path}")
        return True

    except Exception as e:
        print(f"  Error downloading: {e}")
        return False


def get_github_latest_release(owner: str, repo: str) -> dict | None:
    """Fetch the latest release info from GitHub API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching release info: {e}")
        return None


def download_claude() -> bool:
    """Download the latest Claude Code Windows .exe from GCS distribution bucket."""
    print("\n" + "=" * 60)
    print("CLAUDE CODE")
    print("=" * 60)

    GCS_BUCKET = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases"
    PLATFORM = "win32-x64"

    # Get latest version
    try:
        print("  Fetching latest version...")
        response = requests.get(f"{GCS_BUCKET}/latest")
        response.raise_for_status()
        version = response.text.strip()
        print(f"  Latest version: {version}")
    except Exception as e:
        print(f"  Error fetching latest version: {e}")
        return False

    # Get manifest for checksum
    try:
        print("  Fetching manifest...")
        response = requests.get(f"{GCS_BUCKET}/{version}/manifest.json")
        response.raise_for_status()
        manifest = response.json()
        checksum = manifest.get("platforms", {}).get(PLATFORM, {}).get("checksum")
        if not checksum:
            print(f"  Error: Platform {PLATFORM} not found in manifest")
            return False
        print(f"  Expected checksum: {checksum[:16]}...")
    except Exception as e:
        print(f"  Error fetching manifest: {e}")
        return False

    # Download binary
    download_url = f"{GCS_BUCKET}/{version}/{PLATFORM}/claude.exe"
    output_path = Path("claude.exe")

    success = download_file(download_url, output_path, f"Claude Code {version}")

    if not success:
        return False

    # Verify checksum
    print("  Verifying checksum...")
    sha256_hash = hashlib.sha256()
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    actual_checksum = sha256_hash.hexdigest().lower()

    if actual_checksum != checksum.lower():
        print(f"  Error: Checksum verification failed!")
        print(f"    Expected: {checksum}")
        print(f"    Actual:   {actual_checksum}")
        output_path.unlink()
        return False

    print(f"  Checksum verified")
    print(f"  Claude Code {version} downloaded successfully")
    return True


def download_opencode() -> bool:
    """Download the latest OpenCode Windows .exe from GitHub releases."""
    print("\n" + "=" * 60)
    print("OPENCODE")
    print("=" * 60)

    release_data = get_github_latest_release("sst", "opencode")
    if not release_data:
        return False

    version = release_data.get("tag_name", "unknown")
    print(f"  Latest version: {version}")

    # Find Windows .exe asset (prefer x64)
    windows_asset = None
    fallback_zip = None

    for asset in release_data.get("assets", []):
        name = asset["name"].lower()
        # Prefer .exe files
        if "windows" in name and name.endswith(".exe"):
            if "x64" in name or "x86_64" in name or "amd64" in name:
                windows_asset = asset
                break
            elif windows_asset is None:
                windows_asset = asset
        # Track .zip as fallback
        elif "windows" in name and name.endswith(".zip") and fallback_zip is None:
            fallback_zip = asset

    # Use .zip fallback if no .exe found
    if not windows_asset and fallback_zip:
        windows_asset = fallback_zip
        print("  Note: No .exe found, falling back to .zip")

    if not windows_asset:
        print("  Error: No Windows release found in latest release")
        print("  Available assets:")
        for asset in release_data.get("assets", []):
            print(f"    - {asset['name']}")
        return False

    asset_name = windows_asset["name"]
    download_url = windows_asset["browser_download_url"]

    output_path = Path(asset_name)
    success = download_file(download_url, output_path, f"OpenCode {version}")

    if success:
        # Rename .exe to simpler name
        if output_path.suffix == ".exe":
            simple_name = "opencode.exe"
            if output_path.name != simple_name:
                output_path.rename(simple_name)
                print(f"  Renamed to: {simple_name}")
        print(f"  OpenCode {version} downloaded successfully")

    return success


def download_codex() -> bool:
    """Download the latest Codex Windows release from GitHub."""
    print("\n" + "=" * 60)
    print("CODEX")
    print("=" * 60)

    release_data = get_github_latest_release("openai", "codex")
    if not release_data:
        return False

    version = release_data.get("tag_name", "unknown")
    print(f"  Latest version: {version}")

    # Find Windows x64 executable (prefer x86_64 for broader compatibility)
    windows_assets = []
    for asset in release_data.get("assets", []):
        name = asset["name"].lower()
        # Look for Windows executables (x86_64 preferred)
        if "windows" in name and name.endswith(".exe") and "x86_64" in name:
            # Skip auxiliary tools, prioritize main codex binary
            if asset["name"].startswith("codex-x86_64"):
                windows_assets.insert(0, asset)  # Main binary first
            else:
                windows_assets.append(asset)

    if not windows_assets:
        # Fallback to aarch64 if no x86_64
        for asset in release_data.get("assets", []):
            name = asset["name"].lower()
            if "windows" in name and name.endswith(".exe"):
                windows_assets.append(asset)

    if not windows_assets:
        print("  Error: No Windows release found in latest release")
        print("  Available assets:")
        for asset in release_data.get("assets", [])[:10]:
            print(f"    - {asset['name']}")
        print("    ...")
        return False

    # Download main codex binary
    main_asset = windows_assets[0]
    asset_name = main_asset["name"]
    download_url = main_asset["browser_download_url"]

    output_path = Path(asset_name)
    success = download_file(download_url, output_path, f"Codex {version}")

    if success:
        # Rename to simpler name
        simple_name = "codex.exe"
        output_path.rename(simple_name)
        print(f"  Renamed to: {simple_name}")
        print(f"  Codex {version} downloaded successfully")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Download latest Windows binaries for Claude, OpenCode, and Codex"
    )
    parser.add_argument(
        "tools",
        nargs="*",
        choices=["claude", "opencode", "codex"],
        help="Specific tools to download (default: all)"
    )

    args = parser.parse_args()

    # If no tools specified, download all
    tools_to_download = args.tools if args.tools else ["claude", "opencode", "codex"]

    print("Binary Downloader")
    print("=" * 60)
    print(f"Tools to download: {', '.join(tools_to_download)}")

    results = {}

    if "claude" in tools_to_download:
        results["Claude Code"] = download_claude()

    if "opencode" in tools_to_download:
        results["OpenCode"] = download_opencode()

    if "codex" in tools_to_download:
        results["Codex"] = download_codex()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for tool, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {tool}: {status}")

    # Exit with error if any downloads failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
