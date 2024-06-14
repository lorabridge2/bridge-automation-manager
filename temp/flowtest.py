from LBflow import LBflow

flows = []

flows.append(LBflow(1))
flows.append(LBflow(2))

def seek_flow(_flow_id) -> LBflow:
    for flow in flows:
        if flow.id == _flow_id:
            return flow
    return None

my_flow = seek_flow(3)
print(my_flow.id)


