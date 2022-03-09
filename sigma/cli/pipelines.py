from sigma.pipelines.sysmon import sysmon_pipeline
from sigma.pipelines.crowdstrike import crowdstrike_fdr_pipeline
from sigma.processing.resolver import ProcessingPipelineResolver

pipelines = ProcessingPipelineResolver({
    "sysmon": sysmon_pipeline,
    "crowdstrike_fdr": crowdstrike_fdr_pipeline,
})