#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText

class Email(object):
    def __init__(self, smtp_server='localhost', default_email_from=None, default_email_to=None):
        self.smtp_server = smtp_server
        self.default_email_from = default_email_from
        self.default_email_to = default_email_to
    
    def __call__(self, title, content, email_from=None, email_to=None):
        if email_from is None:
            if self.default_email_from is None:
                raise Exception('No source email defined')
            email_from = self.default_email_from
        if email_to is None:
            if self.default_email_to is None:
                raise Exception('No destination email defined')
            email_to = self.default_email_to
    
        mime_msg = MIMEText(content)
        mime_msg['Subject'] = title
        mime_msg['From'] = email_from
        mime_msg['To'] = email_to
        s = smtplib.SMTP(self.smtp_server)
        s.sendmail(email_from, [email_to], mime_msg.as_string())
        s.quit()
