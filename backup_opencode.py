"""
Script to backup and restore OpenCode configuration and cache directories.
Supports two modes:
  - collect: Backup directories to a zip file
  - export: Restore directories from a zip file
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from datetime import datetime
import requests


def get_opencode_dirs():
    """Get the OpenCode config, cache, and bun cache directories using Path.home()."""
    home = Path.home()
    config_dir = home / ".config" / "opencode"
    cache_dir = home / ".cache" / "opencode"
    bun_cache_dir = home / ".bun" / "install" / "cache"
    return config_dir, cache_dir, bun_cache_dir


def download_opencode_windows_release():
    """Download the latest OpenCode Windows release from GitHub."""
    print("Fetching latest OpenCode release from GitHub...")

    api_url = "https://api.github.com/repos/sst/opencode/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        release_data = response.json()

        # Find Windows asset
        windows_asset = None
        for asset in release_data.get("assets", []):
            if "windows" in asset["name"].lower() and asset["name"].endswith(".zip"):
                windows_asset = asset
                break

        if not windows_asset:
            print("Warning: No Windows release found in latest release")
            return None

        asset_name = windows_asset["name"]
        download_url = windows_asset["browser_download_url"]

        print(f"Downloading {asset_name}...")

        # Download the file
        asset_response = requests.get(download_url, stream=True)
        asset_response.raise_for_status()

        output_path = Path(asset_name)

        with open(output_path, 'wb') as f:
            for chunk in asset_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Downloaded {asset_name}")
        return output_path

    except Exception as e:
        print(f"Error downloading OpenCode release: {e}")
        return None


def collect(output_file=None, password=None):
    """Collect OpenCode directories and create a zip backup."""
    # Download latest OpenCode Windows release
    opencode_release = download_opencode_windows_release()

    config_src, cache_src, bun_cache_src = get_opencode_dirs()

    # Create a temporary directory for staging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"opencode_backup_{timestamp}")
    config_dest = backup_dir / "config"
    cache_dest = backup_dir / "cache"
    bun_cache_dest = backup_dir / "bun_cache"

    try:
        # Create backup directory structure
        backup_dir.mkdir(exist_ok=True)

        # Copy config directory
        if config_src.exists():
            print(f"Copying {config_src} to {config_dest}...")
            shutil.copytree(config_src, config_dest)
        else:
            print(f"Warning: {config_src} does not exist")

        # Copy cache directory
        if cache_src.exists():
            print(f"Copying {cache_src} to {cache_dest}...")
            shutil.copytree(cache_src, cache_dest)
        else:
            print(f"Warning: {cache_src} does not exist")

        # Copy bun cache directory
        if bun_cache_src.exists():
            print(f"Copying {bun_cache_src} to {bun_cache_dest}...")
            shutil.copytree(bun_cache_src, bun_cache_dest)
        else:
            print(f"Warning: {bun_cache_src} does not exist")

        # Create zip file
        if output_file is None:
            zip_filename = f"opencode_backup_{timestamp}.zip"
        else:
            zip_filename = output_file

        # Use system zip command for password protection if password is provided
        if password:
            print(f"Creating password-protected zip file: {zip_filename}...")
            # Change to backup directory and create password-protected zip
            try:
                subprocess.run(
                    ["zip", "-r", "-P", password, f"../{zip_filename}", "."],
                    cwd=backup_dir,
                    check=True,
                    capture_output=True
                )
                print(f"✓ Password protection applied")
            except subprocess.CalledProcessError as e:
                print(f"Error creating password-protected zip: {e}")
                print(f"Falling back to unprotected zip...")
                password = None

        if not password:
            print(f"Creating zip file: {zip_filename}...")
            # Create unprotected zip using Python's zipfile module
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through the backup directory and add all files
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(backup_dir)
                        zipf.write(file_path, arcname)

        print(f"✓ Collection completed successfully: {zip_filename}")
        if opencode_release:
            print(f"✓ OpenCode Windows release downloaded: {opencode_release}")
        return zip_filename

    finally:
        # Clean up temporary directory
        if backup_dir.exists():
            print("Cleaning up temporary files...")
            shutil.rmtree(backup_dir)


def export(zip_file, password=None):
    """Export (restore) OpenCode directories from a zip backup."""
    config_dest, cache_dest, bun_cache_dest = get_opencode_dirs()

    if not Path(zip_file).exists():
        print(f"Error: Zip file not found: {zip_file}")
        sys.exit(1)

    # Create a temporary directory for extraction
    temp_dir = Path(f"opencode_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    try:
        temp_dir.mkdir(exist_ok=True)

        if password:
            # Use system unzip command for password-protected archives
            print(f"Extracting password-protected zip file: {zip_file}...")
            try:
                subprocess.run(
                    ["unzip", "-P", password, "-d", str(temp_dir), zip_file],
                    check=True,
                    capture_output=True
                )
                print(f"✓ Successfully extracted with password")
            except subprocess.CalledProcessError as e:
                print(f"Error extracting password-protected zip: {e}")
                print("Trying with Python's zipfile module...")
                with zipfile.ZipFile(zip_file, 'r') as zipf:
                    zipf.extractall(temp_dir, pwd=password.encode())
                print(f"✓ Successfully extracted with password")
        else:
            print(f"Extracting {zip_file}...")
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                zipf.extractall(temp_dir)

        # Restore config directory
        config_src = temp_dir / "config"
        if config_src.exists():
            if config_dest.exists():
                print(f"Removing existing {config_dest}...")
                shutil.rmtree(config_dest)
            print(f"Restoring {config_src} to {config_dest}...")
            config_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(config_src, config_dest)
        else:
            print(f"Warning: config directory not found in zip file")

        # Restore cache directory
        cache_src = temp_dir / "cache"
        if cache_src.exists():
            if cache_dest.exists():
                print(f"Removing existing {cache_dest}...")
                shutil.rmtree(cache_dest)
            print(f"Restoring {cache_src} to {cache_dest}...")
            cache_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(cache_src, cache_dest)
        else:
            print(f"Warning: cache directory not found in zip file")

        # Restore bun cache directory
        bun_cache_src = temp_dir / "bun_cache"
        if bun_cache_src.exists():
            if bun_cache_dest.exists():
                print(f"Removing existing {bun_cache_dest}...")
                shutil.rmtree(bun_cache_dest)
            print(f"Restoring {bun_cache_src} to {bun_cache_dest}...")
            bun_cache_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(bun_cache_src, bun_cache_dest)
        else:
            print(f"Warning: bun_cache directory not found in zip file")

        print(f"✓ Export completed successfully")

    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            print("Cleaning up temporary files...")
            shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Backup and restore OpenCode configuration and cache directories"
    )
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run", required=True)

    # Collect mode
    collect_parser = subparsers.add_parser("collect", help="Collect and backup directories to a zip file")
    collect_parser.add_argument(
        "-o", "--output",
        help="Output zip file name (default: opencode_backup_TIMESTAMP.zip)"
    )
    collect_parser.add_argument(
        "-p", "--password",
        help="Password to protect the zip file"
    )

    # Export mode
    export_parser = subparsers.add_parser("export", help="Export (restore) directories from a zip file")
    export_parser.add_argument(
        "zip_file",
        help="Zip file to restore from"
    )
    export_parser.add_argument(
        "-p", "--password",
        help="Password to extract the zip file"
    )

    args = parser.parse_args()

    if args.mode == "collect":
        collect(args.output, args.password)
    elif args.mode == "export":
        export(args.zip_file, args.password)


if __name__ == "__main__":
    main()
