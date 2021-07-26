import json
import requests

from Logger.logger import logger
from Config.settings import config

class Message(object):
    def __init__(self):
        self.DEBUG = config.settings("Debug", "DEBUG")
        self.URL = config.settings("Message", "TARGET_SERVER")
    
    def sendFriendMessage(self, message, userid):
        
        try:
            path = "sendFriendMessage"
            self.URL = "http://{}/{}".format(self.URL, path)
    
            body = {
                "sessionKey": "YourSession",
                "target": userid,
                "messageChain": [
                    {"type": "Plain", "text": message}
                ]
            }
            sender = requests.post(self.URL, data=json.dumps(body))
    
            mes = message.replace("\n", " ")
            if len(mes) > 10:
                mes = mes[:10] + "···"
            logger.info("Send {}".format(mes))
    
            if self.DEBUG:
                print(sender.request.self.URL)
                sender.raise_for_status()
                print(sender.text)
                
            return True
        except:
            logger.error("Message Send Failed")
            return False
    
    
    def sendGroupMessage(self, message, groupid):
        try:
            path = "sendGroupMessage"
            self.URL = "http://{}/{}".format(self.URL, path)
    
            body = {
                "sessionKey": "YourSession",
                "target": groupid,
                "messageChain": [
                    {"type": "Plain", "text": message}
                ]
            }
            sender = requests.post(self.URL, data=json.dumps(body))
            mes = message.replace("\n", " ")
            if len(mes) > 10:
                mes = mes[:10] + "···"
            logger.info("Send {}".format(mes))
    
            if self.DEBUG:
                print(sender.request.self.URL)
                sender.raise_for_status()
                print(sender.text)
                
            return True
        except:
            logger.error("Message Send Failed")
            return False

message = Message()

# 兼容0.4.6以下版本

def sendFriendMessage(message, userid):
    message.sendFriendMessage(message, userid)

def sendGroupMessage(message, groupid):
    message.sendGroupMessage(message, groupid)
