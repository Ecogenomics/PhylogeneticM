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


def ErrorLog(msg):
    sys.stderr.write(str(msg))
    sys.stderr.flush()

def GetTopParent(wxObject):
    parent = wxObject.GetParent()
    while True:
        if parent.GetParent() is None:
            return parent
        parent = parent.GetParent()

class GenomeTreerGenomeLists(wx.Frame):        
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        
        panel = wx.Panel(self)

        panel.Layout()

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
        
#--------------- Menu Bar

        self.DefaultMenuBar = GenomeTreerMenuBar()
        
        self.PreLoginMenuBar = GenomeTreerLoginMenuBar()
        
        self.SetMenuBar(self.PreLoginMenuBar)
        
        self.Bind(wx.EVT_MENU, self.ShowAddFastaGenome, id=self.DefaultMenuBar.fastaAddId)
        self.Bind(wx.EVT_MENU, self.ShowGenomeLists, id=self.DefaultMenuBar.GenomeListsId)
        self.Bind(wx.EVT_MENU, self.Calc16S, id=self.DefaultMenuBar.Calc16SId)
        
        
#--------------- Login Text Control

        self.LoggedInUserText = wx.StaticText(panel, -1, "Logged out")
        self.UserDivider = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)

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
        sizer.Add(self.UserDivider, 0, wx.EXPAND|wx.ALL, 5)
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
            if result[1] == crypt.crypt(self.PasswordTextCtrl.GetValue(), "GT"):
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
    
    def ShowGenomeLists(self, event):
        if self.GenomeListsFrame is None:
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
        self.conn.close()
        self.cur.close()
        
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
                
    
    def ExportGenomicFasta(self, genome_id):
        conn = self.conn
        cur = self.cur
        cur.execute("SELECT genomic_fasta " +
                    "FROM genomes " +
                    "WHERE id = %s ", [genome_id])
        result = cur.fetchone()
        if result is None:
            return None
        (genomic_oid,) = result
        
        fasta_lobject = conn.lobject(genomic_oid, 'r')
        
        fastafile = tempfile.mkstemp()
        
        fasta_lobject.export(fastafile[1])
        
        return fastafile[1]
        
    def AddFastaGenome(self, fasta_file, name, desc, id_prefix, source_id, id_at_source, replace_id_at_source=False):
        conn = self.conn
        cur = self.cur
        
        match = re.search('^[A-Z]$', id_prefix)
        if not match:
            raise Exception()
        
        try:
            fasta_fh = open(fasta_file, "rb")
        except:
            raise Exception("Cannot open " + fasta_file)
        fasta_fh.close()
        
        global UserId
        if UserId <= 0:
            raise Exception("UserId:" + str(UserId))
        
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
        
        if replace_id_at_source:
            id_at_source = new_id
                
        cur.execute("INSERT INTO genomes (tree_id, name, description, owner_id, genome_source_id, id_at_source) "
            + "VALUES (%s, %s, %s, %s, %s, %s) "
            + "RETURNING id" , (new_id, name, desc, UserId, source_id, id_at_source))
        
        row_id = cur.fetchone()[0]
        
        fasta_lobject = conn.lobject(0, 'w', 0, fasta_file)
        
        cur.execute("UPDATE genomes SET genomic_fasta = %s WHERE id = %s",
                    (fasta_lobject.oid, row_id))
        
        fasta_lobject.close()
        
        conn.commit()
            
        
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

