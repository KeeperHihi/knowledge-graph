import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.utils.io import read_json, read_jsonl, write_csv, write_json, write_jsonl


class AtomicIoTestCase(unittest.TestCase):
    def test_json_jsonl_and_csv_outputs_are_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)

            json_path = base_dir / "output" / "demo.json"
            write_json(json_path, {"name": "图灵", "count": 2})
            self.assertEqual(read_json(json_path), {"name": "图灵", "count": 2})

            jsonl_path = base_dir / "output" / "demo.jsonl"
            write_jsonl(jsonl_path, [{"id": 1}, {"id": 2}])
            self.assertEqual(read_jsonl(jsonl_path), [{"id": 1}, {"id": 2}])

            csv_path = base_dir / "output" / "demo.csv"
            write_csv(csv_path, ["head", "relation", "tail"], [["Alan Turing", "published", "论文"]])
            self.assertNotIn("\r\n", csv_path.read_text(encoding="utf-8"))
            with csv_path.open("r", encoding="utf-8", newline="") as file:
                rows = list(csv.reader(file))
            self.assertEqual(
                rows,
                [["head", "relation", "tail"], ["Alan Turing", "published", "论文"]],
            )

            tmp_files = [
                item.name
                for item in (base_dir / "output").iterdir()
                if item.name.endswith(".tmp")
            ]
            self.assertEqual(tmp_files, [])

    def test_failed_json_serialization_does_not_replace_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "demo.json"
            write_json(json_path, {"status": "old"})

            with self.assertRaises(TypeError):
                write_json(json_path, {"bad": object()})

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), {"status": "old"})


if __name__ == "__main__":
    unittest.main()
