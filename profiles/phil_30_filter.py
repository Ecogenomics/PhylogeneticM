import os
import sys
import psycopg2 as pg
import xml.etree.ElementTree as ET

def MakeTreeData(GenomeDatabase, marker_set_id, list_of_genome_ids, directory, prefix=None, **kwargs):
    """
    TODO - This function is ugly, it needs to be cleaned up.
    """
    if not os.path.isdir(directory):
        GenomeDatabase.ReportError("Directory doesn't exist: " + directory)
        return None
    
    cur = GenomeDatabase.conn.cursor()
      
    cur.execute("SELECT count(*) " +
                "FROM marker_set_contents  " +
                "WHERE set_id = %s", (marker_set_id,))
    
    (total_marker_count,) = cur.fetchone()
    
    cur.execute("SELECT genome_id, count(aligned_markers.marker_id) "+
                "FROM aligned_markers, marker_set_contents " +
                "WHERE set_id = %s " +
                "AND aligned_markers.marker_id =  marker_set_contents.marker_id " +
                "GROUP BY genome_id", (marker_set_id,))
    
    genome_gene_counts = dict(cur.fetchall())
    
    cur.execute("SELECT genome_id, count(aligned_markers.marker_id) "+
                "FROM aligned_markers, marker_set_contents " +
                "WHERE set_id = 1 " +
                "AND aligned_markers.marker_id =  marker_set_contents.marker_id " +
                "GROUP BY genome_id")
    
    phylosift_gene_counts = dict(cur.fetchall())
    
    chosen_markers = list()
    
    # For all of the markers, get the expected marker size.
    cur.execute("SELECT markers.id, size " +
                "FROM markers, marker_set_contents " +
                "WHERE set_id = %s " +
                "AND marker_id = markers.id "
                "ORDER by markers.id", (marker_set_id,))
    
    for marker_id, size in cur:
        chosen_markers.append((marker_id, size))
    
    aligned_markers = dict()
    
    for genome_id in list_of_genome_ids:
        cur.execute("SELECT tree_id, name, XMLSERIALIZE(document metadata as text), username "+
                    "FROM genomes, users "+
                    "WHERE users.id = owner_id "+
                    "AND genomes.id = %s", (genome_id,))
        result = cur.fetchone()
        if not result:
            continue
        (tree_id, name, xmlstr, owner) = result
        # Check if complete.
        if phylosift_gene_counts[genome_id] < 20:
            sys.stderr.write("WARNING: Genome %s has < 30 markers (%i) in the database and will be missing from the output files.\n" % (tree_id, phylosift_gene_counts[genome_id]))
            continue
        cur.execute("SELECT aligned_markers.marker_id, sequence "
                    "FROM aligned_markers, marker_set_contents "+
                    "WHERE marker_set_contents.marker_id = aligned_markers.marker_id " +
                    "AND genome_id = %s " +
                    "AND set_id = %s ", (genome_id, marker_set_id))
        if (cur.rowcount == 0):
            sys.stderr.write("WARNING: Genome %s has no markers in the database and will be missing from the output files.\n" % tree_id)
        for marker_id, sequence in cur:
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
        prefix = "genome_tree_data"
    gg_fh = open(os.path.join(directory, prefix + ".greengenes"), 'wb')
    fasta_fh = open(os.path.join(directory, prefix + ".fasta"), 'wb')
    for genome_id in aligned_markers.keys():                    
        aligned_seq = '';
        for marker_id, size in chosen_markers:
            if aligned_markers[genome_id]['markers'][marker_id]:
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
            
        # Bacteria only
        if internal_tax[:len('d__Bacteria')] != 'd__Bacteria':
            continue
        
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