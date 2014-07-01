__author__ = 'ocarrere'

from .call import DeferredCallHandler
from .queue import EventQueue, Event
from .state import state
from .state import StateValidationError

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
