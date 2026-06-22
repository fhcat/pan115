# pan115

A cross-platform CLI tool that exports 115.com download links to an [aria2](https://aria2.github.io/) input file — without needing a browser.

Inspired by the [acgotaku/115](https://github.com/acgotaku/115) Chrome extension. This tool replicates its core functionality (VIP ProAPI encrypted download URL fetching) as a standalone Python CLI.

## Requirements

- Python 3.10+
- A 115.com VIP account
- Cookies exported from your browser (see below)

## Installation

```bash
git clone https://github.com/fhcat/pan115.git
cd pan115
pip install -e .
```

This installs a `115` command on your PATH.

## Getting Your Cookies

1. Install the [Cookie-Editor](https://cookie-editor.com/) browser extension
2. Log in to [115.com](https://115.com)
3. Open Cookie-Editor, click **Export → Export as Netscape**
4. Save the file as `cookies.txt`

## Usage

### Export an entire folder (recursive)

You need the folder's CID (the number in the URL when you open a folder in 115.com, e.g. `https://115.com/?cid=12345678`).

```bash
115 folder 12345678 --cookies cookies.txt --output aria2.conf
```

### Export a single file by pick_code

```bash
115 file <pick_code> --cookies cookies.txt --output aria2.conf
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--cookies`, `-c` | `cookies.txt` | Path to Netscape cookie file |
| `--output`, `-o` | `aria2.conf` | Output aria2 input file path |
| `--delay`, `-d` | `300` | Delay (ms) between API calls (folder mode only) |

### Download with aria2

```bash
aria2c -i aria2.conf -j 4
```

## Output Format

```
https://cdn.115cdn.net/path/to/file.mkv?t=...
  out=FolderName/file.mkv
  header=User-Agent: Mozilla/5.0 ...
  header=Referer: https://115.com/
  header=Cookie: acw_tc=...
  checksum=sha-1=...
```

## How It Works

The extension uses two API calls:

1. **File listing**: `GET webapi.115.com/files?cid=<id>&limit=1000` — recursively lists folder contents
2. **Download URL**: `POST proapi.115.com/app/chrome/downurl` — fetches authenticated CDN URLs using the same RSA+XOR encryption scheme as the browser extension (`src/pan115/crypto.py`)

Authentication is via browser cookies (Netscape format).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
