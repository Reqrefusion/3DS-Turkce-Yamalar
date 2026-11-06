from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import layton_xs_tool as tool  # noqa: E402


class CompressionTests(unittest.TestCase):
    def test_lz10_round_trips(self) -> None:
        generator = random.Random(12345)
        samples = [
            b"",
            b"x",
            b"abc",
            b"A" * 5000,
            bytes(range(256)) * 8,
            bytes(generator.randrange(256) for _ in range(10000)),
        ]
        for sample in samples:
            with self.subTest(length=len(sample)):
                compressed = tool.lz10_compress(sample)
                decompressed, consumed = tool.lz10_decompress(compressed, len(sample))
                self.assertEqual(sample, decompressed)
                self.assertEqual(len(compressed), consumed)

    def test_huffman_round_trips(self) -> None:
        generator = random.Random(67890)
        samples = [
            b"",
            b"x",
            b"A" * 1000,
            bytes(range(256)) * 4,
            bytes(generator.randrange(256) for _ in range(5000)),
        ]
        for bits in (4, 8):
            for sample in samples:
                with self.subTest(bits=bits, length=len(sample)):
                    compressed = tool.huffman_compress(sample, bits)
                    decompressed, consumed = tool.huffman_decompress(
                        compressed, len(sample), bits
                    )
                    self.assertEqual(sample, decompressed)
                    self.assertEqual(len(compressed), consumed)

    def test_rle_round_trips(self) -> None:
        samples = [b"", b"abc", b"A" * 1000, bytes(range(256)) * 3]
        for sample in samples:
            compressed = tool.rle_compress(sample)
            decompressed, consumed = tool.rle_decompress(compressed, len(sample))
            self.assertEqual(sample, decompressed)
            self.assertEqual(len(compressed), consumed)


class XscrTests(unittest.TestCase):
    def test_longer_strings_do_not_corrupt_following_entries(self) -> None:
        source = tool.XsFile.from_bytes(tool._synthetic_xs())
        rebuilt, expected, _ = source.rebuild(
            {
                "text000000": "A much longer replacement than the source string",
                "text000001": "Ikinci metin de uzatildi",
            }
        )
        output = tool.XsFile.from_bytes(rebuilt)
        actual = {record.text_id: record.original for record in output.text_records()}
        self.assertEqual(expected, actual)
        self.assertEqual(source.table0, output.table0)
        self.assertEqual(source.entries[1], output.entries[1])
        self.assertEqual(output.entries[0][1], output.entries[3][1])

    def test_strict_encoding_rejects_turkish_glyphs(self) -> None:
        with self.assertRaises(tool.XsError):
            tool.encode_translation("İğne", "strict")

    def test_turkish_ascii_encoding_is_explicit(self) -> None:
        normalized, encoded, changes = tool.encode_translation(
            "Çığ şölende—", "turkish-ascii"
        )
        self.assertEqual("Cig solende-", normalized)
        self.assertEqual(normalized, encoded.decode("cp932"))
        self.assertTrue(changes)


class KupTests(unittest.TestCase):
    def test_malformed_entity_is_recovered(self) -> None:
        contents = """<?xml version="1.0" encoding="utf-8"?>
<kup><entries><entry name="text000000"><original>&lt;T&gt;Hello</original>
<edited>&lt;M1/2/3&gt>Merhaba</edited><subEntries /></entry></entries></kup>
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.kup"
            path.write_text(contents, encoding="utf-8")
            entries, recovered = tool.parse_kup(path)
        self.assertTrue(recovered)
        self.assertEqual(("<T>Hello", "<M1/2/3>Merhaba"), entries["text000000"])


if __name__ == "__main__":
    unittest.main()
