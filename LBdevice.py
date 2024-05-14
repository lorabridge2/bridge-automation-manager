from LBnode import LBnode

class LBdevice(LBnode):
    def __init__(self, id, type, device_id):
        self.id = id
        self.type = type
        self.wires = []
        self.nodered_template = {}
        self.device_id = device_id
        
        