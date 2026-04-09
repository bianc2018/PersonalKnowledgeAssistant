import ipaddress
import json
from urllib.parse import urlparse


def safe_json_parse(text: str):
    """Parse JSON from LLM output, stripping markdown fences if present."""
    try:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif raw.startswith("`"):
            raw = raw.strip("`")
        return json.loads(raw)
    except Exception:
        return None


def validate_url(url: str) -> str | None:
    """Validate a URL for safe HTTP fetch. Returns error message if invalid, None if ok."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "仅支持 http/https 协议"
    hostname = parsed.hostname
    if not hostname:
        return "URL 缺少主机名"
    # Block localhost/loopback names
    lower_host = hostname.lower()
    if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return "禁止访问本地地址"
    # Block private IP ranges
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast:
            return "禁止访问私有网络地址"
    except ValueError:
        # hostname is not a bare IP, that's fine
        pass
    return None
