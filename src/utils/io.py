import csv
import io
import json
from pathlib import Path
from typing import Iterable, List, Sequence
from uuid import uuid4

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


def _atomic_write_text(path: Path, content: str) -> None:
    ensure_parent(path)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        tmp_path.write_text(content, encoding=DEFAULT_ENCODING)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_json(path: Path, data) -> None:
    content = json.dumps(data, ensure_ascii=False, indent=2)
    _atomic_write_text(path, content)


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
    content = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    _atomic_write_text(path, content)


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    _atomic_write_text(path, output.getvalue())


def load_entities(path: Path) -> List[Entity]:
    data = read_json(path)
    return [Entity(**item) for item in data]
