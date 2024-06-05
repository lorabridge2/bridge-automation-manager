import json
import array
import redis
import os

from enum import IntEnum
from redis_queue_listener import RedisQueueListener

from error_messages import error_messages
from LBnode import LBnode
from LBflow import LBflow
from LBdevice import LBdevice

import template_loader

# Action bytes:
# 0 - Remove node
# 1 - Add node
# 2 - Add device
# 3 - Parameter update
# 4 - Connect node
# 5 - Disconnect node
# 6 - Enable flow
# 7 - Disable flow
# 8 - Time sync response
# 9 - Add flow
# 10 - Flow complete

flows = []
compressed_commands = []
debug_print = True


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
    THERMOSTAT = 9
    COUNTDOWN_SWITCH = 10


node_template_files_dictionary = {
    node_bytes.COUNTDOWN_SWITCH.value: "countdown_switch.json",
    node_bytes.TIMER_SWITCH.value: "timer_switch.json",
    node_bytes.BINARY_DEVICE.value: "mqtt_out.json",
    node_bytes.BINARY_SENSOR.value: "mqtt_in.json",
}

# Same as above


# TODO: Need more fine grained description with byte index and width in bytes
# optionally, just place "node_id_b1" and "node_id_b2" to describe multi byte fields

command_byte_structures = {
    "add_flow": {"action_byte": 0, "flow_id": 1},
    "flow_complete": {"action_byte": 0, "flow_id": 1},
    "add_node": {"action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3},
    "add_device": {
        "action_byte": 0,
        "flow_id": 1,
        "node_id": 2,
        "node_type": 3,
        "lb_device": 4,
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
    new_node.nodered_template = template_loader.load_nodered_template(
        node_template_files_dictionary[node_type]
    )
    new_node.wires = [-1] * len(new_node.nodered_template[0]["outputs"])

    _flow.nodes.append(new_node)

    return error_messages.NO_ERRORS


def add_device(flow_id, node_id, node_type, lb_device) -> int:

    _flow = seek_flow(flow_id)
    if _flow == None:
        return error_messages.FLOW_NOT_FOUND

    if node_type not in list(map(int, node_bytes)):
        return error_messages.NODE_TYPE_NOT_FOUND

    if template_loader.get_device_ieee_id(lb_device) == None:
        return error_messages.DEVICE_NOT_FOUND

    new_device = LBdevice(node_id, node_type, lb_device)
    new_device.nodered_template = template_loader.load_nodered_template(
        node_template_files_dictionary[node_type]
    )
    new_device.wires = [-1] * len(new_device.nodered_template[0]["outputs"])
    new_device.device_id = lb_device

    _flow.nodes.append(new_device)

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


def parameter_update(
    flow_id, node_id, parameter_id, num_bytes, parameter_type, raw_bytes
):
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


def remove_node(flow_id, node_id) -> int:
    return error_messages.NO_ERRORS


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

        case action_bytes.FLOW_COMPLETE:

            # TODO: This sanity check does not really work if we plan to use more than bytes in commands!!!

            if len(command) is not len(command_byte_structures["flow_complete"]):
                return error_messages.COMMAND_MALFORMED

            flow_id = command[command_byte_structures["flow_complete"]["flow_id"]]

            template_loader.compose_nodered_flow_to_json(
                flows[0], "lorawan_experiment.json"
            )

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
            output_node = command[
                command_byte_structures["connect_node"]["output_node"]
            ]
            output = command[command_byte_structures["connect_node"]["output"]]
            input_node = command[command_byte_structures["connect_node"]["input_node"]]
            input = command[command_byte_structures["connect_node"]["input"]]

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
            parameter_id = command[
                command_byte_structures["parameter_update"]["parameter_id"]
            ]
            bytes_num = command[command_byte_structures["parameter_update"]["bytes"]]
            parameter_type = command[
                command_byte_structures["parameter_update"]["type"]
            ]
            raw_bytes = command[
                command_byte_structures["parameter_update"]["content"] :
            ]

            err = parameter_update(
                flow_id, node_id, parameter_id, bytes_num, parameter_type, raw_bytes
            )

            return err
        # "connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5}


# How to get active flow nodered json: curl -X GET -H "Accept: application/json" http://10.203.14.242:1880/flows -o active_flow.json


def process_downlink_data(data):
    print("Processing downlink data")
    # This function can be customized to process the received data
    data2 = data.decode("utf-8")
    cmd_array = bytearray.fromhex(data2)
    parse_compressed_command(cmd_array)


if __name__ == "__main__":
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
    queue_listener.join()

    # # Keep the main thread alive
    # try:
    #     while True:
    #         pass
    # except KeyboardInterrupt:
    #     pass
