import xml.etree.ElementTree as et

def ReturnExtantOrCreateElement(root, child):
    """
    Returns a 2-tuple (nodeList, created) where nodeList is either a list of
    extant nodes or a single element list containing the newly created node
    and created is a bool which is True if the node was created.  
    """
    extant = root.findall(child)
    if len(extant) == 0:
        newNode = et.SubElement(root, child)
        return ([newNode], True)
    else:
        return (extant, False)