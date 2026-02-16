# """
# Unit tests for run_preprocess.py

# We test:
# 1 - Missing batch marker
# 2 - Batch exists and preprocess works
# 3 - Multiple files in batch
# 4 - Processed directory creation
# """

# import pytest
# from pathlib import Path
# import sys

# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

# from scripts.run_preprocess import main


# # 1 - Missing batch marker

# def test_preprocess_missing_marker(tmp_path, monkeypatch):
#     """
#     Scenario:
#         current_batch.txt does not exist.

#     Expected:
#         Script exits with SystemExit.
#     """

#     raw = tmp_path / "raw"
#     processed = tmp_path / "processed"

#     raw.mkdir()
#     processed.mkdir()

#     marker = tmp_path / "current_batch.txt"

#     monkeypatch.setattr("scripts.run_preprocess.RAW_DIR", raw)
#     monkeypatch.setattr("scripts.run_preprocess.PROCESSED_DIR", processed)
#     monkeypatch.setattr("scripts.run_preprocess.BATCH_MARKER", marker)

#     with pytest.raises(SystemExit):
#         main()


# # 2 - Batch exists and preprocess works

# def test_preprocess_single_file(tmp_path, monkeypatch):
#     """
#     Scenario:
#         One CSV file exists in raw/<batch_id>/.

#     Expected:
#         Processed file created in processed/<batch_id>/.
#     """

#     raw = tmp_path / "raw"
#     processed = tmp_path / "processed"

#     batch_dir = raw / "batch_test"
#     batch_dir.mkdir(parents=True)

#     file = batch_dir / "file.csv"
#     file.write_text("a,b\n1,2")

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     monkeypatch.setattr("scripts.run_preprocess.RAW_DIR", raw)
#     monkeypatch.setattr("scripts.run_preprocess.PROCESSED_DIR", processed)
#     monkeypatch.setattr("scripts.run_preprocess.BATCH_MARKER", marker)

#     # Mock preprocess to identity function
#     monkeypatch.setattr(
#         "scripts.run_preprocess.preprocess",
#         lambda df: df
#     )

#     main()

#     assert (processed / "batch_test" / "file.csv").exists()


# # 3 - Multiple files in batch

# def test_preprocess_multiple_files(tmp_path, monkeypatch):
#     """
#     Scenario:
#         Multiple CSV files in raw batch.

#     Expected:
#         All files processed and saved.
#     """

#     raw = tmp_path / "raw"
#     processed = tmp_path / "processed"

#     batch_dir = raw / "batch_test"
#     batch_dir.mkdir(parents=True)

#     for i in range(3):
#         (batch_dir / f"file_{i}.csv").write_text("a,b\n1,2")

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     monkeypatch.setattr("scripts.run_preprocess.RAW_DIR", raw)
#     monkeypatch.setattr("scripts.run_preprocess.PROCESSED_DIR", processed)
#     monkeypatch.setattr("scripts.run_preprocess.BATCH_MARKER", marker)

#     monkeypatch.setattr(
#         "scripts.run_preprocess.preprocess",
#         lambda df: df
#     )

#     main()

#     processed_batch = processed / "batch_test"
#     assert len(list(processed_batch.glob("*.csv"))) == 3


# # 4 - Processed directory creation

# def test_preprocess_creates_processed_dir(tmp_path, monkeypatch):
#     """
#     Scenario:
#         processed/<batch_id>/ does not exist.

#     Expected:
#         Directory is created automatically.
#     """

#     raw = tmp_path / "raw"
#     raw.mkdir()

#     batch_dir = raw / "batch_test"
#     batch_dir.mkdir()

#     (batch_dir / "file.csv").write_text("a,b\n1,2")

#     marker = tmp_path / "current_batch.txt"
#     marker.write_text("batch_test")

#     processed = tmp_path / "processed"

#     monkeypatch.setattr("scripts.run_preprocess.RAW_DIR", raw)
#     monkeypatch.setattr("scripts.run_preprocess.PROCESSED_DIR", processed)
#     monkeypatch.setattr("scripts.run_preprocess.BATCH_MARKER", marker)

#     monkeypatch.setattr(
#         "scripts.run_preprocess.preprocess",
#         lambda df: df
#     )

#     main()

#     assert (processed / "batch_test").exists()
