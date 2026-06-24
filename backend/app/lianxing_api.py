from __future__ import annotations

import json
import base64
import hashlib
import subprocess
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode, urlsplit

from app.config import get_settings
from app.schemas import Granularity, Rule


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("list", "rows", "items", "records", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    for key in ("list", "rows", "items", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _has_next(payload: Any, page: int, page_size: int, item_count: int) -> bool:
    if not isinstance(payload, dict):
        return item_count >= page_size
    data = payload.get("data", payload)
    source = data if isinstance(data, dict) else payload
    for key in ("has_next", "hasNext", "has_more", "hasMore"):
        if key in source:
            return bool(source[key])
    total = source.get("total") if isinstance(source, dict) else None
    if total is not None:
        try:
            return page * page_size < int(total)
        except (TypeError, ValueError):
            pass
    return item_count >= page_size


def _period(value: Any, granularity: Granularity) -> str:
    if isinstance(value, datetime):
        dt = value.date()
    elif isinstance(value, date):
        dt = value
    else:
        text = str(value)
        if "T" in text:
            text = text.split("T", 1)[0]
        if " " in text:
            text = text.split(" ", 1)[0]
        dt = datetime.strptime(text[:10], "%Y-%m-%d").date()
    return dt.strftime("%Y-%m-%d" if granularity == "day" else "%Y-%m-01")


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _date_for_request(value: str, granularity: Granularity) -> str:
    if granularity == "month":
        return value[:7]
    return value


def _sign_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    padding = block_size - (len(data) % block_size)
    return data + bytes([padding]) * padding


def _aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        cipher = Cipher(algorithms.AES(key), modes.ECB())
        encryptor = cipher.encryptor()
        return encryptor.update(_pkcs7_pad(data)) + encryptor.finalize()
    except ModuleNotFoundError:
        cipher_name = {16: "aes-128-ecb", 24: "aes-192-ecb", 32: "aes-256-ecb"}[len(key)]
        process = subprocess.run(
            ["openssl", "enc", f"-{cipher_name}", "-K", key.hex(), "-nosalt"],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            detail = process.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"OpenSSL AES signing failed: {detail}") from None
        return process.stdout


def _build_sign(params: dict[str, Any], app_key: str) -> str:
    filtered = {key: value for key, value in params.items() if value != ""}
    joined = "&".join(f"{key}={_sign_value(filtered[key])}" for key in sorted(filtered))
    md5_text = hashlib.md5(joined.encode("utf-8")).hexdigest().upper()
    key = app_key.encode("utf-8")
    if len(key) not in (16, 24, 32):
        raise RuntimeError("LINGXING_APP_KEY must be 16, 24, or 32 bytes for Lingxing AES signing")
    encrypted = _aes_ecb_encrypt(md5_text.encode("utf-8"), key)
    return base64.b64encode(encrypted).decode("utf-8")


def _response_text(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read()
    except Exception:
        body = b""
    if not body:
        return ""
    text = body.decode("utf-8", errors="replace").strip()
    return text[:1000]


def _safe_path(url: str) -> str:
    parsed = urlsplit(url)
    return parsed.path or url


class LingxingApiClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_module_records(
        self,
        rule: Rule,
        start_date: str,
        end_date: str,
        granularity: Granularity,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        if not self.settings.lingxing_api_base_url:
            raise RuntimeError("LINGXING_API_BASE_URL is not configured")

        base = self.settings.lingxing_api_base_url.rstrip("/")
        path = rule.erp_module_path if rule.erp_module_path.startswith("/") else f"/{rule.erp_module_path}"
        url = f"{base}{path}"
        records: list[dict[str, Any]] = []
        page = 1
        config = rule.erp_request_config or {}
        extra_params = config.get("extraParams") or {}
        if not isinstance(extra_params, dict):
            raise RuntimeError("ERP extraParams must be a JSON object")
        start_param = str(config.get("startDateParam") or "startDate")
        end_param = str(config.get("endDateParam") or "endDate")
        page_param = str(config.get("pageParam") or "page")
        page_size_param = str(config.get("pageSizeParam") or "pageSize")
        monthly_param = str(config.get("monthlyQueryParam") or "monthlyQuery")

        while True:
            payload = dict(extra_params)
            payload[start_param] = _date_for_request(start_date, granularity)
            payload[end_param] = _date_for_request(end_date, granularity)
            payload[page_param] = page
            payload[page_size_param] = page_size
            if monthly_param:
                payload[monthly_param] = granularity == "month"
            response = self._post_json(url, payload)
            items = _extract_items(response)
            records.extend(items)
            if not _has_next(response, page, page_size, len(items)):
                break
            page += 1
        return records

    def _post_json(self, url: str, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if not self.settings.lingxing_app_key:
            raise RuntimeError("LINGXING_APP_KEY is not configured")
        if not self.settings.lingxing_access_token:
            raise RuntimeError("LINGXING_ACCESS_TOKEN is not configured")

        timestamp = int(time.time())
        sign_params = dict(payload)
        sign_params.update(
            {
                "access_token": self.settings.lingxing_access_token,
                "app_key": self.settings.lingxing_app_key,
                "timestamp": timestamp,
            }
        )
        query_params = {
            "access_token": self.settings.lingxing_access_token,
            "app_key": self.settings.lingxing_app_key,
            "timestamp": timestamp,
            "sign": _build_sign(sign_params, self.settings.lingxing_app_key),
        }
        signed_url = f"{url}?{urlencode(query_params)}"

        request = urllib.request.Request(signed_url, data=body, headers=headers, method="POST")
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self.settings.lingxing_timeout_seconds) as response:
                    text = response.read().decode("utf-8")
                    result = json.loads(text) if text else {}
                    if isinstance(result, dict) and str(result.get("code", "0")) not in {"0", "200", "success"}:
                        raise RuntimeError(f"Lingxing API error {result.get('code')}: {result.get('msg')}")
                    return result
            except urllib.error.HTTPError as exc:
                detail = _response_text(exc)
                message = f"Lingxing API HTTP {exc.code} on {_safe_path(url)}"
                if detail:
                    message = f"{message}: {detail}"
                raise RuntimeError(message) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(0.4 * (attempt + 1))
            except RuntimeError:
                raise
        raise RuntimeError(f"Lingxing API request failed: {last_error}")


def fetch_erp_aggregate(
    rule: Rule,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    client: Optional[LingxingApiClient] = None,
) -> dict[tuple[str, str, str], Decimal]:
    api = client or LingxingApiClient()
    records = api.fetch_module_records(rule, start_date, end_date, granularity)
    result: dict[tuple[str, str, str], Decimal] = {}
    for record in records:
        period = _period(record.get(rule.erp_date_field), granularity)
        store = str(record.get(rule.erp_store_field) or "")
        for metric in rule.metrics:
            key = (period, store, metric.name)
            if metric.aggregation == "count":
                value = Decimal("1")
            else:
                value = _decimal(record.get(metric.erp_field))
            result[key] = result.get(key, Decimal("0")) + value
    return result
