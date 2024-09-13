import os
import sys

import device_classes

import redis

redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), port=6379, db=0)

compressed_commands = []

# add flow
compressed_commands.append([9, 0])

# add MQTT input for temperature sensor
# "add_device": { "action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3, "lb_device": 4},

compressed_commands.append([2, 0, 0, 4, 3, int(device_classes.DEVICE_CLASSES.index('temperature'))])

# add MQTT output for switch

compressed_commands.append([2, 0, 1, 1, 1, int(device_classes.DEVICE_CLASSES.index('state'))])

# add hysteresis

compressed_commands.append([1, 0, 2, 9])

# connect temperature to thermostat node
# "connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5},

compressed_commands.append([4, 0, 0, 0, 2, 0])

# connect hysteresis to MQTT output

compressed_commands.append([4, 0, 2, 0, 1, 0])

# update threshold parameter 

#parameter_update(flow_id, node_id, parameter_id, num_bytes, parameter_type, raw_bytes)
# "parameter_update": {"action_byte":0, "flow_id": 1, "node_id": 2, "parameter_id": 3, "bytes": 4, "type": 5, "content": 6}

compressed_commands.append([3, 0, 3, 0, 4, 2, 0, 0, 172, 65])
compressed_commands.append([3, 0, 3, 1, 4, 2, 154, 153, 189, 65])


# flow complete

compressed_commands.append([10,0])

# upload flow

compressed_commands.append([12,0])

# enable flow

compressed_commands.append([6,0])

if __name__ == "__main__":

  for cmd in compressed_commands:
    temp_hex_string = ''.join('{:02x}'.format(x) for x in cmd)
    #print(temp_hex_string)
    redis_client.lpush("lbcommands", temp_hex_string)