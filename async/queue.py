from gevent.queue import Queue

__author__ = 'ocarrere'


class Event(object):
    def __init__(self, name, data=None):
        self._name = name
        self._data = data

    def match(self, *args):
        return self._name in args


class EventQueue(Queue):
    def all(self, timeout=None, until_empty=False):
        while not until_empty or not self.empty():
            event = self.get(timeout=timeout)
            if event == StopIteration:
                return
            yield event
            event.handled = False
