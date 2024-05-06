from LBnode import LBnode

class LBdevice(LBnode):
    def __init__(self, id, type, device_id):
        self.id = id
        self.type = type
        self.device_id = device_id
        self.input_node = -1
        self.output_node = -1
        self.nodered_id = 0