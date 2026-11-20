from django.urls import path
from inventory import views

urlpatterns = [
    path('api/products/', views.products),
    path('api/products/<int:product_id>/movements/', views.movements),
]
