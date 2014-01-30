from gevent.event import AsyncResult
from .queue import EventQueue

class _AsyncCallEvent(object):
    def __init__(self, name, *args, **kwargs):
        self._name = name
        self._args = args
        self._kwargs = kwargs
        self._result = AsyncResult()

    def wait(self, timeout):
        return self._result.get(timeout=timeout)

    def execute(self, target):
        try:
            function = getattr(target, self._name)
            self._result.set(function(*self._args, **self._kwargs))
        except Exception as error:
            self._result.set_exception(error)


class _Async(object):
    class Handle(object):
        def __init__(self, target, name, timeout):
            self._name = name
            self._target = target
            self._timeout = timeout

        def __call__(self, *args, **kwargs):
            event = _AsyncCallEvent(self._name, *args, **kwargs)
            self._target.add_request(event)
            return event.wait(self._timeout)

    def __init__(self, target):
        self._target = target
        self._timeout = None

    def __call__(self, timeout=None):
        self._timeout = timeout
        return self

    def __getattr__(self, name):
        return self.Handle(self._target, name, self._timeout)


class AsyncCallHandler(object):
    def __init__(self):
        self._requests = EventQueue()
        self.async = _Async(self)

    def add_request(self, request):
        self._requests.put(request)

    def stop_processing(self):
        self._requests.put(StopIteration)

    def process(self, forever=False):
        for event in self._requests.all(until_empty=not forever):
            event.execute(self)
