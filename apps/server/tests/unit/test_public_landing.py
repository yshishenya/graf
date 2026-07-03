def test_public_landing_is_self_serve_entry(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Встреча останется с вами" in response.text
    assert "GRAF сам записывает звонок" in response.text
    assert "Сразу к регистрации" not in response.text
    assert "Любой сервис для созвонов" in response.text
    assert "GRAF записывает встречу там, где вы уже созваниваетесь" in response.text
    assert "GRAF REC" not in response.text
    assert "Примеры поддерживаемых платформ" not in response.text
    assert "Яндекс Телемост" in response.text
    assert "SberJazz" in response.text
    assert "TrueConf" in response.text
    assert "МТС Линк" in response.text
    assert "Контур.Толк" in response.text
    assert "DION" in response.text
    assert "Без бота в звонке" in response.text
    assert "через минуты" not in response.text
    assert "Транскрипт" in response.text
    assert "Запуск в Q3" in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 2
    assert 'href="/sign-up?next=/meetings"' not in response.text
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
    assert "/static/cabinet/favicon.ico?v=" in response.text
    assert 'width="940"' in response.text
    assert 'height="710"' in response.text
    assert "landing-tools-strip.png" not in response.text
    assert "https://" not in response.text


def test_public_landing_has_keyboard_entry_points(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert '<a class="skip-link" href="#main">' in response.text
    assert '<main id="main">' in response.text
