import json

from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Product, Sale, SaleLine, StockMovement


def parse_json(request):
    try:
        value = json.loads(request.body)
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


@csrf_exempt  # Local demo only. Add authentication and CSRF protection before deployment.
def products(request):
    if request.method == 'GET':
        return JsonResponse({'products': list(Product.objects.values('id', 'sku', 'name', 'quantity', 'reorder_level'))})
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = parse_json(request)
    if not data or not isinstance(data.get('sku'), str) or not data['sku'].strip() or not isinstance(data.get('name'), str) or not data['name'].strip():
        return JsonResponse({'error': 'sku and name are required'}, status=400)
    reorder_level = data.get('reorder_level', 0)
    if type(reorder_level) is not int or reorder_level < 0:
        return JsonResponse({'error': 'reorder_level must be a non-negative integer'}, status=400)
    try:
        product = Product.objects.create(sku=data['sku'].strip(), name=data['name'].strip(), reorder_level=reorder_level)
    except IntegrityError:
        return JsonResponse({'error': 'SKU already exists'}, status=409)
    return JsonResponse({'id': product.id, 'sku': product.sku, 'name': product.name, 'quantity': 0, 'reorder_level': reorder_level}, status=201)


def low_stock(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    products = Product.objects.filter(reorder_level__gt=0, quantity__lte=F('reorder_level')).values('id', 'sku', 'name', 'quantity', 'reorder_level')
    return JsonResponse({'products': list(products)})


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


@csrf_exempt  # Local demo only. Add authentication and CSRF protection before deployment.
def sales(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = parse_json(request)
    if not data or not isinstance(data.get('reference'), str) or not data['reference'].strip() or len(data['reference'].strip()) > 64:
        return JsonResponse({'error': 'A reference of 1–64 characters is required'}, status=400)
    lines = data.get('lines')
    if not isinstance(lines, list) or not lines or any(not isinstance(line, dict) or type(line.get('product_id')) is not int or type(line.get('quantity')) is not int or line['quantity'] <= 0 for line in lines):
        return JsonResponse({'error': 'Provide non-empty lines with product_id and positive quantity'}, status=400)
    requested = {line['product_id']: line['quantity'] for line in lines}
    if len(requested) != len(lines):
        return JsonResponse({'error': 'Each product may appear only once'}, status=400)
    reference = data['reference'].strip()
    with transaction.atomic():
        prior = Sale.objects.filter(reference=reference).first()
        if prior:
            old = dict(prior.lines.values_list('product_id', 'quantity'))
            if old != requested:
                return JsonResponse({'error': 'Reference reused with different items'}, status=409)
            return JsonResponse({'sale_id': prior.id, 'replayed': True})
        products = list(Product.objects.select_for_update().filter(id__in=requested).order_by('id'))
        if len(products) != len(requested):
            return JsonResponse({'error': 'Product not found'}, status=404)
        if any(product.quantity < requested[product.id] for product in products):
            return JsonResponse({'error': 'Insufficient stock'}, status=409)
        sale = Sale.objects.create(reference=reference)
        for product in products:
            amount = requested[product.id]
            product.quantity -= amount
            product.save(update_fields=['quantity'])
            SaleLine.objects.create(sale=sale, product=product, quantity=amount)
            StockMovement.objects.create(product=product, kind='out', amount=amount, reference=f'sale:{reference}:{product.id}')
        return JsonResponse({'sale_id': sale.id, 'replayed': False}, status=201)
