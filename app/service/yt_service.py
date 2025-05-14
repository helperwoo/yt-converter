import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

def send_mail(filepath: str, to: str = None):
    # 이메일 설정
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    email_account = os.getenv("EMAIL_ACCOUNT")
    email_password = os.getenv("EMAIL_PASSWORD")

    # 이메일 내용 설정
    to_email = to or os.getenv("EMAIL_TO")
    subject = "유튜브 영상"
    body = "유튜브 영상"

    # MIME 설정
    msg = MIMEMultipart()
    msg["From"] = email_account
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with open(filepath, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(filepath)}",
            )
            msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_account, email_password)
            server.sendmail(email_account, to_email, msg.as_string())
            print("Email with attachment sent successfully!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False