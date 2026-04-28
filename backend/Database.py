import mysql.connector
import random

class Database:
    def __init__(self):
        self.config ={
            "host": "localhost",
            "user": "root",
            "password":"metropolia12",
            "database":"Glitch in Transit"
        }
    def connect(self):
        return mysql.connector.connect(**self.config)