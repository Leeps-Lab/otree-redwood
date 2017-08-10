from collections import defaultdict
from huey.contrib.djhuey import HUEY
import mockredis
import otree.common_internal
import time


redis = None


class track():

    def __init__(self, context):
        self.context = context
        global redis
        if not redis:
            if otree.common_internal.USE_REDIS:
                redis = HUEY.storage.conn
            else:
                redis = mockredis.mock_redis_client()

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, type, value, traceback):
        elapsed_time = float(time.time() - self.start)
        update(self.context, elapsed_time)


def update(context, value):
    key = 'redwood-{}'.format(context)
    redis.hset(key, 'tracking_context', context)
    redis.hincrbyfloat(key, 'sum', value)
    redis.hincrbyfloat(key, 'count', 1)
    redis.sadd('redwood-tracking-contexts', key)


def items():
    global redis
    if not redis:
        if otree.common_internal.USE_REDIS:
            redis = HUEY.storage.conn
        else:
            redis = mockredis.mock_redis_client()
    items = {}
    for key in redis.smembers('redwood-tracking-contexts'):
        tracking_context = redis.hget(key, 'tracking_context')
        items[tracking_context] = {}
        mean = float(redis.hget(key, 'sum')) / float(redis.hget(key, 'count'))
        items[tracking_context]['mean'] = mean
    return items