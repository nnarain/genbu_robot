#!/usr/bin/env python3
"""
Generate web-friendly GLB mesh assets from a ROS URDF/Xacro robot description.

Usage:
    generate_mesh_assets.py <xacro_file> --output-dir <dir>

The script:
    1. Expands the Xacro file to a URDF string using the ``xacro`` tool.
    2. Parses the URDF to collect every ``<mesh filename="..."/>`` URI.
    3. Resolves ``package://`` and ``file://`` URIs to absolute paths.
    4. Converts each DAE / STL mesh to GLB.
    5. Writes a minimal ``manifest.json`` mapping source file paths to GLB paths.

All outputs are placed under *output_dir*:
  <output_dir>/meshes/<name>.glb
  <output_dir>/manifest.json
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# URDF / Xacro helpers
# ---------------------------------------------------------------------------

def expand_xacro(xacro_file: str) -> str:
    """Return the URDF XML produced by expanding *xacro_file*."""
    result = subprocess.run(
        ["xacro", xacro_file],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def extract_mesh_uris(urdf_string: str) -> list[str]:
    """Return a deduplicated list of all mesh ``filename`` attributes in *urdf_string*."""
    root = ET.fromstring(urdf_string)
    seen: set[str] = set()
    uris: list[str] = []
    for mesh in root.iter("mesh"):
        filename = mesh.get("filename", "")
        if filename and filename not in seen:
            seen.add(filename)
            uris.append(filename)
    return uris


def build_logical_name_map(mesh_uris: list[str]) -> dict[str, str]:
    """Build stable logical names for each URI, handling stem collisions deterministically."""
    by_stem: dict[str, list[str]] = {}
    for uri in mesh_uris:
        stem = Path(uri.split("/")[-1]).stem
        by_stem.setdefault(stem, []).append(uri)

    name_map: dict[str, str] = {}
    for stem, uris in by_stem.items():
        uris.sort()
        if len(uris) == 1:
            name_map[uris[0]] = stem
            continue

        for uri in uris:
            suffix = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:8]
            name_map[uri] = f"{stem}_{suffix}"

    return name_map


# ---------------------------------------------------------------------------
# URI resolution
# ---------------------------------------------------------------------------

def _ros2_pkg_share(package_name: str) -> str:
    """Return the share directory for a ROS 2 package."""
    result = subprocess.run(
        ["ros2", "pkg", "prefix", package_name],
        capture_output=True,
        text=True,
        check=True,
    )
    prefix = result.stdout.strip()
    return os.path.join(prefix, "share", package_name)


def resolve_uri(uri: str) -> str | None:
    """Resolve a ``package://`` or ``file://`` URI to an absolute path.

    Returns *None* if the URI cannot be resolved.
    """
    if uri.startswith("package://"):
        remainder = uri[len("package://"):]
        parts = remainder.split("/", 1)
        package_name = parts[0]
        relative_path = parts[1] if len(parts) > 1 else ""
        try:
            share_dir = _ros2_pkg_share(package_name)
            return os.path.join(share_dir, relative_path)
        except subprocess.CalledProcessError:
            return None

    if uri.startswith("file://"):
        return urllib.parse.unquote(uri[len("file://"):])

    return None


# ---------------------------------------------------------------------------
# Mesh conversion
# ---------------------------------------------------------------------------

def convert_to_glb(src: str, dst: str) -> bool:
    """
    Convert input mesh to GLB format.
    """
    cmd = f'assimp export "{src}" "{dst}" --format glb --embed'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR converting {src} to {dst}:\n{result.stderr}", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args):

    urdf_path = Path(args.urdf)
    if not urdf_path.exists():
        raise FileNotFoundError(f"URDF file not found: {urdf_path}")

    output_dir = Path(args.output_dir)
    meshes_dir = output_dir / "meshes"
    meshes_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    # 1. Expand Xacro → URDF
    print(f"Expanding xacro: {args.urdf}")
    try:
        urdf_string = expand_xacro(args.urdf)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to expand xacro: {exc.stderr}") from exc

    # 2. Extract mesh URIs
    mesh_uris = extract_mesh_uris(urdf_string)
    mesh_uris = sorted(mesh_uris)
    uri_name_map = build_logical_name_map(mesh_uris)

    print(f"Found {len(mesh_uris)} unique mesh reference(s)")

    manifest_entries: dict[str, str] = {}
    failures = 0
    converted = 0

    for uri in mesh_uris:
        name = uri_name_map[uri]
        print(f"\nProcessing: {uri}")

        # 3. Resolve URI → absolute path
        abs_path = resolve_uri(uri)
        if abs_path is None:
            print(f"  WARNING: unrecognised URI scheme, skipping: {uri}", file=sys.stderr)
            failures += 1
            continue
        if not os.path.exists(abs_path):
            print(f"  WARNING: file not found: {abs_path}", file=sys.stderr)
            failures += 1
            continue

        # 4. Convert to GLB
        glb_path = meshes_dir / f"{name}.glb"
        rel_glb = str(glb_path.resolve())
        print(f"  {abs_path} → {glb_path}")
        if not convert_to_glb(abs_path, str(glb_path)):
            failures += 1
            continue
        converted += 1

        # 5. Record in manifest
        manifest_entries[Path(abs_path).name] = rel_glb
        print(f"  OK")

    # 6. Write manifest.json
    manifest = dict(sorted(manifest_entries.items()))
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    print(f"\nManifest written to {manifest_path}")
    print(
        "Converted "
        f"{len(manifest_entries)}/{len(mesh_uris)} mesh(es); "
        f"{converted} converted, {failures} failure(s)"
    )

    if failures > 0:
        raise RuntimeError(f"{failures} mesh conversion(s) failed; see warnings above")
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GLB mesh assets from a URDF/Xacro robot description.")
    parser.add_argument("urdf", help="Path to the main .urdf file")
    parser.add_argument("--output-dir", "-o", required=True, help="Destination directory for generated assets")

    args = parser.parse_args()

    sys.exit(main(args))
