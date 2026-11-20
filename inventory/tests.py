import json

from django.test import TestCase

from .models import Product, StockMovement


class InventoryTests(TestCase):
    def post_json(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    def test_create_and_list_product(self):
        created = self.post_json('/api/products/', {'sku': 'MUG-1', 'name': 'Mug'})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['quantity'], 0)
        listed = self.client.get('/api/products/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()['products'][0]['sku'], 'MUG-1')
        self.assertEqual(self.post_json('/api/products/', {'sku': 'MUG-1', 'name': 'Other'}).status_code, 409)

    def test_stock_change_and_replay(self):
        product = Product.objects.create(sku='MUG-1', name='Mug')
        url = f'/api/products/{product.id}/movements/'
        movement = {'kind': 'in', 'amount': 5, 'reference': 'supplier-100'}
        self.assertEqual(self.post_json(url, movement).status_code, 201)
        replay = self.post_json(url, movement)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()['replayed'])
        product.refresh_from_db()
        self.assertEqual(product.quantity, 5)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_cannot_sell_more_than_available(self):
        product = Product.objects.create(sku='MUG-1', name='Mug', quantity=2)
        response = self.post_json(f'/api/products/{product.id}/movements/', {'kind': 'out', 'amount': 3, 'reference': 'sale-1'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_reference_cannot_change_meaning(self):
        product = Product.objects.create(sku='MUG-1', name='Mug')
        url = f'/api/products/{product.id}/movements/'
        self.post_json(url, {'kind': 'in', 'amount': 5, 'reference': 'delivery-1'})
        response = self.post_json(url, {'kind': 'in', 'amount': 10, 'reference': 'delivery-1'})
        self.assertEqual(response.status_code, 409)
        product.refresh_from_db()
        self.assertEqual(product.quantity, 5)
