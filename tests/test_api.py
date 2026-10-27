"""Автоматизированные HTTP API-тесты TestShop (pytest + requests)."""
import pytest


def test_01_health(client, base_url):
    r = client.get(f"{base_url}/api/health", timeout=5)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "TestShop API"}


def test_02_register_success(client, base_url, credentials):
    r = client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    assert r.status_code == 201
    assert isinstance(r.json()["id"], int)
    assert r.json()["email"] == credentials["email"]


def test_03_register_invalid_email(client, base_url, credentials):
    credentials["email"] = "invalid-email"
    r = client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    assert r.status_code == 400
    assert "error" in r.json()


def test_04_register_duplicate(client, base_url, credentials):
    first = client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    second = client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    assert first.status_code == 201
    assert second.status_code == 409


def test_05_login_success(client, base_url, credentials):
    client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    r = client.post(f"{base_url}/api/login", json=credentials, timeout=5)
    assert r.status_code == 200
    assert r.json()["token_type"] == "Bearer"
    assert isinstance(r.json()["access_token"], str)
    assert len(r.json()["access_token"]) > 20


def test_06_login_wrong_password(client, base_url, credentials):
    client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    credentials["password"] = "WrongPassword123!"
    r = client.post(f"{base_url}/api/login", json=credentials, timeout=5)
    assert r.status_code == 401


def test_07_profile_without_token(client, base_url):
    r = client.get(f"{base_url}/api/profile", timeout=5)
    assert r.status_code == 401


def test_08_profile_invalid_token(client, base_url):
    r = client.get(f"{base_url}/api/profile", headers={"Authorization": "Bearer invalid-token"}, timeout=5)
    assert r.status_code == 401


def test_09_profile_valid_token(client, base_url, credentials, auth_headers):
    r = client.get(f"{base_url}/api/profile", headers=auth_headers, timeout=5)
    assert r.status_code == 200
    assert r.json()["email"] == credentials["email"]
    assert isinstance(r.json()["id"], int)


def test_10_cart_contract(client, base_url, auth_headers):
    r = client.get(f"{base_url}/api/cart", headers=auth_headers, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert {"items", "promo", "subtotal", "discount", "total"} <= data.keys()
    assert data["items"][0]["quantity"] == 1
    assert data["subtotal"] == data["total"] == 50_000
    assert data["discount"] == 0


@pytest.mark.parametrize("quantity,expected_status", [(1, 200), (99, 200), (0, 400), (100, 400), (-1, 400), (1.5, 400), (True, 400)])
def test_11_quantity_boundaries(client, base_url, auth_headers, quantity, expected_status):
    r = client.patch(f"{base_url}/api/cart/quantity", headers=auth_headers, json={"quantity": quantity}, timeout=5)
    assert r.status_code == expected_status
    if expected_status == 200:
        assert r.json()["items"][0]["quantity"] == quantity
        assert r.json()["total"] == 50_000 * quantity
    else:
        assert "error" in r.json()


def test_12_valid_promo(client, base_url, auth_headers):
    r = client.post(f"{base_url}/api/cart/promo", headers=auth_headers, json={"code": "SALE10"}, timeout=5)
    assert r.status_code == 200
    assert r.json()["subtotal"] == 50_000
    assert r.json()["discount"] == 5_000
    assert r.json()["total"] == 45_000


def test_13_invalid_promo(client, base_url, auth_headers):
    r = client.post(f"{base_url}/api/cart/promo", headers=auth_headers, json={"code": "BADCODE"}, timeout=5)
    assert r.status_code == 400
    assert "error" in r.json()


def test_14_xss_like_promo_rejected(client, base_url, auth_headers):
    payload = "<script>alert(1)</script>"
    r = client.post(f"{base_url}/api/cart/promo", headers=auth_headers, json={"code": payload}, timeout=5)
    assert r.status_code == 400
    assert "error" in r.json()


def test_15_unknown_endpoint(client, base_url):
    r = client.get(f"{base_url}/api/unknown", timeout=5)
    assert r.status_code == 404


def test_16_unsupported_method(client, base_url):
    r = client.put(f"{base_url}/api/cart", timeout=5)
    assert r.status_code == 405


def test_17_delete_item(client, base_url, auth_headers):
    r = client.delete(f"{base_url}/api/cart/item", headers=auth_headers, timeout=5)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


def test_18_delete_twice(client, base_url, auth_headers):
    first = client.delete(f"{base_url}/api/cart/item", headers=auth_headers, timeout=5)
    second = client.delete(f"{base_url}/api/cart/item", headers=auth_headers, timeout=5)
    assert first.status_code == 200
    assert second.status_code == 404


def test_19_empty_json_body(client, base_url):
    r = client.post(f"{base_url}/api/register", json={}, timeout=5)
    assert r.status_code == 400
    assert "error" in r.json()


def test_20_cart_without_auth(client, base_url):
    r = client.get(f"{base_url}/api/cart", timeout=5)
    assert r.status_code == 401
