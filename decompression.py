import json
import array
import redis
import os
import traceback
import time
import hashlib
import threading
import pickle

from enum import IntEnum
from redis_queue_listener import RedisQueueListener

from error_messages import error_messages
from LBnode import LBnode
from LBflow import LBflow
from LBdevice import LBdevice

import template_loader
import device_classes

flows = []
compressed_commands = []
debug_print = True


redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
)

REDIS_FLOW_DIGESTS = "lorabridge:flows:digests"
REDIS_DEVICE_JOIN = "lorabridge:device:join"
REDIS_DEVICE_NAME = "lorabridge:device:name"

new_node = LBnode(1, 2)

# TODO: These should not be hard coded, but loaded from a config file (json?)


class action_bytes(IntEnum):
    REMOVE_NODE = 0
    ADD_NODE = 1
    ADD_DEVICE = 2
    PARAMETER_UPDATE = 3
    CONNECT_NODE = 4
    DISCONNECT_NODE = 5
    ENABLE_FLOW = 6
    DISABLE_FLOW = 7
    TIME_SYNC_RESPONSE = 8
    ADD_FLOW = 9
    FLOW_COMPLETE = 10
    REMOVE_FLOW = 11
    UPLOAD_FLOW = 12
    GET_DEVICES = 13


class parameter_data_types(IntEnum):
    BOOLEAN = 0
    INTEGER = 1
    FLOAT = 2
    STRING = 3


class node_bytes(IntEnum):
    BINARY_DEVICE = 1
    HYBRID_DEVICE = 2
    BINARY_SENSOR = 3
    NUMERIC_SENSOR = 4
    ALERT = 5
    LOGIC_AND = 6
    LOGIC_OR = 7
    TIMER_SWITCH = 8
    HYSTERESIS = 9
    COUNTDOWN_SWITCH = 10
    USER_EVENT = 11


node_template_files_dictionary = {
    node_bytes.COUNTDOWN_SWITCH.value: "countdown_switch_new.json",
    node_bytes.TIMER_SWITCH.value: "timer_switch_new.json",
    node_bytes.BINARY_DEVICE.value: "mqtt_out_binary.json",
    node_bytes.BINARY_SENSOR.value: "mqtt_in_binary.json",
    node_bytes.NUMERIC_SENSOR.value: "mqtt_in_numeric.json",
    node_bytes.HYSTERESIS: "hysteresis.json",
    node_bytes.LOGIC_AND: "logical_and.json",
    node_bytes.LOGIC_OR: "logical_or.json",
    node_bytes.USER_EVENT: "user_event.json",
}

# Same as above

# TODO: Need more fine grained description with byte index and width in bytes
# optionally, just place "node_id_b1" and "node_id_b2" to describe multi byte fields

command_byte_structures = {
    "add_flow": {"action_byte": 0, "flow_id": 1},
    "enable_flow": {"action_byte": 0, "flow_id": 1},
    "disable_flow": {"action_byte": 0, "flow_id": 1},
    "flow_complete": {"action_byte": 0, "flow_id": 1},
    "remove_flow": {"action_byte": 0, "flow_id": 1},
    "upload_flow": {"action_byte": 0, "flow_id": 1},
    "add_node": {"action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3},
    "remove_node": {"action_byte":0, "flow_id": 1, "node_id": 2},
    "add_device": {
        "action_byte": 0,
        "flow_id": 1,
        "node_id": 2,
        "node_type": 3,
        "lb_device": 4,
        "lb_attribute": 5,
    },
    "connect_node": {
        "action_byte": 0,
        "flow_id": 1,
        "output_node": 2,
        "output": 3,
        "input_node": 4,
        "input": 5,
    },
    "parameter_update": {
        "action_byte": 0,
        "flow_id": 1,
        "node_id": 2,
        "parameter_id": 3,
        "bytes": 4,
        "type": 5,
        "content": 6,
    },
    "get_devices": {"action_byte": 0},
}


def add_flow(flow_id) -> int:

    # TODO: if flow exists, but is not complete: reset flow (remove nodes etc)
    _flow = seek_flow(flow_id)

    if _flow != None:
        return error_messages.DUPLICATE_FOUND

    flows.append(LBflow(flow_id))

    return error_messages.NO_ERRORS


def delete_flow(flow_id) -> int:

    _flow = seek_flow(flow_id)

    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    else:
        flows.remove(seek_flow(flow_id))

def backup_flows():
    flow_file = open('flowbackup.dat', 'w') 
    pickle.dump(flows, flow_file)

def restore_flows():
    try:
        with open('flowbackup.dat', 'rb') as file:
            obj = pickle.load(file)
            print("Flow data restored from backup file.")
            return obj
    except FileNotFoundError:
        print(f"Could not restore flows: The file flowbackup.dat was not found.")
    except pickle.UnpicklingError:
        print("Error: The flow backup file is not a valid pickle file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")



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
    new_node.nodered_template = template_loader.load_nodered_template(
        node_template_files_dictionary[node_type]
    )
    new_node.wires = [-1] * len(new_node.nodered_template[0]["outputs"])

    _flow.nodes.append(new_node)

    return error_messages.NO_ERRORS


def add_device(flow_id, node_id, node_type, lb_device, lb_attribute) -> int:

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND

    if node_type not in list(map(int, node_bytes)):
        return error_messages.NODE_TYPE_NOT_FOUND

    if template_loader.get_device_ieee_id(lb_device) == None:
        return error_messages.DEVICE_NOT_FOUND

    new_device = LBdevice(node_id, node_type, lb_device, lb_attribute)
    new_device.nodered_template = template_loader.load_nodered_template(
        node_template_files_dictionary[node_type]
    )
    new_device.wires = [-1] * len(new_device.nodered_template[0]["outputs"])
    new_device.device_id = lb_device
    new_device.device_attribute = lb_attribute

    _flow.nodes.append(new_device)

    return error_messages.NO_ERRORS


def remove_node(flow_id, node_id) -> int:
  
    _flow = seek_flow(flow_id)

    if _flow == None:
        return error_messages.FLOW_NOT_FOUND
    
    _node = seek_node(flow_id, node_id)

    if _node == None:
        return error_messages.NODE_NOT_FOUND
    
    _flow.nodes.remove(_node)

    for node in _flow.nodes:        
        if node_id in node.wires:
            node.wires.remove(node_id)

    return error_messages.NO_ERRORS



# TODO: Get output nodered id


def connect_nodes(flow_id, output_node_id, output_id, input_node_id, input_id) -> int:

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND

    _input_node = seek_node(flow_id, input_node_id)
    if _input_node == None:
        return error_messages.NODE_NOT_FOUND

    _output_node = seek_node(flow_id, output_node_id)
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

    _output_node = seek_node(flow_id, output_node_id)
    if _output_node == None:
        return error_messages.NODE_NOT_FOUND

    _output_node.wires[output_id] = -1

    return error_messages.NO_ERRORS


def parameter_update(flow_id, node_id, parameter_id, num_bytes, parameter_type, raw_bytes):
    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND

    _node = seek_node(flow_id, node_id)
    if _node == None:
        return error_messages.NODE_NOT_FOUND

    # Convert value

    new_value = 0

    match parameter_type:
        case parameter_data_types.BOOLEAN:
            new_value = bool(raw_bytes[0])
        case parameter_data_types.INTEGER:
            new_value = int.from_bytes(raw_bytes[0:num_bytes], "big")
        case parameter_data_types.FLOAT:
            arr = array.array("f")
            arr.frombytes(bytearray(raw_bytes[0:num_bytes]))
            new_value = arr[0]
        case parameter_data_types.STRING:
            new_value = bytes(raw_bytes[0:num_bytes]).decode("utf-8")

    if "parameters" in _node.nodered_template[0]:
        parameter = _node.nodered_template[0]["parameters"][parameter_id]

        if parameter == None:
            return error_messages.PARAMETER_NOT_FOUND
        else:
            parameter["current_value"] = new_value
    else:
        return error_messages.PARAMETER_NOT_FOUND


# TODO: Before actual deletion, traverse all connections (wires) in flows nodes and remove all the output connections to the node being deleted







def pull_device_update():

    device_keys = redis_client.execute_command("HKEYS lorabridge:device:registry:id")



    for device_key in device_keys:
        ieee_id = redis_client.execute_command(
            "HGET lorabridge:device:registry:id " + device_key.decode("utf-8")
        )
        dev_attributes = redis_client.execute_command(
            "SMEMBERS lorabridge:device:attributes:" + ieee_id.decode("utf-8")
        )

        manuf_name = redis_client.execute_command(
            "GET lorabridge:device:name:" + ieee_id.decode("utf-8")
        )

        if manuf_name == None:
            manuf_name = "unknown".encode("utf-8")

        dev_attributes = [item.decode() for item in dev_attributes]
        
        dev_name = int(device_key).to_bytes(1,"big") + ieee_id + manuf_name
        redis_client.lpush(REDIS_DEVICE_NAME, dev_name)

        dev_join = int(device_key).to_bytes(1, "big")
        # dev_join_dict = {"lbdevice_join": [int.from_bytes(device_key, "big")]} # results in 49 for b"1"
        for dev_attribute in dev_attributes:
            if dev_attribute in device_classes.DEVICE_CLASSES:
                dev_join += device_classes.DEVICE_CLASSES.index(dev_attribute).to_bytes(1, "big")
        redis_client.lpush(REDIS_DEVICE_JOIN, dev_join)


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

            err = add_flow(flow_id)

            current_flow = seek_flow(flow_id)

            current_flow.raw_commands.append(command)

            print(err)

        case action_bytes.ENABLE_FLOW:

            if len(command) is not len(command_byte_structures["enable_flow"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["enable_flow"]["flow_id"]]

            current_flow = seek_flow(flow_id)

            current_flow.raw_commands.append(command)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            current_flow.nodered_flow_dict["disabled"] = False

            template_loader.upload_flow_to_nodered(current_flow, True)

        case action_bytes.DISABLE_FLOW:

            if len(command) is not len(command_byte_structures["disable_flow"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["disable_flow"]["flow_id"]]

            current_flow = seek_flow(flow_id)

            current_flow.raw_commands.append(command)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            current_flow.nodered_flow_dict["disabled"] = True

            template_loader.upload_flow_to_nodered(current_flow, True)

        case action_bytes.REMOVE_FLOW:

            if len(command) is not len(command_byte_structures["remove_flow"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["remove_flow"]["flow_id"]]

            current_flow = seek_flow(flow_id)

            if current_flow != None:
                template_loader.delete_flow_from_nodered(current_flow)
                delete_flow(flow_id)
            else:
                return error_messages.FLOW_NOT_FOUND

        case action_bytes.FLOW_COMPLETE:

            # TODO: This sanity check does not really work if we plan to use more than bytes in commands!!!

            if len(command) is not len(command_byte_structures["flow_complete"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["flow_complete"]["flow_id"]]

            current_flow = seek_flow(flow_id)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND
            
            current_flow.raw_commands.append(command)

            flow_filename = "lb_flow" + str(flow_id) + ".json"

            template_loader.compose_nodered_flow_to_json(current_flow, flow_filename)

            flow_digest = hash(current_flow)

            flow_digest_dict = {"lbflow_digest": bytes([flow_id]) + flow_digest}

            print("Digest: ", flow_digest)

            # Push flow_id + digest (64 bits -> 8xhex) to a redis queue

            redis_client.lpush(REDIS_FLOW_DIGESTS, json.dumps(flow_digest_dict))

            backup_flows()

        case action_bytes.UPLOAD_FLOW:

            if len(command) is not len(command_byte_structures["upload_flow"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["upload_flow"]["flow_id"]]

            current_flow = seek_flow(flow_id)

            current_flow.raw_commands.append(command)

            if current_flow != None:
                current_flow.nodered_id = template_loader.upload_flow_to_nodered(
                    current_flow, False
                )
            else:
                return error_messages.FLOW_NOT_FOUND

        case action_bytes.ADD_NODE:
            if len(command) is not len(command_byte_structures["add_node"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["add_node"]["flow_id"]]
            node_id = command[command_byte_structures["add_node"]["node_id"]]
            node_type = command[command_byte_structures["add_node"]["node_type"]]

            current_flow = seek_flow(flow_id)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            _node = seek_node(flow_id, node_id)

            if _node != None:
                return error_messages.DUPLICATE_FOUND

            current_flow.raw_commands.append(command)

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
            lb_attribute = command[command_byte_structures["add_device"]["lb_attribute"]]

            current_flow = seek_flow(flow_id)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            _node = seek_node(flow_id, node_id)

            if _node != None:
                return error_messages.DUPLICATE_FOUND

            current_flow.raw_commands.append(command)

            err = add_device(flow_id, node_id, node_type, lb_device, lb_attribute)
            return err

        case action_bytes.CONNECT_NODE:
            if len(command) is not len(command_byte_structures["connect_node"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["connect_node"]["flow_id"]]
            output_node = command[command_byte_structures["connect_node"]["output_node"]]
            output = command[command_byte_structures["connect_node"]["output"]]
            input_node = command[command_byte_structures["connect_node"]["input_node"]]
            input = command[command_byte_structures["connect_node"]["input"]]

            current_flow = seek_flow(flow_id)
            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            _input_node = seek_node(flow_id, input_node)
            if _input_node == None:
                return error_messages.NODE_NOT_FOUND

            _output_node = seek_node(flow_id, output_node)
            if _output_node == None:
                return error_messages.NODE_NOT_FOUND

            current_flow.raw_commands.append(command)

            err = connect_nodes(flow_id, output_node, output, input_node, input)
            print(err)
            print("output node", output_node)
            print("input node", input_node)
            return err

        case action_bytes.PARAMETER_UPDATE:
            # Variable length command..

            # TODO: sanity check for correct length should be made

            # if len(command) is not len(command_byte_structures["parameter_update"]):
            #    return error_messages.COMMAND_MALFORMED

            #  "parameter_update": {"action_byte":0, "flow_id": 1, "node_id": 2, "parameter_id": 3, "bytes": 4, "type": 5, "content": 6}

            flow_id = command[command_byte_structures["parameter_update"]["flow_id"]]
            node_id = command[command_byte_structures["parameter_update"]["node_id"]]
            parameter_id = command[command_byte_structures["parameter_update"]["parameter_id"]]
            bytes_num = command[command_byte_structures["parameter_update"]["bytes"]]
            parameter_type = command[command_byte_structures["parameter_update"]["type"]]
            raw_bytes = command[command_byte_structures["parameter_update"]["content"] :]

            current_flow = seek_flow(flow_id)

            if current_flow == None:
                return error_messages.FLOW_NOT_FOUND

            _node = seek_node(flow_id, node_id)

            if _node == None:
                return error_messages.NODE_NOT_FOUND

            current_flow.raw_commands.append(command)

            err = parameter_update(
                flow_id, node_id, parameter_id, bytes_num, parameter_type, raw_bytes
            )

            backup_flows()

            return err

        case action_bytes.REMOVE_NODE:
            if len(command) is not len(command_byte_structures["remove_node"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["remove_node"]["flow_id"]]
            node_id = command[command_byte_structures["remove_node"]["node_id"]]

            current_flow = seek_flow(flow_id)

            err = remove_node(flow_id, node_id)

            current_flow.raw_commands.append(command)

            return err

        case action_bytes.GET_DEVICES:
            pull_device_update()

    return error_messages.NO_ERRORS
    # "connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5}


def process_downlink_data(data):
    print("Processing downlink data")
    # This function can be customized to process the received data
    data2 = data.decode("utf-8")

    print("Parser got following hex string:", data2)

    cmd_array = bytearray.fromhex(data2)
    err_msg = parse_compressed_command(cmd_array)

    if err_msg != error_messages.NO_ERRORS:
        print("Parsing error: ", err_msg)


def excepthook(args):
    print(args)
    traceback.print_tb(args.exc_traceback)
    os._exit(1)


if __name__ == "__main__":
    threading.excepthook = excepthook
    # Replace 'my_queue' with the name of your Redis queue
    queue_listener = RedisQueueListener(
        "__keyspace@0__:lbcommands",
        {
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", 6379)),
            "db": int(os.environ.get("REDIS_DB", 0)),
        },
        process_downlink_data,
    )

    queue_listener.start()
    # queue_listener.join()

    # Restore backup flows

    restore_flows()

    # # Keep the main thread alive
    #
    # Zombie code below activated just to enable Keyboard interrupt ;) -Haru

    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        pass
