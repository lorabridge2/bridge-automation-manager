import pickle
import hashlib

class LBflow:
    def __init__(self, id):
        self.id = id        
        self.nodes = []
        self.nodered_id = ''
        self.nodered_flow_dict = {}
        self.raw_commands = []            
        self.iscomplete = False
    
    def __hash__(self) -> int:        
        return bytes(bytearray.fromhex(hashlib.sha1(repr(self.raw_commands).encode()).hexdigest()[-16:]))
    