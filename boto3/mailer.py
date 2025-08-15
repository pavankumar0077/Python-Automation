import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def send_individual_emails(subject, body, recipients, pdf_path=None):
    # Email settings
    sender_email = 'dasarepavan007@gmail.com'
    sender_password = 'app-password'  # Use App Password if 2-Step Verification is enabled

    # Create base HTML body template for beautification
    html_body_template = """<html>
    <body style="font-family: 'Segoe UI'; background-color:#f4f4f4; padding:20px; color:#333;">
    <div style="max-width:600px; margin:0 auto; background-color:white; padding:20px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
    <h2 style="color:#4CAF50; text-align:center;">Welcome to Batch-7!</h2>
    <p style="font-size:18px; color:#555;">Hello <b>{name}</b>,</p>
    <p>We are excited to announce that <b>Batch-7</b> of our <b>DevSecOps & Cloud DevOps Bootcamp</b> is starting on <b>2nd November 2024</b>. Secure your spot now!</p>
    <ul>
    <li>CI/CD Tools</li>
    <li>Infrastructure as Code</li>
    <li>Security Tools</li>
    <li>Cloud Platforms</li>
    <li>Hands-on Projects</li>
    </ul>
    <p style="text-align:center;"><a href="https://devopsshack.com" style="background-color:#4CAF50; color:white; padding:15px; border-radius:5px;">Enroll Now</a></p>
    <p>Best Regards,<br>DevOps Shack Team</p>
    </div>
    </body>
    </html>"""

    for recipient in recipients:
        name = recipient.split('@')[0].capitalize()  # Personalize the message
        html_body = html_body_template.format(name=name)
        # Create the email message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient
        msg.attach(MIMEText(html_body, 'html'))

        # Attach the PDF if provided
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                pdf_part = MIMEBase('application', 'octet-stream')
                pdf_part.set_payload(pdf_file.read())
                encoders.encode_base64(pdf_part)
                pdf_part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf_path)}')
                msg.attach(pdf_part)

        # Send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())

# Example usage
recipients_list = ['dasaripavankumar27@gmail.com', 'tube8943@gmail.com']
send_individual_emails('Enroll Now: Batch-7 Starting on 2nd November', 'Batch-7 is starting soon!',
recipients_list, 'Batch-7-Syllabus.pdf')
