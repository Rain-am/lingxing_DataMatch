from __future__ import annotations

import json
import base64
import hashlib
import subprocess
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode, urlsplit

from app.config import Settings, get_settings, update_env_values
from app.schemas import Granularity, Rule, Source


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


def _expand_nested_data_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for item in items:
        detail_rows = item.get("data")
        if isinstance(detail_rows, list):
            parent = {key: value for key, value in item.items() if key != "data"}
            for detail in detail_rows:
                if isinstance(detail, dict):
                    expanded.append({**parent, **detail})
            continue
        expanded.append(item)
    return expanded


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
    if isinstance(value, list):
        return sum((_decimal(item) for item in value), Decimal("0"))
    return Decimal(str(value))


def _field_value(record: dict[str, Any], field: str) -> Any:
    if not field:
        return None
    if field in record:
        return record.get(field)
    nested_data = record.get("data")
    if isinstance(nested_data, dict) and field in nested_data:
        return nested_data.get(field)
    if isinstance(nested_data, list):
        nested_values = _walk_field_path(nested_data, [field])
        if nested_values:
            return nested_values
    parts = [part for part in field.replace(">>", ".").split(".") if part]
    if parts and parts[0] == "data" and "data" not in record:
        fallback = _walk_field_path(record, parts[1:])
        if fallback is not None:
            return fallback
    return _walk_field_path(record, parts)


def _walk_field_path(value: Any, parts: list[str]) -> Any:
    for part in parts:
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list):
            next_values = []
            for item in value:
                if isinstance(item, dict):
                    nested = item.get(part)
                    if isinstance(nested, list):
                        next_values.extend(nested)
                    elif nested is not None:
                        next_values.append(nested)
            value = next_values
        else:
            return None
    return value


def _store_value(record: dict[str, Any], field: str) -> str:
    value = _field_value(record, field)
    if isinstance(value, list):
        unique_values = []
        for item in value:
            if item not in unique_values:
                unique_values.append(item)
        if len(unique_values) == 1:
            value = unique_values[0]
        else:
            value = ",".join(str(item) for item in unique_values)
    return str(value or "")


def _date_for_request(value: str, granularity: Granularity) -> str:
    if granularity == "month":
        return value[:7]
    return value


def _month_windows(start_date: str, end_date: str) -> list[tuple[str, str, str]]:
    start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
    current = start.replace(day=1)
    windows: list[tuple[str, str, str]] = []
    while current <= end:
        last_day = monthrange(current.year, current.month)[1]
        month_start = current
        month_end = current.replace(day=last_day)
        clipped_start = max(start, month_start)
        clipped_end = min(end, month_end)
        windows.append((current.strftime("%Y-%m-01"), clipped_start.isoformat(), clipped_end.isoformat()))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return windows


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


def _is_success_response(result: Any) -> bool:
    return isinstance(result, dict) and str(result.get("code", "0")) in {"0", "200", "success"}


def _is_auth_error_message(message: str) -> bool:
    lower = message.lower()
    return any(
        marker in lower
        for marker in (
            "授权失效",
            "授权有效期",
            "access_token",
            "access token",
            "token expired",
            "token invalid",
            "invalid token",
        )
    )


class LingxingApiError(RuntimeError):
    def __init__(self, message: str, *, auth_error: bool = False) -> None:
        super().__init__(message)
        self.auth_error = auth_error


class LingxingTokenManager:
    refresh_margin_seconds = 300

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def access_token(self) -> str:
        if self._has_valid_cached_token():
            return self.settings.lingxing_access_token
        return self.refresh()

    def refresh(self) -> str:
        if not self.settings.lingxing_api_base_url:
            raise RuntimeError("LINGXING_API_BASE_URL is not configured")
        if not self.settings.lingxing_app_key:
            raise RuntimeError("LINGXING_APP_KEY is not configured")
        if not self.settings.lingxing_app_secret:
            raise RuntimeError("LINGXING_APP_SECRET is not configured")

        base = self.settings.lingxing_api_base_url.rstrip("/")
        url = f"{base}/api/auth-server/oauth/access-token"
        boundary = f"----lingxing{int(time.time() * 1000)}"
        body = self._multipart_body(
            boundary,
            {
                "appId": self.settings.lingxing_app_key,
                "appSecret": self.settings.lingxing_app_secret,
            },
        )
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.lingxing_timeout_seconds) as response:
                text = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = _response_text(exc)
            message = f"Lingxing token HTTP {exc.code}"
            if detail:
                message = f"{message}: {detail}"
            raise RuntimeError(message) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Lingxing token request failed: {exc}") from exc

        result = json.loads(text) if text else {}
        if not _is_success_response(result):
            raise RuntimeError(f"Lingxing token error {result.get('code')}: {result.get('msg')}")
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict) or not data.get("access_token"):
            raise RuntimeError("Lingxing token response missing access_token")

        access_token = str(data["access_token"])
        refresh_token = str(data.get("refresh_token") or "")
        expires_in = self._expires_in(data.get("expires_in"))
        expires_at = int(time.time()) + expires_in
        update_env_values(
            {
                "LINGXING_ACCESS_TOKEN": access_token,
                "LINGXING_REFRESH_TOKEN": refresh_token,
                "LINGXING_TOKEN_EXPIRES_AT": str(expires_at),
            }
        )
        get_settings.cache_clear()
        self.settings = Settings(
            **{
                **self.settings.__dict__,
                "lingxing_access_token": access_token,
                "lingxing_refresh_token": refresh_token,
                "lingxing_token_expires_at": expires_at,
            }
        )
        return access_token

    def _has_valid_cached_token(self) -> bool:
        if not self.settings.lingxing_access_token:
            return False
        expires_at = self.settings.lingxing_token_expires_at
        if not expires_at:
            return True
        return expires_at - int(time.time()) > self.refresh_margin_seconds

    @staticmethod
    def _expires_in(value: Any) -> int:
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            seconds = 7200
        return max(seconds, 0)

    @staticmethod
    def _multipart_body(boundary: str, fields: dict[str, str]) -> bytes:
        lines: list[str] = []
        for key, value in fields.items():
            lines.extend(
                [
                    f"--{boundary}",
                    f'Content-Disposition: form-data; name="{key}"',
                    "",
                    value,
                ]
            )
        lines.append(f"--{boundary}--")
        lines.append("")
        return "\r\n".join(lines).encode("utf-8")


class LingxingApiClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.token_manager = LingxingTokenManager(self.settings)

    def fetch_module_records(
        self,
        rule: Rule,
        start_date: str,
        end_date: str,
        granularity: Granularity,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        source = Source(
            name="ERP",
            type="erp",
            table_or_path=rule.erp_module_path,
            date_field=rule.erp_date_field,
            store_field=rule.erp_store_field,
            request_config=rule.erp_request_config,
            metrics=rule.metrics,
        )
        return self.fetch_source_records(source, start_date, end_date, granularity, page_size)

    def fetch_source_records(
        self,
        source: Source,
        start_date: str,
        end_date: str,
        granularity: Granularity,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        if not self.settings.lingxing_api_base_url:
            raise RuntimeError("LINGXING_API_BASE_URL is not configured")

        base = self.settings.lingxing_api_base_url.rstrip("/")
        path = source.table_or_path if source.table_or_path.startswith("/") else f"/{source.table_or_path}"
        url = f"{base}{path}"
        records: list[dict[str, Any]] = []
        config = source.request_config or {}
        windows = (
            _month_windows(start_date, end_date)
            if source.period_mode == "request_month"
            else [("", start_date, end_date)]
        )
        for request_period, window_start, window_end in windows:
            records.extend(self._fetch_window_records(url, config, window_start, window_end, granularity, page_size, request_period))
        return records

    def _fetch_window_records(
        self,
        url: str,
        config: dict[str, Any],
        start_date: str,
        end_date: str,
        granularity: Granularity,
        page_size: int,
        request_period: str = "",
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        extra_params = config.get("extraParams") or {}
        if not isinstance(extra_params, dict):
            raise RuntimeError("ERP extraParams must be a JSON object")
        extra_params = dict(extra_params)
        extra_params["currencyCode"] = "USD"
        order_profit = "orderprofit" in url.lower()
        start_param = str(config.get("startDateParam") or "startDate")
        end_param = str(config.get("endDateParam") or "endDate")
        page_param = str(config.get("pageParam") or "page")
        page_size_param = str(config.get("pageSizeParam") or "pageSize")
        offset_param = str(config.get("offsetParam") or ("offset" if order_profit else ""))
        length_param = str(config.get("lengthParam") or ("length" if order_profit else ""))
        monthly_param = str(config.get("monthlyQueryParam") or "monthlyQuery")
        pagination_mode = str(config.get("paginationMode") or ("offset" if offset_param or length_param else "page"))
        if order_profit and pagination_mode == "page" and not config.get("paginationMode"):
            pagination_mode = "offset"
        effective_page_size = max(page_size, 5000) if order_profit and pagination_mode == "offset" else page_size
        page = 1
        offset = int(config.get("offsetStart") or 0)

        while True:
            payload = dict(extra_params)
            payload[start_param] = start_date if request_period else _date_for_request(start_date, granularity)
            payload[end_param] = end_date if request_period else _date_for_request(end_date, granularity)
            if pagination_mode == "offset":
                payload[offset_param or "offset"] = offset
                payload[length_param or "length"] = effective_page_size
            else:
                payload[page_param] = page
                payload[page_size_param] = effective_page_size
            if monthly_param:
                payload[monthly_param] = granularity == "month"
            response = self._post_json(url, payload)
            raw_items = _extract_items(response)
            items = _expand_nested_data_items(raw_items)
            if request_period:
                for item in items:
                    item["_request_period"] = request_period
            records.extend(items)
            if not _has_next(response, page, effective_page_size, len(raw_items)):
                break
            page += 1
            offset += effective_page_size
        return records

    def _post_json(self, url: str, payload: dict[str, Any]) -> Any:
        try:
            return self._post_json_with_retry(url, payload)
        except LingxingApiError as exc:
            raise RuntimeError(str(exc)) from exc

    def _post_json_with_retry(self, url: str, payload: dict[str, Any]) -> Any:
        try:
            return self._post_json_once(url, payload, self.token_manager.access_token())
        except LingxingApiError as exc:
            if not exc.auth_error:
                raise
            return self._post_json_once(url, payload, self.token_manager.refresh())

    def _post_json_once(self, url: str, payload: dict[str, Any], access_token: str) -> Any:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if not self.settings.lingxing_app_key:
            raise RuntimeError("LINGXING_APP_KEY is not configured")
        if not access_token:
            raise RuntimeError("LINGXING_ACCESS_TOKEN is not configured")

        timestamp = int(time.time())
        sign_params = dict(payload)
        sign_params.update(
            {
                "access_token": access_token,
                "app_key": self.settings.lingxing_app_key,
                "timestamp": timestamp,
            }
        )
        query_params = {
            "access_token": access_token,
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
                    if isinstance(result, dict) and not _is_success_response(result):
                        message = f"Lingxing API error {result.get('code')}: {result.get('msg')}"
                        raise LingxingApiError(message, auth_error=_is_auth_error_message(message))
                    return result
            except urllib.error.HTTPError as exc:
                detail = _response_text(exc)
                message = f"Lingxing API HTTP {exc.code} on {_safe_path(url)}"
                if detail:
                    message = f"{message}: {detail}"
                raise LingxingApiError(message, auth_error=_is_auth_error_message(message)) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(0.4 * (attempt + 1))
            except LingxingApiError:
                raise
        raise LingxingApiError(f"Lingxing API request failed: {last_error}")


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
        period = _period(_field_value(record, rule.erp_date_field), granularity)
        store = _store_value(record, rule.erp_store_field)
        for metric in rule.metrics:
            key = (period, store, metric.name)
            if metric.aggregation == "count":
                value = Decimal("1")
            else:
                value = _decimal(_field_value(record, metric.erp_field))
            result[key] = result.get(key, Decimal("0")) + value
    return result


def fetch_erp_source_values(
    source: Source,
    start_date: str,
    end_date: str,
    granularity: Granularity,
    client: Optional[LingxingApiClient] = None,
) -> dict[tuple[str, str, str, str], Decimal]:
    api = client or LingxingApiClient()
    records = api.fetch_source_records(source, start_date, end_date, granularity)
    store_mapping: dict[str, str] = {}
    if source.store_mapping.enabled:
        from app.warehouse import fetch_store_mapping

        store_mapping = fetch_store_mapping(source.store_mapping)
    result: dict[tuple[str, str, str, str], Decimal] = {}
    for record in records:
        if source.period_mode == "request_month":
            period = str(record.get("_request_period") or "")
        else:
            period = _period(_field_value(record, source.date_field), granularity)
        raw_store = _store_value(record, source.store_field)
        store = store_mapping.get(raw_store, raw_store)
        for metric in source.metrics:
            key = (period, store, metric.name, source.name)
            if metric.aggregation == "count":
                value = Decimal("1")
            else:
                value = _decimal(_field_value(record, metric.erp_field))
            result[key] = result.get(key, Decimal("0")) + value
    return result
