#!/usr/bin/env python
import wx
import sys
import os
import re
import crypt
import subprocess
import tempfile
import threading
import time
import random

import psycopg2 as pg

#--------------- Program globals

UserId = -1
Username = ''
    
def readfa(fp): # this is a generator function
    """https://github.com/lh3/"""
    last = None # this is a buffer keeping the last unprocessed line
    while True: # mimic closure; is it a bad idea?
        if not last: # the first record or a record following a fastq
            for l in fp: # search for the start of the next record
                if l[0] in '>@': # fasta/q header line
                    last = l[:-1] # save this line
                    break
        if not last: break
        name, seqs, last = last[1:].split()[0], [], None
        for l in fp: # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+': # this is a fasta record
            yield name, ''.join(seqs), None # yield a fasta record
            if not last: break
        else: # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp: # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq): # have read enough quality
                    last = None
                    yield name, seq, ''.join(seqs); # yield a fastq record
                    break
            if last: # reach EOF before reading enough quality
                yield name, seq, None # yield a fasta record instead
                break


def GetTopParent(wxObject):
    parent = wxObject.GetParent()
    while True:
        if parent.GetParent() is None:
            return parent
        parent = parent.GetParent()


class GenomeTreerManageUsers(wx.Frame):        
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):

        size = (600, 600) # Default size
        
        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        
        panel = wx.Panel(self)
        
        self.conn = GetTopParent(self).conn
        self.cur = GetTopParent(self).cur
        conn = self.conn
        cur = self.cur

#--------------- Users List

        UserListSizer = wx.BoxSizer(wx.VERTICAL)

        cur.execute("SELECT users.id, users.username " +
                    "FROM users " +
                    "WHERE users.type_id > (" +
                        "SELECT type_id " +
                        "FROM users " +
                        "WHERE id = %s) " +
                    "OR id = %s", (UserId, UserId))
        
        self.visibleUsers = cur.fetchall()
        
        self.visibleUsernameList = [x[1] for x in self.visibleUsers]
        
        self.UsersListStaticText = wx.StaticText(panel, -1, "Users List")
        self.UsersList = wx.ListBox(panel, -1, choices=self.visibleUsernameList)
        
        UserListSizer.Add(self.UsersListStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        UserListSizer.Add(self.UsersList, 1, wx.EXPAND|wx.ALL, 5)
        
#--------------- Add User Section

#--------------------------- Add User - Static Text Title

        self.AddUserTitleStaticText = wx.StaticText(panel, -1, "Add User")

#--------------------------- Add User - Username Text Ctrl

        self.AddUsernameStaticText = wx.StaticText(panel, -1, "Username:")
        self.AddUsernameTextCtrl =  wx.TextCtrl(panel, -1)
        
        AddUsernameSizer = wx.BoxSizer(wx.HORIZONTAL)
        AddUsernameSizer.Add(self.AddUsernameStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        AddUsernameSizer.Add(self.AddUsernameTextCtrl, 1, wx.ALL, 5)
        
#--------------------------- Add User - Password Text Ctrl

        self.AddPasswordStaticText =   wx.StaticText(panel, -1, "Password:")
        self.AddPasswordTextCtrl =  wx.TextCtrl(panel, -1, style=wx.PASSWORD)
        
        AddPasswordSizer = wx.BoxSizer(wx.HORIZONTAL)
        AddPasswordSizer.Add(self.AddPasswordStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        AddPasswordSizer.Add(self.AddPasswordTextCtrl, 1, wx.ALL, 5)
        
#--------------------------- Add User - Password Confirmation Text Ctrl

        self.AddConfirmPasswordStaticText = wx.StaticText(panel, -1, "Confirm Password:")
        self.AddConfirmPasswordTextCtrl = wx.TextCtrl(panel, -1, style=wx.PASSWORD)
        
        AddConfirmPasswordSizer = wx.BoxSizer(wx.HORIZONTAL)
        AddConfirmPasswordSizer.Add(self.AddConfirmPasswordStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        AddConfirmPasswordSizer.Add(self.AddConfirmPasswordTextCtrl, 1, wx.ALL, 5)

#--------------------------- Add User - User Type Selection

        cur.execute("SELECT id, name " +
                    "FROM user_types " +
                    "WHERE id > (" +
                        "SELECT type_id " +
                        "FROM users " +
                        "WHERE id = %s)", (UserId,))
               
        self.userTypesList = cur.fetchall()
        
        self.userTypeNameList = [x[1] for x in self.userTypesList]

        self.AddUserTypeStaticText = wx.StaticText(panel, -1, "User Type:")
        self.AddUserTypeList = wx.Choice(panel, -1, choices = self.userTypeNameList)
        
        AddUserTypeSizer = wx.BoxSizer(wx.HORIZONTAL)
        AddUserTypeSizer.Add(self.AddUserTypeStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        AddUserTypeSizer.Add(self.AddUserTypeList, 1, wx.ALL, 5)

#--------------------------- Add User - Add User Button

        self.AddUserButtonId = wx.NewId()
        self.AddUserButton = wx.Button(panel, self.AddUserButtonId, "Add User")
        self.Bind(wx.EVT_BUTTON, self.AddUserEvent, id = self.AddUserButtonId)
        if len(self.userTypesList) == 0:
            self.AddUserButton.Disable()

#--------------------------- Add User - Section Sizer

        AddUserSizer = wx.BoxSizer(wx.VERTICAL)
        AddUserSizer.Add(self.AddUserTitleStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        AddUserSizer.Add(AddUsernameSizer, 0, wx.EXPAND|wx.ALL, 0)
        AddUserSizer.Add(AddPasswordSizer, 0, wx.EXPAND|wx.ALL, 0)
        AddUserSizer.Add(AddConfirmPasswordSizer, 1, wx.EXPAND|wx.ALL, 0)
        AddUserSizer.Add(AddUserTypeSizer, 1, wx.EXPAND|wx.ALL, 0)
        
#--------------- Modify User Section

#--------------------------- Modify User - Static Text Title

        self.ModifyUserTitleStaticText = wx.StaticText(panel, -1, "Modify User")

#--------------------------- Modify User - Username Text Ctrl

        self.ModifyUsernameStaticText = wx.StaticText(panel, -1, "Username:")
        self.ModifyUsernameTextCtrl =  wx.StaticText(panel, -1, "")
        
        ModifyUsernameSizer = wx.BoxSizer(wx.HORIZONTAL)
        ModifyUsernameSizer.Add(self.ModifyUsernameStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        ModifyUsernameSizer.Add(self.ModifyUsernameTextCtrl, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        
#--------------------------- Modify User - Password Text Ctrl

        self.ModifyPasswordStaticText =   wx.StaticText(panel, -1, "Password:")
        self.ModifyPasswordTextCtrl =  wx.TextCtrl(panel, -1, style=wx.PASSWORD)
        
        ModifyPasswordSizer = wx.BoxSizer(wx.HORIZONTAL)
        ModifyPasswordSizer.Add(self.ModifyPasswordStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        ModifyPasswordSizer.Add(self.ModifyPasswordTextCtrl, 1, wx.ALL, 5)
        
#--------------------------- Modify User - Password Confirmation Text Ctrl

        self.ModifyConfirmPasswordStaticText = wx.StaticText(panel, -1, "Confirm Password:")
        self.ModifyConfirmPasswordTextCtrl = wx.TextCtrl(panel, -1, style=wx.PASSWORD)
        
        ModifyConfirmPasswordSizer = wx.BoxSizer(wx.HORIZONTAL)
        ModifyConfirmPasswordSizer.Add(self.ModifyConfirmPasswordStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        ModifyConfirmPasswordSizer.Add(self.ModifyConfirmPasswordTextCtrl, 1, wx.ALL, 5)

#--------------------------- Modify User - User Type Selection

        cur.execute("SELECT id, name " +
                    "FROM user_types " +
                    "WHERE id > (" +
                        "SELECT type_id " +
                        "FROM users " +
                        "WHERE id = %s)", (UserId,))
        
        self.userTypesList = cur.fetchall()
        self.userTypeNameList = [x[1] for x in self.userTypesList]

        self.ModifyUserTypeStaticText = wx.StaticText(panel, -1, "User Type:")
        self.ModifyUserTypeList = wx.Choice(panel, -1, choices = self.userTypeNameList)
        
        ModifyUserTypeSizer = wx.BoxSizer(wx.HORIZONTAL)
        ModifyUserTypeSizer.Add(self.ModifyUserTypeStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        ModifyUserTypeSizer.Add(self.ModifyUserTypeList, 1, wx.ALL, 5)
        
        self.ModifyUserButton = wx.Button(panel, -1, "Save")
        
#--------------------------- Add User - Section Sizer

        ModifyUserSizer = wx.BoxSizer(wx.VERTICAL)
        ModifyUserSizer.Add(self.ModifyUserTitleStaticText, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        ModifyUserSizer.Add(ModifyUsernameSizer, 0, wx.EXPAND|wx.ALL, 0)
        ModifyUserSizer.Add(ModifyPasswordSizer, 0, wx.EXPAND|wx.ALL, 0)
        ModifyUserSizer.Add(ModifyConfirmPasswordSizer, 1, wx.EXPAND|wx.ALL, 0)
        ModifyUserSizer.Add(ModifyUserTypeSizer, 1, wx.EXPAND|wx.ALL, 0)
        
        
#--------------- User Details Sizer
        
        UserDetailsSizer = wx.BoxSizer(wx.VERTICAL)
        UserDetailsSizer.Add(AddUserSizer, 1, wx.EXPAND|wx.ALL, 5)
        UserDetailsSizer.Add(self.AddUserButton, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        UserDetailsSizer.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        UserDetailsSizer.Add(ModifyUserSizer, 1, wx.EXPAND|wx.ALL, 5)
        UserDetailsSizer.Add(self.ModifyUserButton, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        
#--------------- Main Sizer (Layout)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        sizer.Add(UserListSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel, -1, style=wx.LI_VERTICAL), 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(UserDetailsSizer, 1, wx.ALL, 5)
        panel.SetSizer(sizer)
        panel.Layout()

#--------------- Events

    def AddUserEvent(self, event):
        
        if self.AddPasswordTextCtrl.GetValue() != self.AddConfirmPasswordTextCtrl.GetValue():
            ErrorLog("Passwords don't match!")
        else:
            self.CreateUser(self.AddUsernameTextCtrl.GetValue(),
                            self.AddPasswordTextCtrl.GetValue(),
                            self.userTypesList[self.AddUserTypeList.GetSelection()][0])
            

class GenomeTreerGenomeLists(wx.Frame):        
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):

        size = (600, 600) # Default size
        
        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        
        panel = wx.Panel(self)
        
        CreateListSizer = self.CreateGenomeListLayoutInit(panel)
        EditListSizer = wx.BoxSizer(wx.VERTICAL)
        
#--------------- Main Sizer (Layout)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(CreateListSizer, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel, -1, style=wx.LI_VERTICAL), 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(EditListSizer, 1, wx.EXPAND|wx.ALL, 5)
        panel.SetSizer(sizer)
        panel.Layout()

    def CreateGenomeListLayoutInit(self, panel):
            
#--------------- Add Genome List Button
    
        self.AddGenomeListButtonId = wx.NewId()
        self.AddGenomeListButton = wx.Button(panel, self.AddGenomeListButtonId, "Create Genome List")
        
        self.Bind(wx.EVT_BUTTON, self.CreateGenomeList, id=self.AddGenomeListButtonId)
    
#--------------- Import List From File

        #self.FilePickerText = wx.StaticText(panel, -1, "File to import:")
        #self.FilePicker = wx.FilePickerCtrl(panel, -1, style=wx.FLP_DEFAULT_STYLE)
        
        #FilePickerSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        #FilePickerSizer.Add(self.FilePickerText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        #FilePickerSizer.Add(self.FilePicker, 1, wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Description Text Control

        self.GenomeListStaticText = wx.StaticText(panel, -1, "Genome List:")
        self.GenomeListTextCtrl = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE)
        
        GenomeListSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        GenomeListSizer.Add(self.GenomeListStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        GenomeListSizer.Add(self.GenomeListTextCtrl, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Import Selection Type

        self.TreeIDRadioButton = wx.RadioButton(panel, -1, "ACE Genome Tree IDs")
        self.DatabaseIDRadioButton = wx.RadioButton(panel, -1, "Database Specific IDs")
        
        conn = GetTopParent(self).conn
        cur = GetTopParent(self).cur
        
        query = "SELECT id, name FROM genome_sources"
        cur.execute(query)
        self.sources = cur.fetchall()
        
        sources_name = [x[1] for x in self.sources]
        
        self.SourceText = wx.StaticText(panel, -1, "Database (Genome Source):")
        self.SourceDropDown = wx.Choice(panel, -1, choices=sources_name)
        

#--------------- Sizer (Layout)

        sizer = wx.BoxSizer(wx.VERTICAL)
        #sizer.Add(FilePickerSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, "Create A Genome List"), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(GenomeListSizer, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.TreeIDRadioButton, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.DatabaseIDRadioButton, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.SourceText, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.SourceDropDown, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.AddGenomeListButton, 0, wx.EXPAND|wx.ALL, 5)

        return sizer

    def CreateGenomeList(self, event):
        genome_ids = self.CheckGenomeList()
        if len(genome_ids) == 0:
            ErrorLog("No suitable IDs found to create list.\n")
            return
        addFastaDiag = GenomeTreerCreateGenomeListsDialog(self, -1,  "Create genome list (FASTA)...")
        addFastaDiag.StoreGenomeList(genome_ids)
        addFastaDiag.ShowModal()
    
    def CheckGenomeList(self):
        
        conn = GetTopParent(self).conn
        cur = GetTopParent(self).cur
        
        randid = random.randint(0,16**8)
        temp_table_name = "ids_%x" % (randid,)
        tree_ids = self.GenomeListTextCtrl.GetValue().split("\n")
        
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

   
class GenomeTreerCreateGenomeListsDialog(wx.Dialog):        
    def __init__(self, parent, id = -1, title = None, pos = None, size = None, style = None, name = None):
        
        wx.Dialog.__init__(self, parent, id, title, pos, size)
        
        self.genome_list = None
        
        panel = wx.Panel(self)

#--------------- Name Text Control
               
        self.NameStaticText = wx.StaticText(panel, -1, "Name:")
        self.NameTextCtrl = wx.TextCtrl(panel, -1)
        
        NameSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        NameSizer.Add(self.NameStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        NameSizer.Add(self.NameTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER, 0)
        
#--------------- Description Text Control
        
        self.DescriptionStaticText = wx.StaticText(panel, -1, "Description:")
        self.DescriptionTextCtrl = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE)
        
        DescriptionSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        DescriptionSizer.Add(self.DescriptionStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        DescriptionSizer.Add(self.DescriptionTextCtrl, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Privacy Check Control

        self.PrivacyStaticText = wx.StaticText(panel, -1, "Private:")
        self.PrivacyCheckBox = wx.CheckBox(panel, -1)
        
        PrivacySizer = wx.BoxSizer(wx.HORIZONTAL)
        
        PrivacySizer.Add(self.PrivacyStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        PrivacySizer.Add(self.PrivacyCheckBox, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Add Genome Button
        
        self.AddListButtonId = wx.NewId()
        self.AddListButton = wx.Button(panel, self.AddListButtonId, "Create List")
        
        self.Bind(wx.EVT_BUTTON, self.CreateGenomeListEvt, id=self.AddListButtonId)
        
#--------------- Main Sizer (Layout)
                
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(NameSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(DescriptionSizer, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(PrivacySizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.AddListButton, 0, wx.ALL|wx.ALIGN_CENTER, 5)
        panel.SetSizer(sizer)
        panel.Layout()
        
#--------------- Add Genome Event Handler

    def CreateGenomeListEvt(self, event):
        self.CreateGenomeList(self.genome_list,
                                          self.NameTextCtrl.GetValue(), 
                                          self.DescriptionTextCtrl.GetValue(),
                                          UserId,
                                          self.PrivacyCheckBox.GetValue())
        self.EndModal(0)
    
    
    def StoreGenomeList(self, genome_list):
        self.genome_list = genome_list

   
class GenomeTreerAddGenomeDialog(wx.Dialog):
    def __init__(self, parent, id = -1, title = None, pos = None, size = None, style = None, name = None):
        
        wx.Dialog.__init__(self, parent, id, title, pos, size)
        
        panel = wx.Panel(self)
        
#--------------- Name Text Control

        self.NameStaticText = wx.StaticText(panel, -1, "Name:")
        self.NameTextCtrl = wx.TextCtrl(panel, -1)
        
        NameSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        NameSizer.Add(self.NameStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        NameSizer.Add(self.NameTextCtrl, 1, wx.ALL|wx.ALIGN_CENTER, 0)
        
#--------------- Description Text Control

        self.DescriptionStaticText = wx.StaticText(panel, -1, "Description:")
        self.DescriptionTextCtrl = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE)
        
        DescriptionSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        DescriptionSizer.Add(self.DescriptionStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        DescriptionSizer.Add(self.DescriptionTextCtrl, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Select Source
        
        conn = GetTopParent(self).conn
        cur = GetTopParent(self).cur
        
        query = "SELECT id, name FROM genome_sources"
        cur.execute(query)
        self.sources = cur.fetchall()
        
        sources_name = [x[1] for x in self.sources]
        
        self.SourceText = wx.StaticText(panel, -1, "Genome Source:")
        self.SourceDropDown = wx.Choice(panel, -1, choices=sources_name)
        
        SourceSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        SourceSizer.Add(self.SourceText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        SourceSizer.Add(self.SourceDropDown, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)
        
        self.SourceIDText = wx.StaticText(panel, -1, "ID (at source):")
        self.SourceIDTextCtrl = wx.TextCtrl(panel, -1)
        
        SourceIDSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        SourceIDSizer.Add(self.SourceIDText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        SourceIDSizer.Add(self.SourceIDTextCtrl, 1,  wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)
                
        
#--------------- Select FASTA file
        
        self.FilePickerText = wx.StaticText(panel, -1, "FASTA file:")
        self.FilePicker = wx.FilePickerCtrl(panel, -1, style=wx.FLP_DEFAULT_STYLE)
        
        FilePickerSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        FilePickerSizer.Add(self.FilePickerText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        FilePickerSizer.Add(self.FilePicker, 1, wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 0)

#--------------- Add Genome Button
        
        self.AddGenomesButtonId = wx.NewId()
        self.AddGenomesButton = wx.Button(panel, self.AddGenomesButtonId, "Add Genome")
        
        self.Bind(wx.EVT_BUTTON, self.AddFastaGenome, id=self.AddGenomesButtonId)
        
#--------------- Main Sizer (Layout)
                
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(FilePickerSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(NameSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(DescriptionSizer, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(SourceSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(SourceIDSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.AddGenomesButton, 0, wx.ALL|wx.ALIGN_CENTER, 5)
        panel.SetSizer(sizer)
        panel.Layout()
        
#--------------- Add Genome Event Handler

    def AddFastaGenome(self, event):
        self.GetParent().AddFastaGenome(self.FilePicker.GetPath(),
                                        self.NameTextCtrl.GetValue(), 
                                        self.DescriptionTextCtrl.GetValue(),
                                        "C", 
                                        self.sources[self.SourceDropDown.GetSelection()][0],
                                        "",
                                        True)
        
        self.EndModal(0)


class GenomeTreerLoginMenuBar(wx.MenuBar):
    def __init__(self):
        wx.MenuBar.__init__(self)

        fileMenu = wx.Menu()

        fileMenu.Append(wx.ID_EXIT, "E&xit", "Exit GenomeTreer")
        
        self.Append(fileMenu, "F&ile")


class GenomeTreerMenuBar(wx.MenuBar):
    def __init__(self):
        wx.MenuBar.__init__(self)

        fileMenu = wx.Menu()

        fileMenu.Append(wx.ID_EXIT, "E&xit", "Exit GenomeTreer")
        
        self.manageUsersId = wx.NewId()
        fileMenu.Append(self.manageUsersId, "Manage Users", "Manage Database Users")

        # bind the menu event to an event handler
        #self.Bind(wx.EVT_MENU, self.OnTimeToClose, id=wx.ID_EXIT)

        # and put the menu on the menubar
        self.Append(fileMenu, "F&ile")
        
        genomesMenu = wx.Menu()
        
        self.Append(genomesMenu, "G&enomes")
        
#--------------- Add Genomes Sub Menu

        addGenomesSubMenu = wx.Menu()
        
        self.ncbiAddId = wx.NewId()
        addGenomesSubMenu.Append(self.ncbiAddId, "From NCBI...", "Add a new genome by specifying an Genbank Identifier (GI) or NCBI accession")
        
        self.imgAddId = wx.NewId()
        addGenomesSubMenu.Append(self.ncbiAddId, "From IMG...", "Add a new genome by specifying an IMG taxon id")
        
        self.fastaAddId = wx.NewId()
        addGenomesSubMenu.Append(self.fastaAddId, "From Fasta...", "Add a new genome providing a genomic FASTA file")
        
        genomesMenu.AppendSubMenu(addGenomesSubMenu, "Add", "Add a genome to the database")
        
        self.GenomeListsId = wx.NewId()
        genomesMenu.Append(self.GenomeListsId, "Genome Lists...", "Create a list of genomes...")
        
        markersMenu = wx.Menu()
        
        self.Append(markersMenu, "M&arkers")
        
        self.Calc16SId = wx.NewId()
        markersMenu.Append(self.Calc16SId, "Calculate 16S...", "Locate 16S markers...")


class GenomeTreerForm(wx.Frame):
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        
        panel = wx.Panel(self)
        
        self.CreateStatusBar()
        
        self.GenomeListsFrame = None
        self.UserManagementFrame = None
        
#--------------- Menu Bar

        self.DefaultMenuBar = GenomeTreerMenuBar()
        
        self.PreLoginMenuBar = GenomeTreerLoginMenuBar()
        
        self.SetMenuBar(self.PreLoginMenuBar)
        
        self.Bind(wx.EVT_MENU, self.ShowAddFastaGenome, id=self.DefaultMenuBar.fastaAddId)
        self.Bind(wx.EVT_MENU, self.ShowGenomeLists, id=self.DefaultMenuBar.GenomeListsId)
        #self.Bind(wx.EVT_MENU, self.Calc16S, id=self.DefaultMenuBar.Calc16SId)
        #self.Bind(wx.EVT_MENU, self.Exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.ShowUserManagement, id=self.DefaultMenuBar.manageUsersId)
        
        
#--------------- Login Text Control

        self.LoggedInUserText = wx.StaticText(panel, -1, "Logged out")

        self.UsernameStaticText = wx.StaticText(panel, -1, "Username:")
        self.UsernameTextCtrl = wx.TextCtrl(panel, -1, size=(200,-1))
        
        UsernameSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        UsernameSizer.Add(self.UsernameStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        UsernameSizer.Add(self.UsernameTextCtrl, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        
        self.PasswordStaticText = wx.StaticText(panel, -1, "Password:")
        self.PasswordTextCtrl = wx.TextCtrl(panel, -1, size=(200,-1), style=wx.TE_PASSWORD)
        
        PasswordSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        PasswordSizer.Add(self.PasswordStaticText, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        PasswordSizer.Add(self.PasswordTextCtrl, 0, wx.ALL|wx.ALIGN_CENTER, 0)
        
#--------------- Add Genome Button
        
        self.LoginButtonId = wx.NewId()
        self.LoginButton = wx.Button(panel, self.LoginButtonId, "Login")
        
        self.Bind(wx.EVT_BUTTON, self.UserLogin, id=self.LoginButtonId)
        
        #self.MassButtonId = wx.NewId()
        #self.MassButton = wx.Button(panel, self.MassButtonId, "Mass add")
        
        #self.Bind(wx.EVT_BUTTON, self.MassAddGenomes, id=self.MassButtonId)
        
#--------------- Main Sizer (Layout)
                
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(self.LoggedInUserText, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        sizer.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(UsernameSizer, 0, wx.ALL|wx.ALIGN_CENTER, 5)
        sizer.Add(PasswordSizer, 0, wx.ALL|wx.ALIGN_CENTER, 5)
        sizer.Add(self.LoginButton, 0, wx.ALL|wx.ALIGN_CENTER, 5)

        panel.SetSizer(sizer)
        panel.Layout()
        
        self.panel = panel
        
#--------------- Other init

        self.MakePostgresConnection()

#--------------- Events

    def UserLogin(self, event):
        global UserId
        global Username
        query = "SELECT id, password FROM users WHERE username = %s"
        self.cur.execute(query, [self.UsernameTextCtrl.GetValue()])
        result = self.cur.fetchone()
        if result:
            if result[1] == Passwordify(self.PasswordTextCtrl.GetValue()):
                UserId = result[0]
                Username = self.UsernameTextCtrl.GetValue()
                self.LoggedInUserText.SetLabel("Logged in as: " + Username)
                self.HideLoginCtrls()
                self.panel.Layout()
                self.SetMenuBar(self.DefaultMenuBar)
            else:
                sys.stderr.write("Incorrect password\n")
                sys.stderr.flush()
        else:
            sys.stderr.write("User not found\n")
            sys.stderr.flush()

    def ShowUserManagement(self, event):
        if not self.UserManagementFrame:
            self.UserManagementFrame = GenomeTreerManageUsers(self, -1, "User Management")
        self.UserManagementFrame.Show(True)

    def ShowGenomeLists(self, event):
        if not self.GenomeListsFrame:
            self.GenomeListsFrame = GenomeTreerGenomeLists(self, -1, "Genome Lists", size=(100,100))
        self.GenomeListsFrame.Show(True)

    def ShowAddFastaGenome(self, event):
        addFastaDiag = GenomeTreerAddGenomeDialog(self, -1,  "Add genome (FASTA)...")
        addFastaDiag.ShowModal()
        
    def Calc16S(self, event):
        cur = self.cur
        cur.execute("SELECT id from genomes")
        genome_ids = []
        for (genome_id,) in cur:
            self.Calculate16SForGenome(genome_id)

            
        
#--------------- Functions

    def MakePostgresConnection(self):
        self.conn = pg.connect("dbname=genome_tree host=/tmp/")
        self.cur = self.conn.cursor()
        
    def ClosePostgresConnection(self):
        self.cur.close()
        self.conn.close()
        
    def HideLoginCtrls(self):
        self.UsernameStaticText.Hide()
        self.UsernameTextCtrl.Hide()
        self.PasswordStaticText.Hide()
        self.PasswordTextCtrl.Hide()
        self.LoginButton.Hide()
    
    def Calculate16SForGenome(self, genome_id, overwrite=False):
        conn = self.conn
        cur = self.cur
        #Get 16S marker id
        cur.execute("SELECT markers.id " +
                    "FROM markers, databases " +
                    "WHERE databases.id = markers.database_id " +
                    "AND databases.name = 'Internal' " +
                    "AND markers.database_specific_id = '16S'")
        (marker_id, ) = cur.fetchone()       
        if not overwrite:
            cur.execute("SELECT count(marker_id) " +
                        "FROM aligned_markers " +
                        "WHERE genome_id = %s " +
                        "AND marker_id = %s", (genome_id, marker_id))
            (count, ) = cur.fetchone()
            if count > 0:
                sys.stderr.write(temp_dir)
                sys.stderr.flush()
                return False
        fasta_file = self.ExportGenomicFasta(genome_id)
        if not fasta_file:
            return False
        
        temp_dir = tempfile.mkdtemp()
        subprocess.call(["ssu-align", "-f", "--dna",
                                    fasta_file, temp_dir])
        os.unlink(fasta_file)
        
        for root,dirs,files in os.walk(temp_dir):
            for filename in files:
                if filename[-3:] == '.fa':
                    fp = open(filename, 'rb')
                    for (name, seq, qual) in readfq(fp):
                        cur.execute("INSERT INTO aligned_markers")
                    fp.close()
                    
    
    #def MassAddGenomes(self, event):
    #    sys.stderr.write("Eventing!\n");
    #    sys.stderr.flush()
    #    path = "/home/uqaskars/genomes/"
    #    for root, dirs, files in os.walk(path):
    #        for name in sorted(files):
    #            if name[-4:] == '.fna':
    #                prefix = name[:-4]
    #                self.AddFastaGenome(os.path.join(root, name), prefix, None, "A", 2, prefix)

class GenomeTreerLauncher:

    def MakeAppFrame(self):
        return GenomeTreerForm(None, -1, "Genome Trees", size=(640, 480),
                             style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)

    def Main(self):
        app = wx.PySimpleApp()
        win = self.MakeAppFrame()
        win.Show(True)
        app.MainLoop()


##-------------- Main program

if __name__ == '__main__':

    launcher = GenomeTreerLauncher()
    
    launcher.Main()

