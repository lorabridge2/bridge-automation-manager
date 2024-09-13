import os
import sys

import device_classes

import redis

redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), port=6379, db=0)

compressed_commands = []

# add flow
compressed_commands.append([9, 0])

# add MQTT output for switch

compressed_commands.append([2, 0, 0, 1, 1, int(device_classes.DEVICE_CLASSES.index('state'))])

# add timer switch

compressed_commands.append([1, 0, 1, 8])

# connect timed switch to MQTT output
# "connect_node": {"action_byte": 0, "flow_id": 1, "output_node": 2,"output":3, "input_node": 4, "input": 5},

compressed_commands.append([4, 0, 1, 0, 0, 0])

# update countdown parameter 

#parameter_update(flow_id, node_id, parameter_id, num_bytes, parameter_type, raw_bytes)
# "parameter_update": {"action_byte":0, "flow_id": 1, "node_id": 2, "parameter_id": 3, "bytes": 4, "type": 5, "content": 6}

compressed_commands.append([3, 0, 1, 0, 1, 1, 9])
compressed_commands.append([3, 0, 1, 1, 1, 1, 12])
compressed_commands.append([3, 0, 1, 2, 1, 1, 15])
compressed_commands.append([3, 0, 1, 3, 1, 1, 15])

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