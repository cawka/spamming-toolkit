#!/usr/bin/env python3

import csv
import logging
import os
import re
import smtplib
import sys
import argparse

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.nonmultipart import MIMENonMultipart
from email import encoders
from time import sleep

from . import config # Our file config.py

# setup logging to specified log file
logging.basicConfig(level=logging.DEBUG)

class PyMailer():
    """
    A python bulk mailer commandline utility. Takes six arguments: the path to the html file to be parsed; the database of recipients (.csv); the subject of the email; email address the mail comes from; the name the email is from; the number of emails to send to each recipient.
    """
    def __init__(self, args, **kwargs):
        if args.txt:
            self.txt_path            = args.txt
        else:
            self.txt_path = ""
        self.html_path               = args.html[0]
        self.csv_path                = args.addresses[0]
        self.subject                 = args.subject[0]
        self.images                  = args.image
        self.attachments             = args.attach
        self.from_name               = kwargs.get('from_name', config.FROM_NAME)
        self.from_email              = kwargs.get('to_name', config.FROM_EMAIL)
        self.nb_emails_per_recipient = kwargs.get('nb_emails_per_recipient', config.NB_EMAILS_PER_RECIPIENT)

    def _stats(self, message):
        pass
        # """
        # Update stats log with: last recipient (in case the server crashes); datetime started; datetime ended; total number of recipients attempted; number of failed recipients; and database used.
        # """
        # try:
        #     stats_file = open(config.STATS_FILE, 'r')
        # except IOError:
        #     raise IOError("Invalid or missing stats file path.")

        # stats_entries = stats_file.read().split('\n')

        # # check if the stats entry exists if it does overwrite it with the new message
        # is_existing_entry = False
        # if stats_entries:
        #     for i, entry in enumerate(stats_entries):
        #         if entry:
        #             if message[:5] == entry[:5]:
        #                 stats_entries[i] = message
        #                 is_existing_entry = True

        # # if the entry does not exist append it to the file
        # if not is_existing_entry:
        #     stats_entries.append(message)

        # stats_file = open(config.STATS_FILE, 'w')
        # for entry in stats_entries:
        #     if entry:
        #         stats_file.write("%s\n" % entry)
        # stats_file.close()

    def _validate_email(self, email_address):
        """
        Validate the supplied email address.
        """
        if not email_address or len(email_address) < 5:
            return None
        if not re.match(r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", email_address):
            return None
        return email_address

    @staticmethod
    def _prepare_text(template, recipient_data):
        """
        Open, parse and substitute placeholders with recipient data.
        """
        try:
            file = open(template, 'rt', encoding='utf-8')
        except IOError:
            raise IOError("Invalid or missing html file path.")

        content = file.read()
        if not content:
            raise Exception("The html file is empty.")

        # replace all placeolders associated to recipient_data keys
        if recipient_data:
            for key, value in recipient_data.items():
                placeholder = "%%%%%s%%%%" % key.upper()
                content = content.replace(placeholder, value)

        return content

    def _form_email(self, recipient_data):
        """
        Form the html email, including mimetype and headers.
        """

        # instatiate the email object and assign headers
        email_message = MIMEMultipart('related')
        email_message.preamble = 'This is a multi-part message in MIME format.'

        if self.txt_path != "":
            txt = MIMEText(PyMailer._prepare_text(self.txt_path, recipient_data), 'plain', _charset='utf-8')
            # encoders.encode_quopri(txt)
            email_message.attach(txt)

        if self.html_path != "":
            html = MIMEText(PyMailer._prepare_text(self.html_path, recipient_data), 'html', _charset='utf-8')
            # encoders.encode_quopri(html)
            email_message.attach(html)

        for image in self.images:
            with open(image, 'rb') as f:
                imageMime = MIMEImage(f.read())
            imageMime.add_header('Content-ID', '<%s>' % image)
            email_message.attach(imageMime)

        for attachment in self.attachments:
            with open(attachment[1], 'rb') as f:
                attachmentMime = MIMENonMultipart(attachment[0].split('/')[0], attachment[0].split('/')[1])
                attachmentMime.set_payload(f.read())
                if attachment[0].split('/')[0] == 'text':
                    encoders.encode_quopri(attachmentMime)
                attachmentMime.add_header('Content-Disposition', 'attachment; filename=%s' % attachment[1])
                email_message.attach(attachmentMime)

        email_message['From'] = recipient_data.get('sender')
        email_message['To'] = recipient_data.get('recipient')
        email_message['Subject'] = self.subject

        return email_message.as_string()

    def _parse_csv(self, csv_path=None):
        """
        Parse the entire csv file and return a list of dicts.
        """
        is_resend = csv_path is not None
        if not csv_path:
            csv_path = self.csv_path

        try:
            csv_file = open(csv_path, 'r+t', encoding='utf-8')
        except IOError:
            raise IOError("Invalid or missing csv file path.")

        csv_reader = csv.reader(csv_file)

        """
        Invalid emails ignored
        """
        variables_names = []
        recipients_list = []
        for i, row in enumerate(csv_reader):
            # Get header keys
            if i == 0:
                for cell in row:
                    variables_names.append(cell)
                continue

            # Get all variables
            variables = {}
            for j, var_name in enumerate(variables_names):
                if var_name == 'email':
                    if self._validate_email(row[j]):
                        variables[var_name] = row[j]
                        recipients_list.append(variables)
                else:
                    variables[var_name] = row[j]

        # clear the contents of the resend csv file
        if is_resend:
            csv_file.write('')

        csv_file.close()

        return recipients_list

    def send(self, recipient_list=None):
        """
        Iterate over the recipient list and send the specified email.
        """
        if config.ENCRYPT_MODE != 'none' and config.ENCRYPT_MODE != 'ssl' and config.ENCRYPT_MODE != 'starttls':
            raise Exception("Please choose a correct ENCRYPT_MODE")

        if not recipient_list:
            recipient_list = self._parse_csv()

        # instantiate the number of falied recipients
        failed_recipients = 0

        for recipient_data in recipient_list:
            if recipient_data.get('name'):
                recipient_data['recipient'] = "%s <%s>" % (recipient_data.get('name'), recipient_data.get('email'))
            else:
                recipient_data['recipient'] = recipient_data.get('email')

            recipient_data['sender'] = "%s <%s>" % (self.from_name, self.from_email)

            # instantiate the required vars to send email
            message = self._form_email(recipient_data)

            with open("debug.eml", "wt") as out:
                out.write(message)

            for nb in range(0, self.nb_emails_per_recipient):
                print("Sending to %s..." % recipient_data.get('recipient'))
                try:
                    # send the actual email
                    if config.ENCRYPT_MODE == 'ssl':
                        smtp_server = smtplib.SMTP_SSL(host=config.SMTP_HOST, port=config.SMTP_PORT, timeout=100)
                    else:
                        smtp_server = smtplib.SMTP(host=config.SMTP_HOST, port=config.SMTP_PORT, timeout=100)

                    if config.ENCRYPT_MODE != 'none':
                        smtp_server.ehlo()
                        if config.ENCRYPT_MODE == 'starttls':
                            smtp_server.starttls()
                            smtp_server.ehlo()

                    if config.SMTP_USER and config.SMTP_PASSWORD:
                        smtp_server.login(config.SMTP_USER, config.SMTP_PASSWORD)

                    smtp_server.sendmail(recipient_data.get('sender'), recipient_data.get('recipient'), message)
                    smtp_server.close()
                    # save the last recipient to the stats file incase the process fails
                    self._stats("LAST RECIPIENT: %s" % recipient_data.get('recipient'))

                    # allow the system to sleep for .25 secs to take load off the SMTP server
                    sleep(1)
                except smtplib.SMTPException as e:
                    print("EXCEPTION")
                    print(repr(e))
                    logging.error("Recipient email address failed: %s\n=== Exception ===\n%s" % (recipient, repr(e)))

                    # save the number of failed recipients to the stats file
                    failed_recipients = failed_recipients + 1
                    self._stats("FAILED RECIPIENTS: %s" % failed_recipients)

    def send_test(self):
        self.send(recipient_list=config.TEST_RECIPIENTS)

    def count_recipients(self, csv_path=None):
        return len(self._parse_csv(csv_path))


parser = argparse.ArgumentParser(description='PyMailer, a simple bulk mailer script')
parser.add_argument('-t', dest='test_only', action='store_true',
                    help='Send to test emails in config.py only')
parser.add_argument('-s', dest='send', action='store_true',
                    help='Send to email in the supplied CSV file')

parser.add_argument('--txt',    metavar='txt',     nargs='?', help='txt template')
parser.add_argument('html',     metavar='html',    nargs=1, help='HTML template')
parser.add_argument('--image',  action='append', help='Image files to embed, refered using cid:filename in HTML (can be repeated multiple times)')
parser.add_argument('addresses', metavar='dest_csv',nargs=1, help='CSV containing names and addresses (<name>,<address)*')
parser.add_argument('subject',  metavar='subject', nargs=1, help='Email subject')

if __name__ == '__main__':
    args = parser.parse_args()
    if not args.test_only and not args.send:
        print("ERROR: Either -t or -s must be specified")
        sys.exit(1)

    print (args.image)

    pymailer = PyMailer(args)

    if args.send:
        if input("You are about to send to %s recipients. Do you want to continue (yes/no)? " % pymailer.count_recipients()) == 'yes':
            # save the csv file used to the stats file
            pymailer._stats("CSV USED: %s" % args.addresses[0])

            # send the email and try resend to failed recipients
            pymailer.send()
            pymailer.resend_failed()
        else:
            print("Aborted.")
            sys.exit()
    elif args.test_only:
        if input("You are about to send a test mail to all recipients as specified in config.py. Do you want to continue (yes/no)? ") == 'yes':
            pymailer.send_test()
        else:
            print("Aborted.")
            sys.exit()

    # save the end time to the stats file
    pymailer._stats("END TIME: %s" % datetime.now())
