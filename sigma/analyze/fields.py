"""Extract field names from Sigma rules."""
from __future__ import annotations

from operator import add
from typing import List, Set, Tuple
from sigma.rule import SigmaRule, SigmaDetection, SigmaDetectionItem
from sigma.collection import SigmaCollection
from sigma.correlations import SigmaCorrelationRule
from sigma.exceptions import SigmaError, SigmaPlaceholderError
from sigma.modifiers import SigmaExpandModifier
from sigma.types import SigmaString
from sigma.processing.pipeline import ProcessingPipeline


def get_fields(
    backend,
    rule: SigmaRule | SigmaCorrelationRule,
    collect_errors: bool = True,
) -> Tuple[List[str], List[SigmaError]]:
    """Extract field names from a Sigma rule.
    
    Args:
        backend: A Backend instance used to escape and quote field names
        rule: A SigmaRule or SigmaCorrelationRule to extract fields from
        collect_errors: Whether to collect errors. Defaults to True.
    
    Returns:
        Tuple[List[str], List[SigmaError]]: A list of fields and any errors found
    """
    fields: List[str] = []
    errors: List[SigmaError] = []
    
    def noop(field: str) -> str:
        """A no-op function that returns the field as-is."""
        return field
    
    # Get the field escaper from the backend
    escape_and_quote_field = getattr(backend, "escape_and_quote_field", lambda x: x)
    if not callable(escape_and_quote_field):
        escape_and_quote_field = noop
    
    if isinstance(rule, SigmaRule):
        if not rule.detection:
            return fields, errors
        
        # Extract fields from each detection
        for key in frozenset(rule.detection.detections.keys()):
            _fields, _errors = _get_fields_from_detection_items(
                backend,
                rule.detection.detections[key].detection_items,
                collect_errors,
            )
            fields.extend(_fields)
            errors.extend(_errors)
    
    elif isinstance(rule, SigmaCorrelationRule):
        # Handle correlation rules
        if rule.group_by:
            fields.extend([escape_and_quote_field(field) for field in rule.group_by])
        
        # Handle aliases
        if rule.aliases:
            aliases_to_remove = set()
            for field_alias in rule.aliases:
                esc_field_alias = escape_and_quote_field(field_alias.alias)
                if esc_field_alias in fields:
                    aliases_to_remove.add(esc_field_alias)
                    fields.extend([
                        escape_and_quote_field(field)
                        for field in field_alias.mapping.values()
                    ])
            fields = [f for f in fields if f not in aliases_to_remove]
    
    return fields, errors


def _get_fields_from_detection_items(
    backend,
    detection_items: List[SigmaDetectionItem | SigmaDetection],
    collect_errors: bool = True,
) -> Tuple[List[str], List[SigmaError]]:
    """Extract fields from detection items recursively.
    
    Args:
        backend: A Backend instance used to escape and quote field names
        detection_items: A list of SigmaDetectionItem or SigmaDetection
        collect_errors: Whether to collect errors. Defaults to True.
    
    Returns:
        Tuple[List[str], List[SigmaError]]: A list of fields and any errors found
    """
    fields: List[str] = []
    errors: List[SigmaError] = []
    
    def noop(field: str) -> str:
        """A no-op function that returns the field as-is."""
        return field
    
    escape_and_quote_field = getattr(backend, "escape_and_quote_field", lambda x: x)
    if not callable(escape_and_quote_field):
        escape_and_quote_field = noop
    
    for di in detection_items:
        if isinstance(di, SigmaDetectionItem) and hasattr(di, "field") and di.field:
            if collect_errors:
                # Check for unexpanded placeholders
                has_placeholder_modifier = any(
                    [
                        is_sem
                        for mod in di.modifiers
                        if (is_sem := issubclass(mod, SigmaExpandModifier))
                    ]
                )
                has_placeholder_value = any(
                    [
                        is_placeholder
                        for val in di.value
                        if (
                            is_placeholder := isinstance(val, SigmaString)
                            and (
                                hasattr(val, "contains_placeholder")
                                and val.contains_placeholder()
                            )
                        )
                    ]
                )
                if all([has_placeholder_modifier, has_placeholder_value]):
                    errors.append(
                        SigmaPlaceholderError(
                            "Cannot extract fields from Sigma rule with unexpanded placeholders."
                        )
                    )
            fields.append(escape_and_quote_field(di.field))
        elif isinstance(di, SigmaDetection):
            # Recursively extract fields from nested detections
            _fields, _errors = _get_fields_from_detection_items(
                backend, di.detection_items, collect_errors
            )
            fields.extend(_fields)
            errors.extend(_errors)
    
    return fields, errors


def extract_fields_from_collection(
    collection: SigmaCollection,
    backend,
    collect_errors: bool = True,
) -> Tuple[Set[str], List[SigmaError]]:
    """Extract all unique field names from a Sigma collection.
    
    Args:
        collection: A SigmaCollection to extract fields from
        backend: A Backend instance used to escape and quote field names
        collect_errors: Whether to collect errors. Defaults to True.
    
    Returns:
        Tuple[Set[str], List[SigmaError]]: A set of unique field names and any errors found
    """
    all_fields: Set[str] = set()
    all_errors: List[SigmaError] = []
    
    for rule in collection:
        # Try to apply any processing pipelines if available
        last_processing_pipeline = getattr(rule, "last_processing_pipeline", None)
        if not last_processing_pipeline:
            backend_processing_pipeline = (
                getattr(backend, "backend_processing_pipeline", None) or None
            )
            processing_pipeline = getattr(backend, "processing_pipeline", None) or None
            output_format_processing_pipeline = (
                getattr(backend, "output_format_processing_pipeline", None) or None
            )
            
            if output_format_processing_pipeline and isinstance(output_format_processing_pipeline, dict):
                output_format_processing_pipeline = (
                    output_format_processing_pipeline.get(
                        getattr(backend, "format", "default")
                    )
                )
            
            if backend_processing_pipeline is None:
                backend_processing_pipeline = ProcessingPipeline()
            if processing_pipeline is None:
                processing_pipeline = ProcessingPipeline()
            if output_format_processing_pipeline is None:
                output_format_processing_pipeline = ProcessingPipeline()
            
            last_processing_pipeline = add(
                backend_processing_pipeline,
                add(processing_pipeline, output_format_processing_pipeline),
            )
        
        # Apply the processing pipeline to the rule
        try:
            rule = last_processing_pipeline.apply(rule)
        except Exception:
            # If pipeline application fails, continue with the rule as-is
            pass
        
        # Extract fields from the rule
        fields, errors = get_fields(backend, rule, collect_errors)
        all_fields.update(fields)
        all_errors.extend(errors)
    
    return all_fields, all_errors

