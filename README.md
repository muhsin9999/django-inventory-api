# Django Inventory API

An independent Django API for tracking products and stock movements in a small shop. It records an external reference for each movement, rejects overselling, and makes retries idempotent.

## Run

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

`POST /api/products/` with `{"sku":"MUG-1","name":"Mug"}` creates a product. `GET /api/products/` lists products. `POST /api/products/1/movements/` with `{"kind":"in","amount":5,"reference":"delivery-1"}` adds stock. Repeating the same reference and request returns the original movement without changing stock again.

The project uses SQLite for local setup. It is a demonstration, not a deployed production system. Before production use it needs authentication, CSRF protection, PostgreSQL, and concurrency testing against PostgreSQL.
