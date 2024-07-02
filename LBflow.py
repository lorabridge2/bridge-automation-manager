import pickle

class LBflow:
    def __init__(self, id):
        self.id = id        
        self.nodes = []
        self.nodered_id = ''
        self.nodered_flow_dict = {}            
        self.iscomplete = False
    
    def __hash__(self) -> int:
        return hash(pickle.dumps(self.nodes))
    