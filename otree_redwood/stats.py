from collections import defaultdict
import time


observations = defaultdict(lambda: [])
fields = defaultdict(lambda: 0)


class track():

    def __init__(self, context):
        self.context = context
        
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, type, value, traceback):
        elapsed_time = time.time() - self.start
        observations[self.context].append(elapsed_time)
        while len(observations) > 10000:
            observations.pop(0)

    def add(self, key, value):
        fields[key] += value