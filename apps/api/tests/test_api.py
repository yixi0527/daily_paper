def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_articles_endpoint_returns_seeded_article(client) -> None:
    response = client.get("/api/articles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["title"] == "Circuit mechanisms of memory consolidation"


def test_search_endpoint_filters_by_author(client) -> None:
    response = client.get("/api/search", params={"author": "Ada"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert "Ada" in payload["items"][0]["article"]["authors_text"]
