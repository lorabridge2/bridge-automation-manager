compression_commands = {
    "add_flow": { "action_byte": 0, "flow_id": 1},
    "add_node": { "action_byte": 0, "flow_id": 1, "node_id": 2, "node_type": 3, "lb_device": 4}
}

key_len = min([(len(v)) for k, v in compression_commands.items()])

print(key_len)
print(compression_commands["add_node"]["flow_id"])