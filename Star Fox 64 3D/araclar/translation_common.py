from __future__ import annotations
import hashlib, json, re
from pathlib import Path

TAG_RE = re.compile(r"\{\{MSBT:([0-9A-Fa-f]+)\}\}")
FILE_RE = re.compile(r"^[0-9a-fA-F]{8}\.msbt$")


def control_tokens(s: str) -> list[str]:
    return [m.group(1).upper() for m in TAG_RE.finditer(s)]


def visible_len(line: str) -> int:
    line = TAG_RE.sub("", line).replace("{{NUL}}", "").replace("{{EMPTY}}", "")
    return len(line)


def max_visible_chars(s: str) -> int:
    return max((visible_len(line) for line in s.split("\n")), default=0)


def source_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows=[]
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: geçersiz JSON: {exc}") from exc
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            row={k:v for k,v in row.items() if not k.startswith("_")}
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"))+"\n")
