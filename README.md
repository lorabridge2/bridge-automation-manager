This repo accomplishes the following:

* Fetches compressed automation config/update packets from a redis queue
* Decompresses and parses the automations (compression rules shall be defined in a datastructure which is bootstrapped on bridge&on user-side at installation)
* Registers high level node&connection IDs and links them with low level Nodered nodes&connections (this part is a bit foggy still, needs to be clarified)
* Generates Nodered json
* Updates nodered via API calls
