import sys
import os
import re
import crypt
import subprocess
import tempfile
import time
import random
import bcrypt
import string

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
        self.lastErrorMessage = None

#-------- General Functions
    
    def ReportError(self, msg):
        self.lastErrorMessage = str(msg) + "\n"
        
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
    
    def GenerateRandomPassword(self, length=8):
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for x in range(8))
        
    def GenerateHashedPassword(self, password):
        return bcrypt.hashpw(password, bcrypt.gensalt())
    
    def CheckPlainTextPassword(self, password, hashed_password):
        return bcrypt.hashpw(password, hashed_password) == hashed_password
    
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
            (userid, hashed, type_id) = result
            if self.CheckPlainTextPassword(password, hashed):
                self.currentUser = User(result[0], username, result[2])
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
            self.ReportError("You need to be logged in to create a user")
            return False
        
        if userTypeId <= self.currentUser.getTypeId():
            self.ReportError("Cannot create a user with same or higher level privileges")
            return False
        
        cur = self.conn.cursor()
        cur.execute("INSERT into users (username, password, type_id) " +
                    "VALUES (%s, %s, %s) ", (username,
                                             self.GenerateHashedPassword(password),
                                             userTypeId))
        self.conn.commit()
        
        return True
    
    def ModifyUser(self, user_id, password=None, userTypeId=None):
        
        if not self.IsPostgresConnectionActive():
            self.ReportError("Unable to establish database connection.")
            return False
        
        if not self.currentUser:
            self.ReportError("You need to be logged in to modify a user.")
            return False
        
        if userTypeId <= self.currentUser.getTypeId():
            self.ReportError("Cannot change a user to have the same or higher level privileges as you.")
            return False
        
        cur = self.conn.cursor()
        query = "SELECT user_id FROM users WHERE if = %s"
        cur.execute(query, [user_id])
        
        result = cur.fetchone()

        if not result:
            self.ReportError("Unable to find user id: " + user_id)
            return False            
        
        if password is not None:
            if not password:
                self.ReportError("You must specify a non-blank password.")
                return False
            else:
                cur.execute("UPDATE users SET password = %s WHERE id = %s", 
                    (Passwordify(password), user_id))
        
        if userTypeId is not None:
            cur.execute("UPDATE users SET userTypeId = %s WHERE id = %s", 
                    (userTypeId,  user_id))
        
        self.conn.commit()
        return True
    
#    def DeleteUser(self, user_id):  ----- TODO: Add a function for deleting users
        
#-------- Genome List Management

    def CreateGenomeList(self, genome_list, name, description, owner_id, private):
        
        cur = self.conn.cursor()
        
        randid = random.randint(0,16**8)
        temp_table_name = "ids_%x" % (randid,)
        tree_ids = self.GenomeListTextCtrl.GetValue().split("\n")
        
        query = "INSERT INTO genome_lists (name, description, owner_id, private) VALUES (%s, %s, %s, %s) RETURNING id"
        cur.execute(query, (name, description, owner_id, private))
        (genome_list_id, ) = cur.fetchone()
        
        query = "INSERT INTO genome_list_contents (list_id, genome_id) VALUES (%s, %s)"
        cur.executemany(query, [(genome_list_id, x) for x in genome_list])
        
        self.conn.commit()
        
        return True
    
    def CheckListAgainstPostgres(self, queryList, table, column):

    
      def CheckGenomeList(self):
        
        conn = GetTopParent(self).conn
        cur = GetTopParent(self).cur
        
        # Remove empty rows
        insert_params = [(x,) for x in tree_ids if x]
    
        cur.execute("CREATE TEMP TABLE %s (genome_id text)" % (temp_table_name,) )
        cur.executemany("INSERT INTO %s (genome_id) VALUES (%%s)" % (temp_table_name,), insert_params)
        conn.commit()
        
        if self.DatabaseIDRadioButton.GetValue():
            source_id = self.sources[self.SourceDropDown.GetSelection()][0]
            query = "SELECT id FROM genomes WHERE genome_source_id = %%s AND id_at_source IN (SELECT genome_id from %s)" % (temp_table_name,)
            cur.execute(query, (source_id,))
            genome_ids = [x[0] for x in cur.fetchall()]
            
            query = "SELECT genome_id from %s EXCEPT SELECT id_at_source from genomes WHERE genome_source_id = %%s" % (temp_table_name,)
            cur.execute(query, (source_id,))
            missing_ids = [x[0] for x in cur.fetchall()]
            
        else:
            cur.execute("SELECT id FROM genomes WHERE tree_id IN (SELECT genome_id from %s)" % (temp_table_name,))
            genome_ids = [x[0] for x in cur.fetchall()]
            
            cur.execute("SELECT genome_id from %s EXCEPT SELECT tree_id from genomes" % (temp_table_name,))
            missing_ids = [x[0] for x in cur.fetchall()]
            
        if len(missing_ids) > 0:
            ErrorLog("Warning: The following entered IDs were not found in the " +
                     "database and have been excluded from the list:\n %s \n" % ("\n".join(missing_ids),))

        return genome_ids

#-------- Fasta File Management

    def ExportGenomicFasta(self, genome_id, destfile=None):
        
        cur = self.conn.cursor()
        
        cur.execute("SELECT genomic_fasta " +
                    "FROM genomes " +
                    "WHERE id = %s ", [genome_id])
        result = cur.fetchone()
        
        if result is None:
            return None
        (genomic_oid,) = result
        
        fasta_lobject = conn.lobject(genomic_oid, 'r')
        
        if destfile is None:
            destfile = tempfile.mkstemp()[1]
        
        fasta_lobject.export(destfile)
        
        return destfile
    
    def AddFastaGenome(self, fasta_file, name, desc, id_prefix, source_id, id_at_source=None):
        
        cur = self.conn.cursor()
        
        match = re.search('^[A-Z]$', id_prefix)
        if not match:
            self.ReportError("Tree ID prefixes must be in the range A-Z")
            return False
        
        try:
            fasta_fh = open(fasta_file, "rb")
        except:
            self.ReportError("Cannot open Fasta file: " + fasta_file)
            return False
        fasta_fh.close()
        
        if not self.currentUser:
            self.ReportError("You need to be logged in to add a FASTA file.")
            return False
        
        query = "SELECT tree_id FROM genomes WHERE tree_id like %s order by tree_id desc;"
        cur.execute(query, (id_prefix + '%',))
        last_id = None
        for (tree_id,) in cur:
            last_id = tree_id
            break
        if (last_id is None):
            new_id = id_prefix + "00000001"
        else:
            new_id = id_prefix + "%08.i" % (int(last_id[1:]) + 1)
        
        if id_at_source is None:
            id_at_source = new_id

        initial_xml_string = 'XMLPARSE (DOCUMENT \'<?xml version="1.0"?><data></data>\')'
        cur.execute("INSERT INTO genomes (tree_id, name, description, metadata, owner_id, genome_source_id, id_at_source) "
            + "VALUES (%s, %s, %s, " + initial_xml_string + ", %s, %s, %s) "
            + "RETURNING id" , (new_id, name, desc, UserId, source_id, id_at_source))
        
        row_id = cur.fetchone()[0]
        
        fasta_lobject = self.conn.lobject(0, 'w', 0, fasta_file)
        
        cur.execute("UPDATE genomes SET genomic_fasta = %s WHERE id = %s",
                    (fasta_lobject.oid, row_id))
        
        fasta_lobject.close()
        
        self.conn.commit()
    