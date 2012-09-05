import wx
import sys
import os
import re
import crypt
import subprocess
import tempfile
import time
import random

import psycopg2 as pg

#---- User Class

class User(object):
    def __init__(self, userId, userName, typeId):
        self.userId = userId
        self.userName = userName
        self.typeId = typeId
    
    def getUserName(self):
        return self.userName
    
    def getUserId(self):
        return self.userId
    
    def getTypeId(self):
        return self.typeId

#--- Main Genome Database Object

class GenomeDatabase(object):
    def __init__(self):
        self.conn = None
        self.currentUser = None

#-------- General Functions
    
    def ReportError(msg):
        sys.stderr.write(str(msg) + "\n")
        sys.stderr.flush()
        
#-------- Database Connection Management

    def MakePostgresConnection(self):
        self.conn = pg.connect("dbname=genome_tree host=/tmp/")
        
    def ClosePostgresConnection(self):
        self.conn.close()
        self.conn = None
    
    def IsPostgresConnectionActive(self):
        if self.conn is not None:
            cur = self.conn.cursor()
            try:
                cur.execute("SELECT * from genomes")
            except:
                return False
            cur.close()
            return True
        else:
            return False

#-------- User Login Management
    
    def Passwordify(plaintext):
        return crypt.crypt(password, "GT")
    
    def UserLogin(self, username, password):
   
        if not self.IsPostgresConnectionActive():
            self.ReportError("Unable to establish database connection")
            return None
   
        cur = self.conn.cursor()
        query = "SELECT id, password, type_id FROM users WHERE username = %s"
        cur.execute(query, [username])
        result = cur.fetchone()
        cur.close()
        if result:
            (userid, password, type_id) = result
            if password == Passwordify(password):
                self.currentUser = User(result[0], result[2])
                return User
            else:
                self.ReportError("Incorrect password")
        else:
            self.ReportError("User not found")
        return None

#-------- User Management

    def CreateUser(self, username, password, userTypeId):
        
        if not self.IsPostgresConnectionActive():
            self.ReportError("Unable to establish database connection")
            return False
        
        if not self.currentUser:
            self.ReportError("You need to be logged in to to create a user")
            return False
        
        cur = self.conn.cursor()
        
        if userTypeId <= self.currentUser.getTypeId():
            self.ReportError("Cannot create a user with same or higher level privileges")
            return False
        
        cur.execute("INSERT into users (username, password, type_id) " +
                    "VALUES (%s, %s, %s) ", (username, Passwordify(password), userTypeId))
        
        self.conn.commit()
        
        return True
        
        
    