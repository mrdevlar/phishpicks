from importlib import metadata

__version__ = metadata.version(__name__)

from .configuration import Configuration
from .data import PhishData, Show, Track
from .picks import PhishPicks
from .repl import PhishREPL
