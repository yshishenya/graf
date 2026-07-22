from starlette.responses import HTMLResponse

from twobrain_rec_server.cabinet.templates import cabinet_html_response


def test_cabinet_full_page_response_does_not_set_hx_vary() -> None:
    response = cabinet_html_response("<main>full</main>")

    assert isinstance(response, HTMLResponse)
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "hx-request" not in response.headers.get("vary", "").lower()


def test_cabinet_hx_response_sets_vary_header() -> None:
    response = cabinet_html_response("<section>fragment</section>", hx_request=True)

    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["Vary"] == "HX-Request"
