# """
# Unit tests for run_archive.py

# We test:
# 1 - Missing batch marker
# 2 - Archive moves files correctly
# 3 - Archive directory creation
# 4 - Marker removal
# """

# import pytest
# from pathlib import Path
# import sys

# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

# from scripts.run_archive import main


# # 1 - Missing batch marker

# def test_archive_missing_marker(tmp_path, monkeypatch):
#     """
#     Scenario:
#         current_batch.txt does not exist.

#     Expected:
#         Script runs safely and does nothing.
#     """

#     incoming = tmp_path / "incoming"
#     archive = tmp_path / "archive"

#     incoming.mkdir()
#     archive.mkdir()

#     marker = tmp_path / "current_batch.txt"

#     monkeypatch.setattr("scripts.run_archive.INCOMING_DIR", incoming)
#     monkeypatch.setattr("scripts.run_archive.ARCHIVE_DIR", archive)
#     monkeypatch.setattr("scripts.run_archive.BATCH_MARKER", marker)

#     main()  # Should not raise


# # 2 - Archive moves files correctly

# def test_archive_moves_files(tmp_path, monkeypatch):
#     """
#     Scenario:
#         incoming contains files and marker exists.

#     Expected:
#         Files moved to archive/<batch_id>/.
#     """

#     incoming = tmp_path / "incoming"
#     archive = tmp_path / "archive"

#     incoming.mkdir()
#     archive.mkdir()

#     file = incoming / "file.csv"
#     file.write_text("data")

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     monkeypatch.setattr("scripts.run_archive.INCOMING_DIR", incoming)
#     monkeypatch.setattr("scripts.run_archive.ARCHIVE_DIR", archive)
#     monkeypatch.setattr("scripts.run_archive.BATCH_MARKER", marker)

#     main()

#     assert not file.exists()
#     assert (archive / "batch_test" / "file.csv").exists()


# # 3 - Archive directory creation

# def test_archive_creates_directory(tmp_path, monkeypatch):
#     """
#     Scenario:
#         archive/<batch_id>/ does not exist.

#     Expected:
#         Directory is created automatically.
#     """

#     incoming = tmp_path / "incoming"
#     incoming.mkdir()

#     (incoming / "file.csv").write_text("data")

#     archive = tmp_path / "archive"

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     monkeypatch.setattr("scripts.run_archive.INCOMING_DIR", incoming)
#     monkeypatch.setattr("scripts.run_archive.ARCHIVE_DIR", archive)
#     monkeypatch.setattr("scripts.run_archive.BATCH_MARKER", marker)

#     main()

#     assert (archive / "batch_test").exists()


# # 4 - Marker removal

# def test_archive_removes_marker(tmp_path, monkeypatch):
#     """
#     Scenario:
#         After archiving, marker should be deleted.

#     Expected:
#         current_batch.txt no longer exists.
#     """

#     incoming = tmp_path / "incoming"
#     archive = tmp_path / "archive"

#     incoming.mkdir()
#     archive.mkdir()

#     (incoming / "file.csv").write_text("data")

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     monkeypatch.setattr("scripts.run_archive.INCOMING_DIR", incoming)
#     monkeypatch.setattr("scripts.run_archive.ARCHIVE_DIR", archive)
#     monkeypatch.setattr("scripts.run_archive.BATCH_MARKER", marker)

#     main()

#     assert not marker.exists()
