"""
Script to backup and restore OpenCode configuration and cache directories.
Supports two modes:
  - collect: Backup directories to a zip file
  - export: Restore directories from a zip file
"""

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path
from datetime import datetime


def get_opencode_dirs():
    """Get the OpenCode config, cache, and bun cache directories using Path.home()."""
    home = Path.home()
    config_dir = home / ".config" / "opencode"
    cache_dir = home / ".cache" / "opencode"
    bun_cache_dir = home / ".bun" / "install" / "cache"
    return config_dir, cache_dir, bun_cache_dir


def collect(output_file=None):
    """Collect OpenCode directories and create a zip backup."""
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

        print(f"Creating zip file: {zip_filename}...")

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the backup directory and add all files
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(backup_dir)
                    zipf.write(file_path, arcname)

        print(f"✓ Collection completed successfully: {zip_filename}")
        return zip_filename

    finally:
        # Clean up temporary directory
        if backup_dir.exists():
            print("Cleaning up temporary files...")
            shutil.rmtree(backup_dir)


def export(zip_file):
    """Export (restore) OpenCode directories from a zip backup."""
    config_dest, cache_dest, bun_cache_dest = get_opencode_dirs()

    if not Path(zip_file).exists():
        print(f"Error: Zip file not found: {zip_file}")
        sys.exit(1)

    # Create a temporary directory for extraction
    temp_dir = Path(f"opencode_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    try:
        # Extract zip file
        print(f"Extracting {zip_file}...")
        temp_dir.mkdir(exist_ok=True)

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

    # Export mode
    export_parser = subparsers.add_parser("export", help="Export (restore) directories from a zip file")
    export_parser.add_argument(
        "zip_file",
        help="Zip file to restore from"
    )

    args = parser.parse_args()

    if args.mode == "collect":
        collect(args.output)
    elif args.mode == "export":
        export(args.zip_file)


if __name__ == "__main__":
    main()
