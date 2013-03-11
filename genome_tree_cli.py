#!/usr/bin/env python
import argparse
import sys
import genome_tree_backend as backend
import getpass
import random
import os

import profiles

def ErrorReport(msg):
    sys.stderr.write(msg)
    sys.stderr.flush()

def NewPasswordPrompt(GenomeDatabase):
    autogenerated = False
    password = getpass.getpass("Enter new password (leave blank to auto-generate):")
    if password == '':
        password = GenomeDatabase.GenerateRandomPassword()
        autogenerated = True
    if not autogenerated and (password != getpass.getpass("Confirm password:")) :
        ErrorReport("Passwords don't match.\n")
        return None
    return (password, autogenerated)

def CreateUser(GenomeDatabase, args):
    password_tuple = NewPasswordPrompt(GenomeDatabase)
    if password_tuple is not None:
        (password, autogenerated) = password_tuple
    else:
        return False
    user_type_id = GenomeDatabase.GetUserTypeIdFromUserTypeName(args.type)
    if user_type_id is not None:
        if not GenomeDatabase.CreateUser(args.username, password, user_type_id):
            print GenomeDatabase.lastErrorMessage
            return False
    else:
        ErrorReport("User type should be either admin or user.\n")
        return False
    if autogenerated:
        print "Temporary password: " + password + "\n"
    print "User Created!\n"
    return True
        
def ModifyUser(GenomeDatabase, args):
    
    user_id = GenomeDatabase.GetUserIdFromUsername(args.username)
    
    password = None
    if args.password:
        password_tuple = NewPasswordPrompt(GenomeDatabase)
        if password_tuple is not None:
            (password, autogenerated) = password_tuple
        else:
            return False
        
    if GenomeDatabase.ModifyUser(user_id, password, args.type):
        if args.password and autogenerated:
            print "New temporary password: " + password + "\n"
        print "User Modified!"
        return True
    else:
        print GenomeDatabase.lastErrorMessage
        return False
        
def ShowUser(GenomeDatabase, args):
    pass
    
def DeleteUser(GenomeDatabase, args):
    pass

def AddFastaGenome(GenomeDatabase, args):
    if (args.id_at_source is None) != (args.source is None):
        ErrorReport("You need to specify either none or both of --id_at_source and --source.\n")
        return False
    if (args.id_at_source is not None):
        if GenomeDatabase.currentUser.getTypeId() > 1:
            ErrorReport("Only administrators can add externally referenced genomes.\n")
            return False
        source_id = GenomeDatabase.GetGenomeSourceIdFromName(args.source)
        if source_id is None:
            ErrorReport("Unable to find source: %s\n" %(args.source,))
            return False
        genome_id = GenomeDatabase.AddFastaGenome(args.filename, args.name, args.description, 'A',
                                                  source_id, args.id_at_source)
    else:
        genome_id = GenomeDatabase.AddFastaGenome(args.filename, args.name, args.description, 'C')
    if genome_id is not None:
        (tree_id, name, description, owner_id) = GenomeDatabase.GetGenomeInfo(genome_id)
        print "Added %s as %s\n" % (name, tree_id)
    else:
        ErrorReport(GenomeDatabase.lastErrorMessage)
    if args.genome_list_id is not None:
        genome_id = GenomeDatabase.GetGenomeId(tree_id)
        if GenomeDatabase.ModifyGenomeList(args.genome_list_id, operation='add',
                genome_ids=[genome_id]):
            print "Added %s (%s) to genome list %s" % (name, tree_id, args.genome_list_id)
        else:
            ErrorReport("Unable to add genome "+name+ "("+tree_id+") to list "+args.genome_list_id)

def AddManyFastaGenomes(GenomeDatabase, args):
    fh = open(args.batchfile, "rb")
    added_ids = []
    errors = 0
    for line in fh:
        splitline = line.split("\t")
        if len(splitline) >= 5:
            if GenomeDatabase.currentUser.getTypeId() > 1:
                ErrorReport("Only administrators can add externally referenced genomes.\n")
                ErrorReport("Offending genome: %s\n" % (splitline[0].rstrip(),))
                errors = 1
                break
            database_source_id = GenomeDatabase.GetGenomeSourceIdFromName(splitline[3].rstrip())
            if database_source_id is None:
                print "Unable to find database %s for genome %s" % (splitline[3].rstrip(), splitline[0].rstrip())
                errors = 1
                break
            genome_id = GenomeDatabase.AddFastaGenome(splitline[0].rstrip(), splitline[1].rstrip(), splitline[2].rstrip(), "A",
                                                      database_source_id, splitline[4].rstrip())
            if genome_id is not None:
                added_ids.append(genome_id)
            else:
                ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
                errors = 1
                break
        else:
            genome_id = GenomeDatabase.AddFastaGenome(splitline[0].rstrip(), splitline[1].rstrip(), splitline[2].rstrip(), "C")
            if genome_id is not None:
                added_ids.append(genome_id)
            else:
                ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
                errors = 1
                break
    if errors:
        for genome_id in added_ids:
            GenomeDatabase.DeleteGenome(genome_id)
        ErrorReport("Errors in mass addition, not completed. See previous error messages for details.\n")
        return None
    if args.genome_list_name is not None:
        list_id = GenomeDatabase.CreateGenomeList(added_ids, args.genome_list_name, "",
                                                  GenomeDatabase.currentUser.getUserId(), True)
        print "Added all genomes under list id: %s\n" % (list_id,)
        print "You can modify the list particulars using the ModifyGenomeList command.\n"
    elif args.genome_list_id is not None:
        #genome_ids_list = [GenomeDatabase.GetGenomeId(x) for x in added_ids
        #                   if GenomeDatabase.GetGenomeId(x) is not None]
        if GenomeDatabase.ModifyGenomeList(args.genome_list_id,
                operation='add', genome_ids=added_ids):
            print "Added %d genomes to genome list %s" % (len(added_ids),
                    args.genome_list_id)
        else:
            ErrorReport("Filed to modify genome list" + args.genome_list_id)
    else:
        for genome_id in added_ids:
            (tree_id, name, description, owner_id) = GenomeDatabase.GetGenomeInfo(genome_id)
            print "Added %s as %s\n" % (name, tree_id)

def ExportFasta(GenomeDatabase, args):
    tree_ids = []
    if args.tree_id is not None:
        tree_ids.extend(args.tree_id)
    if args.batchfile is not None:
        with open(args.batchfile) as fp:
            for line in fp:
                tree_ids.append(line.rstrip())
    if args.output_fasta is not None:
        outfp = open(args.output_fasta, 'w')

    try:
        for tid in tree_ids:
            genome_id = GenomeDatabase.GetGenomeId(tid)
            if not genome_id:
                ErrorReport("Genome not found.\t" + str(tid))
            else:
                genome = GenomeDatabase.ExportGenomicFasta(genome_id)
                if args.output_fasta is not None:
                    outfp.write(genome)
                    outfp.write('\n')
                elif args.batchfile is not None and args.prefix is not None:
                    outfp = open(os.path.join(args.prefix, tid + '.fasta'), 'w')
                    outfp.write(genome)
                    outfp.close()
                else:
                    print genome
    finally:
        if args.output_fasta is not None:
            outfp.close()


def DeleteGenome(GenomeDatabase, args):
    tree_ids = args.tree_ids.split(',')
    for tree_id in tree_ids:
        genome_id = GenomeDatabase.GetGenomeId(tree_id)
        if genome_id is not None:
            if GenomeDatabase.DeleteGenome(genome_id) is None:
                ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
            else:
                ErrorReport(tree_id + " sucessfully deleted.\n")
                

def SearchGenomes(GenomeDatabase, args):
    user_id = None
    if args.owner is None:
        user_id = GenomeDatabase.currentUser.getUserId()
    elif args.owner != '-1':
        user_id = GenomeDatabase.GetUserIdFromUsername(args.owner)
        if user_id is None:
            ErrorReport(GenomeDatabase.lastErrorMessage)
            return None
    return_array = GenomeDatabase.SearchGenomes(args.tree_id, args.name, args.description,
                                                args.list_id, user_id)
    
    if not return_array:
        return None

    format_str = "%12.12s %50.50s %15.15s %25.25s %50.50s"
    print format_str % ("Tree ID","Name","Owner","Added","Description")
    for (tree_id, name, username, date_added, description) in return_array:
        print format_str % (tree_id, name, username, date_added, description)

def ShowGenome(GenomeDatabase, args):
    pass
        
def ShowGenomeSources(GenomeDatabase, args):
    print "Current genome sources:"
    for (source_id, name) in GenomeDatabase.GetGenomeSources():
        print "    " + name
        
def CreateGenomeList(GenomeDatabase, args):
    genome_source = None
    if args.source:
        genome_source = GenomeDatabase.GetGenomeSourceIdFromName(args.source)
        if genome_source is None:
            print GenomeDatabase.lastErrorMessage()
            return False
    genome_list = list()
    
    fh = open(args.filename, 'rb')
    for line in fh:
        line = line.rstrip()
        genome_id = GenomeDatabase.GetGenomeId(line, genome_source)
        if genome_id:
            genome_list.append(genome_id)
        else:
            ErrorReport("Unable to find genome: %s, ignoring\n" % (line,))
    fh.close()
    
    GenomeDatabase.CreateGenomeList(genome_list, args.name, args.description,
                                    GenomeDatabase.currentUser.getUserId(),
                                    not args.public)
    
def ModifyGenomeList(GenomeDatabase, args):
    
    tree_ids_list = []
    
    if args.tree_ids:
        tree_ids_list = args.tree_ids.split(",")
        
    genome_ids_list = [GenomeDatabase.GetGenomeId(x) for x in tree_ids_list
                       if GenomeDatabase.GetGenomeId(x) is not None]
    
    ret_val = GenomeDatabase.ModifyGenomeList(args.list_id, args.name, args.description,
                                              genome_ids_list, args.operation, not(args.public))
    
    if not(ret_val):
        ErrorReport(GenomeDatabase.lastErrorMessage)
    
    
def CloneGenomeList(GenomeDatabase, args):
    genome_source = None
    if args.source:
        genome_source = GenomeDatabase.GetGenomeSourceIdFromName(args.source)
        if genome_source is None:
            ErrorReport(GenomeDatabase.lastErrorMessage)
            return False
    genome_list = list()
    
    fh = open(args.filename, 'rb')
    for line in fh:
        line = line.rstrip()
        genome_id = GenomeDatabase.GetGenomeId(line, genome_source)
        if genome_id:
            genome_list.append(genome_id)
        else:
            ErrorReport("Unable to find genome: %s, ignoring\n" % (line,))
    fh.close()
    
    GenomeDatabase.CreateGenomeList(genome_list, args.name, args.description,
                                    GenomeDatabase.currentUser.getUserId(),
                                    not args.public)

def DeleteGenomeList(GenomeDatabase, args):
    if not args.force:
        if GenomeDatabase.DeleteGenomeList(args.list_id, args.force):
            if raw_input("Are you sure you want to delete this list? ")[0].upper() != 'Y':
                return False
    GenomeDatabase.DeleteGenomeList(args.list_id, True)

def CreateTreeData(GenomeDatabase, args):    
    list_ids = []
    if args.list_ids:
        list_ids = args.list_ids.split(",")
    genome_id_set = set()
    if args.tree_ids:
        extra_ids = [GenomeDatabase.GetGenomeId(x) for x in args.tree_ids.split(",")]
        genome_id_set = genome_id_set.union(set(extra_ids))
    for list_id in list_ids:
        temp_genome_list = GenomeDatabase.GetGenomeIdListFromGenomeListId(list_id)
        if temp_genome_list:
            genome_id_set = genome_id_set.union(set(temp_genome_list))
    core_lists = []
    if args.core_lists:
        if args.core_lists == 'both':
            core_lists = ['public', 'private']
        else:
            core_lists = [args.core_lists]
    profile_config_dict = dict()
    if args.profile_args:
        profile_args = args.profile_args.split(',')
        for profile_arg in profile_args:
            key_value_pair = profile_arg.split('=')
            try:
                profile_config_dict[key_value_pair[0]] = key_value_pair[1]
            except IndexError:
                profile_config_dict[key_value_pair[0]] = None
    
    if (len(genome_id_set) > 0) or (len(core_lists) != 0):
        GenomeDatabase.MakeTreeData(args.marker_set_id, core_lists, list(genome_id_set), args.profile, args.out_dir, config_dict=profile_config_dict)

def ShowAllGenomeLists(GenomeDatabase, args):
    if args.self_owned:
        genome_lists = GenomeDatabase.GetVisibleGenomeLists(GenomeDatabase.currentUser.getUserId())
    else:
        genome_lists = GenomeDatabase.GetVisibleGenomeLists()
    
    print "ID\tName\tOwner\tDesc\n"
    for (list_id, name, description, user) in genome_lists:
        print "\t".join((str(list_id), name, user, description)),"\n"

def ShowAllMarkerSets(GenomeDatabase, args):
    marker_sets = GenomeDatabase.GetVisibleMarkerSets()
    
    print "ID\tName\tOwner\tDesc\n"
    for (list_id, name, description, user) in marker_sets:
        print "\t".join((str(list_id), name, user, description)),"\n"

def RecalculateMarkers(GenomeDatabase, args):
    tree_ids = list()
    if args.listfile:
        fh = open(args.listfile, 'rb')
        for line in fh:
            tree_ids.append(line.rstrip())   
        fh.close()
    elif args.tree_ids:
        tree_ids = args.tree_ids.split(",")
    else:
        ErrorReport("Need to specify one of --tree_ids or --filename.\n")
        return False
    for tree_id in tree_ids:
        genome_id = GenomeDatabase.GetGenomeId(tree_id)
        GenomeDatabase.RecalculateMarkersForGenome(genome_id)

def RecalculateAllMarkers(GenomeDatabase, args):
    if not GenomeDatabase.RecalculateAllMarkers():
        ErrorReport(GenomeDatabase.lastErrorMessage + "\n")

def AddCustomMetadata(GenomeDatabase, args):
    data_dict = dict()
    fh = open(args.metadata_file,'rb')
    for line in fh:
        splitline = line.strip().split('\t')
        data_dict[splitline[0]] = splitline[1]
    if not GenomeDatabase.UpdateTaxonomies(args.xml_path, data_dict):
        ErrorReport(GenomeDatabase.lastErrorMessage() + "\n")

def UpdateTaxonomies(GenomeDatabase, args):
    tax_dict = dict()
    fh = open(args.taxonomy_file,'rb')
    for line in fh:
        splitline = line.strip().split('\t')
        tax_dict[splitline[0]] = splitline[1]
    if not GenomeDatabase.UpdateTaxonomies(tax_dict):
        ErrorReport(GenomeDatabase.lastErrorMessage() + "\n")

def ModifyCoreLists(GenomeDatabase, args):
    genome_ids = list()
    for tree_id in args.tree_ids.split(","):
        genome_id = GenomeDatabase.GetGenomeId(tree_id)
        if not genome_id:
            ErrorReport("Unable to find genome id for" + tree_id + "\n" + GenomeDatabase.lastErrorMessage + "\n")
            return False
        else:
            genome_ids.append(genome_id)
    if not GenomeDatabase.ModifyCoreList(genome_ids, args.operation):
        ErrorReport(GenomeDatabase.lastErrorMessage + "\n")

def AddMarkers(GenomeDatabase, args):
    database_id = GenomeDatabase.GetMarkerDatabaseIDFromName(args.dbname)
    if database_id is None:
        ErrorReport("Database %s not known\n" % (args.dbname,))
        return False
    added_marker_ids = GenomeDatabase.AddMarkers(args.file, database_id, args.use_existing)
    if not added_marker_ids:
        ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
        return False
    if args.marker_set_name:
        if GenomeDatabase.CreateMarkerSet(added_marker_ids, args.marker_set_name, "", GenomeDatabase.currentUser.getUserId(), False):
            return True
        else:
            ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
            return False
    if args.marker_set_id:
        if GenomeDatabase.ModifyMarkerSet(args.marker_set_id, None, None, added_marker_ids, 'add'):
            return True
        else:
            ErrorReport(GenomeDatabase.lastErrorMessage + "\n")
            return False
    
def DeleteMarkers(GenomeDatabase, args):
    for marker_id in args.marker_ids.split(','):
        GenomeDatabase.DeleteMarker(marker_id)
        
def ShowAllMarkerSets(GenomeDatabase, args):
    pass
    
    
if __name__ == '__main__':
    
    # create the top-level parser
    parser = argparse.ArgumentParser(prog='genome_tree_cli.py')
    parser.add_argument('-u', dest='login_username',
                        help='Username to log into the database', default=getpass.getuser()),
    parser.add_argument('-p', dest='password_filename',
                        help='A File containing password for the user'),
    parser.add_argument('--dev', dest='dev', action='store_true',
                        help='Connect to the developer database')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Run in debug mode')
    
    subparsers = parser.add_subparsers(help='Sub-Command Help', dest='subparser_name')
    
# -- User management subparsers

# -------- Create users
    
    parser_createuser = subparsers.add_parser('CreateUser',
                                              help='Create user help')
    parser_createuser.add_argument('--user', dest = 'username',
                                   required=True, help='Username of the created user')
    parser_createuser.add_argument('--type', dest = 'type',
                                   required=True, help='User type')
    parser_createuser.set_defaults(func=CreateUser)
    
# -------- Modify users
    
    parser_modifyuser = subparsers.add_parser('ModifyUser', help='Modify user help')
    parser_modifyuser.add_argument('--user', dest = 'username',
                                   required=True, help='Username of the user')
    parser_modifyuser.add_argument('--type', dest = 'type', help='User type')
    parser_modifyuser.add_argument('--password', dest = 'password',
                                   action = 'store_true', help='User type')
    parser_modifyuser.set_defaults(func=ModifyUser)
    
# -------- Show users
    
    parser_showuser = subparsers.add_parser('ShowUser', help='Show user help')
    parser_showuser.add_argument('--user', dest = 'username',
                                required=True, help='Username of the user')
    parser_showuser.set_defaults(func=ShowUser)
    
# -------- Delete users
    
    parser_deleteuser = subparsers.add_parser('DeleteUser', help='Delete user help')
    parser_deleteuser.add_argument('--user', dest = 'username',
                                   required=True, help='Username of the user to delete')
    parser_deleteuser.add_argument('--force', dest = 'force', action='store_true',
                                   help='Do not prompt for confirmation')
    parser_deleteuser.set_defaults(func=DeleteUser)
       
# -------- Genome management subparsers
    
    parser_addfastagenome = subparsers.add_parser('AddFastaGenome',
                                    help='Add a genome to the tree from a Fasta file')
    parser_addfastagenome.add_argument('--file', dest = 'filename',
                                       required=True, help='FASTA file to add')
    parser_addfastagenome.add_argument('--name', dest = 'name',
                                       required=True, help='Name of the genome')
    parser_addfastagenome.add_argument('--description', dest = 'description',
                                       required=True, help='Brief description of the genome')
    parser_addfastagenome.add_argument('--source', dest = 'source',
                                       help='The source of this genome (see ShowGenomeSources)')
    parser_addfastagenome.add_argument('--modify_list', dest = 'genome_list_id',
                                       help='Modify a genome list with the \
                                       specified id by adding the current \
                                       genome to it')
    parser_addfastagenome.add_argument('--id_at_source', dest = 'id_at_source',
                                       help='The id of this genome at the specified source')
    parser_addfastagenome.set_defaults(func=AddFastaGenome)
    
    
    parser_addmanyfastagenomes = subparsers.add_parser('AddManyFastaGenomes',
                                    help='Add a genome to the tree from a Fasta file')
    parser_addmanyfastagenomes.add_argument('--batchfile', dest = 'batchfile',
                                    required=True, help='Add genomes en masse with a batch file (one genome per line, tab separated in 3 columns (filename,name,desc))')
    mutex_group = parser_addmanyfastagenomes.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('--modify_list', dest = 'genome_list_id',
                                    help='Modify a genome list with the \
                                    specified id and add all batchfile genomes into it.')
    mutex_group.add_argument('--create_list', dest = 'genome_list_name',
                                    help='Create a genome list with the specified name and add all batchfile genomes into it.')
    parser_addmanyfastagenomes.set_defaults(func=AddManyFastaGenomes)
    
# --------- Export FASTA Genome
    
    parser_exportfasta = subparsers.add_parser('ExportFasta',
                                    help='Export a genome to a FASTA file')
    parser_exportfasta.add_argument('--tree_id', dest = 'tree_id', action='append',
                                    help='Tree ID to export. This option can be '
                                    'specified multiple times')
    parser_exportfasta.add_argument('--outdir', dest = 'prefix', default='.',
                                    help='output directory to use when exporting genomes with a batch file')
    parser_exportfasta.add_argument('--output', dest = 'output_fasta',
                                    help='Output the genome to a FASTA file')
    parser_exportfasta.add_argument('--batchfile', dest='batchfile', 
                                    help='A file containing tree ids to extract')
    parser_exportfasta.set_defaults(func=ExportFasta)

    
# --------- Delete FASTA Genome

    parser_deletegenome = subparsers.add_parser('DeleteGenome',
                                    help='Delete a genome from the database')
    parser_deletegenome.add_argument('--tree_ids', dest = 'tree_ids',
                                    required=True, help='List of Tree IDs (comma separated)')
    parser_deletegenome.set_defaults(func=DeleteGenome)

# --------- Genome Searching

    parser_searchgenome = subparsers.add_parser('SearchGenomes',
                                    help='Add a genome to the tree from a Fasta file')
    parser_searchgenome.add_argument('--name', dest = 'name',
                                       help='Search for genomes containing this name')
    parser_searchgenome.add_argument('--description', dest = 'description',
                                       help='Search for genomes containing this description')
    parser_searchgenome.add_argument('--tree_id', dest = 'tree_id',
                                       help='Show genome with this tree_id')
    parser_searchgenome.add_argument('--list_id', dest = 'list_id',
                                       help='Show all genomes in this list')
    parser_searchgenome.add_argument('--owner', dest = 'owner', nargs='?', default='-1',
                                       help='Search for genomes owned by this username. ' +
                                      'With no parameter finds genomes owned by the current user')
    parser_searchgenome.set_defaults(func=SearchGenomes) 
    
# --------- Show Genome Sources
    
    parser_showgenomesources = subparsers.add_parser('ShowGenomeSources',
                                help='Show the sources of the genomes')
    parser_showgenomesources.set_defaults(func=ShowGenomeSources)
    
# --------- Create A Genome List

    parser_creategenomelist = subparsers.add_parser('CreateGenomeList',
                                        help='Create a genome list from a list of accessions')
    parser_creategenomelist.add_argument('--file', dest = 'filename',
                                       required=True, help='File containing list of accessions')
    parser_creategenomelist.add_argument('--source', dest = 'source',
                                       help='Source of the accessions listed in the file')
    parser_creategenomelist.add_argument('--name', dest = 'name',
                                       required=True, help='Name of the genome list')
    parser_creategenomelist.add_argument('--description', dest = 'description',
                                       required=True, help='Brief description of the genome list')
    parser_creategenomelist.add_argument('--public', dest = 'public', default=False,
                                       action='store_true', help='Make the list visible to all users.')
    parser_creategenomelist.set_defaults(func=CreateGenomeList)
    
# --------- Modify A Genome List

    parser_modifygenomelist = subparsers.add_parser('ModifyGenomeList',
                                        help='Modify a genome list')
    parser_modifygenomelist.add_argument('--list_id', dest = 'list_id',
                                        required=True, help='File containing list of accessions')
    parser_modifygenomelist.add_argument('--tree_ids', dest = 'tree_ids',
                                        help='List of tree_ids to add/remove from list')
    parser_modifygenomelist.add_argument('--operation', dest = 'operation', choices=('add','remove'),
                                        help='What to do with the tree_ids with regards to the genome list.')
    parser_modifygenomelist.add_argument('--description', dest = 'description',
                                        help='Change the brief description of the genome list to this.')
    parser_modifygenomelist.add_argument('--name', dest = 'name',
                                        help='Modify the name of the list to this.')   
    parser_modifygenomelist.add_argument('--public', dest = 'public', type=bool,
                                        help='Change whether the list is private or public.')
    parser_modifygenomelist.set_defaults(func=ModifyGenomeList)

# --------- Clone A Genome List

    parser_clonegenomelist = subparsers.add_parser('CloneGenomeList',
                                        help='Create a genome list from a list of accessions')
    parser_clonegenomelist.add_argument('--list_id', dest = 'list_id', type=int,
                                       required=True, help='File containing list of accessions')
    parser_clonegenomelist.add_argument('--name', dest = 'name',
                                       required=True, help='Name of the genome list')
    parser_clonegenomelist.add_argument('--description', dest = 'description',
                                       required=True, help='Brief description of the genome list')
    parser_clonegenomelist.add_argument('--public', dest = 'public', default=False,
                                       action='store_true', help='Make the list visible to all users.')
    parser_clonegenomelist.set_defaults(func=CloneGenomeList)


# --------- Delete A Genome List

    parser_deletegenomelist = subparsers.add_parser('DeleteGenomeList',
                                        help='Create a genome list from a list of accessions')
    parser_deletegenomelist.add_argument('--list_id', dest = 'list_id', type=int,
                                       required=True, help='ID of the genome list to delete')
    parser_deletegenomelist.add_argument('--force', dest = 'force', action='store_true',
                                        help='Do not prompt for confirmation of deletion')
    parser_deletegenomelist.set_defaults(func=DeleteGenomeList)

# -------- Show All Genome Lists

    parser_showallgenomelists = subparsers.add_parser('ShowAllGenomeLists',
                                        help='Create a genome list from a list of accessions')
    parser_showallgenomelists.add_argument('--owned', dest = 'self_owned',  default=False,
                                        action='store_true', help='Only show genome lists owned by you.')
    parser_showallgenomelists.set_defaults(func=ShowAllGenomeLists)

# -------- Generate Tree Data
    
    parser_createtreedata = subparsers.add_parser('CreateTreeData',
                                        help='Generate data to create genome tree')
    parser_createtreedata.add_argument('--core_lists', dest = 'core_lists', choices=('private', 'public', 'both'),
                                        help='Include the genomes from one or all of the ACE core genome lists in the output files.')
    parser_createtreedata.add_argument('--list_ids', dest = 'list_ids',
                                        help='Create genome tree data from these lists (comma separated).')
    parser_createtreedata.add_argument('--set_id', dest = 'marker_set_id',
                                        required=True, help='Use this marker set for the genome tree.')
    parser_createtreedata.add_argument('--tree_ids', dest = 'tree_ids',
                                        help='Add these tree_ids to the output, useful for including outgroups (comma separated).')
    parser_createtreedata.add_argument('--output', dest = 'out_dir',
                                        required=True, help='Directory to output the files')
    parser_createtreedata.add_argument('--profile', dest = 'profile',
                                        help='Marker profile to use (default: %s)' % (profiles.ReturnDefaultProfileName(),))
    parser_createtreedata.add_argument('--profile_args', dest = 'profile_args',
                                        help='Arguments to provide to the profile')
    parser_createtreedata.set_defaults(func=CreateTreeData)
     
# -------- Marker management subparsers

    parser_recalculatemarkers = subparsers.add_parser('RecalculateMarkers',
                                help='Recalculate markers')
    parser_recalculatemarkers.add_argument('--tree_ids', dest = 'tree_ids',
                                         help='List of Tree IDs (comma separated)')
    parser_recalculatemarkers.add_argument('--filename', dest = 'listfile',
                                         help='File containing list of Tree IDs (newline separated)')
    parser_recalculatemarkers.set_defaults(func=RecalculateMarkers)
    
    parser_recalculateallmarkers = subparsers.add_parser('RecalculateAllMarkers',
                                help='Recalculate all the markers')

    parser_recalculateallmarkers.set_defaults(func=RecalculateAllMarkers)

#--------- Metadata managements

    parser_addcustommetadata = subparsers.add_parser('AddCustomMetadata',
                                  help='Add custom metadata to the database')
    parser_addcustommetadata.add_argument('--xml_path', dest = 'xml_path',
                                        required=True, help='XML path of metadata to be added (e.g "data/custom/metadatafield)')
    parser_addcustommetadata.add_argument('--metadata_file', dest = 'metadata_file',
                                        required=True, help='File (tab separated) containing tree ids and data to be added at specified XML path')
    parser_addcustommetadata.set_defaults(func=AddCustomMetadata)
    
    
    parser_updatetaxonomies = subparsers.add_parser('UpdateTaxonomies',
                                        help='Update the internal taxonomies')
    parser_updatetaxonomies.add_argument('--taxonomy_file', dest = 'taxonomy_file',
                                        required=True, help='File containing tree ids and taxonomies (tab separated)')
    parser_updatetaxonomies.set_defaults(func=UpdateTaxonomies)

#--------- Metadata managements - ModifyCoreLists

    parser_modifycorelist = subparsers.add_parser('ModifyCoreLists',
                                help='Add/remove genomes the private/public core list.')
    parser_modifycorelist.add_argument('--tree_ids', dest = 'tree_ids',
                                         required=True,  help='List of Tree IDs (comma separated)')
    parser_modifycorelist.add_argument('--operation', dest = 'operation', choices=('private','public','remove'),
                                         required=True,  help='Operation to perform')
    parser_modifycorelist.set_defaults(func=ModifyCoreLists)

#--------- Marker Management

    parser_addmarkers = subparsers.add_parser('AddMarkers', 
                                 help='Add in one or many marker HMMs into the database')
    parser_addmarkers.add_argument('--database_name', dest='dbname', required=True, 
                                help='Name of the database that the markers belong to')
    parser_addmarkers.add_argument('--file', dest='file', required=True,
                                help='File containing the HMM model(s) for the marker(s)')
    parser_addmarkers.add_argument('--use_existing', dest='use_existing', action='store_true', default=False,
                                help='If copies of this marker already exist in the database, use the copy in the database. These markers will still be added to the specified marker set (if specified)')
    mutex_group = parser_addmarkers.add_mutually_exclusive_group(required=False)
    mutex_group.add_argument('--modify_set', dest = 'marker_set_id',
                                    help='Modify a marker set with the \
                                    specified id and add all markers to it.')
    mutex_group.add_argument('--create_set', dest = 'marker_set_name',
                                    help='Create a marker set with the specified name and add these markers to it.')
    parser_addmarkers.set_defaults(func=AddMarkers)
    
    parser_showallmarkerdatabases = subparsers.add_parser('ShowAllMarkerDatabases',
                                                          help='Shows all the possible databases markers can com from')
    parser_showallmarkerdatabases.set_defaults(func=ModifyCoreLists)

#--------- Marker Management

    parser_deletemarkers = subparsers.add_parser('DeleteMarkers',
                                    help='Delete markers from the database')
    parser_deletemarkers.add_argument('--marker_ids', dest = 'marker_ids',
                                    required=True, help='List of Marker IDs (comma separated)')
    parser_deletemarkers.set_defaults(func=DeleteMarkers)

# -------- Show All Genome Lists

    parser_showallmarkersets = subparsers.add_parser('ShowAllMarkerSets',
                                        help='Shows the details of a Marker Set')
    parser_showallmarkersets.set_defaults(func=ShowAllMarkerSets)

    args = parser.parse_args()
    
    # Initialise the backend
    GenomeDatabase = backend.GenomeDatabase()
    if args.dev:
        GenomeDatabase.MakePostgresConnection(10000)
    else:
        GenomeDatabase.MakePostgresConnection()
        
    if args.debug:
        GenomeDatabase.SetDebugMode(True)
    # Login
    
    if args.password_filename:
        fh = open(args.password_filename, 'rb')
        password = fh.readline().rstrip()
        fh.close()
    else:
        password = getpass.getpass("Enter your password (%s):" % (args.login_username,)) 
    
    User = GenomeDatabase.UserLogin(args.login_username, password)    
    
    if not User:
        ErrorReport("Database login failed. The following error was reported:\n" +
                    "\t" + GenomeDatabase.lastErrorMessage)
        sys.exit(-1)

    args.func(GenomeDatabase, args)


