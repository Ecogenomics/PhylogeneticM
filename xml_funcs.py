import xml.etree.ElementTree as et

def ReturnExtantOrCreateElement(root, child):
    """
    Returns a 2-tuple (nodeList, created) where nodeList is either a list of
    extant nodes or a single element list containing the newly created node
    and created is a bool which is True if the node was created.  
    """
    xml_path_as_array = child.split('/')
    parent = root
    for immediate_child in xml_path_as_array:
        extant = parent.findall(immediate_child)
        if len(extant) == 0:
            newNode = et.SubElement(parent, immediate_child)
            parent = newNode
            created = True
        else:
            parent = extant[0]
            created = False
    return ([parent], created)
    