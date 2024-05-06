import uuid

# TODO: Check for ID collisions!

def generate_nodered_id() -> str:
    nodered_id =  f'{uuid.uuid4().int>>64:x}'
    return nodered_id