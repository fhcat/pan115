"""
Format FileInfo dicts into aria2 input file format.

aria2c consumes this with: aria2c -i <output_file>
"""
from pathlib import Path

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_REFERER = "https://115.com/"


def format_entry(info: dict) -> str:
    """Return the aria2 input-file block for a single file."""
    lines = [info["link"]]
    lines.append(f"  out={info['name']}")
    lines.append(f"  header=User-Agent: {_USER_AGENT}")
    lines.append(f"  header=Referer: {_REFERER}")
    if info.get("cookie"):
        lines.append(f"  header=Cookie: {info['cookie']}")
    if info.get("sha1"):
        lines.append(f"  checksum=sha-1={info['sha1']}")
    return "\n".join(lines)


def write(file_infos: list[dict], output: Path) -> int:
    """
    Write all file infos to an aria2 input file.
    Returns the number of entries written.
    """
    blocks = [format_entry(info) for info in file_infos]
    output.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return len(blocks)
