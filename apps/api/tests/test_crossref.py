import httpx
from app.core.settings import Settings
from app.services.crossref import CrossrefClientService


class StubHTTPClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.request: dict | None = None

    def get(self, url: str, *, params: dict | None = None, headers: dict | None = None):
        self.request = {"url": url, "params": params, "headers": headers}
        return self.response


def test_fetch_recent_uses_cursor_compatible_crossref_parameters() -> None:
    response = httpx.Response(
        200,
        json={"message": {"items": [], "next-cursor": "next"}},
        request=httpx.Request("GET", CrossrefClientService.BASE_URL),
    )
    http = StubHTTPClient(response)
    service = CrossrefClientService(http, Settings(sync_lookback_days=60))

    result = service.fetch_recent({"issn": "1939-1471"})

    assert http.request is not None
    params = http.request["params"]
    assert params is not None
    assert params["cursor"] == "*"
    assert params["filter"].startswith("issn:1939-1471,from-pub-date:")
    assert "sort" not in params
    assert "order" not in params
    assert result["next_cursor"] == "next"
