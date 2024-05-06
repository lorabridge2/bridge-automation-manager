
import json

from enum import IntEnum


from error_messages import error_messages
from LBnode import LBnode
from LBflow import LBflow
from LBdevice import LBdevice    

import template_loader

ENABLE_DEBUG = 0

#Action bytes:
#0 - Remove node
#1 - Add node
#2 - Add device
#3 - Parameter update
#4 - Connect node
#5 - Disconnect node
#6 - Enable flow
#7 - Disable flow
#8 - Time sync response
#9 - Add flow
#10 - Flow complete

flows = []
compressed_commands = []
debug_print = True


new_node = LBnode(1,2)

# TODO: These should not be hard coded, but loaded from a config file (json?)

action_byte_dictionary = {
    "remove_node": 0,
    "add_node": 1,
    "add_device": 2,
    "parameter_update": 3,
    "connect_node": 4,
    "disconnect_node": 5,
    "enable_flow": 6,
    "disable_flow": 7,
    "time_sync_response": 8,
    "add_flow": 9,
    "flow_complete": 10
}

class action_bytes(IntEnum):
    REMOVE_NODE = action_byte_dictionary["remove_node"]
    ADD_NODE = action_byte_dictionary["add_node"]
    ADD_DEVICE = action_byte_dictionary["add_device"]
    PARAMETER_UPDATE = action_byte_dictionary["parameter_update"]
    CONNECT_NODE = action_byte_dictionary["connect_node"]
    DISCONNECT_NODE = action_byte_dictionary["disconnect_node"]
    ENABLE_FLOW = action_byte_dictionary["enable_flow"]
    DISABLE_FLOW = action_byte_dictionary["disable_flow"]
    TIME_SYNC_RESPONSE = action_byte_dictionary["time_sync_response"]
    ADD_FLOW = action_byte_dictionary["add_flow"]
    FLOW_COMPLETE = action_byte_dictionary["flow_complete"]

node_type_dictionary = {
    "binary_device": 1,
    "hybrid_device": 2,
    "binary_sensor": 3,
    "numeric_sensor": 4,    
    "alert": 5,
    "logic_and": 6,
    "logic_or": 7,
    "timed_switch": 8,
    "thermostat": 9,
    "countdown_switch": 10
}

node_template_files_dictionary = {
    node_type_dictionary["countdown_switch"] : "countdown_switch.json",
    node_type_dictionary["binary_device"] : "mqtt_out.json",
    node_type_dictionary["binary_sensor"] : "mqtt_in.json"
}

# Same as above

class node_bytes(IntEnum):
    BINARY_DEVICE = node_type_dictionary["binary_device"]
    HYBRID_DEVICE = node_type_dictionary["hybrid_device"]
    BINARY_SENSOR = node_type_dictionary["binary_sensor"]
    NUMERIC_SENSOR = node_type_dictionary["numeric_sensor"]
    ALERT = node_type_dictionary["alert"]
    LOGIC_AND = node_type_dictionary["logic_and"]
    LOGIC_OR = node_type_dictionary["logic_or"]
    TIMED_SWITCH = node_type_dictionary["timed_switch"]
    THERMOSTAT = node_type_dictionary["thermostat"]
    COUNTDOWN_SWITCH = node_type_dictionary["countdown_switch"]



# TODO: Need more fine grained description with byte index and width in bytes
# optionally, just place "node_id_b1" and "node_id_b2" to describe multi byte fields

command_byte_structures = {
    "add_flow": { "action_byte": 0, "flow_id": 1},
    "flow_complete": {"action_byte": 0, "flow_id": 1},
    "add_node": { "action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3},
    "add_device": { "action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3, "lb_device": 4},
    "connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5},
    "parameter_update": {"action_byte":0, "flow_id": 1, "node_id": 2, "parameter_id": 3, "bytes": 4, "type": 5, "content": 6}
}


def add_flow(flow_id) -> int:

    # TODO: if flow exists, but is not complete: reset flow (remove nodes etc)

    flows.append(LBflow(flow_id))

    return error_messages.NO_ERRORS

# TODO: might be better to provide flows as parameter

def seek_flow(_flow_id) -> LBflow:
    for flow in flows:
        if flow.id == _flow_id:
            return flow
    return None

def seek_node(_flow_id, _node_id) -> LBnode:
    for flow in flows:
        if flow.id == _flow_id:            
            for node in flow.nodes:                
                if node.id == _node_id:                    
                    return node
    return None

# TODO: Add registration to redis, fetch nodered id and add nodered id to append

def add_node(flow_id, node_id, node_type) -> int:  

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    
    if node_type not in list(map(int, node_bytes)):
        return error_messages.NODE_TYPE_NOT_FOUND
    
    new_node = LBnode(node_id, node_type)
    new_node.nodered_template = template_loader.load_nodered_template(node_template_files_dictionary[node_type])
    new_node.wires = [-1] * len(new_node.nodered_template[0]["outputs"])

    _flow.nodes.append(new_node)

    return error_messages.NO_ERRORS

# TODO: Add registration to redis, fetch nodered id and add nodered id to append

def add_device(flow_id,node_id,node_type, lb_device) -> int:    
    
    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    
    if node_type not in list(map(int, node_bytes)):
        return error_messages.NODE_TYPE_NOT_FOUND
    
    flows.nodes.append(LBdevice(node_id, node_type, lb_device))
    
    return error_messages.NO_ERRORS

# TODO: Get output nodered id

def connect_nodes(flow_id, output_node_id, output_id, input_node_id, input_id) -> int:

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    
    _input_node = seek_node(flow_id,input_node_id)
    if _input_node == None:
        return error_messages.NODE_NOT_FOUND
    
    _output_node = seek_node(flow_id,output_node_id)
    if _output_node == None:
        return error_messages.NODE_NOT_FOUND
    
    output_nodered_uuid = _output_node.nodered_template[0]["outputs"][output_id]
    
    input_nodered_uuid = _input_node.nodered_template[0]["inputs"][input_id]
 
    _output_node.wires[output_id] = input_nodered_uuid

    # TODO: Optinal ADD Here: or later in final generator function, which updates the output node "notset" wire in the template

    for nr_output_node in _output_node.nodered_template[1:]:
        if nr_output_node["id"] == output_nodered_uuid:
            nr_output_node["wires"] = [[input_nodered_uuid]]

    return error_messages.NO_ERRORS


def disconnect_nodes(flow_id, output_node_id, output_id) -> int:

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    
    _output_node = seek_node(flow_id,output_node_id)
    if _output_node == None:
        return error_messages.NODE_NOT_FOUND
    
    _output_node.wires[output_id] = -1

    return error_messages.NO_ERRORS

# TODO: Before actual deletion, traverse all connections (wires) in flows nodes and remove all the output connections to the node being deleted

def remove_node(flow_id, node_id) -> int:
    return error_messages.NO_ERRORS


def export_nodered_flow(filename : str) -> int:
    err = template_loader.compose_nodered_flow_to_json(flows[0], filename)
    return err



def parse_compressed_command(command) -> int:
    # Sanity checks:

    # If command less than minimum command length->error

    min_command_length = min([(len(v)) for k, v in command_byte_structures.items()])

    if len(command) < min_command_length:
        return error_messages.COMMAND_MALFORMED
    
    # Action bytes
    action_byte = command[0]

    if action_byte not in list(map(int, action_bytes)):
        return error_messages.COMMAND_NOT_FOUND

    if debug_print:    
        print("Action: ", action_bytes(action_byte))
    
    match action_byte:
        case action_bytes.ADD_FLOW:

            # TODO: This sanity check does not really work if we plan to use more than bytes in commands!!!

            if len(command) is not len(command_byte_structures["add_flow"]):
                return error_messages.COMMAND_MALFORMED 

            flow_id = command[command_byte_structures["add_flow"]["flow_id"]]
            add_flow(flow_id)

        case action_bytes.ADD_NODE:
            if len(command) is not len(command_byte_structures["add_node"]):
                return error_messages.COMMAND_MALFORMED
            
            flow_id = command[command_byte_structures["add_node"]["flow_id"]]
            node_id = command[command_byte_structures["add_node"]["node_id"]]
            node_type = command[command_byte_structures["add_node"]["node_type"]]
            
            err = add_node(flow_id, node_id, node_type)
            print(err)
            return err

        case action_bytes.ADD_DEVICE:

            if len(command) is not len(command_byte_structures["add_device"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["add_device"]["flow_id"]]
            node_id = command[command_byte_structures["add_device"]["node_id"]]
            node_type = command[command_byte_structures["add_device"]["node_type"]]
            lb_device = command[command_byte_structures["add_device"]["lb_device"]]
            err = add_device(flow_id, node_id, node_type, lb_device)
            return err
            
        case action_bytes.CONNECT_NODE:
            if len(command) is not len(command_byte_structures["connect_node"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["connect_node"]["flow_id"]]
            output_node = command[command_byte_structures["connect_node"]["output_node"]]
            output = command[command_byte_structures["connect_node"]["output"]]
            input_node = command[command_byte_structures["connect_node"]["input_node"]]
            input = command[command_byte_structures["connect_node"]["input"]]

            err = connect_nodes(flow_id, output_node, output, input_node, input)
            print(err)
            print("output node", output_node)
            print("input node", input_node)
            return err

        #"connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5}

# add flow
compressed_commands.append([9, 0])

# add MQTT input for switch state

compressed_commands.append([1, 0, 0, 3])

# add MQTT input for occupancy sensor

compressed_commands.append([1, 0, 1, 3])

# add MQTT output for switch

compressed_commands.append([1, 0, 2, 1])

# add timed switch

compressed_commands.append([1, 0, 3, 10])

# connect switch state to switch node

compressed_commands.append([4, 0, 0, 0, 3, 0])

# connect occupancy state to switch node

compressed_commands.append([4, 0, 1, 0, 3, 1])

# connect timed switch to MQTT output

compressed_commands.append([4, 0, 3, 0, 2, 0])

for cmd in compressed_commands:
    parse_compressed_command(cmd)

#print(flows[0].nodes[1].id)

# How to get active flow nodered json: curl -X GET -H "Accept: application/json" http://10.203.14.242:1880/flows -o active_flow.json

export_nodered_flow("switch_experiment.json")

