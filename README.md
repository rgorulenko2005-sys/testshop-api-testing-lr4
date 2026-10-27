# ЛР4 — Этап 3. API-автотесты TestShop

Автотесты используют **pytest + requests** и отправляют настоящие HTTP-запросы к Flask API.
Тестовый сервер автоматически запускается на свободном локальном порту через pytest-фикстуру.
Не нужно отдельно запускать `python app.py` для автотестов. Данные пользователей уникальны для каждого теста.

## Windows PowerShell

```powershell
cd lr4-stage3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -v
python -m pytest -v --html=api-report.html --self-contained-html
```

В `tests/test_api.py` — 20 тестовых функций, одна из которых параметризована семью наборами данных, итого **26 тестовых случаев**.
Проверяются positive, negative, boundary, security (отказ в доступе без/с неверным токеном), contract.
XSS-проверка подтверждает отказ от недопустимого промокода, а не полноценную XSS-безопасность.

Для CI используется этот же запуск `python -m pytest -v`.
