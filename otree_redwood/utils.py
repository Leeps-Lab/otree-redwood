import threading
import time


_timers = {}
class DiscreteEventEmitter():

    def __init__(self, interval, period_length, group, callback, start_immediate=False):
        self.interval = float(interval)
        self.period_length = period_length
        self.group = group
        self.intervals = self.period_length / self.interval
        self.callback = callback
        self.current_interval = 0
        if self.group not in _timers:
            # TODO: Should replace this with something like Huey/Celery so it'll survive a server restart.
            self.timer = threading.Timer(0 if start_immediate else self.interval, self._tick)
            _timers[self.group] = self.timer
        else:
            self.timer = None

    def _tick(self):
        start = time.time()
        self.callback(self.current_interval, self.intervals)
        self.current_interval += 1
        if self.current_interval < self.intervals:
            self.timer = threading.Timer(self._time, self._tick)
            _timers[self.group] = self.timer
            self.timer.start()
    
    @property
    def _time(self):
        return self.interval - ((time.time() - self.start_time) % self.interval)

    def start(self):
        if self.timer:
            self.start_time = time.time()
            self.timer.start()

    def stop(self):
        del _timers[self.group]
