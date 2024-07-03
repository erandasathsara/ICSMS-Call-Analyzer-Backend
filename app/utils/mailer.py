from app.config.config import Configurations
from app.models.send_mail import MailObject
from email.mime.text import MIMEText
from smtplib import SMTP_SSL

import logging

def send_mail(data: dict):
    msg = MailObject(**data)
    message = MIMEText(msg.body, "html")
    message["From"] = Configurations.mail_username
    message["To"] = ", ".join(msg.to)
    message["Subject"] = msg.subject

    try:
        with SMTP_SSL(Configurations.mail_host, Configurations.mail_port) as server:
            server.login(Configurations.mail_username, Configurations.mail_password)
            logging.info("Sending the email.")
            server.send_message(message)
            server.quit()
            logging.info("Email sent successfully.")
        return True
    except Exception as e:
        print(e)
        return False
