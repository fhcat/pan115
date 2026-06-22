"""
pan115 CLI — export 115.com download links to aria2 input file.

Usage:
  115 folder <cid> [options]
  115 file <pickcode> [options]
"""
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from .api import Client115
from . import aria2

app = typer.Typer(help="Export 115.com download links to an aria2 input file.")

_COOKIES_DEFAULT = Path("cookies.txt")
_OUTPUT_DEFAULT = Path("aria2.conf")
_DELAY_DEFAULT = 300


def _safe_echo(text: str) -> None:
    """Print text, replacing characters that can't be encoded by the terminal."""
    enc = sys.stdout.encoding or "utf-8"
    safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
    typer.echo(safe)


def _resolve_cookies(cookies: Optional[Path]) -> Path:
    p = cookies or _COOKIES_DEFAULT
    if not p.exists():
        typer.echo(f"[error] Cookie file not found: {p}", err=True)
        raise typer.Exit(1)
    return p


@app.command()
def folder(
    cid: str = typer.Argument(..., help="115.com folder CID"),
    cookies: Optional[Path] = typer.Option(None, "--cookies", "-c", help="Netscape cookie file"),
    output: Path = typer.Option(_OUTPUT_DEFAULT, "--output", "-o", help="Output aria2 conf file"),
    delay: int = typer.Option(_DELAY_DEFAULT, "--delay", "-d", help="Delay between API calls (ms)"),
):
    """Recursively export all files from a 115.com folder."""
    cookie_path = _resolve_cookies(cookies)
    client = Client115(cookie_path, delay_ms=delay)

    typer.echo(f"Listing folder {cid} ...")
    entries = client.list_folder(cid)
    typer.echo(f"Found {len(entries)} file(s). Fetching download URLs ...")

    file_infos = []
    for i, entry in enumerate(entries, 1):
        _safe_echo(f"  [{i}/{len(entries)}] {entry['path']}{entry['file_name']}")
        try:
            info = client.get_download_url(entry)
            file_infos.append(info)
        except Exception as e:
            typer.echo(f"  [warn] Skipping {entry['pick_code']}: {e}", err=True)
        if i < len(entries):
            time.sleep(delay / 1000.0)

    count = aria2.write(file_infos, output)
    typer.echo(f"Written {count} entries to {output}")


@app.command()
def file(
    pickcode: str = typer.Argument(..., help="115.com file pick_code"),
    cookies: Optional[Path] = typer.Option(None, "--cookies", "-c", help="Netscape cookie file"),
    output: Path = typer.Option(_OUTPUT_DEFAULT, "--output", "-o", help="Output aria2 conf file"),
):
    """Export a single file by its pick_code."""
    cookie_path = _resolve_cookies(cookies)
    client = Client115(cookie_path)

    entry = {"pick_code": pickcode, "sha1": "", "path": "", "file_name": pickcode}
    typer.echo(f"Fetching download URL for {pickcode} ...")
    try:
        info = client.get_download_url(entry)
    except Exception as e:
        typer.echo(f"[error] {e}", err=True)
        raise typer.Exit(1)

    count = aria2.write([info], output)
    typer.echo(f"Written {count} entry to {output}")


def main():
    app()
