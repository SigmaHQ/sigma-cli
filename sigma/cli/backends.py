from collections import namedtuple
from sigma.backends.splunk import SplunkBackend
from sigma.backends.insight_idr import InsightIDRBackend

Backend = namedtuple("Backend", ("cls", "text", "formats"))

backends = {
    "splunk": Backend(SplunkBackend, "Splunk", {
        "default": "Plain Splunk queries",
        "savedsearches": "Splunk savedsearches.conf",
        "data_model": "Splunk CIM data model tstats queries",
    }),
    "insightidr": Backend(InsightIDRBackend, "Rapid7 InsightIDR", {
        "default": "Simple queries",
        "leql_advanced_search": "Advanced queries",
        "leql_detection_definition": "LEQL detection rule logic format",
    }),
}
