import smtplib
from email.message import EmailMessage

def send_mail(to, subject, body):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login('mahithavema@gmail.com', 'tkxy jacv pmyt tjux')
    message = EmailMessage()
    message['From'] = 'mahithavema@gmail.com'
    message['To'] = to
    message['Subject'] = subject
    message.set_content(body)
    s.send_message(message)
    s.quit()
    
