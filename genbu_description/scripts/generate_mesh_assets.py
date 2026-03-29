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
    5. Writes a ``manifest.json`` mapping source file names to GLB paths and
       the mesh's global pose (xyz / rpy relative to the robot root link).

All outputs are placed under *output_dir*:
  <output_dir>/meshes/<name>.glb
  <output_dir>/manifest.json

Manifest entry format::

    {
      "<source_filename>": {
        "glb": "<absolute_path_to_glb>",
        "xyz": [x, y, z],
        "rpy": [roll, pitch, yaw]
      },
      ...
    }
"""

import argparse
import hashlib
import json
import math
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
# URDF pose extraction helpers
# ---------------------------------------------------------------------------

def _parse_floats(s: str) -> list[float]:
    """Parse a space-separated string of floats; returns [0, 0, 0] for empty input."""
    return [float(v) for v in s.split()] if s.strip() else [0.0, 0.0, 0.0]


def _rpy_to_matrix(rpy: list[float]) -> list[list[float]]:
    """Convert RPY Euler angles (extrinsic XYZ / R = Rz·Ry·Rx) to a 3×3 rotation matrix."""
    r, p, y = rpy
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    return [
        [ cy * cp,  cy * sp * sr - sy * cr,  cy * sp * cr + sy * sr],
        [ sy * cp,  sy * sp * sr + cy * cr,  sy * sp * cr - cy * sr],
        [-sp,        cp * sr,                  cp * cr              ],
    ]


def _matrix_to_rpy(m: list[list[float]]) -> list[float]:
    """Convert a 3×3 rotation matrix to RPY Euler angles (extrinsic XYZ / R = Rz·Ry·Rx)."""
    pitch = math.atan2(-m[2][0], math.sqrt(m[0][0] ** 2 + m[1][0] ** 2))
    if abs(math.cos(pitch)) < 1e-10:  # gimbal lock
        roll = 0.0
        yaw = math.atan2(-m[1][2], m[1][1])
    else:
        roll = math.atan2(m[2][1], m[2][2])
        yaw = math.atan2(m[1][0], m[0][0])
    return [roll, pitch, yaw]


def _compose_transforms(
    parent_xyz: list[float],
    parent_rpy: list[float],
    child_xyz: list[float],
    child_rpy: list[float],
) -> tuple[list[float], list[float]]:
    """Compose two SE(3) transforms: T_parent * T_child → (xyz, rpy)."""
    R_p = _rpy_to_matrix(parent_rpy)
    R_c = _rpy_to_matrix(child_rpy)

    # Rotate child origin by parent rotation and add parent origin
    rotated = [
        R_p[0][0] * child_xyz[0] + R_p[0][1] * child_xyz[1] + R_p[0][2] * child_xyz[2],
        R_p[1][0] * child_xyz[0] + R_p[1][1] * child_xyz[1] + R_p[1][2] * child_xyz[2],
        R_p[2][0] * child_xyz[0] + R_p[2][1] * child_xyz[1] + R_p[2][2] * child_xyz[2],
    ]
    xyz = [parent_xyz[i] + rotated[i] for i in range(3)]

    # Compose rotation matrices R = R_p * R_c
    R = [
        [sum(R_p[i][k] * R_c[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]
    rpy = _matrix_to_rpy(R)
    return xyz, rpy


_IDENTITY_POSE: tuple[list[float], list[float]] = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])


def extract_link_poses(urdf_string: str) -> dict[str, tuple[list[float], list[float]]]:
    """Compute the global pose (relative to the root link) of every link in the URDF.

    Returns a dict mapping link name → (xyz, rpy).
    """
    root_xml = ET.fromstring(urdf_string)

    # child_link_name → (parent_link_name, local_xyz, local_rpy)
    joint_map: dict[str, tuple[str, list[float], list[float]]] = {}
    for joint in root_xml.iter("joint"):
        parent_el = joint.find("parent")
        child_el = joint.find("child")
        origin_el = joint.find("origin")
        if parent_el is None or child_el is None:
            continue
        parent_name = parent_el.get("link", "")
        child_name = child_el.get("link", "")
        xyz = _parse_floats(origin_el.get("xyz", "") if origin_el is not None else "")
        rpy = _parse_floats(origin_el.get("rpy", "") if origin_el is not None else "")
        joint_map[child_name] = (parent_name, xyz, rpy)

    # The root link(s) are those that never appear as a joint child
    all_links = {link.get("name", "") for link in root_xml.iter("link")}
    root_links = all_links - set(joint_map.keys())

    # BFS: propagate poses from roots outward
    poses: dict[str, tuple[list[float], list[float]]] = {
        link: ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) for link in root_links
    }
    changed = True
    while changed:
        changed = False
        for child, (parent, local_xyz, local_rpy) in joint_map.items():
            if child not in poses and parent in poses:
                parent_xyz, parent_rpy = poses[parent]
                poses[child] = _compose_transforms(
                    parent_xyz, parent_rpy, local_xyz, local_rpy
                )
                changed = True

    return poses


def extract_mesh_uri_to_link(urdf_string: str) -> dict[str, str]:
    """Return a mapping from mesh URI to the name of the link that contains it."""
    root_xml = ET.fromstring(urdf_string)
    uri_to_link: dict[str, str] = {}
    for link in root_xml.iter("link"):
        link_name = link.get("name", "")
        for mesh in link.iter("mesh"):
            filename = mesh.get("filename", "")
            if filename and filename not in uri_to_link:
                uri_to_link[filename] = link_name
    return uri_to_link


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

    # 2. Extract mesh URIs and link poses
    mesh_uris = extract_mesh_uris(urdf_string)
    mesh_uris = sorted(mesh_uris)
    uri_name_map = build_logical_name_map(mesh_uris)

    link_poses = extract_link_poses(urdf_string)
    uri_to_link = extract_mesh_uri_to_link(urdf_string)

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

        # 5. Record in manifest with position data
        link_name = uri_to_link.get(uri, "")
        xyz, rpy = link_poses.get(link_name, _IDENTITY_POSE)
        manifest_entries[Path(abs_path).name] = {
            "glb": rel_glb,
            "xyz": [round(v, 6) for v in xyz],
            "rpy": [round(v, 6) for v in rpy],
        }
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
