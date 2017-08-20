import time
import json
from redis import ConnectionError
import logging
import jsonpickle
log = logging.getLogger("redis-conn")


class RedisConn(object):
    def __init__(self, redis_conn, sub_channel='rtu-cmd', pub_channel='rtu-cmd', cli_id=None):
        self._redis_conn = redis_conn

        self._pubsub = self._redis_conn.pubsub(ignore_subscribe_messages=False)
        log.error("subscribing: %s" % sub_channel)
        self._pubsub.subscribe(sub_channel)

        self._sub_channel_name = sub_channel
        self._pub_channel_name = pub_channel

        self._cli_id = cli_id

    def subscribe(self, channel_name):
        self._pubsub.subscribe(channel_name)

    def listen(self, rcv_timeout=0.01):

        message = True
        while message:
            try:
                message = self._pubsub.get_message(timeout=rcv_timeout)
            except ConnectionError:
                log.error("lost connection to Redis")
                time.sleep(1)
                break
            if message:
                log.debug("%s - receied pub message: %s" % (self._cli_id, message))
                if message['type'] == 'message':
                    try:
                        return jsonpickle.loads(message['data'])
                    except ValueError:
                        return message['data']
        return None

    def publish(self, payload, channel=None):
        if channel is None:
            channel = self._pub_channel_name
        log.debug("publishing to channel: %s \n %s" % (channel, payload))
        try:
            payload = jsonpickle.dumps(payload)
        except ValueError:
            pass
        self._redis_conn.publish(channel, payload)

    def hgetall(self, *args, **kwargs):
        return self._redis_conn.hgetall(*args, **kwargs)

    def hget(self, *args, **kwargs):
        return self._redis_conn.hget(*args, **kwargs)

    def hmset(self, *args, **kwargs):
        return self._redis_conn.hmset(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._redis_conn.delete(*args, **kwargs)

    def hdel(self, *args, **kwargs):
        return self._redis_conn.hdel(*args, **kwargs)

    def hset(self, *args, **kwargs):
        return self._redis_conn.hset(*args, **kwargs)

    def set(self, *args, **kwargs):
        return self._redis_conn.set(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._redis_conn.get(*args, **kwargs)