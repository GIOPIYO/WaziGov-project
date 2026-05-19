"""Tiny dataset downloader/loader helpers for satellite change detection.

The helpers here are intentionally small and dependency-light:
- download a ZIP archive from a URL to a local cache path
- extract the archive
- resolve standard LEVIR-CD / OSCD folder layouts into before/after/mask paths

If you already have the dataset extracted locally, you can call the resolver
directly. If you have a public URL to a ZIP mirror, use `download_and_prepare`.
"""

from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DatasetPaths:
    root: Path
    a_dir: Path
    b_dir: Path
    mask_dir: Path


@dataclass(frozen=True)
class DatasetPreset:
    preset_name: str
    dataset_name: str
    description: str
    env_var: str
    default_url: Optional[str] = None


# Presets intentionally support environment-variable URLs so we can switch mirrors
# without changing code across environments.
DATASET_PRESETS: dict[str, DatasetPreset] = {
    "levir-cd-public": DatasetPreset(
        preset_name="levir-cd-public",
        dataset_name="levir-cd",
        description="LEVIR-CD public ZIP mirror",
        env_var="LEVIR_CD_PUBLIC_URL",
        default_url="https://github.com/SiruiA/Levir-CD-Dataset/archive/refs/heads/main.zip",
    ),
    "oscd-public": DatasetPreset(
        preset_name="oscd-public",
        dataset_name="oscd",
        description="OSCD public ZIP mirror",
        env_var="OSCD_PUBLIC_URL",
        default_url=None,
    ),
}


def list_dataset_presets() -> list[DatasetPreset]:
    return list(DATASET_PRESETS.values())


def get_preset(preset_name: str) -> DatasetPreset:
    preset = DATASET_PRESETS.get(preset_name)
    if preset is None:
        available = ", ".join(sorted(DATASET_PRESETS))
        raise ValueError(f"Unknown preset '{preset_name}'. Available presets: {available}")
    return preset


def resolve_preset_url(preset: DatasetPreset, explicit_url: Optional[str] = None) -> str:
    if explicit_url:
        return explicit_url

    env_url = None
    try:
        import os

        env_url = os.environ.get(preset.env_var)
    except Exception:
        env_url = None

    if env_url:
        return env_url

    if preset.default_url:
        return preset.default_url

    raise ValueError(
        f"Preset '{preset.preset_name}' has no configured mirror URL yet. "
        f"Set environment variable {preset.env_var} or pass --preset-url."
    )


def _pick_existing(root: Path, candidates: list[str]) -> Optional[Path]:
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def _pick_existing_recursive(root: Path, candidates: list[str]) -> Optional[Path]:
    direct = _pick_existing(root, candidates)
    if direct is not None:
        return direct

    candidate_names = {Path(candidate).parts[-1].lower() for candidate in candidates}
    for path in root.rglob("*"):
        if path.is_dir() and path.name.lower() in candidate_names:
            return path
    return None


def resolve_dataset_paths(dataset_root: Path, dataset_name: str) -> DatasetPaths:
    root = Path(dataset_root)
    name = dataset_name.lower().strip()

    if name not in {"levir", "levir-cd", "oscd"}:
        raise ValueError("dataset_name must be one of: levir, levir-cd, oscd")

    if not root.exists():
        raise FileNotFoundError(
            f"Dataset root does not exist: {root}. Provide the real extracted dataset path, "
            "or use --smoke-test for a synthetic demo, or --download-url for a ZIP mirror."
        )

    # Standard layouts used by the datasets.
    if name in {"levir", "levir-cd"}:
        a_dir = _pick_existing_recursive(root, ["A", "train/A", "Train/A", "images/A", "before"])
        b_dir = _pick_existing_recursive(root, ["B", "train/B", "Train/B", "images/B", "after"])
        mask_dir = _pick_existing_recursive(root, ["label", "labels", "train/label", "Train/label", "masks", "mask"])
    else:
        a_dir = _pick_existing_recursive(root, ["A", "train/A", "images/A", "before"])
        b_dir = _pick_existing_recursive(root, ["B", "train/B", "images/B", "after"])
        mask_dir = _pick_existing_recursive(root, ["label", "labels", "train/label", "mask", "masks"])

    if a_dir is None or b_dir is None or mask_dir is None:
        raise FileNotFoundError(
            f"Could not resolve expected before/after/mask folders inside {root}. "
            "Check the extracted dataset layout or pass the explicit folder paths. "
            "Common layouts are LEVIR-CD train/A, train/B, train/label or OSCD A/B/label style folders."
        )

    return DatasetPaths(root=root, a_dir=a_dir, b_dir=b_dir, mask_dir=mask_dir)


def download_zip(url: str, destination: Path, overwrite: bool = False) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not overwrite:
        return destination

    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        total = response.headers.get("Content-Length")
        total_size = int(total) if total and total.isdigit() else None
        downloaded = 0
        chunk_size = 1024 * 1024

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if total_size:
                percent = (downloaded / total_size) * 100.0
                print(f"\rDownloading {destination.name}: {percent:5.1f}%", end="", file=sys.stderr)

    if total_size:
        print(file=sys.stderr)

    return destination


def extract_zip(archive_path: Path, extract_to: Path, overwrite: bool = False) -> Path:
    archive_path = Path(archive_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    marker = extract_to / ".extract_complete"
    if marker.exists() and not overwrite:
        return extract_to

    if overwrite and extract_to.exists():
        for child in extract_to.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(extract_to)

    marker.write_text(f"Extracted from {archive_path.name}\n", encoding="utf-8")
    return extract_to


def download_and_prepare(
    url: str,
    dataset_name: str,
    cache_dir: Path,
    overwrite: bool = False,
) -> DatasetPaths:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"{dataset_name.lower().replace('-', '_')}.zip"
    archive_path = download_zip(url, cache_dir / archive_name, overwrite=overwrite)
    extract_dir = extract_zip(archive_path, cache_dir / dataset_name.lower().replace('-', '_'), overwrite=overwrite)
    return resolve_dataset_paths(extract_dir, dataset_name)


def download_from_preset(
    preset_name: str,
    cache_dir: Path,
    overwrite: bool = False,
    preset_url: Optional[str] = None,
) -> DatasetPaths:
    preset = get_preset(preset_name)
    url = resolve_preset_url(preset, explicit_url=preset_url)
    return download_and_prepare(
        url=url,
        dataset_name=preset.dataset_name,
        cache_dir=cache_dir,
        overwrite=overwrite,
    )