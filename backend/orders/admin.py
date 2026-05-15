from django.contrib import admin
from .models import Order, OrderItem, Invoice, ReturnRequest, ReturnRequestItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_price', 'is_completed', 'created_at']
    list_filter = ['status', 'is_completed']
    search_fields = ['customer__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OrderItemInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'issued_at']
    readonly_fields = ['issued_at']


class ReturnRequestItemInline(admin.TabularInline):
    model = ReturnRequestItem
    extra = 0
    readonly_fields = ['subtotal_refund_amount']


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'customer', 'status', 'total_refund_amount', 'requested_at']
    list_filter = ['status']
    search_fields = ['customer__email', 'order__id']
    readonly_fields = ['requested_at', 'received_at', 'approved_at', 'rejected_at']
    inlines = [ReturnRequestItemInline]
