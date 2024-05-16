# add flow
compressed_commands.append([9, 0])

# add MQTT input for switch state

compressed_commands.append([2, 0, 0, 3, 1])

# add MQTT input for occupancy sensor

compressed_commands.append([2, 0, 1, 3, 6])

# add MQTT output for switch

compressed_commands.append([2, 0, 2, 1, 1])

# add timed switch

compressed_commands.append([1, 0, 3, 10])

# connect switch state to switch node

compressed_commands.append([4, 0, 0, 0, 3, 0])

# connect occupancy state to switch node

compressed_commands.append([4, 0, 1, 0, 3, 1])

# connect timed switch to MQTT output

compressed_commands.append([4, 0, 3, 0, 2, 0])

# update countdown parameter 

#parameter_update(flow_id, node_id, parameter_id, num_bytes, parameter_type, raw_bytes)

# flow complete

compressed_commands.append([10,0])

compressed_commands.append([3, 0, 3, 0, 1, parameter_data_types.INTEGER, 15])

for cmd in compressed_commands:
    parse_compressed_command(cmd)

export_nodered_flow("switch_experiment.json")