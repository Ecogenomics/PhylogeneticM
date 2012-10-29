import os
import psycopg2 as pg

def MakeTreeData(GenomeDatabase, list_of_genome_ids, directory, prefix=None, **kwargs):
    """
    TODO - This function is ugly, it needs to be cleaned up.
    """
    if not os.path.isdir(directory):
        GenomeDatabase.ReportError("Directory doesn't exist: " + directory)
        return None
    
    cur = GenomeDatabase.conn.cursor()
    
    # For all of the markers, get the expected marker size.
    aligned_markers = dict()
    cur.execute("SELECT markers.id, database_specific_id, size " +
                "FROM markers, databases " +
                "WHERE database_id = databases.id " +
                "AND databases.name = 'Phylosift'"
                "ORDER by database_specific_id")
    
    chosen_markers = list()
    for marker_id, phylosift_id, size in cur:
        chosen_markers.append((marker_id, phylosift_id, size))

    cur.execute("SELECT tree_id, genome_id, marker_id, sequence, name "+
                "FROM aligned_markers, genomes " +
                "WHERE genomes.id = genome_id " +
                "AND dna is false")
    
    for tree_id, genome_id, marker_id, sequence, name in cur:
        if (genome_id in list_of_genome_ids):
            if genome_id not in aligned_markers:
                aligned_markers[genome_id] = dict()
                aligned_markers[genome_id]['markers']    = dict()
                aligned_markers[genome_id]['name']  = name
                aligned_markers[genome_id]['tree_id']  = tree_id
            aligned_markers[genome_id]['markers'][marker_id] = sequence
            #For all the fields, replace None type with "".
            aligned_markers[genome_id] = dict(map((lambda (k, v): (k, "") if v is None else (k, v)),
                                                aligned_markers[genome_id].items()))

    if prefix is None:
        prefix = "Phylosift_PMPROK_Individual"
    gg_fh = open(os.path.join(directory, prefix + ".greengenes"), 'wb')
    
    for marker_id, phylosift_id, size in chosen_markers:
        fasta_fh = open(os.path.join(directory, prefix + "_" + phylosift_id + ".fasta"), 'wb')
        for genome_id in aligned_markers.keys():
            if marker_id in aligned_markers[genome_id]['markers']:
                fasta_outstr = ">%s\n%s\n" % (aligned_markers[genome_id]['tree_id'],
                                              aligned_markers[genome_id]['markers'][marker_id])
                fasta_fh.write(fasta_outstr)
        fasta_fh.close()
        
    for genome_id in aligned_markers.keys():  
        gg_list = ["BEGIN",
                   "db_name=%s" % aligned_markers[genome_id]['tree_id'],
                   "organism=%s" % aligned_markers[genome_id]['name'],
                   "prokMSA_id=%s" % (aligned_markers[genome_id]['tree_id']),
                   "warning=",
                   "aligned_seq=",
                   "END"]   
        gg_outstr = "\n".join(gg_list) + "\n\n";
        gg_fh.write(gg_outstr);
    
    gg_fh.close()
    fasta_fh.close()
    
    return True