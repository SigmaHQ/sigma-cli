from collections import namedtuple
from sigma.pipelines.sysmon import sysmon_pipeline
from sigma.pipelines.crowdstrike import crowdstrike_fdr_pipeline
from sigma.pipelines.splunk import splunk_windows_pipeline, splunk_windows_sysmon_acceleration_keywords, splunk_cim_data_model
from sigma.pipelines.windows import windows_pipeline
from sigma.pipelines.elasticsearch.windows import ecs_windows, ecs_windows_old
from sigma.pipelines.elasticsearch.zeek import ecs_zeek_beats, ecs_zeek_corelight, zeek_raw
from sigma.processing.resolver import ProcessingPipelineResolver

Pipeline = namedtuple("Pipeline", ("generator", "backends"))    # Describes a pipeline

pipelines = {
    "sysmon": Pipeline(sysmon_pipeline, ()),
    "crowdstrike_fdr": Pipeline(crowdstrike_fdr_pipeline, ()),
    "splunk_windows": Pipeline(splunk_windows_pipeline, ("splunk",)),
    "splunk_sysmon_acceleration": Pipeline(splunk_windows_sysmon_acceleration_keywords, ("splunk",)),
    "splunk_cim": Pipeline(splunk_cim_data_model, ("splunk",)),
    "ecs_windows": Pipeline(ecs_windows, ("elasticsearch", "opensearch")),
    "ecs_windows_old": Pipeline(ecs_windows_old, ("elasticsearch", "opensearch")),
    "ecs_zeek_beats": Pipeline(ecs_zeek_beats, ("elasticsearch", "opensearch")),
    "ecs_zeek_corelight": Pipeline(ecs_zeek_corelight, ("elasticsearch", "opensearch")),
    "zeek": Pipeline(zeek_raw, ()),
    "windows": Pipeline(windows_pipeline, ()),
}

pipeline_resolver = ProcessingPipelineResolver({
    identifier: pipeline.generator
    for identifier, pipeline in pipelines.items()
})