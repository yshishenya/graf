def test_public_landing_is_self_serve_entry(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Встреча останется с вами" in response.text
    assert "GRAF сам записывает звонок" in response.text
    assert "Сразу к регистрации" in response.text
    assert "Без ботов" in response.text
    assert "Транскрипт" in response.text
    assert "Запуск в Q3" in response.text
    assert response.text.count('href="/sign-up?next=/meetings"') >= 2
    assert "Посмотреть" not in response.text
    assert "демо" not in response.text
    assert "пилот" not in response.text
    assert ">01<" not in response.text
    assert ">02<" not in response.text
    assert ">03<" not in response.text
    assert ">04<" not in response.text


def test_public_landing_uses_local_static_assets(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "/static/public/landing.css?v=" in response.text
    assert "/static/public/landing-hero-product.png?v=" in response.text
    assert "/static/public/landing-tools-strip.png?v=" in response.text
    assert "/static/cabinet/favicon.ico?v=" in response.text
    assert 'width="940"' in response.text
    assert 'height="710"' in response.text
    assert 'width="820"' in response.text
    assert 'height="130"' in response.text
    assert "https://" not in response.text


def test_public_landing_has_keyboard_entry_points(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert '<a class="skip-link" href="#main">' in response.text
    assert '<main id="main">' in response.text
