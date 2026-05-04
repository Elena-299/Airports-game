import mysql.connector
import random

class Database:
    def __init__(self):
        self.config ={
            "host": "localhost",
            "user": "root",
            "password":"Python",
            "database":"glitch_in_transit"
        }
    def connect(self):
        return mysql.connector.connect(**self.config)