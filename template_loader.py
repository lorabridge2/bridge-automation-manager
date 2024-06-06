# TODO: Rename to nodered_template_manager

import json
import redis
import nodered_id_gen
import LBflow
from error_messages import error_messages
import os
import urllib

# TODO: replace eth to localhost later on bridge

NODERED_HOST = os.environ.get("NODERED_HOST", "localhost")
NODERED_PORT = int(os.environ.get("NODERED_PORT", 1880))

nodered_mqtt_broker = ""

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))


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
                template_nodes["type"] == "mqtt in"
                and node.nodered_template[0]["type"] == "lb_mqtt_input"
            ):
                template_nodes["topic"] = "zigbee2mqtt/" + get_device_ieee_id(
                    node.device_id
                )

            # TODO: mqtt output topic should actually be defined in the template and not hardcoded here.

            if (
                template_nodes["type"] == "mqtt out"
                and node.nodered_template[0]["type"] == "lb_mqtt_output"
            ):
                template_nodes["topic"] = (
                    "zigbee2mqtt/" + get_device_ieee_id(node.device_id) + "/set"
                )

            nodered_flow[0]["nodes"].append(template_nodes)

        # nodered_flow.append(node.nodered_template[1:])

    # Check for parameters to be updated/initialized

    if "parameters" in node.nodered_template[0]:
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

    nodered_flow_json = json.dumps(nodered_flow[0], indent=4)

    with open(output_file, "w") as json_file:
        json_file.write(nodered_flow_json)


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
