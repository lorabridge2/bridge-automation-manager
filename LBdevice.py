from LBnode import LBnode

class LBdevice(LBnode):
    def __init__(self, id, type, device_id):
        super().__init__(id, type)
        self.device_id = device_id
        
        