from functools import wraps
import logging
from gevent import Greenlet, getcurrent, GreenletExit

_LOG = logging.getLogger(__name__)
logging.basicConfig()
logging.root.setLevel(logging.DEBUG)


class ValidationError(Exception):
    pass

class State(Greenlet):
    def __init__(self, fun, transitions_out, *args, **kwargs):
        self._name = fun.__name__
        if transitions_out:
            if type(transitions_out) != list:
                transitions_out = [transitions_out]
        else:
            transitions_out = []
        self._transitions_out = transitions_out
        super(State, self).__init__(fun, *args, **kwargs)

    def validate_transition(self, to_fun):
        name = to_fun.__name__
        if name not in self._transitions_out:
            raise ValidationError("Moving to invalid state "
                                  "{} from {}".format(name,
                                                      self._name))

    def __str__(self):
        return "<State name={}>".format(self._name)


def state(function=None, transitions_to=None):
    def func_wrapper(fun):
        @wraps(fun)
        def spawn_state(*args, **kwargs):
            current_state = getcurrent() if type(getcurrent()) == State else None

            if current_state:
                current_state.validate_transition(fun)

            new = State(fun, transitions_to, *args, **kwargs)
            new.start()
            _LOG.debug("Launching state %s", new._name)
            if current_state:
                _LOG.debug("Leaving state %s", current_state._name)
                raise GreenletExit
        return spawn_state

    if not function:
        def waiting_for_func(fun):
            return func_wrapper(fun)
        return waiting_for_func

    else:
        return func_wrapper(function)

    return func_wrapper
