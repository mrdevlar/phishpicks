from importlib import metadata

__version__ = metadata.version(__name__)

from .configuration import Configuration
from .data import PhishData
