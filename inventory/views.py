import json

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Product, StockMovement


def parse_json(request):
    try:
        value = json.loads(request.body)
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


@csrf_exempt  # Local demo only. Add authentication and CSRF protection before deployment.
def products(request):
    if request.method == 'GET':
        return JsonResponse({'products': list(Product.objects.values('id', 'sku', 'name', 'quantity'))})
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = parse_json(request)
    if not data or not isinstance(data.get('sku'), str) or not data['sku'].strip() or not isinstance(data.get('name'), str) or not data['name'].strip():
        return JsonResponse({'error': 'sku and name are required'}, status=400)
    try:
        product = Product.objects.create(sku=data['sku'].strip(), name=data['name'].strip())
    except IntegrityError:
        return JsonResponse({'error': 'SKU already exists'}, status=409)
    return JsonResponse({'id': product.id, 'sku': product.sku, 'name': product.name, 'quantity': 0}, status=201)


@csrf_exempt  # Local demo only. Add authentication and CSRF protection before deployment.
def movements(request, product_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = parse_json(request)
    if not data or data.get('kind') not in ('in', 'out') or type(data.get('amount')) is not int or data['amount'] <= 0 or not isinstance(data.get('reference'), str) or not data['reference'].strip():
        return JsonResponse({'error': 'Valid kind, positive amount and reference are required'}, status=400)
    reference = data['reference'].strip()
    with transaction.atomic():
        existing = StockMovement.objects.filter(reference=reference).first()
        if existing:
            if existing.product_id != product_id or existing.kind != data['kind'] or existing.amount != data['amount']:
                return JsonResponse({'error': 'Reference reused with different details'}, status=409)
            return JsonResponse({'movement_id': existing.id, 'quantity': existing.product.quantity, 'replayed': True})
        product = Product.objects.select_for_update().filter(id=product_id).first()
        if product is None:
            return JsonResponse({'error': 'Product not found'}, status=404)
        if data['kind'] == 'out' and product.quantity < data['amount']:
            return JsonResponse({'error': 'Insufficient stock'}, status=409)
        product.quantity += data['amount'] if data['kind'] == 'in' else -data['amount']
        product.save(update_fields=['quantity'])
        movement = StockMovement.objects.create(product=product, kind=data['kind'], amount=data['amount'], reference=reference)
        return JsonResponse({'movement_id': movement.id, 'quantity': product.quantity, 'replayed': False}, status=201)
