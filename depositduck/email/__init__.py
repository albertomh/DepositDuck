"""
(c) 2024 Alberto Morón Hernández
"""

import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import (
    SMTP,
    SMTP_SSL,
    SMTPDataError,
    SMTPHeloError,
    SMTPNotSupportedError,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
)

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from depositduck import BASE_DIR
from depositduck.dependables import get_logger
from depositduck.models.email import HtmlEmail
from depositduck.models.sql.email import Email
from depositduck.settings import Settings

LOG = get_logger()


async def render_html_email(template_name: str, context: HtmlEmail) -> str:
    templates_dir_path = BASE_DIR / "email" / "templates"

    env = Environment(
        loader=FileSystemLoader(templates_dir_path),
        autoescape=select_autoescape(["html", "jinja2"]),
    )

    template = env.get_template(template_name)
    rendered_html = template.render(context.model_dump())

    return rendered_html


async def record_email(
    db_session_factory: async_sessionmaker,
    sender: EmailStr,
    recipient: EmailStr,
    subject: str,
    html_body: str,
):
    session: AsyncSession
    async with db_session_factory.begin() as session:
        email = Email(
            sender_address=sender,
            recipient_address=recipient,
            subject=subject,
            body=html_body,
            sent_at=datetime.now(timezone.utc),
        )
        session.add(email)


async def send_email(
    settings: Settings,
    db_session_factory: async_sessionmaker,
    recipient: EmailStr,
    subject: str,
    html_body: str,
    plain_body: str | None = None,
) -> None:
    sender = settings.smtp_sender_address
    smtp_password = settings.smtp_password
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    html_part = MIMEText(html_body, "html")
    if plain_body:
        text_part = MIMEText(plain_body, "plain")
        message.attach(text_part)
    # email clients render last part first, so html must be last
    message.attach(html_part)

    smtp_cm: SMTP
    if settings.smtp_use_ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        smtp_cm = SMTP_SSL(settings.smtp_server, settings.smtp_port, context=ssl_context)
    else:
        smtp_cm = SMTP(
            settings.smtp_server,
            settings.smtp_port,
        )
    with smtp_cm as server:
        try:
            if settings.smtp_use_ssl:
                server.starttls()
                server.login(sender, smtp_password)
            server.sendmail(sender, recipient, message.as_string())
            await record_email(db_session_factory, sender, recipient, subject, html_body)
        except (
            SMTPHeloError,
            SMTPRecipientsRefused,
            SMTPSenderRefused,
            SMTPDataError,
            SMTPNotSupportedError,
        ) as e:
            # TODO: alert of failure and retry
            LOG.error(f"TODO: {e}")
        finally:
            server.quit()
