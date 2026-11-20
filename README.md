# Django Inventory API

An independent Django API for a small shop's inventory and sales flow. It tracks products, stock receipts and adjustments, multi-item sales, and products that need restocking. References make retries safe, and a sale is rejected without changing any stock when one of its items is unavailable.

## Run

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

## API walkthrough

1. `POST /api/products/` with `{"sku":"MUG-1","name":"Mug","reorder_level":3}` creates a product. `GET /api/products/` lists current quantities.
2. `POST /api/products/1/movements/` with `{"kind":"in","amount":5,"reference":"delivery-1"}` records a delivery. Repeating the same request returns the original result without adding stock twice.
3. `POST /api/sales/` with `{"reference":"order-101","lines":[{"product_id":1,"quantity":2}]}` records a sale and its outgoing stock movements. A sale can contain several products. Repeating a sale reference with different items returns a conflict.
4. `GET /api/products/low-stock/` lists products at or below their reorder level. A reorder level of zero disables the alert for that product.

The Django test suite covers product creation, stock receipts, overselling, idempotent retries, sale conflicts, rollback when stock is insufficient, and low-stock reporting.

The project uses SQLite for local setup. It is a demonstration, not a deployed production system. Before production use it needs authentication, CSRF protection, input limits, PostgreSQL, and concurrent-sale testing against PostgreSQL.
