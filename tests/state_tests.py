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
