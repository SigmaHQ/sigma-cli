from sigma.pipelines.sysmon import sysmon_pipeline
from sigma.pipelines.crowdstrike import crowdstrike_fdr_pipeline
from sigma.pipelines.splunk import splunk_windows_pipeline, splunk_windows_sysmon_acceleration_keywords, splunk_cim_data_model
from sigma.pipelines.windows import windows_pipeline
from sigma.processing.resolver import ProcessingPipelineResolver

pipelines = ProcessingPipelineResolver({
    "sysmon": sysmon_pipeline,
    "crowdstrike_fdr": crowdstrike_fdr_pipeline,
    "splunk_windows": splunk_windows_pipeline,
    "splunk_sysmon_acceleration": splunk_windows_sysmon_acceleration_keywords,
    "splunk_cim": splunk_cim_data_model,
    "windows": windows_pipeline,
})