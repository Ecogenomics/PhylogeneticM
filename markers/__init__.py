class Marker(object):
    def __init__(self, name, version, database, rel_path):
        self.name = name
        self.version = version
        self.database = database
        self.rel_path = rel_path

phylosift_v2_markers = [Marker("PMPROK00003","2","Phylosift","phylosift/v2/PMPROK00003.hmm"),
                        Marker("PMPROK00014","2","Phylosift","phylosift/v2/PMPROK00014.hmm"),
                        Marker("PMPROK00015","2","Phylosift","phylosift/v2/PMPROK00015.hmm"),
                        Marker("PMPROK00019","2","Phylosift","phylosift/v2/PMPROK00019.hmm"),
                        Marker("PMPROK00020","2","Phylosift","phylosift/v2/PMPROK00020.hmm"),
                        Marker("PMPROK00022","2","Phylosift","phylosift/v2/PMPROK00022.hmm"),
                        Marker("PMPROK00024","2","Phylosift","phylosift/v2/PMPROK00024.hmm"),
                        Marker("PMPROK00025","2","Phylosift","phylosift/v2/PMPROK00025.hmm"),
                        Marker("PMPROK00028","2","Phylosift","phylosift/v2/PMPROK00028.hmm"),
                        Marker("PMPROK00029","2","Phylosift","phylosift/v2/PMPROK00029.hmm"),
                        Marker("PMPROK00031","2","Phylosift","phylosift/v2/PMPROK00031.hmm"),
                        Marker("PMPROK00034","2","Phylosift","phylosift/v2/PMPROK00034.hmm"),
                        Marker("PMPROK00041","2","Phylosift","phylosift/v2/PMPROK00041.hmm"),
                        Marker("PMPROK00047","2","Phylosift","phylosift/v2/PMPROK00047.hmm"),
                        Marker("PMPROK00048","2","Phylosift","phylosift/v2/PMPROK00048.hmm"),
                        Marker("PMPROK00050","2","Phylosift","phylosift/v2/PMPROK00050.hmm"),
                        Marker("PMPROK00051","2","Phylosift","phylosift/v2/PMPROK00051.hmm"),
                        Marker("PMPROK00052","2","Phylosift","phylosift/v2/PMPROK00052.hmm"),
                        Marker("PMPROK00053","2","Phylosift","phylosift/v2/PMPROK00053.hmm"),
                        Marker("PMPROK00054","2","Phylosift","phylosift/v2/PMPROK00054.hmm"),
                        Marker("PMPROK00060","2","Phylosift","phylosift/v2/PMPROK00060.hmm"),
                        Marker("PMPROK00064","2","Phylosift","phylosift/v2/PMPROK00064.hmm"),
                        Marker("PMPROK00067","2","Phylosift","phylosift/v2/PMPROK00067.hmm"),
                        Marker("PMPROK00068","2","Phylosift","phylosift/v2/PMPROK00068.hmm"),
                        Marker("PMPROK00069","2","Phylosift","phylosift/v2/PMPROK00069.hmm"),
                        Marker("PMPROK00071","2","Phylosift","phylosift/v2/PMPROK00071.hmm"),
                        Marker("PMPROK00074","2","Phylosift","phylosift/v2/PMPROK00074.hmm"),
                        Marker("PMPROK00075","2","Phylosift","phylosift/v2/PMPROK00075.hmm"),
                        Marker("PMPROK00081","2","Phylosift","phylosift/v2/PMPROK00081.hmm"),
                        Marker("PMPROK00086","2","Phylosift","phylosift/v2/PMPROK00086.hmm"),
                        Marker("PMPROK00087","2","Phylosift","phylosift/v2/PMPROK00087.hmm"),
                        Marker("PMPROK00092","2","Phylosift","phylosift/v2/PMPROK00092.hmm"),
                        Marker("PMPROK00093","2","Phylosift","phylosift/v2/PMPROK00093.hmm"),
                        Marker("PMPROK00094","2","Phylosift","phylosift/v2/PMPROK00094.hmm"),
                        Marker("PMPROK00097","2","Phylosift","phylosift/v2/PMPROK00097.hmm"),
                        Marker("PMPROK00106","2","Phylosift","phylosift/v2/PMPROK00106.hmm"),
                        Marker("PMPROK00123","2","Phylosift","phylosift/v2/PMPROK00123.hmm"),
                        Marker("PMPROK00126","2","Phylosift","phylosift/v2/PMPROK00126.hmm")]

def getAllMarkerSets():
    return phylosift_v2_markers

