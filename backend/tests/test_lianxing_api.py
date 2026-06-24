from io import BytesIO
from types import SimpleNamespace
import urllib.error

import pytest

from app import lianxing_api
from app.lianxing_api import LingxingApiClient


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
        lingxing_timeout_seconds=1,
    )

    with pytest.raises(RuntimeError) as exc_info:
        client._post_json("https://openapi.lingxing.com/example/path", {"page": 1})

    message = str(exc_info.value)
    assert "Lingxing API HTTP 403 on /example/path" in message
    assert "ip not allowed" in message
    assert "secret-token" not in message
    assert "secret-sign" not in message
