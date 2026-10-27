"""Запуск реального локального HTTP-сервера для тестов requests."""
import threading
import uuid

import pytest
import requests
from werkzeug.serving import make_server

from app import app


@pytest.fixture(scope="session")
def base_url():
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def client(base_url):
    with requests.Session() as session:
        session.request_timeout = 5
        yield session


@pytest.fixture
def credentials():
    return {"email": f"test-{uuid.uuid4().hex}@example.com", "password": "Password123!"}


@pytest.fixture
def auth_headers(client, base_url, credentials):
    response = client.post(f"{base_url}/api/register", json=credentials, timeout=5)
    assert response.status_code == 201, response.text
    response = client.post(f"{base_url}/api/login", json=credentials, timeout=5)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
