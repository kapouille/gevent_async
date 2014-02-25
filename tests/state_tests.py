from gevent import sleep
from async import state, StateValidationError
from unittest2 import TestCase

__author__ = 'ocarrere'


class TestState(TestCase):
    def test_state_started(self):
        class Object(object):
            def __init__(self):
                self.initial_reached = False

            @state
            def initial(self):
                self.initial_reached = True

        obj = Object()
        obj.initial()
        self.assertEqual(obj.initial_reached, False)
        sleep()
        self.assertEqual(obj.initial_reached, True)

    def test_chained_transitions(self):
        class Object(object):
            def __init__(self):
                self.reached = set()

            @state(transitions_to="second")
            def initial(self):
                self.reached.add("initial")
                self.second()

            @state
            def second(self):
                self.reached.add("second")

        obj = Object()
        obj.initial()
        all_states = set(["initial", "second"])
        self.assertNotEqual(obj.reached, all_states)
        # allow scheduling for the first state
        sleep()
        # allow scheduling for the second state
        sleep()
        self.assertEqual(obj.reached, all_states)

    def test_wrong_transition(self):
        class Object(object):
            def __init__(self, test):
                self.reached = set()
                self._test = test

            @state
            def initial(self):
                self.reached.add("initial")
                self._test.assertRaises(StateValidationError,
                                        self.second)

            @state
            def second(self):
                self.reached.add("second")

        obj = Object(self)
        obj.initial()
        self.assertNotIn("initial", obj.reached)
        self.assertNotIn("second", obj.reached)
        sleep()
        self.assertIn("initial", obj.reached)
        self.assertNotIn("second", obj.reached)

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

    def test_execution_started(self):
        def on_transition(new_state, target):
            target.state = new_state

        class Object(object):
            def __init__(self):
                self.state = None

            @state(on_start=on_transition)
            def a_state(self):
                pass

        obj = Object()
        obj.a_state()

        self.assertIsNotNone(obj.state)
        self.assertFalse(obj.state.execution_started.ready())

        sleep()

        self.assertTrue(obj.state.execution_started.ready())

