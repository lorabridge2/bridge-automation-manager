import redis
import threading


class RedisQueueListener:
    def __init__(self, queue_name, redis_conn, callback):
        self.queue_name = queue_name
        self.callback = callback
        self.redis_conn = redis.Redis(
            host=redis_conn["host"], port=redis_conn["port"], db=redis_conn["db"]
        )
        self.pubsub = self.redis_conn.pubsub()
        self.pubsub.subscribe(self.queue_name)
        self.thread = threading.Thread(target=self.listen)
        self.thread.daemon = (
            True  # Set the thread as a daemon to exit when the main program exits
        )

    def listen(self):
        for message in self.pubsub.listen():
            # print(message)
            if message["type"] == "message":
                command = message["data"]
                if command == b"lpush":
                    data = self.redis_conn.rpop("lbcommands")
                    self.callback(data)

    def start(self):
        self.thread.start()
