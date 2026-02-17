import uuid
import os

from data.linked_files import canonicalize_linked_images


def test_canonicalize_linked_images_hardlink(tmp_path, monkeypatch):

    images_dir = tmp_path / "raw_images"
    images_root = tmp_path / "images"

    images_dir.mkdir()

    # Create source file
    src_file = images_dir / "img1.tif"
    src_file.write_bytes(b"hardlink_test")

    files_by_name = {
        "satellite": ["img1.tif"]
    }

    # Make UUID deterministic
    class DummyUUID:
        hex = "fixeduuid"

    monkeypatch.setattr(uuid, "uuid4", lambda: DummyUUID())

    mapping = canonicalize_linked_images(
        images_dir=images_dir,
        images_root=images_root,
        files_by_name=files_by_name,
        use_hardlink=True,
    )

    dest_file = images_root / "satellite" / "fixeduuid.tif"

    # 1. File exists
    assert dest_file.exists()

    # 2. Same inode (true hardlink)
    assert src_file.stat().st_ino == dest_file.stat().st_ino
    assert src_file.stat().st_dev == dest_file.stat().st_dev

    # 3. Content identical
    assert dest_file.read_bytes() == b"hardlink_test"

    # 4. Mapping correct
    assert mapping["satellite"]["img1.tif"] == "images/satellite/fixeduuid.tif"
