from io import BytesIO
from types import SimpleNamespace
import json
import time
import urllib.error

import pytest

from app import lianxing_api
from app.lianxing_api import LingxingApiClient, LingxingTokenManager


def test_http_error_includes_body_without_signed_query(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=BytesIO(b'{"message":"ip not allowed"}'),
        )

    monkeypatch.setattr(lianxing_api.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lianxing_api, "_build_sign", lambda params, app_key: "secret-sign")

    client = LingxingApiClient()
    client.settings = SimpleNamespace(
        lingxing_app_key="ak_38uk3Zx3JDWpl",
        lingxing_access_token="secret-token",
        lingxing_token_expires_at=0,
        lingxing_timeout_seconds=1,
    )
    client.token_manager = SimpleNamespace(access_token=lambda: "secret-token", refresh=lambda: "secret-token")

    with pytest.raises(RuntimeError) as exc_info:
        client._post_json("https://openapi.lingxing.com/example/path", {"page": 1})

    message = str(exc_info.value)
    assert "Lingxing API HTTP 403 on /example/path" in message
    assert "ip not allowed" in message
    assert "secret-token" not in message
    assert "secret-sign" not in message


def test_token_manager_generates_token_and_updates_env(monkeypatch) -> None:
    captured_updates = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "code": "200",
                    "msg": "OK",
                    "data": {
                        "access_token": "new-token",
                        "refresh_token": "new-refresh",
                        "expires_in": 7200,
                    },
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        body = request.data.decode("utf-8")
        assert "appId" in body
        assert "ak_38uk3Zx3JDWpl" in body
        assert "appSecret" in body
        assert "super-secret" in body
        return FakeResponse()

    monkeypatch.setattr(lianxing_api.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lianxing_api, "update_env_values", lambda updates: captured_updates.update(updates))
    monkeypatch.setattr(lianxing_api.time, "time", lambda: 1000)

    manager = LingxingTokenManager(
        SimpleNamespace(
            lingxing_api_base_url="https://openapi.lingxing.com",
            lingxing_app_key="ak_38uk3Zx3JDWpl",
            lingxing_app_secret="super-secret",
            lingxing_access_token="",
            lingxing_refresh_token="",
            lingxing_token_expires_at=0,
            lingxing_timeout_seconds=1,
        )
    )

    assert manager.access_token() == "new-token"
    assert captured_updates == {
        "LINGXING_ACCESS_TOKEN": "new-token",
        "LINGXING_REFRESH_TOKEN": "new-refresh",
        "LINGXING_TOKEN_EXPIRES_AT": "8200",
    }
    assert manager.settings.lingxing_access_token == "new-token"


def test_expiring_token_is_refreshed_before_request(monkeypatch) -> None:
    used_tokens = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"code":"0","data":{"list":[]}}'

    def fake_urlopen(request, timeout):
        used_tokens.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr(lianxing_api.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lianxing_api, "_build_sign", lambda params, app_key: "safe-sign")

    client = LingxingApiClient()
    client.settings = SimpleNamespace(
        lingxing_app_key="ak_38uk3Zx3JDWpl",
        lingxing_access_token="old-token",
        lingxing_token_expires_at=int(time.time()) + 60,
        lingxing_timeout_seconds=1,
    )
    client.token_manager = SimpleNamespace(access_token=lambda: "fresh-token", refresh=lambda: "fresh-token")

    client._post_json("https://openapi.lingxing.com/example/path", {"page": 1})

    assert "access_token=fresh-token" in used_tokens[0]


def test_auth_error_refreshes_token_and_retries_once(monkeypatch) -> None:
    used_tokens = []
    refresh_count = 0

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self.body

    def fake_urlopen(request, timeout):
        used_tokens.append(request.full_url)
        if len(used_tokens) == 1:
            return FakeResponse('{"code":"403","msg":"授权失效，请更新授权有效期或检查权限"}'.encode("utf-8"))
        return FakeResponse(b'{"code":"0","data":{"list":[]}}')

    def fake_refresh():
        nonlocal refresh_count
        refresh_count += 1
        return "new-token"

    monkeypatch.setattr(lianxing_api.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lianxing_api, "_build_sign", lambda params, app_key: "safe-sign")

    client = LingxingApiClient()
    client.settings = SimpleNamespace(
        lingxing_app_key="ak_38uk3Zx3JDWpl",
        lingxing_access_token="old-token",
        lingxing_token_expires_at=0,
        lingxing_timeout_seconds=1,
    )
    client.token_manager = SimpleNamespace(access_token=lambda: "old-token", refresh=fake_refresh)

    result = client._post_json("https://openapi.lingxing.com/example/path", {"page": 1})

    assert result["code"] == "0"
    assert refresh_count == 1
    assert "access_token=old-token" in used_tokens[0]
    assert "access_token=new-token" in used_tokens[1]


def test_erp_window_forces_usd_currency(monkeypatch) -> None:
    captured_payloads = []

    client = LingxingApiClient()
    client._post_json = lambda url, payload: captured_payloads.append(payload) or {"code": "0", "data": {"list": []}}

    client._fetch_window_records(
        "https://openapi.lingxing.com/example/path",
        {"extraParams": {"currencyCode": "CNY"}, "pageParam": "page", "pageSizeParam": "pageSize"},
        "2026-01-01",
        "2026-01-31",
        "month",
        200,
    )

    assert captured_payloads[0]["currencyCode"] == "USD"


def test_token_error_does_not_expose_secret(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(
            json.dumps({"code": "2001001", "msg": "app not exist", "data": None}).encode("utf-8")
        )

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self.body

    monkeypatch.setattr(lianxing_api.urllib.request, "urlopen", fake_urlopen)

    manager = LingxingTokenManager(
        SimpleNamespace(
            lingxing_api_base_url="https://openapi.lingxing.com",
            lingxing_app_key="ak_38uk3Zx3JDWpl",
            lingxing_app_secret="super-secret",
            lingxing_access_token="",
            lingxing_refresh_token="",
            lingxing_token_expires_at=0,
            lingxing_timeout_seconds=1,
        )
    )

    with pytest.raises(RuntimeError) as exc_info:
        manager.refresh()

    message = str(exc_info.value)
    assert "Lingxing token error 2001001" in message
    assert "super-secret" not in message
