from django.urls import path

from . import views


urlpatterns = [
    path('', views.cart_detail, name='cart-detail'),
    path('clear/', views.clear_cart, name='cart-clear'),
    path('items/', views.add_cart_item, name='cart-add-item'),
    path('items/<int:item_id>/', views.update_cart_item, name='cart-update-item'),
    path('items/<int:item_id>/delete/', views.delete_cart_item, name='cart-delete-item'),
]

