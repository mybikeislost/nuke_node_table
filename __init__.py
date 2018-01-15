import logging

# python 3 compatibility
try:
    basestring
except NameError:
    basestring = str

logging.getLogger(__name__).addHandler(logging.NullHandler())