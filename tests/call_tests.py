from gevent import sleep, spawn, Timeout
from async import DeferredCallHandler
from unittest2 import TestCase


class TestDeferredCalls(TestCase):

    def test_call(self):
        class Handler(DeferredCallHandler):
            def __init__(self):
                super(Handler, self).__init__()
                self.executed = False
                self.args = None
                self.kwargs = None

            def do_something(self):
                self.executed = True

            def do_something_with_params(self, *args, **kwargs):
                self.executed = True
                self.args = args
                self.kwargs = kwargs

        handler = Handler()
        handler.do_something()
        self.assertTrue(handler.executed)

        handler = Handler()
        spawn(handler.process, forever=True)
        handler.sync.do_something()
        self.assertTrue(handler.executed)
        handler.stop_processing()

        handler = Handler()
        spawn(handler.process, forever=True)
        handler.sync.do_something_with_params("1", 2, three=[3])
        self.assertTrue(handler.executed)
        self.assertEquals(handler.args, ("1", 2))
        self.assertEquals(handler.kwargs, dict(three=[3]))
        handler.stop_processing()

    def test_return_value(self):
        class Handler(DeferredCallHandler):
            def the_answer_to_the_universe_and_everything(self):
                return 42
        handler = Handler()
        spawn(handler.process, forever=True)
        answer = handler.sync.the_answer_to_the_universe_and_everything()
        self.assertEqual(answer, 42)
        handler.stop_processing()

    def test_exception(self):
        class Kaboom(Exception):
            pass

        class Handler(DeferredCallHandler):
            def kaboom(self):
                raise Kaboom()

        handler = Handler()
        spawn(handler.process, forever=True)
        self.assertRaises(Kaboom,
                          handler.sync.kaboom)
        handler.stop_processing()

    def test_timeout(self):
        class Handler(DeferredCallHandler):
            def about_right(self):
                sleep(.01)

            def takes_too_long(self):
                sleep(1)

        handler = Handler()
        spawn(handler.process, forever=True)
        handler.sync(timeout=.1).about_right()

        self.assertRaises(Timeout,
                          handler.sync(timeout=.1).takes_too_long)
        handler.stop_processing()

    def test_oneway(self):
        class Handler(DeferredCallHandler):
            def __init__(self):
                super(Handler, self).__init__()
                self.executed = False
                self.args = None
                self.kwargs = None

            def do_something_with_params(self, *args, **kwargs):
                self.executed = True
                self.args = args
                self.kwargs = kwargs
                return

            def kaboom(self):
                raise Exception()

            def the_answer_to_the_universe_and_everything(self):
                return 42

        handler = Handler()
        spawn(handler.process, forever=True)
        handler.oneway.do_something_with_params("1", 2, three=[3])
        # it shouldn't execute until we yield.
        self.assertFalse(handler.executed)
        sleep()
        self.assertTrue(handler.executed)
        self.assertEquals(handler.args, ("1", 2))
        self.assertEquals(handler.kwargs, dict(three=[3]))

        # ensure no exception is thrown
        handler.oneway.kaboom()
        sleep()

        # ensure it doesn't return anything
        result = handler.oneway.the_answer_to_the_universe_and_everything()
        self.assertIsNone(result)

        handler.stop_processing()
