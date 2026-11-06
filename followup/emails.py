"""Review-ask email (Django email — demo notification path, no live SMS)."""

from django.conf import settings
from django.core.mail import send_mail


def send_review_ask_email(*, customer_name: str, to_email: str, review_url: str) -> None:
    subject = "Thanks from Lakeside Pane Co. — leave a Google review?"
    body = (
        f"Hi {customer_name or 'there'},\n\n"
        "Thanks again for choosing Lakeside Pane Co. "
        "If the glass looks good, a quick Google review helps neighbors find us:\n\n"
        f"{review_url}\n\n"
        "No pressure — and thank you either way.\n\n"
        "— Jordan Hale\n"
        "Lakeside Pane Co. (demo brand)\n"
        "(555) 010-2040\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
