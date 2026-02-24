from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail

from apps.orders.models import Order


def _money(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        return f"{value.quantize(Decimal('0.01'))}"
    return str(value)


def _order_lines(order: Order) -> list[str]:
    lines: list[str] = []
    lines.append(f"Order ID: {order.id}")
    lines.append(f"Status: {order.status}")
    lines.append(f"Date: {order.dt.isoformat()}")
    lines.append("")
    lines.append("Items:")
    total_sum = Decimal("0.00")

    for item in order.items.select_related("product", "shop").all():
        unit_price = item.unit_price if item.unit_price is not None else Decimal("0.00")
        line_total = unit_price * Decimal(item.quantity)
        total_sum += line_total

        lines.append(
            f"- {item.product.name} | shop: {item.shop.name} | qty: {item.quantity} | "
            f"price: {_money(item.unit_price)} | total: {_money(line_total)}"
        )

    lines.append("")
    lines.append(f"TOTAL: {_money(total_sum)}")
    return lines


def send_order_email_to_customer(order: Order) -> None:
    """
    Клиенту — подтверждение приёма заказа.
    """
    user = order.user
    to_email = getattr(user, "email", "") or ""
    if not to_email:
        # Нет email у пользователя — пропускаем
        return

    subject = f"[RetailProcurement] Order #{order.id} accepted"
    body = "\n".join(
        [
            f"Hello, {getattr(user, 'username', 'customer')}!",
            "",
            "Your order has been accepted.",
            "",
            *(_order_lines(order)),
            "",
            "Thank you!",
        ]
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=False,
    )


def send_order_email_to_admin(order: Order) -> None:
    """
    Админу — накладная/заказ на исполнение.
    """
    admin_email = getattr(settings, "ADMIN_EMAIL", None)
    if not admin_email:
        return

    user = order.user
    subject = f"[RetailProcurement] New order #{order.id} for execution"
    body = "\n".join(
        [
            "New order created.",
            "",
            f"Customer: id={user.id} username={getattr(user, 'username', '')} email={getattr(user, 'email', '')}",
            "",
            *(_order_lines(order)),
        ]
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[admin_email],
        fail_silently=False,
    )