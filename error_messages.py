from enum import IntEnum

class error_messages(IntEnum):
    NO_ERRORS = 0
    FLOW_NOT_FOUND = 1
    NODE_NOT_FOUND = 2
    DEVICE_NOT_FOUND = 3
    COMMAND_NOT_FOUND = 4
    COMMAND_SYNTAX_ERROR = 5
    COMMAND_MALFORMED = 6
    NODE_TYPE_NOT_FOUND = 7
    MQTT_BROKER_NOT_FOUND = 8