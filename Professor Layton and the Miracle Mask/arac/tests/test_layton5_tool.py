from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import layton5_tool as tool  # noqa: E402
import layton_xs_tool as xs  # noqa: E402


class PlainFaTests(unittest.TestCase):
    def test_paths_reject_traversal(self) -> None:
        for value in ("../bad.bin", "/absolute.bin", "C:/drive.bin", "a/../../b"):
            with self.subTest(value=value), self.assertRaises(xs.XsError):
                tool.normalize_member_name(value)

    def test_manifest_round_trip_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source_path = directory / "source.fa"
            root = directory / "tree"
            rebuilt_path = directory / "rebuilt.fa"
            tool.create_synthetic_plainfa(source_path)
            archive = tool.PlainFaArchive.open(source_path)
            root.mkdir()
            for entry in archive.entries:
                destination = tool.safe_output_member(root, entry.path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read_entry(entry))
            manifest_path = root / ".layton5_fa_manifest.json"
            tool.write_json(manifest_path, tool.manifest_for_archive(archive))
            tool.pack_from_manifest(
                root,
                manifest_path,
                rebuilt_path,
                preserve_layout=True,
                force=False,
            )
            self.assertEqual(source_path.read_bytes(), rebuilt_path.read_bytes())

    def test_direct_text_injection_keeps_other_members_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source_path = directory / "source.fa"
            output_path = directory / "translated.fa"
            tool.create_synthetic_plainfa(source_path)
            archive = tool.PlainFaArchive.open(source_path)
            project, _ = tool.make_project_from_archive(archive, "txt/uk")
            for rows in project.texts.values():
                for row in rows:
                    if row.text_id == "text000000":
                        row.translation = "A translated line that is much longer"
            report = tool.inject_project_into_archive(
                archive,
                project,
                output_path,
                prefix="txt/uk",
                compression="original",
                encoding_policy="strict",
                ignore_source_hash=False,
                force=False,
            )
            translated = tool.PlainFaArchive.open(output_path)
            original_asset = archive.by_path()["asset/raw.bin"]
            translated_asset = translated.by_path()["asset/raw.bin"]
            self.assertEqual(archive.hash_entry(original_asset), translated.hash_entry(translated_asset))
            self.assertEqual(2, report["xs_files_rebuilt"])
            for path in ("txt/uk/00/a.xs", "txt/uk/00/b.xs"):
                parsed = xs.XsFile.from_bytes(translated.read_entry(translated.by_path()[path]))
                self.assertEqual(
                    "A translated line that is much longer",
                    parsed.text_records()[0].original,
                )

    def test_create_archive_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            tree = directory / "tree"
            output = directory / "created.fa"
            (tree / "a").mkdir(parents=True)
            (tree / "a" / "one.bin").write_bytes(b"one")
            (tree / "two.bin").write_bytes(b"two")
            tool.create_archive_from_directory(tree, output, force=False)
            archive = tool.PlainFaArchive.open(output)
            self.assertEqual(["a/one.bin", "two.bin"], [entry.path for entry in archive.entries])
            self.assertEqual(b"one", archive.read_entry(archive.by_path()["a/one.bin"]))


if __name__ == "__main__":
    unittest.main()
