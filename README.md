gevent_async
============

A small set of utilities to help with writing synchronous code flows in an asynchronous context.

synchronous calls
-----------------

async.AsyncCallHandler allows controlling the execution of method calls in order to prevent contention issues in the context
of heavy greenlet usage.

For instance, imagining we have a Manager entity that must handle some resources in an atomic manner:
  from async import AsyncCallHandler
  class Manager(AsyncCallHandler):
      def manage(self):
          # do things with resources
          # with the assurance that the resources won't
          # be modified during process
          
          self.process() # process pending calls
          
          # do more things
          
      def messes_up_resources(self, modifications):
          # changes resources
          
      def run(self):
          while True:
              self.manage()

  
