import redis
from redis_dict import RedisDict

db = RedisDict(namespace='english_vocablary')