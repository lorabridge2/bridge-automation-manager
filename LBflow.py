class LBflow:
    def __init__(self, id):
        self.id = id        
        self.nodes = []
        self.nodered_id = ''
        self.nodered_flow_dict = {}     
        self.command_buffer = []
        self.iscomplete = False
    