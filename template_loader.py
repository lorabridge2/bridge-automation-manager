# TODO: Rename to nodered_template_manager

import pycurl
import json
import nodered_id_gen
import LBflow
from error_messages import error_messages
from io import BytesIO


# TODO: replace eth to localhost later on bridge

nodered_address = "10.203.14.242:1880"
nodered_mqtt_broker = ""

def load_nodered_template(template_filename : str) -> dict:
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
    
def compose_nodered_flow_to_json(flow : LBflow, output_file : str) -> int:
    nodered_flow = []

    fetch_nodered_mqtt_broker()

    header = {"id": nodered_id_gen.generate_nodered_id(), "type":"tab", "label":"lorabridge flow", "disabled": True, "info": "True heros drink matcha.", "env": []}

    nodered_flow.append(header)

    for node in flow.nodes:

        for template_nodes in node.nodered_template[1:]:
            template_nodes["z"] = header["id"]

            if template_nodes["type"] == "mqtt in" or template_nodes["type"] == "mqtt out":
                template_nodes["broker"] = nodered_mqtt_broker

            nodered_flow.append(template_nodes)

        #nodered_flow.append(node.nodered_template[1:])

    nodered_flow_json = json.dumps(nodered_flow, indent=4)

    with open(output_file,"w") as json_file:
        json_file.write(nodered_flow_json)

    return 0

def fetch_nodered_mqtt_broker() -> int:
    
    global nodered_mqtt_broker

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, nodered_address+"/flow/global")
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()
    body = body.decode('utf-8')
    response_json = json.loads(body)

    for config in response_json["configs"]:
        if config["type"] == "mqtt-broker":
            nodered_mqtt_broker = config["id"]            
            print("MQTT broker found, id: "+nodered_mqtt_broker)
            return error_messages.NO_ERRORS
   

    return error_messages.MQTT_BROKER_NOT_FOUND