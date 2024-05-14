import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

redis_client.hset('lorabridge:device:registry:id', 1, '0x54ef4410004dc531')
redis_client.hset('lorabridge:device:registry:id', 5, '0x00158d0007e3f56d')
redis_client.hset('lorabridge:device:registry:id', 6, '0x00158d0007e3feb9')

value = redis_client.hget('lorabridge:device:registry:id', 1)

print(value.decode('utf-8'))