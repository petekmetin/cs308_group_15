import logging
import os
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _money(value):
    amount = Decimal(str(value or 0))
    return f"${amount:.2f}"


def _invoice_pdf_relative_path(invoice):
    return os.path.join("invoices", f"{invoice.invoice_number}.pdf")


def generate_invoice_pdf(invoice):
    order = (
        invoice.order.__class__.objects
        .select_related("customer", "invoice")
        .prefetch_related("items__sneaker", "items__size")
        .get(id=invoice.order_id)
    )
    relative_path = _invoice_pdf_relative_path(invoice)
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

    document = canvas.Canvas(absolute_path, pagesize=letter)
    width, height = letter
    y = height - 0.75 * inch

    document.setFont("Helvetica-Bold", 20)
    document.drawString(0.75 * inch, y, "SOLEVAULT Invoice")
    document.setFont("Helvetica", 10)
    document.drawRightString(width - 0.75 * inch, y, invoice.invoice_number)

    y -= 0.45 * inch
    issued_at = timezone.localtime(invoice.issued_at).strftime("%Y-%m-%d %H:%M")
    document.drawString(0.75 * inch, y, f"Order #{order.id}")
    document.drawRightString(width - 0.75 * inch, y, f"Issued: {issued_at}")

    y -= 0.35 * inch
    document.drawString(0.75 * inch, y, f"Customer: {order.customer.email}")
    y -= 0.25 * inch
    document.drawString(0.75 * inch, y, f"Card: **** **** **** {order.credit_card_last4 or '----'}")

    y -= 0.35 * inch
    document.setFont("Helvetica-Bold", 11)
    document.drawString(0.75 * inch, y, "Delivery Address")
    y -= 0.23 * inch
    document.setFont("Helvetica", 10)
    for line in (order.delivery_address or "").splitlines() or ["-"]:
        document.drawString(0.75 * inch, y, line[:95])
        y -= 0.18 * inch

    y -= 0.2 * inch
    document.setStrokeColor(colors.HexColor("#333333"))
    document.line(0.75 * inch, y, width - 0.75 * inch, y)
    y -= 0.3 * inch

    document.setFont("Helvetica-Bold", 10)
    document.drawString(0.75 * inch, y, "Item")
    document.drawString(3.85 * inch, y, "Size")
    document.drawRightString(4.8 * inch, y, "Qty")
    document.drawRightString(5.8 * inch, y, "Unit")
    document.drawRightString(width - 0.75 * inch, y, "Subtotal")
    y -= 0.2 * inch
    document.setFont("Helvetica", 9)

    for item in order.items.all():
        if y < 1.25 * inch:
            document.showPage()
            y = height - 0.75 * inch
            document.setFont("Helvetica", 9)

        name = item.sneaker.name[:45]
        size = "-"
        if item.size:
            size = f"{item.size.size_system} {item.size.size}"
        document.drawString(0.75 * inch, y, name)
        document.drawString(3.85 * inch, y, size)
        document.drawRightString(4.8 * inch, y, str(item.quantity))
        document.drawRightString(5.8 * inch, y, _money(item.unit_price))
        document.drawRightString(width - 0.75 * inch, y, _money(item.subtotal))
        y -= 0.23 * inch

    y -= 0.15 * inch
    document.line(4.6 * inch, y, width - 0.75 * inch, y)
    y -= 0.3 * inch
    document.setFont("Helvetica-Bold", 12)
    document.drawRightString(5.8 * inch, y, "Total")
    document.drawRightString(width - 0.75 * inch, y, _money(order.total_price))

    document.save()

    invoice.pdf_path = relative_path
    invoice.save(update_fields=["pdf_path"])
    return absolute_path


def email_invoice_pdf(invoice):
    pdf_path = generate_invoice_pdf(invoice)
    order = invoice.order
    subject = f"Your SoleVault invoice {invoice.invoice_number}"
    body = (
        f"Hi {order.customer.first_name or order.customer.username},\n\n"
        f"Thank you for your SoleVault order #{order.id}. "
        "Your invoice PDF is attached.\n\n"
        "SoleVault"
    )
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.customer.email],
    )
    message.attach_file(pdf_path, mimetype="application/pdf")
    message.send(fail_silently=False)
    return True


def email_refund_approved_notification(return_request):
    try:
        order = return_request.order
        customer = return_request.customer
        subject = f"Your SoleVault refund for Order #{order.id} has been approved"
        body = (
            f"Hi {customer.first_name or customer.username or 'Customer'},\n\n"
            f"We are pleased to inform you that your refund request for Order #{order.id} has been approved.\n"
            f"A total refund of {_money(return_request.total_refund_amount)} has been issued.\n\n"
            f"Thank you for shopping with SoleVault.\n\n"
            f"SoleVault"
        )
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        message.send(fail_silently=False)
        return True
    except Exception as e:
        logger.exception("Refund approval email failed for request %s", return_request.id)
        return False
