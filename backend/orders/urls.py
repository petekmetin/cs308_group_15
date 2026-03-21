from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/cancel/', views.cancel_order, name='order-cancel'),
    path('<int:pk>/refund/', views.request_refund, name='order-refund'),
    path('<int:pk>/approve-refund/', views.approve_refund, name='order-approve-refund'),

    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('deliveries/', views.DeliveryListView.as_view(), name='delivery-list'),
    path('deliveries/<int:pk>/', views.update_delivery, name='delivery-update'),
]