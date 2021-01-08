import smtplib
# from sensitive import GMAIL_SMTP, FROM_EMAIL, PASSWORD
import os

GMAIL_SMTP = os.environ.get('GMAIL_SMTP')
FROM_EMAIL = os.environ.get('FROM_EMAIL')
PASSWORD = os.environ.get('PASSWORD')

def send_email(subject, content):
    with smtplib.SMTP(GMAIL_SMTP) as conn:
        conn.starttls()
        conn.login(user=FROM_EMAIL, password=PASSWORD)

        conn.sendmail(from_addr=FROM_EMAIL,
                      to_addrs="menwa.codes@yahoo.com",
                      msg=f"Subject:{subject}\n\n{content}".encode("utf8"))
