"""Regression checks for script operands, text preservation and control flow."""
import json
from argparse import Namespace
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import aat3ds_tool as tool
import repair_native_controls as repair
from relocate_local_jumps import relocate


def mdt(words, alias=None):
    count = 1 if alias is None else 2
    offsets = [4 + 4 * count] + ([] if alias is None else [alias])
    return struct.pack("<I", count) + struct.pack("<" + "I" * count, *offsets) + struct.pack("<" + "H" * len(words), *words)


def hd(char):
    return ord(char) + 0xFEE0 + 0x80 if char != " " else 0x3080


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.schema = repair.load_schema()

    def test_character_shaped_operand_is_not_converted(self):
        before = mdt([0, 19, hd("A"), hd("B"), 13])
        after, info = tool.convert_switch_mdt(before, "GS1")
        self.assertEqual(struct.unpack_from("<5H", after, 8), (0, 19, hd("A"), 139, 13))
        self.assertEqual(info["converted_words"], 1)

    def test_unknown_text_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported HD text word"):
            tool.convert_switch_mdt(mdt([0, 0xFFFF, 13]), "GS1")

    def test_truncated_operand_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Truncated HD opcode"):
            tool.convert_switch_mdt(mdt([0, 30, 1]), "GS1")

    def test_hd_operand_is_skipped_during_conversion(self):
        after, info = tool.convert_switch_mdt(mdt([0, 127, 3, hd("A"), 13]), "GS1")
        self.assertEqual(struct.unpack_from("<5H", after, 8), (0, 127, 3, 138, 13))
        self.assertEqual(info["converted_words"], 1)

    def test_text_after_two_argument_command_is_preserved(self):
        native = mdt([0, 118, 0, 5, 151, 178, 186, 13])
        translated = mdt([0, 118, 0, 5, 205, 172, 176, 167, 172, 13])
        fixed, info = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, translated)
        self.assertTrue(info["validation"]["text_equal"])

    def test_text_after_single_argument_command_is_preserved(self):
        native = mdt([0, 110, 1, 1553, 13])
        translated = mdt([0, 110, 1, 144, 13])
        fixed, _ = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, translated)

    def test_real_operand_corruption_is_fixed(self):
        native = mdt([0, 53, 22145, 147, 13])
        translated = mdt([0, 53, 22145, 205, 13])
        fixed, _ = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, native)

    def test_ambiguous_speaker_is_reported_and_preserved(self):
        native = mdt([0, 14, 4352, 13])
        translated = mdt([0, 14, 512, 13])
        fixed, info = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, translated)
        self.assertEqual(len(info["pending_operands"]), 1)

    def test_hd_pair_becomes_native_noops(self):
        native = mdt([0, 3, 1, 3, 0, 164, 13])
        translated = mdt([0, 3, 1, 127, 3, 3, 0, 164, 13])
        expected = mdt([0, 3, 1, 127, 127, 3, 0, 164, 13])
        fixed, _ = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, expected)
        again, _ = repair.repair_scenario(native, fixed, self.schema)
        self.assertEqual(again, fixed)

    def test_local_jump_and_alias_follow_translated_target(self):
        native = mdt([0, 53, 1, 14, 164, 3, 0, 13], alias=14)
        translated = mdt([0, 53, 1, 14, 164, 164, 164, 3, 0, 13], alias=14)
        expected = mdt([0, 53, 1, 18, 164, 164, 164, 3, 0, 13], alias=18)
        fixed, info = repair.repair_scenario(native, translated, self.schema)
        self.assertEqual(fixed, expected)
        self.assertEqual(info["relocation"]["changed_jumps"], 1)
        self.assertEqual(info["relocation"]["changed_aliases"], 1)

    def test_reordered_conditions_fail_instead_of_guessing(self):
        native = mdt([0, 53, 1, 14, 53, 257, 14, 13])
        translated = mdt([0, 53, 257, 14, 53, 1, 14, 13])
        with self.assertRaisesRegex(ValueError, "Unresolved control-flow"):
            repair.repair_scenario(native, translated, self.schema)

    def test_old_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            path.write_text(json.dumps({str(i): {"count": 0, "name": str(i)} for i in range(128)}))
            with self.assertRaisesRegex(ValueError, "Outdated"):
                repair.load_schema(path)

    def test_plausible_but_unreviewed_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            raw=json.loads((ROOT/'tools/opcodes_3ds.json').read_text(encoding='utf-8'))
            raw['opcodes']['72']['count']=1
            path=Path(directory)/'schema.json'
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,'unreviewed'):
                repair.load_schema(path)

    def test_inject_cli_updates_both_pack_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data=b'original asset'
            compressed=tool.lz11_compress(data)
            (root/'pack.dat').write_bytes(compressed+bytes((-len(compressed))%4))
            (root/'pack.inc').write_bytes(struct.pack('<QIII',0,len(data),len(compressed),123))
            replacement=b'different replacement data'
            (root/'raw.bin').write_bytes(replacement)
            result=subprocess.run([sys.executable,str(ROOT/'tools/aat3ds_tool.py'),'inject-pack-entry',str(root/'pack.dat'),'0',str(root/'raw.bin'),str(root/'out.dat'),'--inc',str(root/'pack.inc'),'--out-inc',str(root/'out.inc')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            output=(root/'out.dat').read_bytes()
            tool.validate_pack_inc(output,tool.parse_pack_inc((root/'out.inc').read_bytes()))
            self.assertEqual(tool.lz11_decompress(output)[0],replacement)

    def test_asset_groups_use_file_signatures(self):
        for signature,expected in [(b'BCH\x00',('bch','.bch')),(b'.ans',('ans','.ans')),(b'FFNT',('font','.cfnt')),(b'mcol',('mcol','.mcol'))]:
            with self.subTest(signature=signature):
                self.assertEqual(tool.classify_pack_asset(signature+b'asset'),expected)

    def test_large_unknown_file_is_not_mistaken_for_dialogue(self):
        self.assertEqual(tool.classify_pack_asset(b'x'*(1024*1024)),('unknown','.bin'))

    def test_dialogue_group_requires_a_valid_archive_table(self):
        entries=[b'']*74
        entries[1]=mdt([0,13])
        raw=tool.build_mesall(entries)
        self.assertEqual(tool.classify_pack_asset(raw),('dialogues','.dlg'))
        malformed=bytearray(raw)
        struct.pack_into('<I',malformed,4+8,1)
        self.assertEqual(tool.classify_pack_asset(bytes(malformed)),('unknown','.bin'))

    def test_grouped_extraction_preserves_resource_bytes(self):
        assets=[b'BCH\x00picture',b'FFNTfont',b'unknown']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            pack=bytearray()
            for raw in assets:
                pack.extend(tool.lz11_compress(raw))
                pack.extend(bytes((-len(pack))%4))
            (root/'pack.dat').write_bytes(pack)
            tool.cmd_extract_pack(Namespace(pack=str(root/'pack.dat'),out=str(root/'out'),grouped=True))
            manifest=json.loads((root/'out/pack_manifest.json').read_text())
            self.assertEqual([e['path'] for e in manifest],['bch/00000.bch','font/00001.cfnt','unknown/00002.bin'])
            for entry,raw in zip(manifest,assets):
                self.assertEqual((root/'out'/entry['path']).read_bytes(),raw)
                self.assertEqual(entry['sha256'],__import__('hashlib').sha256(raw).hexdigest())

    def test_flat_extraction_keeps_existing_default_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'pack.dat').write_bytes(tool.lz11_compress(b'FFNTfont'))
            tool.cmd_extract_pack(Namespace(pack=str(root/'pack.dat'),out=str(root/'out')))
            self.assertEqual((root/'out/00000.bin').read_bytes(),b'FFNTfont')

    def test_extraction_refuses_to_mix_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'pack.dat').write_bytes(tool.lz11_compress(b'asset'))
            (root/'out').mkdir()
            (root/'out/keep.txt').write_text('keep')
            with self.assertRaisesRegex(ValueError,'empty output'):
                tool.cmd_extract_pack(Namespace(pack=str(root/'pack.dat'),out=str(root/'out'),grouped=True))
            self.assertEqual((root/'out/keep.txt').read_text(),'keep')

    def test_pack_index_is_regenerated_with_replacement(self):
        original = b"original asset"
        compressed = tool.lz11_compress(original)
        pack = compressed + bytes((-len(compressed)) % 4)
        inc = struct.pack("<QIII", 0, len(original), len(compressed), 123)
        replacement = b"replacement asset with a different size"
        new_pack, new_inc, _ = tool.rebuild_pack_with_inc(pack, inc, {0: replacement})
        entries = tool.parse_pack_inc(new_inc)
        tool.validate_pack_inc(new_pack, entries)
        self.assertEqual(tool.lz11_decompress(new_pack)[0], replacement)
        self.assertEqual(entries[0]["decompressed"], len(replacement))

    def test_pack_port_requires_companion_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "requires the matching --inc"):
                tool.port_switch(root / "missing", root / "source", root / "out", True)
            self.assertFalse((root / "out").exists())

    def test_port_runs_native_control_repair_automatically(self):
        native = mdt([0, 53, 1, 14, 164, 3, 0, 13], alias=14)
        translated = mdt([0, 53, 1, 14, hd("a"), hd("a"), hd("a"), 3, 0, 13], alias=14)
        language = tool.build_mesall([mdt([0, 13]), native])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pack.dat").write_bytes(b"fixture")
            source = root / "source/Data/StreamingAssets/GS1/scenario"
            source.mkdir(parents=True)
            (source / "scene_u.mdt").write_bytes(translated)
            with patch.dict(tool.GS_NAMES, {"GS1": ["scene"]}, clear=True), patch.object(tool, "scan_pack", return_value=[]), patch.object(tool, "find_language_entries", return_value={"GS1": (0, language)}), patch.object(tool, "find_ffnt_entries", return_value=[]):
                info = tool.port_switch(root / "pack.dat", root / "source", root / "out")
            output = tool.parse_mesall((root / "out/GS1_mes_all_tr.bin").read_bytes())[1]
            self.assertEqual(output, mdt([0, 53, 1, 18, 164, 164, 164, 3, 0, 13], alias=18))
            self.assertTrue(info["games"]["GS1"]["files"][0]["native_controls"]["validation"]["text_equal"])

    def test_failed_cli_does_not_publish_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["original", "translated"]:
                folder = root / name
                folder.mkdir()
                (folder / "pack.dat").write_bytes(b"bad")
                (folder / "pack.inc").write_bytes(b"bad")
            result = subprocess.run([sys.executable, str(ROOT / "tools/repair_native_controls.py"), "--original", str(root / "original"), "--translated", str(root / "translated"), "--output", str(root / "out")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "out").exists())
            self.assertFalse(list(root.glob(".aat_controls_*")))

    def test_existing_cli_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("keep")
            result = subprocess.run([sys.executable, str(ROOT / "tools/repair_native_controls.py"), "--original", str(root / "missing-original"), "--translated", str(root / "missing-translated"), "--output", str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()

