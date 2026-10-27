"""Учебный REST API TestShop. Данные хранятся в памяти процесса."""
import re
import secrets
from functools import wraps
from threading import Lock
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, g

app = Flask(__name__)
PRICE = 50_000
MIN_QTY, MAX_QTY = 1, 99
_lock = Lock()
_users = {}  # email -> {id, email, password_hash, cart}
_tokens = {}  # bearer token -> email


def error(message, status):
    return jsonify({"error": message}), status


def json_object():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else None


def require_auth(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error("Требуется Bearer-токен", 401)
        with _lock:
            email = _tokens.get(parts[1])
            user = _users.get(email) if email else None
        if user is None:
            return error("Недействительный токен", 401)
        g.user = user
        return func(*args, **kwargs)
    return wrapped


def cart_payload(cart):
    quantity = cart["quantity"] if cart["product_exists"] else 0
    subtotal = PRICE * quantity
    discount = subtotal // 10 if cart["promo"] == "SALE10" else 0
    return {
        "items": ([{"id": 1, "name": "Смартфон TestPhone X", "price": PRICE, "quantity": quantity}]
                  if cart["product_exists"] else []),
        "promo": cart["promo"],
        "subtotal": subtotal,
        "discount": discount,
        "total": subtotal - discount,
    }


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "TestShop API"})


@app.post("/api/register")
def register():
    data = json_object()
    if data is None:
        return error("Ожидается JSON-объект", 400)
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
        return error("Некорректный email", 400)
    if not isinstance(password, str) or not 8 <= len(password) <= 64:
        return error("Пароль должен содержать от 8 до 64 символов", 400)
    email = email.lower()
    with _lock:
        if email in _users:
            return error("Пользователь уже существует", 409)
        user = {"id": len(_users) + 1, "email": email,
                "password_hash": generate_password_hash(password),
                "cart": {"quantity": 1, "product_exists": True, "promo": None}}
        _users[email] = user
    return jsonify({"id": user["id"], "email": email}), 201


@app.post("/api/login")
def login():
    data = json_object()
    if data is None:
        return error("Ожидается JSON-объект", 400)
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return error("Требуются email и password", 400)
    with _lock:
        user = _users.get(email.lower())
    if user is None or not check_password_hash(user["password_hash"], password):
        return error("Неверный email или пароль", 401)
    token = secrets.token_urlsafe(32)
    with _lock:
        _tokens[token] = user["email"]
    return jsonify({"access_token": token, "token_type": "Bearer"})


@app.get("/api/profile")
@require_auth
def profile():
    return jsonify({"id": g.user["id"], "email": g.user["email"]})


@app.get("/api/cart")
@require_auth
def get_cart():
    with _lock:
        return jsonify(cart_payload(g.user["cart"]))


@app.patch("/api/cart/quantity")
@require_auth
def change_quantity():
    data = json_object()
    if data is None:
        return error("Ожидается JSON-объект", 400)
    qty = data.get("quantity")
    if type(qty) is not int or not MIN_QTY <= qty <= MAX_QTY:
        return error("Количество должно быть целым числом от 1 до 99", 400)
    with _lock:
        cart = g.user["cart"]
        if not cart["product_exists"]:
            return error("Корзина пуста", 409)
        cart["quantity"] = qty
        return jsonify(cart_payload(cart))


@app.post("/api/cart/promo")
@require_auth
def apply_promo():
    data = json_object()
    if data is None:
        return error("Ожидается JSON-объект", 400)
    code = data.get("code")
    if not isinstance(code, str) or not code.strip():
        return error("Введите промокод", 400)
    if code.strip() != "SALE10":
        return error("Промокод недействителен", 400)
    with _lock:
        cart = g.user["cart"]
        if not cart["product_exists"]:
            return error("Корзина пуста", 409)
        cart["promo"] = "SALE10"
        return jsonify(cart_payload(cart))


@app.delete("/api/cart/item")
@require_auth
def delete_item():
    with _lock:
        cart = g.user["cart"]
        if not cart["product_exists"]:
            return error("Товар уже удалён", 404)
        cart["product_exists"] = False
        cart["promo"] = None
        cart["quantity"] = 0
        return jsonify(cart_payload(cart))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
