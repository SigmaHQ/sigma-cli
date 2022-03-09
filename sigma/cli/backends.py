from collections import namedtuple
from sigma.backends.splunk import SplunkBackend

Backend = namedtuple("Backend", ("cls", "text"))

backends = {
    "splunk": Backend(SplunkBackend, "Splunk"),
}