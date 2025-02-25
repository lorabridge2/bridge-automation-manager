Automation manager of Bridge Unit
============================================

This repository is part of the [LoRaBridge](https://github.com/lorabridge2/lorabridge) project.

This repository contains source code for automation manager, which performs composition of automation
flows out of received LoRaBridge automation configuration commands. In addition, the software takes care of exporting and uploading
of the user automations into the NodeRED container. 

Features
--------
- Decompression of LB automation commands
- Storage of LB automation flows
- Conversion of LB flows to NodeRED flows
- Uploading of NodeRED flows to NodeRED

## Environment Variables

- `MQTT_HOST`: IP or hostname of MQTT host
- `MQTT_PORT`: Port used by MQTT
- `REDIS_HOST`: IP or hostname of Redis host
- `REDIS_PORT`: Port used by Redis
- `REDIS_DB`: Number of the database used inside Redis
- `NODERED_HOST`: IP or hostname of Nodered host
- `NODERED_PORT`: Port used by Nodered

## License

All the LoRaBridge software components and the documentation are licensed under GNU General Public License 3.0.

## Acknowledgements
The financial support from Internetstiftung/Netidee is gratefully acknowledged. The mission of Netidee is to support development of open-source tools for more accessible and versatile use of the Internet in Austria.