import os
import sys
import psycopg2 as pg
import xml.etree.ElementTree as ET

def MakeTreeData(GenomeDatabase, list_of_genome_ids, directory, prefix=None, **kwargs):
    """
    TODO - This function is ugly, it needs to be cleaned up.
    """
    if not os.path.isdir(directory):
        GenomeDatabase.ReportError("Directory doesn't exist: " + directory)
        return None
    
    cur = GenomeDatabase.conn.cursor()
    
    
    cur.execute("SELECT count(markers.id) " +
                "FROM markers, databases " +
                "WHERE database_id = databases.id " +
                "AND databases.name = 'Phylosift'" +
                "AND markers.version = '2'")
    
    (total_marker_count,) = cur.fetchone()
    
    cur.execute("SELECT genome_id, count(marker_id) "+
                "FROM aligned_markers, databases, markers " +
                "WHERE marker_id = markers.id " +
                "AND database_id = databases.id " +
                "AND databases.name = 'Phylosift' " +
                "AND markers.version = '2'" +
                "GROUP BY genome_id")
    
    genome_gene_counts = dict(cur.fetchall())
    
    # For all of the markers, get the expected marker size.
    aligned_markers = dict()
    cur.execute("SELECT markers.id, database_specific_id, size " +
                "FROM markers, databases " +
                "WHERE database_id = databases.id " +
                "AND databases.name = 'Phylosift' " +
                "AND markers.version = '2'" +
                "ORDER by database_specific_id")
    
    chosen_markers = list()
    for marker_id, phylosift_id, size in cur:
        chosen_markers.append((marker_id, phylosift_id, size))
    for genome_id in list_of_genome_ids:
        cur.execute("SELECT tree_id, marker_id, sequence, name, XMLSERIALIZE(document metadata as text), username "+
                    "FROM aligned_markers, genomes, users " +
                    "WHERE genomes.id = genome_id " +
                    "AND users.id = owner_id "
                    "AND genome_id = %s " + 
                    "AND dna is false", (genome_id,))
        if (cur.rowcount == 0):
            sys.stderr.write("WARNING: Genome id %s has no markers in the database and will be missing from the output files.\n" % genome_id)
        for tree_id, marker_id, sequence, name, xmlstr, owner in cur:
            if genome_id not in aligned_markers:
                aligned_markers[genome_id] = dict()
                aligned_markers[genome_id]['markers']    = dict()
                aligned_markers[genome_id]['name']  = name
                aligned_markers[genome_id]['tree_id']  = tree_id
                aligned_markers[genome_id]['xmlstr']  = xmlstr
                aligned_markers[genome_id]['owner']  = owner
            aligned_markers[genome_id]['markers'][marker_id] = sequence
            #For all the fields, replace None type with "".
            aligned_markers[genome_id] = dict(map((lambda (k, v): (k, "") if v is None else (k, v)),
                                                aligned_markers[genome_id].items()))

    if prefix is None:
        prefix = "Phylosift_PMPROK"
    gg_fh = open(os.path.join(directory, prefix + ".greengenes"), 'wb')
    fasta_fh = open(os.path.join(directory, prefix + ".fasta"), 'wb')
    for genome_id in aligned_markers.keys():                    
        aligned_seq = '';
        for marker_id, phylosift_id, size in chosen_markers:
            if marker_id in aligned_markers[genome_id]['markers']:
                aligned_seq += aligned_markers[genome_id]['markers'][marker_id]
            else:
                aligned_seq += size * '-'            
        
        root = ET.fromstring(aligned_markers[genome_id]['xmlstr'])
        extant = root.findall('internal/greengenes/dereplicated/best_blast/greengenes_tax')
        gg_tax = ''
        if len(extant) != 0:
            gg_tax = extant[0].text
        
        extant = root.findall('internal/taxonomy')
        internal_tax = ''
        if len(extant) != 0:
            internal_tax = extant[0].text
            
        extant = root.findall('internal/core_list')
        core_list_status = ''
        if len(extant) != 0:
            core_list_status = extant[0].text
            
        fasta_outstr = ">%s\n%s\n" % (aligned_markers[genome_id]['tree_id'],
                                      aligned_seq)
        
        gg_list = ["BEGIN",
                   "db_name=%s" % aligned_markers[genome_id]['tree_id'],
                   "organism=%s" % aligned_markers[genome_id]['name'],
                   "prokMSA_id=%s" % aligned_markers[genome_id]['tree_id'],
                   "owner=%s" % aligned_markers[genome_id]['owner'],
                   "genome_tree_tax_string=%s" % internal_tax,
                   "greengenes_tax_string=%s" % gg_tax,
                   "core_list_status=%s" % core_list_status,
                   "remark=%iof%i" % (genome_gene_counts[genome_id], total_marker_count),
                   "warning=",
                   "aligned_seq=%s" % (aligned_seq),
                   "END"]
        
        gg_outstr = "\n".join(gg_list) + "\n\n";
        
        gg_fh.write(gg_outstr);
        fasta_fh.write(fasta_outstr)
    
    gg_fh.close()
    fasta_fh.close()
    
    return True