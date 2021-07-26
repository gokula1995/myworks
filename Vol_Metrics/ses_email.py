import sys
import traceback
import os
from ConfigParser import SafeConfigParser
import smtplib
import logging
import subprocess
import time
import datetime
import fnmatch
import re
from datetime import date, datetime, timedelta
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText
from email import Encoders
import os.path
from datetime import datetime


## Logging for this module only
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('/tmp/mailer.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)
## END - logger initialization


def send_mail (msgsubject, msgtxt, file_name):

    config_file="./mailer.cfg"
    config = SafeConfigParser()
    config.read(config_file)
    error=0

    #msg = MIMEMultipart('alternative')
    msg = MIMEMultipart('mixed')
    msg['Subject'] = msgsubject
    msg['From'] = config.get("mail","mail_from")
    if (not msg['From'] or msg['From']==None or msg['From']==''):
        logger.error ("From address not defined to send mail. Check mail configurations.")
        error=1
    #with open(msgtxt_file, 'r') as f:
      #msgtxt = f.read()
    #logger.info(msgtxt)
    msg.preamble = msgtxt

    if config.get("mail","mail_enable")=='1':
        for j in config.get("mail","mail_to").split(','):
            msg.add_header('To', j)
    else:
        return

    if (not msg.get_all('To') or msg.get_all('To')==None or msg.get_all('To')==['']):
        ## There was some issue in getting the email id's to whom the mail will be sent
        ## Send a mail to administrator [mail('From')] 
        logger.error ("No recipients found to send mail. Check mail configurations.")
        error=1
    email_content = """
                    <head>
                      <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                      <title>html title</title>
                      <style type="text/css" media="screen">
                      table, th, td {
                      border: 1px solid black;
                      border-collapse: collapse;
                      }       
                      </style>
                    </head>
                    <body>
                      %s
                    </body>
                    """ % msgtxt

    msg.attach(MIMEText(email_content, 'HTML'))

    ## Attach the file file_name
    if os.path.isfile(file_name):
        part1 = MIMEBase('application', "octet-stream")
        part1.set_payload(open(file_name, "rb").read())
        Encoders.encode_base64(part1)
        part1.add_header('Content-Disposition', 'attachment; filename="%s"' % basename(file_name))
        msg.attach(part1)
    
    mail_host=config.get("mail","mail_host")
    mail_port=config.get("mail","mail_port")
    mail_user=config.get("mail","mail_user")
    mail_pass=config.get("mail","mail_pass")

    if error == 0 :
        try:
            s=smtplib.SMTP(mail_host,mail_port)
            s.starttls()
        except socket.error:
            logger.error ("Socket error when trying to connect to SMTP server. Check mail configurations.")
            return
        except:
            logger.error ("Error connecting to SMTP server. Check mail configurations.")
            return

        try:
            s.login(mail_user, mail_pass)
        except smtplib.SMTPAuthenticationError:
            s.quit()
            logger.error ("Authentication error. Could not send mail. Check mail configurations.")
            return
        try:
            s.sendmail(msg['From'], msg.get_all('To'), msg.as_string())
        except:
            s.quit()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error ("Error sending mail. Check mail configurations." )
            logger.error(traceback.format_exception(exc_type, exc_value, exc_traceback))
            return
{"mode":"full","isActive":false}
