import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import logging
import time
import base64
logging.basicConfig(level=logging.INFO,  format='%(asctime)s  [%(levelname)s] %(message)s')
class ZET_F50_SMS:
    def __init__(self):
        self.lastSMSid = None
        self.isEmpty = None
        self.SMSDict = None
        self.readFileInfo()
    def readFileInfo(self):
        try:
            with open("lastData.txt", 'r') as file:
                fileStr = file.read()
                self.lastSMSid = fileStr.split()[0]
                self.isEmpty = bool(fileStr.split()[1])
                logging.log(level=logging.INFO, msg="Read from file")
        except:
            with open("lastData.txt", 'w+') as file:
                self.getSMSinfo()
                file.write(f"{self.lastSMSid} {self.isEmpty}")
                logging.log(level=logging.WARNING, msg="File Not Found, Created.")
    def updateFileInfo(self):
        with open("lastData.txt", 'w+') as file:
            file.write(f"{self.lastSMSid} {self.isEmpty}")
    # getSMSinfo UPDATE all the variable in the class
    def getSMSinfo(self):   
        try:
            url = f"http://192.168.0.1/goform/goform_get_cmd_process?isTest=false&cmd=sms_data_total&page=0&data_per_page=500&mem_store=1&tags=10&order_by=order+by+id+desc&_=1734772859922"
            payload={}
            headers = {
                'referer': 'http://192.168.0.1/index.html'
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            sms_return = json.loads(response.text)
            self.SMSDict = sorted(sms_return["messages"], key=lambda x: int(x['id']), reverse=True)
            logging.log(logging.DEBUG, self.SMSDict[0])
            self.isEmpty = False
            self.lastSMSid = self.SMSDict[0]['id']
        except: 
            if response.text == '{"messages":[]}':
                self.isEmpty = True                # there is no message in SMS box.
                self.lastSMSid = 'nan'
            logging.log(logging.ERROR, msg="CAN NOT GET MESSAGE LIST")
    def getNewSMSList(self):
        return_list = []
        idOfReadedSMS = self.lastSMSid
        self.getSMSinfo()
        if self.isEmpty :
            return return_list
        else:
            index = 0
            while(self.SMSDict[index]['id'] != idOfReadedSMS):
                timeSMS = self.SMSDict[index]['date'].split(",")
                newSMS = dict(
                    content     = self.getSMScontent(index),
                    timeReci    = f"{timeSMS[0]}/{timeSMS[1]}/{timeSMS[2]} {timeSMS[3]}:{timeSMS[4]}:{timeSMS[5]}",
                    number      = self.SMSDict[index]['number']
                )
                return_list.append(newSMS)
                index += 1
            return return_list
            

    def getSMScontent(self,index):
            try:
                base64code = self.SMSDict[index]['content']
                decoded_bytes = base64.b64decode(base64code)
                decoded_string = decoded_bytes.decode('utf-8')
                return decoded_string
            except:
                logging.log(level=logging.ERROR, msg="BASE64 DECODE ERROR HAS HAPPENED!")
                return "You have a new message but the base64 decode met a problem!"
         
class EmailNotifier:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def send_email(self, recipient_email, subject, message):
        try:
            # Create email content
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                logging.info(f"Email sent to {recipient_email}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}") 

with open("config.json", 'r') as file:
    config = json.load(file)

time_to_wait = config['time_to_wait']
zte = ZET_F50_SMS()

# Email notifier setup
notifier = EmailNotifier(
    smtp_server=config['smtp_server'],
    smtp_port=config['smtp_port'],
    sender_email=config['sender_email'],
    sender_password=config['sender_password']
)

while True:
    new_messages = zte.getNewSMSList()
    if new_messages:
        for sms in new_messages:
            subject = f"New SMS from {sms['number']}"
            message = f"From: {sms['number']}\nTime: {sms['timeReci']}\nContent: {sms['content']}"
            notifier.send_email(config['recipient_email'], subject, message)
        zte.updateFileInfo()
        logging.log(logging.INFO, 'Got new message and sent mail.')
    time.sleep(time_to_wait)