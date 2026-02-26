from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import receiver

from django_rest_passwordreset.signals import reset_password_token_created


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Sends email with password reset token.
    Сейчас EMAIL_BACKEND = console -> письмо появится в терминале runserver.
    """
    user = reset_password_token.user
    to_email = getattr(user, "email", "") or ""
    if not to_email:
        return

    subject = "[RetailProcurement] Password reset"
    # Можно сделать ссылку на фронт, если он появится:
    # reset_link = f"{FRONT_URL}/reset-password?token={reset_password_token.key}"
    message = "\n".join(
        [
            f"Hello, {getattr(user, 'username', 'user')}!",
            "",
            "You requested password reset.",
            "",
            f"Your reset token: {reset_password_token.key}",
            "",
            "If you did not request this, ignore this email.",
        ]
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=False,
    )