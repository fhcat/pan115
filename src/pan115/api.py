"""
115.com HTTP client.

Loads a Netscape/Cookie-Editor cookie file, then provides:
  - list_folder(cid)         → recursive list of FileEntry dicts
  - get_download_url(entry)  → FileInfo dict with link, name, size, sha1, cookie
"""
import json
import time
from pathlib import Path
from http.cookiejar import MozillaCookieJar
import requests

from .crypto import encode, decode

_WEBAPI = "https://webapi.115.com"
_PROAPI = "https://proapi.115.com"
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_REFERER = "https://115.com/"


def _load_cookies(cookie_path: Path) -> requests.Session:
    """
    Parse a Netscape cookie file that may have Cookie-Editor's #HttpOnly_ prefix,
    load into a requests.Session.
    """
    import http.cookiejar as cj

    jar = MozillaCookieJar()

    lines = cookie_path.read_text(encoding="utf-8").splitlines()
    cleaned = []
    for line in lines:
        if line.startswith("#HttpOnly_"):
            # Strip the prefix so MozillaCookieJar can parse it as a normal entry
            line = line[len("#HttpOnly_"):]
        cleaned.append(line)

    # Write cleaned content to a temp in-memory parse
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(cleaned))
        tmp = f.name

    try:
        jar.load(tmp, ignore_discard=True, ignore_expires=True)
    finally:
        os.unlink(tmp)

    session = requests.Session()
    session.cookies = jar
    session.headers.update({
        "User-Agent": _DEFAULT_UA,
        "Referer": _REFERER,
    })
    return session


class Client115:
    def __init__(self, cookie_path: Path, delay_ms: int = 300):
        self.session = _load_cookies(cookie_path)
        self.delay = delay_ms / 1000.0

    def _get(self, url: str, **params) -> dict:
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, data: dict, headers: dict | None = None) -> dict:
        resp = self.session.post(url, data=data, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_folder(self, cid: str, _path: str = "") -> list[dict]:
        """
        Recursively list all files under a folder CID.
        Returns list of {"pick_code", "sha1", "path"} dicts.
        """
        results: list[dict] = []
        folders_to_visit = [(cid, _path)]

        while folders_to_visit:
            current_cid, current_path = folders_to_visit.pop()
            offset = 0
            while True:
                data = self._get(
                    f"{_WEBAPI}/files",
                    aid=1,
                    limit=1000,
                    show_dir=1,
                    cid=current_cid,
                    offset=offset,
                )
                if not data.get("state"):
                    raise RuntimeError(f"API error listing folder {current_cid}: {data}")

                items = data.get("data", [])
                folder_name = ""
                if data.get("path"):
                    folder_name = data["path"][-1]["name"]
                item_path = current_path + folder_name + "/" if folder_name else current_path

                for item in items:
                    if item.get("sha"):
                        results.append({
                            "pick_code": item["pc"],
                            "sha1": item["sha"],
                            "path": item_path,
                            "file_name": item["n"],
                        })
                    else:
                        folders_to_visit.append((item["cid"], item_path))

                offset += len(items)
                if offset >= data.get("count", 0):
                    break
                time.sleep(self.delay)

        return results

    def get_download_url(self, entry: dict) -> dict:
        """
        Fetch the real download URL for a file entry via ProAPI (VIP).

        Returns FileInfo dict: {name, link, size, sha1, cookie}
        """
        pickcode = entry["pick_code"]
        ts = int(time.time())
        encrypted_data, key = encode(json.dumps({"pickcode": pickcode}), ts)

        resp = self._post(
            f"{_PROAPI}/app/chrome/downurl",
            data={"data": encrypted_data},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not resp.get("state"):
            raise RuntimeError(f"ProAPI error for {pickcode}: {resp}")

        result = json.loads(decode(resp["data"], key))
        file_data = next(iter(result.values()))

        url_obj = file_data.get("url", {})
        file_url = url_obj.get("url", "") if isinstance(url_obj, dict) else str(url_obj)

        if not file_url:
            raise RuntimeError(f"Empty download URL for pickcode {pickcode}")

        # Grab acw_tc cookie from session (MozillaCookieJar doesn't support .get())
        acw_tc = ""
        for cookie in self.session.cookies:
            if cookie.name == "acw_tc":
                acw_tc = cookie.value
                break

        return {
            "name": entry["path"] + (file_data.get("file_name") or entry.get("file_name", pickcode)),
            "link": file_url,
            "size": file_data.get("file_size", 0),
            "sha1": entry.get("sha1", ""),
            "cookie": f"acw_tc={acw_tc}" if acw_tc else "",
            "pickcode": pickcode,
        }
