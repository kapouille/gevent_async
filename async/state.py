from functools import wraps
import logging

from gevent import Greenlet, getcurrent, GreenletExit, sleep
from gevent.event import Event


_LOG = logging.getLogger(__name__)
logging.basicConfig()


class ValidationError(Exception):
    pass


class State(Greenlet):

    def __init__(self, fun, transitions_out, *args, **kwargs):

        self._execution_started = Event()

        def once_started(*args, **kwargs):
            self._execution_started.set()
            fun(*args, **kwargs)

        self.name = fun.func_name
        once_started.func_name = self.name

        if transitions_out:
            if type(transitions_out) != list:
                transitions_out = [transitions_out]
        else:
            transitions_out = []
        self._transitions_out = transitions_out
        super(State, self).__init__(once_started, *args, **kwargs)

    def validate_transition(self, to_fun):
        name = to_fun.__name__
        if name not in self._transitions_out:
            raise ValidationError("Moving to invalid state "
                                  "{} from {}".format(name,
                                                      self.name))
    @property
    def execution_started(self):
        return self._execution_started


def state(function=None, transitions_to=None, on_start=None):
    def func_wrapper(fun):
        @wraps(fun)
        def spawn_state(*args, **kwargs):
            # bodge fix for https://github.com/surfly/gevent/issues/394
            # this will allow state handling code to catch pending
            # exception before it's too late
            sleep()

            current_state = getcurrent() if type(getcurrent()) == State else None

            if current_state:
                current_state.validate_transition(fun)

            new = State(fun, transitions_to, *args, **kwargs)
            new.start()
            if on_start:
                on_start(new, *args, **kwargs)
            _LOG.debug("Moving to state {}".format(new))
            if current_state:
                raise GreenletExit
        return spawn_state

    if not function:
        def waiting_for_func(fun):
            return func_wrapper(fun)
        return waiting_for_func

    else:
        return func_wrapper(function)
