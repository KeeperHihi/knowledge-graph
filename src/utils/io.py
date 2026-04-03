import csv
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from config import DEFAULT_ENCODING
from src.schema.types import Entity


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text_files(directory: Path) -> List[dict]:
    records = []
    for file_path in sorted(directory.glob("*.txt")):
        content = file_path.read_text(encoding=DEFAULT_ENCODING)
        records.append({"text_id": file_path.stem, "content": content})
    return records


def read_json(path: Path):
    with path.open("r", encoding=DEFAULT_ENCODING) as file:
        return json.load(file)


def write_json(path: Path, data) -> None:
    ensure_parent(path)
    with path.open("w", encoding=DEFAULT_ENCODING) as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> List[dict]:
    records = []
    if not path.exists():
        return records

    with path.open("r", encoding=DEFAULT_ENCODING) as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding=DEFAULT_ENCODING) as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding=DEFAULT_ENCODING, newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def load_entities(path: Path) -> List[Entity]:
    data = read_json(path)
    return [Entity(**item) for item in data]
