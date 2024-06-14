

import paho.mqtt.subscribe as subscribe
import json
import device_classes

m = subscribe.simple("zigbee2mqtt/bridge/devices", hostname="10.203.14.242")

raw_payload = m.payload
received_items = json.loads(raw_payload)
ieee_id = "0x54ef4410004dc531"
attribute = "state"

for items in received_items:
    if "friendly_name" in items:
        #print(items)
        if items["friendly_name"] == ieee_id and "definition" in items:
            
            if "exposes" in items["definition"]:
                for exposed_attributes in items["definition"]["exposes"]:
                    # Generic binary sensor
                    if "property" in exposed_attributes and "type" in exposed_attributes and "value_on" in exposed_attributes and "value_off" in exposed_attributes:
                        if attribute in exposed_attributes["property"] and exposed_attributes["type"] == "binary":
                            print({"value_on": exposed_attributes["value_on"], "value_off": exposed_attributes["value_off"]})
                    # Switch
                    if "type" in exposed_attributes and "features" in exposed_attributes:
                        if exposed_attributes["type"] == "switch":
                            for exposed_features in exposed_attributes["features"]:
                                if "property" in exposed_features and "type" in exposed_features and "value_on" in exposed_features and "value_off" in exposed_features:
                                    if attribute in exposed_features["property"]:
                                        print({"value_on": exposed_features["value_on"], "value_off": exposed_features["value_off"]})
            
                

    #print("Received messages:", received_messages)