from django.conf import settings
from django.core.mail import send_mail

from .models import Quote


def send_quote_email(quote: Quote) -> None:
    to = (quote.customer_email or "").strip()
    if not to:
        raise ValueError("Quote has no customer email.")

    lines = []
    for line in quote.lines.all():
        lines.append(
            f"- {line.description}: {line.quantity} × ${line.unit_price} = ${line.line_total}"
        )
    body = (
        f"Hi {quote.customer_name or 'there'},\n\n"
        f"Here is your quote from Lakeside Pane Co.\n\n"
        f"Service address: {quote.service_address or '—'}\n\n"
        + "\n".join(lines)
        + f"\n\nSubtotal: ${quote.subtotal}\n"
        f"Minimum charge: ${quote.minimum_charge}\n"
        f"Total: ${quote.total}\n\n"
        "Reply to this email or call (555) 010-2040 to accept or ask questions.\n\n"
        "— Jordan Hale\n"
        "Lakeside Pane Co. (demo brand)\n"
    )
    send_mail(
        subject=f"Your window cleaning quote — Lakeside Pane Co. #{quote.pk}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )
