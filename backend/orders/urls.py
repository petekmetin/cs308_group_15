from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/cancel/', views.cancel_order, name='order-cancel'),
    path('<int:pk>/refund/', views.request_refund, name='order-refund'),
    path('<int:pk>/approve-refund/', views.approve_refund, name='order-approve-refund'),
    path('<int:pk>/returns/', views.create_return_request, name='order-return-create'),

    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice-pdf'),
    path('reports/sales-summary/', views.sales_summary_report, name='sales-summary-report'),
    path('returns/', views.return_request_list, name='return-request-list'),
    path('returns/<int:pk>/', views.return_request_detail, name='return-request-detail'),
    path('deliveries/', views.DeliveryListView.as_view(), name='delivery-list'),
    path('deliveries/<int:pk>/', views.update_delivery, name='delivery-update'),
]
