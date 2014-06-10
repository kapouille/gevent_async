from gevent import sleep, monkey
monkey.patch_all()
from unittest2 import TestCase
from async.state import state, StateValidationError, StateMachine
from contextlib import contextmanager
import mock
import collections
import itertools
import logging
from Queue import Queue, Empty


_LOG = logging.getLogger(__name__)


class TestState(TestCase):

    @contextmanager
    def transition_tracking(self):
        transitions = collections.defaultdict(lambda: Queue(maxsize=1))

        def tracker(state_machine):
            while True:
                from_to = yield
                transitions[state_machine].put(from_to, block=True)

        with mock.patch.object(StateMachine, 'state_coroutine', new=tracker):
            yield transitions

    def assertTransitions(self,
                          state_machine,
                          expected_states,
                          transition_queue):
        chain = iter(expected_states), iter(expected_states)
        chain[1].next()
        try:
            for expected_transition in itertools.izip(*chain):
                trans = transition_queue.get(block=True, timeout=.01)
                _LOG.debug("Observed transition: %r", trans)
                self.assertEqual(
                    expected_transition,
                    # Convert state objects to their names (may be null)
                    tuple(s and s.name for s in trans),
                )
        except Empty:
            raise AssertionError(
                "Failed to observe state transition: {}".format(
                    expected_transition))

        state_machine.join(timeout=.01)
        self.assertTrue(state_machine.ready())
        self.assertTrue(transition_queue.empty())

    def test_state_started(self):
        class Object(object):
            def __init__(self):
                self.initial_reached = False

            @state
            def initial(self):
                self.initial_reached = True

        obj = Object()
        self.assertEqual(obj.initial_reached, False)
        obj.initial()
        self.assertEqual(obj.initial_reached, False)
        sleep()
        self.assertEqual(obj.initial_reached, True)

    def test_chained_transitions(self):
        class Object(object):

            @state(transitions_to="second")
            def initial(self):
                self.second()

            @state(transitions_to="third")
            def second(self):
                self.third()

            @state
            def third(self):
                pass

        with self.transition_tracking() as transition_map:
            obj = Object()

            self.assertFalse(transition_map)
            obj.initial()

            self.assertEqual(len(transition_map), 1)
            state_machine, transition_queue = transition_map.items()[0]
            self.assertTransitions(
                state_machine,
                [None, 'initial', 'second', 'third'],
                transition_queue)

            self.assertTrue(state_machine.successful())
            self.assertEqual(len(transition_map), 1)

    def test_transition_cycle(self):
        class Object(object):
            def __init__(self):
                self.count = 0

            @state(transitions_to="bar")
            def foo(self):
                self.bar()

            @state(transitions_to="foo")
            def bar(self):
                if self.count < 10:
                    self.count += 1
                    self.foo()

        with self.transition_tracking() as transition_map:
            obj = Object()

            self.assertFalse(transition_map)
            obj.foo()

            self.assertEqual(len(transition_map), 1)
            state_machine, transition_queue = transition_map.items()[0]
            self.assertTransitions(
                state_machine,
                [None] + ['foo', 'bar'] * (1 + 10),
                transition_queue)
            self.assertTrue(state_machine.successful())

            self.assertEqual(len(transition_map), 1)

    def test_wrong_transition(self):
        class Object(object):
            @state(transitions_to="second")
            def initial(self):
                self.second()

            @state()
            def second(self):
                self.third()

            @state
            def third(self):
                pass

        with self.transition_tracking() as transition_map:
            obj = Object()

            self.assertFalse(transition_map)
            obj.initial()

            self.assertEqual(len(transition_map), 1)

            state_machine, transition_queue = transition_map.items()[0]
            self.assertTransitions(
                state_machine,
                [None, 'initial', 'second'],
                transition_queue)

            sleep()
            self.assertEqual(len(transition_map), 1)
            self.assertFalse(state_machine.successful())
            self.assertIsInstance(state_machine.exception,
                                  StateValidationError)

    def test_callback(self):
        def on_transition(new_state, target, *args, **kwargs):
            if "store" in kwargs and kwargs["store"]:
                target.state = new_state

        class Object(object):
            def __init__(self):
                self.state = None

            @state(on_start=on_transition)
            def a_state(self, store=False):
                pass

        obj = Object()
        obj.a_state(store=True)
        sleep()
        self.assertIsNotNone(obj.state)
        obj.state = None
        obj.a_state(store=False)
        sleep()
        self.assertIsNone(obj.state)
