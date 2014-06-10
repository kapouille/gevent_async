============
gevent_async
============

A small set of utilities to help with writing synchronous code flows in a collaborative multitasking context.
It has been designed around the feature set of gevent (http://www.gevent.org)

--------------
deferred calls
--------------

``async.DeferredCallHandler`` is a wrapper for asynchronously handled function calls.
This allows to control in which context the execution of those functions are done, which is essential
in collaborative multitasking.

There are 2 available types of calls:
    - ``sync`` (synchronous): this type of call awaits for the deferred call handle to process the call
      to return. for a user's perspective, it behaves like a regular function call.
    - ``oneway`` (one way): this type of call returns instantly. Due to its nature, there is no way to know
      whether, once it has been processed, it has succeeded or failed.

Example
=======

For instance, imagining we have a Manager entity that must handle some resources in an atomic manner:

.. code-block:: python

    from async import DeferredCallHandler
    class Manager(DeferredCallHandler):
        def manage(self):
            # do things with resources
            # with the assurance that the resources won't
            # be modified during process

            self.process() # process pending calls

            # do more things

        def access_resources(self):
            #returns the resources the manager has properly managed.

        def update_resource(self, data):
            #updates a resource info

        def run(self):
            while True:
                self.manage()

We can startup the manager and call functions on it from multiple greenlets:

.. code-block:: python

    manager = Manager()
    gevent.spawn(manager.run)
    # At that point, the manager entity is will be doing resource management

    resources = ... # we have an array of resources

    def monitor(target):
        for event in target.events():
            # we could apply some transformation to the event, and then
            # forward it to the manager.
            manager.oneway.update_resource(event)

    for resource in resources:
        gevent.spawn(monitor, resource)


    def consumer():
        while True:
            resources = manager.access_resources()
            # at that point, we have the guarantee that the resources
            # are properly managed and will not become stale or corrupted during process.

    consumer()

DeferredCallHandler API documentation
=====================================

* ``def process(forever=False, whitelist=None)``:

  Processes all the the pending deferred calls.

  If ``forever`` is set to ``True``, process will remain waiting for new calls until
  a call to ``stop_processing()`` is performed.

  If ``whitelist`` is set as a list of string, only functions which names match the elements
  in the white list will be executed.

* ``def stop_processing()``:

  Interrupts the iteration through incoming calls of a DeferredCallHandler's call to
  ``process(forever=True)``.

Exceptions
==========

sync calls will forward exceptions just like regular functions:

.. code-block:: python

    from async import DeferredCallHandler
    class Lemming(DeferredCallHandler):
        def kaboom(self):
            raise Exception("#high pitched# oh no!")

    lemming = Lemming()

    spawn(lemming.process, forever=True)

    try:
        lemming.sync.kaboom()
    except Exception:
        pass # We should hit that

    # This should trigger the exception but produce an exception log entry.
    lemming.oneway.kaboom()

Regular function calls
======================

``DeferredCallHandler`` objects don't prevent direct function calls. Use at your own risk:

.. code-block:: python

    from async import DeferredCallHandler
    class Manager(DeferredCallHandler):
        def manage(self):
            # do things with resources
            # with the assurance that the resources won't
            # be modified during process

            self.process() # process pending calls

            # do more things

        def access_resources(self):
            #returns the resources the manager has properly managed.

        def update_resource(self, data):
            #updates a resource info

        def run(self):
            while True:
                self.manage()

    manager = Manager()
    gevent.spawn(manager.run)

    resources = manager.access_resources()
    # !!! The resources may be in the middle of a management process and their state
    # may be incoherent

    resources = manager.sync.access_resources()
    # In that case, we're guaranteed the management process is not running.

Timeouts
========

``sync`` calls can be specified with an optional timeout, to ensure actions are performed
within a given time frame:

.. code-block:: python

    from async import DeferredCallHandler
    class ABitSlow(DeferredCallHandler):
        def taking_my_time(self):
            gevent.sleep(10)

    slow = ABitSlow()

    spawn(slow.process, forever=True)

    try:
        slow.sync(timeout=1).taking_my_time()
    except gevent.Timeout:
        pass # We should hit that

------------------------
multitask state handling
------------------------

Partially inspired by the mechanism of tail recursion, we provide a way to contain and handle code
to manage the behaviour of state machines within greenlets.

The ``@state`` decorator transforms a function method into a state greenlet. When another state function
is invoked, it create a new state greenlet that replaces the current state greenlet, effectively replicating
the behaviour of tail recursion.

For instance:

.. code-block:: python

    @state(transitions_to="growing")
    def sprouting()
        # germination process here
        growing() # the sprouting greenlet terminates and leaves way to the growing one

    @state(transitions_to="flowering")
    def growing()
        # transform CO2 and sunlight to biomass
        flowering() # the growing greenlet terminates and leaves way to the flowering one

    @state(transitions_to=["dead", "withering"])
    def flowering()
        # Grow flowers
        if is_eaten:
            # parameters can be given to state changes.
            dead(is_eaten=True) # the flowering greenlet terminates and leaves way to the dead one
        else:
            withering() # the flowering greenlet terminates and leaves way to the withering one

    @state(transitions_to="dead")
    def withering()
        # Dry up
        dead() # the withering greenlet terminates and leaves way to the dead one

    @state # terminal state, no transitions
    def dead(is_eaten=False)
        if not is_eaten:
            # clean up phase


    sprouting() # spawns the initial state

The ``@state`` decorator can also be used for methods:

.. code-block:: python

    class Flower(object):
        @state(transitions_to="growing")
        def sprouting(self)
            # germination process here
            growing() # the sprouting greenlet terminates and leaves way to the growing one

        # ...

Correct transitions must be specified by the ``transitions_to`` parameter or any incorrect transition
will raise the ``ValidationError`` exception.

Callbacks
=========

Callbacks can be defined on transition. By setting the on_start parameter to a state, a given callback will
be activated whenever a state is started.

The expected callback signature is ``def on_start(state, *args, **kwargs)``, where ``state`` is the
(at that point, still not started) ``async.state.State`` state greenlet which will handle the execution of the state and
``*args`` and ``**kwargs`` are the parameters given to the state call.

For instance:

.. code-block:: python

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

    obj.state # => is now storing the current state object.

