from collections import namedtuple
from sigma.backends.splunk import SplunkBackend
from sigma.backends.insight_idr import InsightIDRBackend
from sigma.backends.qradar import QradarBackend
from sigma.backends.elasticsearch import LuceneBackend
from sigma.backends.opensearch import OpensearchLuceneBackend

Backend = namedtuple("Backend", ("cls", "text", "formats", "requires_pipeline"))

backends = {
    "splunk": Backend(SplunkBackend, "Splunk", {
        "default": "Plain Splunk queries",
        "savedsearches": "Splunk savedsearches.conf",
        "data_model": "Splunk CIM data model tstats queries",
    }, True),
    "insightidr": Backend(InsightIDRBackend, "Rapid7 InsightIDR", {
        "default": "Simple queries",
        "leql_advanced_search": "Advanced queries",
        "leql_detection_definition": "LEQL detection rule logic format",
    }, False),
    "qradar": Backend(QradarBackend, "IBM QRadar", {
        "default": "Plain QRadar AQL queries",
        "extension": "QRadar extensions ZIP package",
    }, False),
    "elasticsearch": Backend(LuceneBackend, "Elasticsearch Lucene", {
        "default": "Plain Elasticsearch Lucene queries",
        "kibana_ndjson": "Kibana NDJSON import file with Lucene queries",
        "dsl_lucene": "Elasticsearch query DSL with embedded Lucene queries",
    }, True),
    "opensearch": Backend(OpensearchLuceneBackend, "OpenSearch Lucene", {
        "default": "Plain Elasticsearch Lucene queries",
        "dashboards_ndjson": "OpenSearch Dashboards NDJSON import file with Lucene queries",
        "monitor_rule": "OpenSearch monitor rule with embedded Lucene query",
        "dsl_lucene": "OpenSearch query DSL with embedded Lucene queries",
    }, True),
}
