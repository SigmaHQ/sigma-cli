from collections import namedtuple
from sigma.backends.splunk import SplunkBackend

Backend = namedtuple("Backend", ("cls", "text", "formats"))

backends = {
    "splunk": Backend(SplunkBackend, "Splunk", {
        "default": "Plain Splunk queries",
        "savedsearches": "Splunk savedsearches.conf"
    }),
}
