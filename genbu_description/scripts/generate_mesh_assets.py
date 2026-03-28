#!/usr/bin/env python3
"""
Generate web-friendly GLB mesh assets from a ROS URDF/Xacro robot description.

Usage:
    generate_mesh_assets.py <xacro_file> --output-dir <dir>

The script:
  1. Expands the Xacro file to a URDF string using the ``xacro`` tool.
  2. Parses the URDF to collect every ``<mesh filename="..."/>`` URI.
  3. Resolves ``package://`` and ``file://`` URIs to absolute paths.
  4. Converts each DAE / STL mesh to GLB using *trimesh*.
  5. Writes a ``manifest.json`` that maps logical names to output paths.

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

try:
    import trimesh  # type: ignore[import]
except ImportError as _trimesh_err:
    print(
        "ERROR: 'trimesh' is required but not installed. "
        "Install it with: pip install 'trimesh[easy]'",
        file=sys.stderr,
    )
    sys.exit(1)


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
    """Convert a DAE or STL file at *src* to GLB and write to *dst*.

    Returns ``True`` on success, ``False`` on failure.
    """
    try:
        scene = trimesh.load(src, force="scene")
        scene.export(dst, file_type="glb")
        return True
    except (OSError, ValueError, Exception) as exc:  # noqa: BLE001
        print(f"  ERROR converting {src}: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Logical naming
# ---------------------------------------------------------------------------

def logical_name(uri: str) -> str:
    """Derive a stable logical name from a mesh URI (stem of the filename)."""
    path = uri.split("/")[-1]
    return Path(path).stem


# ---------------------------------------------------------------------------
# Content hashing (for cache busting)
# ---------------------------------------------------------------------------

def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate GLB mesh assets from a URDF/Xacro robot description."
    )
    parser.add_argument("xacro_file", help="Path to the main .urdf.xacro file")
    parser.add_argument(
        "--output-dir", "-o", required=True, help="Destination directory for generated assets"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    meshes_dir = output_dir / "meshes"
    meshes_dir.mkdir(parents=True, exist_ok=True)

    # 1. Expand Xacro → URDF
    print(f"Expanding xacro: {args.xacro_file}")
    try:
        urdf_string = expand_xacro(args.xacro_file)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: xacro expansion failed:\n{exc.stderr}", file=sys.stderr)
        return 1

    # 2. Extract mesh URIs
    mesh_uris = extract_mesh_uris(urdf_string)
    print(f"Found {len(mesh_uris)} unique mesh reference(s)")

    manifest: dict[str, dict] = {}
    failures = 0

    for uri in mesh_uris:
        name = logical_name(uri)
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
        print(f"  {abs_path} → {glb_path}")
        if not convert_to_glb(abs_path, str(glb_path)):
            failures += 1
            continue

        # 5. Record in manifest
        manifest[name] = {
            "source": uri,
            "glb": str(glb_path.relative_to(output_dir)),
            "sha256": file_sha256(str(glb_path)),
        }
        print(f"  OK")

    # 6. Write manifest.json
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nManifest written to {manifest_path}")
    print(f"Converted {len(manifest)}/{len(mesh_uris)} mesh(es); {failures} failure(s)")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
