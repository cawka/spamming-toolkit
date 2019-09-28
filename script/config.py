"""
Global config file. Change variable below as needed but ensure that the log and
retry files have the correct permissions.
"""

# smtp settings
SMTP_HOST     = 'smtp.cs.fiu.edu'
SMTP_PORT     = '587'
SMTP_USER     = 'your-user'
SMTP_PASSWORD = 'your-password'
ENCRYPT_MODE  = 'starttls' # Choose between 'none', 'ssl' and 'starttls'

# the address and name the email comes from
FROM_NAME = 'YOUR NAME'
FROM_EMAIL = 'you@mail.com'

# The number of emails to send to each recipient
NB_EMAILS_PER_RECIPIENT = 1

# test recipients list
TEST_RECIPIENTS = [
    {'name': 'Your Name', 'email': 'your-test@email.com'},
]
