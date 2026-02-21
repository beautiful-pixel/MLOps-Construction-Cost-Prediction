# Reinitialize source directory from raw and simulation data

import shutil
from pathlib import Path
import os


PROJECT_ROOT_ENV = os.getenv("PROJECT_ROOT")
if not PROJECT_ROOT_ENV:
    raise RuntimeError("PROJECT_ROOT env var is required")
PROJECT_ROOT = Path(PROJECT_ROOT_ENV)

SOURCE_IMAGES = PROJECT_ROOT / "data" / "source" / "train_composite"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SIMULATION_DIR = PROJECT_ROOT / "data" / "simulation"


def collect_images_from(root: Path, destination: Path) -> None:
    """
    Move all images found under root/**/images into destination.
    """

    if not root.exists():
        return

    for images_dir in root.rglob("images"):
        if not images_dir.is_dir():
            continue

        for file in images_dir.glob("*"):
            if not file.is_file():
                continue

            dest_file = destination / file.name

            if dest_file.exists():
                # Avoid overwrite: skip if already present
                continue

            shutil.move(str(file), str(dest_file))


def clean_directory_contents(directory: Path) -> None:
    """
    Remove all contents inside a directory but keep the directory itself.
    """
    if not directory.exists():
        return

    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def main():

    SOURCE_IMAGES.mkdir(parents=True, exist_ok=True)

    print("Collecting images from raw...")
    collect_images_from(RAW_DIR, SOURCE_IMAGES)

    print("Collecting images from simulation...")
    collect_images_from(SIMULATION_DIR, SOURCE_IMAGES)

    print("Cleaning raw directory...")
    clean_directory_contents(RAW_DIR)

    print("Removing simulation directory...")
    if SIMULATION_DIR.exists():
        shutil.rmtree(SIMULATION_DIR)

    print("Reinitialization complete.")


if __name__ == "__main__":
    main()
