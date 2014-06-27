from gevent.event import AsyncResult
from .queue import EventQueue
from logging import getLogger

_LOG = getLogger(__name__)


class _SyncCall(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self._args = args
        self._kwargs = kwargs
        self._result = AsyncResult()

    def wait(self, timeout):
        return self._result.get(timeout=timeout)

    def execute(self, target):
        try:
            function = getattr(target, self.name)
            self._result.set(function(*self._args, **self._kwargs))
        except Exception as error:
            self._result.set_exception(error)


class _Sync(object):
    class Handle(object):
        def __init__(self, target, name, timeout):
            self._name = name
            self._target = target
            self._timeout = timeout

        def __call__(self, *args, **kwargs):
            event = _SyncCall(self._name, *args, **kwargs)
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


class _OnewayCall(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self._args = args
        self._kwargs = kwargs

    def execute(self, target):
        try:
            function = getattr(target, self.name)
            function(*self._args, **self._kwargs)
        except Exception as error:
            _LOG.exception("Oneway call of {} on {} "
                           "failed with error: {}".format(self.name,
                                                          target,
                                                          error))


class _OneWay(object):
    class Handle(object):
        def __init__(self, target, name):
            self._name = name
            self._target = target

        def __call__(self, *args, **kwargs):
            event = _OnewayCall(self._name, *args, **kwargs)
            self._target.add_request(event)

    def __init__(self, target):
        self._target = target

    def __call__(self):
        return self

    def __getattr__(self, name):
        return self.Handle(self._target, name)


class DeferredCallHandler(object):
    def __init__(self):
        self._requests = EventQueue()
        self.sync = _Sync(self)
        self.oneway = _OneWay(self)

    def add_request(self, request):
        self._requests.put(request)

    def stop_processing(self):
        self._requests.put(StopIteration)

    def process(self, forever=False, whitelist=None):
        for event in self._requests.all(until_empty=not forever):
            if not whitelist or event.name in whitelist:
                event.execute(self)
