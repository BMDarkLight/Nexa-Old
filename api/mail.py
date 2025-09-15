import os
import smtplib
import logging
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv
from ssl import create_default_context

# --- Setup ---
load_dotenv(dotenv_path=find_dotenv())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

use_smtp = os.getenv("USE_SMTP", "true").lower() == "true"

if use_smtp == "true":
    # --- SMTP Configuration ---
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_SENDER = os.getenv("SMTP_SENDER")

    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER]):
        raise ConnectionError(
            "SMTP is enabled, but one or more required environment variables are missing: "
            "SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER"
        )


    def send_email(to_email, subject, html_body):
     try:
        # Enforce TLS
        context = create_default_context()

        # Connect to the server
        with smtplib.SMTP_SSL(
            os.getenv("MAIL_HOST"), os.getenv("MAIL_PORT"), context=context
        ) as server:
            server.login(os.getenv("MAIL_USER"), os.getenv("MAIL_PASSWORD"))

            # Prepare the email
            msg = MIMEMultipart()
            msg["From"] = f"<{os.getenv("MAIL_FROM_ADDRESS")}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            # msg.add_header('x-liara-tag', 'test-tag')  # Add custom header
            msg.attach(MIMEText(html_body, "html"))

            # Send the email
            server.sendmail(os.getenv("MAIL_FROM_ADDRESS"), to_email, msg.as_string())
            print(f"Email sent to {to_email} successfully!")
     except Exception as e:
        print(f"Failed to send email: {e}")

else:
    # --- Resend Configuration ---
    import resend

    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_SENDER = os.getenv("RESEND_SENDER", "Nexa <onboarding@resend.dev>")
    
    if not RESEND_API_KEY:
         raise ConnectionError("USE_SMTP is false, but RESEND_API_KEY is not set.")

    resend.api_key = RESEND_API_KEY

    def send_email(to_email: str, subject: str, html_body: str):
        try:
            params: resend.Emails.SendParams = {
                "from": RESEND_SENDER,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            email = resend.Emails.send(params)
            logger.info(f"Resend email sent to {to_email} successfully! ID: {email.get('id')}")
            return email
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via Resend: {e}")
            raise
