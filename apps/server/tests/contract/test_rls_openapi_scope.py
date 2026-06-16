from __future__ import annotations


def test_openapi_scope_does_not_include_future_product_surfaces(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"])

    forbidden_fragments = (
        "dashboard",
        "billing",
        "/admin",
        "desktop/capture",
        "mediascribe/direct",
    )

    for path in paths:
        assert not any(fragment in path for fragment in forbidden_fragments)
