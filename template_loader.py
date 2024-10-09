# TODO: Rename to nodered_template_manager

import json
import redis
import nodered_id_gen
import LBflow
import paho.mqtt.subscribe as subscribe
from error_messages import error_messages
import device_classes
import os
import urllib
import hashlib
from urllib import request
from urllib import error

# TODO: replace eth to localhost later on bridge

NODERED_HOST = os.environ.get("NODERED_HOST", "localhost")
NODERED_PORT = int(os.environ.get("NODERED_PORT", 1880))

nodered_mqtt_broker = ""

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))


def load_nodered_template(template_filename: str) -> dict:
    nr_template_dict = {}

    # feature req: add sanity check for json?

    with open(template_filename) as json_file:
        nr_template_dict = json.load(json_file)

        nr_old_ids = []

        for nr_node in nr_template_dict[1:]:
            nr_old_ids.append(nr_node["id"])

        nr_old_template = json.dumps(nr_template_dict)

        for id_to_be_replaced in nr_old_ids:
            new_id = nodered_id_gen.generate_nodered_id()
            nr_old_template = nr_old_template.replace(id_to_be_replaced, new_id)

        return json.loads(nr_old_template)


def compose_nodered_flow_to_json(flow: LBflow, output_file: str) -> None:
    nodered_flow = []

    fetch_nodered_mqtt_broker()

    header = {
        "id": nodered_id_gen.generate_nodered_id(),
        "type": "tab",
        "label": "lorabridge flow",
        "disabled": True,
        "info": "True heros drink matcha.",
        "env": [],
        "nodes": [],
        "configs": [],
    }

    nodered_flow.append(header)

    for node in flow.nodes:

        for template_nodes in node.nodered_template[1:]:
            template_nodes["z"] = header["id"]

            if (
                template_nodes["type"] == "mqtt in"
                or template_nodes["type"] == "mqtt out"
            ):
                template_nodes["broker"] = nodered_mqtt_broker

            if (
                template_nodes["type"]
                == "mqtt in"
                # and node.nodered_template[0]["type"] == "lb_mqtt_input_numeric"
                # or node.nodered_template[0]["type"] == "lb_mqtt_input_binary"
            ):
                node.nodered_template[0]["parameters"][0]["current_value"] = (
                    device_classes.DEVICE_CLASSES[node.device_attribute]
                )

                template_nodes["topic"] = "zigbee2mqtt/" + get_device_ieee_id(
                    node.device_id
                )

            if node.nodered_template[0]["type"] == "lb_mqtt_input_binary":
                boolean_attributes = get_boolean_definitions_ieee_id(
                    get_device_ieee_id(node.device_id),
                    device_classes.DEVICE_CLASSES[node.device_attribute],
                )

                if isinstance(boolean_attributes["value_on"], str):
                    node.nodered_template[0]["parameters"][1]["current_value"] = (
                        '"' + boolean_attributes["value_on"] + '"'
                    )
                    node.nodered_template[0]["parameters"][2]["current_value"] = (
                        '"' + boolean_attributes["value_off"] + '"'
                    )
                if isinstance(boolean_attributes["value_on"], bool):
                    node.nodered_template[0]["parameters"][1]["current_value"] = str(
                        boolean_attributes["value_on"]
                    ).lower()
                    node.nodered_template[0]["parameters"][2]["current_value"] = str(
                        boolean_attributes["value_off"]
                    ).lower()

            if node.nodered_template[0]["type"] == "lb_mqtt_output_binary":
                boolean_attributes = get_boolean_definitions_ieee_id(
                    get_device_ieee_id(node.device_id),
                    device_classes.DEVICE_CLASSES[node.device_attribute],
                )

                if isinstance(boolean_attributes["value_on"], str):
                    node.nodered_template[0]["parameters"][1]["current_value"] = (
                        '\\"' + boolean_attributes["value_on"] + '\\"'
                    )
                    node.nodered_template[0]["parameters"][2]["current_value"] = (
                        '\\"' + boolean_attributes["value_off"] + '\\"'
                    )
                    node.nodered_template[0]["parameters"][4]["current_value"] = (
                        '"' + boolean_attributes["value_on"] + '"'
                    )
                    node.nodered_template[0]["parameters"][5]["current_value"] = (
                        '"' + boolean_attributes["value_off"] + '"'
                    )
                if isinstance(boolean_attributes["value_on"], bool):
                    node.nodered_template[0]["parameters"][1]["current_value"] = (
                        '"' + str(boolean_attributes["value_on"]).lower() + '"'
                    )
                    node.nodered_template[0]["parameters"][2]["current_value"] = (
                        '"' + str(boolean_attributes["value_off"]).lower() + '"'
                    )
                    node.nodered_template[0]["parameters"][4]["current_value"] = str(
                        boolean_attributes["value_on"]
                    ).lower()
                    node.nodered_template[0]["parameters"][5]["current_value"] = str(
                        boolean_attributes["value_off"]
                    ).lower()

            if (
                template_nodes["type"]
                == "mqtt out"
                # and node.nodered_template[0]["type"] == "lb_mqtt_output"
                # or node.nodered_template[0]["type"] == "lb_mqtt_output_binary"
            ):
                node.nodered_template[0]["parameters"][0]["current_value"] = (
                    device_classes.DEVICE_CLASSES[node.device_attribute]
                )
                template_nodes["topic"] = (
                    "zigbee2mqtt/" + get_device_ieee_id(node.device_id) + "/set"
                )

            nodered_flow[0]["nodes"].append(template_nodes)

        # nodered_flow.append(node.nodered_template[1:])

        # Check for parameters to be updated/initialized

        if "parameters" in node.nodered_template[0]:
            # print("Updating parameters for ", node.nodered_template[0]["description"])
            for parameter in node.nodered_template[0]["parameters"]:

                parameter_node_id = parameter["node_id"]
                parameter_tag = parameter["nametag"]
                parameter_nodekey = parameter["nodekey"]
                parameter_value = parameter["current_value"]

                for nodered_node in nodered_flow[0]["nodes"]:
                    if nodered_node["id"] == parameter_node_id:
                        # If parameter is a part of a string (such as code), we replace simply the tag with strigified value.
                        # If parametertag -is- the value, then we substitute the value itself

                        # TODO: sanity check for type violations (corrupted template)

                        if type(nodered_node[parameter_nodekey]) == str:
                            if nodered_node[parameter_nodekey] == parameter_tag:
                                nodered_node[parameter_nodekey] = parameter_value
                            else:
                                nodered_node[parameter_nodekey] = nodered_node[
                                    parameter_nodekey
                                ].replace(parameter_tag, str(parameter_value))

    flow.nodered_flow_dict = nodered_flow[0]

    #nodered_flow_json = json.dumps(nodered_flow[0], indent=4)

    #with open(output_file, "w") as json_file:
    #    json_file.write(nodered_flow_json)


def delete_flow_from_nodered(flow: LBflow):

    headers = {"Content-Type": "application/json"}
    url = "http://" + NODERED_HOST + ":1880/flow" + "/" + str(flow.nodered_id)
    selected_method = "DELETE"

    req = request.Request(
        url,
        b"",
        headers,
        origin_req_host=None,
        unverifiable=False,
        method=selected_method,
    )

    try:
        resp = request.urlopen(req)
    except error.HTTPError as e:
        print("Nodered API request returned HTTP error: ", e.code)
        exit(0)
    except error.URLError as e:
        print("Nodered API request returned URL error: ", e.reason)
    else:
        print("Flow deletion result:", resp.read())


def upload_flow_to_nodered(flow: LBflow, update: bool):
    headers = {"Content-Type": "application/json"}
    url = "http://" + NODERED_HOST + ":1880/flow"
    selected_method = "POST"

    if update:
        selected_method = "PUT"
        url += "/" + str(flow.nodered_id)

    nr_flow = json.dumps(flow.nodered_flow_dict)

    nr_flow_bin = nr_flow if type(nr_flow) == bytes else nr_flow.encode("utf-8")
    req = request.Request(
        url,
        nr_flow_bin,
        headers,
        origin_req_host=None,
        unverifiable=False,
        method=selected_method,
    )

    
    resp = request.urlopen(req)

    flow_resp_raw = resp.read()

    flow_resp = json.loads(flow_resp_raw)

    flow_id = ""

    if "id" not in flow_resp:
        print("Flow upload to Nodered failed.")
        # TODO: Inform user
    else:
        flow_id = flow_resp["id"]

    return flow_id


def upload_flow_to_nodered_from_file(input_file):
    headers = {"Content-Type": "application/json"}
    url = "http://" + NODERED_HOST + ":1880/flow"

    with open(input_file, "r") as nr_file:
        nr_flow = nr_file.read()

        nr_flow_bin = nr_flow if type(nr_flow) == bytes else nr_flow.encode("utf-8")
        req = request.Request(url, nr_flow_bin, headers)
        resp = request.urlopen(req)

        flow_resp_raw = resp.read()

        flow_resp = json.loads(flow_resp_raw)

        flow_id = ""

        if "id" not in flow_resp:
            print("Flow upload to Nodered failed.")
            # TODO: Inform user
        else:
            flow_id = flow_resp["id"]

        return flow_id


def fetch_nodered_mqtt_broker() -> int:

    global nodered_mqtt_broker

    response_json = json.loads(
        urllib.request.urlopen(f"http://{NODERED_HOST}:{NODERED_PORT}/flow/global")
        .read()
        .decode("utf-8")
    )

    for config in response_json["configs"]:
        if config["type"] == "mqtt-broker":
            nodered_mqtt_broker = config["id"]
            print("MQTT broker found, id: " + nodered_mqtt_broker)
            return error_messages.NO_ERRORS

    return error_messages.MQTT_BROKER_NOT_FOUND


def get_device_ieee_id(lb_id):
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    value = redis_client.hget("lorabridge:device:registry:id", lb_id)

    return value.decode("utf-8")


def get_boolean_definitions_ieee_id(ieee_id, attribute):

    m = subscribe.simple(
        "zigbee2mqtt/bridge/devices", hostname=MQTT_HOST, port=MQTT_PORT
    )

    raw_payload = m.payload
    received_items = json.loads(raw_payload)
    # ieee_id = "0x54ef4410004dc531"
    # attribute = "state"

    for items in received_items:
        if "friendly_name" in items:
            # print(items)
            if items["friendly_name"] == ieee_id and "definition" in items:

                if "exposes" in items["definition"]:
                    for exposed_attributes in items["definition"]["exposes"]:
                        # Generic binary sensor
                        if (
                            "property" in exposed_attributes
                            and "type" in exposed_attributes
                            and "value_on" in exposed_attributes
                            and "value_off" in exposed_attributes
                        ):
                            if (
                                attribute in exposed_attributes["property"]
                                and exposed_attributes["type"] == "binary"
                            ):
                                # print({"value_on": exposed_attributes["value_on"], "value_off": exposed_attributes["value_off"]})
                                return {
                                    "value_on": exposed_attributes["value_on"],
                                    "value_off": exposed_attributes["value_off"],
                                }
                        # Switch
                        if (
                            "type" in exposed_attributes
                            and "features" in exposed_attributes
                        ):
                            if exposed_attributes["type"] == "switch":
                                for exposed_features in exposed_attributes["features"]:
                                    if (
                                        "property" in exposed_features
                                        and "type" in exposed_features
                                        and "value_on" in exposed_features
                                        and "value_off" in exposed_features
                                    ):
                                        if attribute in exposed_features["property"]:
                                            return {
                                                "value_on": exposed_features[
                                                    "value_on"
                                                ],
                                                "value_off": exposed_features[
                                                    "value_off"
                                                ],
                                            }
    return {}
