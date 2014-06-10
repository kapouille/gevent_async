from functools import wraps
import logging
import collections
import gevent


_LOG = logging.getLogger(__name__)
logging.basicConfig()

_Params = collections.namedtuple('Params', ('args', 'kwargs'))


class StateValidationError(Exception):
    pass


class StateMachine(object):

    @staticmethod
    def state_coroutine(state_machine):
        while True:
            old_state, new_state = yield

    @staticmethod
    def create_state_coroutine(state_machine):
        cr = StateMachine.state_coroutine(state_machine)
        cr.send(None)
        return cr

    def __init__(self):
        self._state = None
        self._state_greenlet = None
        self._state_coroutine = self.create_state_coroutine(self)

    def do_transition(self, to_state, params):
        if self._state is None:
            _LOG.debug("Starting in state {!r} ({!r})".format(to_state, self))
        else:
            self._state.validate_transition(to_state)
            _LOG.debug("Moving to state {!r} ({!r})".format(to_state, self))

        # FIXME: bodge fix for https://github.com/surfly/gevent/issues/394
        #
        # Force a check for pending exceptions raised against this
        # thread/greenlet (e.g. from .kill())
        # We need to do this before we start another greenlet, otherwise we
        # can hide from the fatal exception
        gevent.sleep()

        (from_state, self._state, self._state_greenlet, old_greenlet) = (
            self._state,
            to_state,
            StateGreenlet(self, to_state, params),
            self._state_greenlet)

        self._state_coroutine.send((from_state, to_state))

        if old_greenlet and gevent.getcurrent() != old_greenlet:
            old_greenlet.kill()

        self._state_greenlet.start()

    def join(self, timeout=None):
        return self._state_greenlet.join(timeout=timeout)

    def ready(self):
        return self._state_greenlet.ready()

    def successful(self):
        return self._state_greenlet.successful()

    @property
    def exception(self):
        return self._state_greenlet.exception


class State(object):

    def __init__(self, function, transitions_to=None, on_start=None):
        self._function = function
        if transitions_to is None:
            transitions_to = []
        elif not isinstance(transitions_to, (tuple, list, set)):
            transitions_to = [transitions_to]
        self._transitions_out = frozenset(transitions_to)
        self._on_start = on_start

    @property
    def name(self):
        return self._function.func_name

    def validate_transition(self, to_state):
        if (self._transitions_out is not None
                and to_state.name not in self._transitions_out):
            raise StateValidationError(
                "Invalid state transition {} -> {}".format(
                    self.name, to_state.name))

    def __call__(self, *args, **kwargs):
        if self._on_start is not None:
            self._on_start(self, *args, **kwargs)
        return self._function(*args, **kwargs)

    def __repr__(self):
        return '<{0.__class__.__name__} {0._function!r}>'.format(self)


class StateGreenlet(gevent.Greenlet):

    def __init__(self, state_machine, state, params):
        self.state_machine = state_machine
        self.state = state
        super(StateGreenlet, self).__init__(state,
                                            *params.args,
                                            **params.kwargs)


def spawn_state(state, params):
    current_greenlet = gevent.getcurrent()
    is_state_greenlet = isinstance(current_greenlet, StateGreenlet)

    if is_state_greenlet:
        state_machine = current_greenlet.state_machine
    else:
        state_machine = StateMachine()

    state_machine.do_transition(to_state=state, params=params)

    # A StateGreenlet must exit immediately if they start a new state
    # greenlet
    if is_state_greenlet:
        raise gevent.GreenletExit()

    return state_machine


def state(function=None, transitions_to=None, on_start=None):
    def func_wrapper(fun):
        state = State(fun, transitions_to=transitions_to, on_start=on_start)

        @wraps(fun)
        def wrapped(*args, **kwargs):
            return spawn_state(state=state, params=_Params(args, kwargs))
        return wrapped

    if function is None:
        return func_wrapper
    else:
        return func_wrapper(function)
