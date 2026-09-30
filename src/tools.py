"""Domain-Specific Tools for Siemens Knowledge Fabric with Guided Error Recovery."""

from typing import Any, Dict, List
from src.observability import trace_intent_and_outcome
from src.schemas import (
    ArchitectureImpactReport,
    CodeDependencyNode,
    KnowledgeGraphQueryInput,
    KnowledgeGraphQueryOutput,
    ModernizationTask,
    UserStoryItem,
)

# Simulated Spanner Graph Knowledge Fabric dataset for immediate local demo execution
MOCK_SPANNER_GRAPH_DB: Dict[str, List[Dict[str, Any]]] = {
    "AxisControlPanel": [
        {
            "node_id": "fn_calc_torque_01",
            "node_type": "FUNCTION",
            "name": "CalculateAxisTorqueLimiter",
            "file_path": "legacy/motion_control/axis_panel.cpp",
            "linked_requirement_id": "REQ-2008-MOTION-441",
            "similarity_score": 0.96,
        },
        {
            "node_id": "fn_emergency_stop_02",
            "node_type": "FUNCTION",
            "name": "TriggerSafetyInterlockBus",
            "file_path": "legacy/safety/interlock_bus.cpp",
            "linked_requirement_id": "REQ-2004-SIL3-109",
            "similarity_score": 0.93,
        },
        {
            "node_id": "mod_webui_bridge_03",
            "node_type": "MODULE",
            "name": "AxisTelemetryWebSocketAdapter",
            "file_path": "modern_web/adapters/axis_ws_bridge.ts",
            "linked_requirement_id": "JIRA-MOD-8821",
            "similarity_score": 0.89,
        },
        {
            "node_id": "doc_pdf_manual_04",
            "node_type": "DESIGN_DOC",
            "name": "SIMATIC_Axis_Control_Spec_2006.pdf",
            "file_path": "gs://siemens-legacy-manuals/2006/SIMATIC_Axis_Control_Spec_2006.pdf",
            "linked_requirement_id": "REQ-2006-HMI-012",
            "similarity_score": 0.91,
        },
    ]
}


@trace_intent_and_outcome("traverse_spanner_code_graph_gql")
def traverse_spanner_code_graph_gql(
    component_name: str,
    search_mode: str = "HYBRID_GQL_ANN",
    max_hops: int = 2,
) -> Dict[str, Any]:
    """
    Traverses the Siemens Spanner Graph Knowledge Fabric using Graph Query Language (GQL),
    Approximate Nearest Neighbor (ANN) vector embeddings, and full-text keyword search.

    Purpose:
        Identifies upstream and downstream code dependencies, class-to-module hierarchies,
        and linked historical design documents (Jira, Confluence, scanned PDFs) for a
        target legacy industrial software component.

    Args:
        component_name (str): Name of the legacy software module or class to inspect
            (e.g., "AxisControlPanel" or "Axis Control Panel").
        search_mode (str): Retrieval mode. Must be one of "HYBRID_GQL_ANN", "GQL_ONLY",
            or "SEMANTIC_ANN_ONLY". Defaults to "HYBRID_GQL_ANN".
        max_hops (int): Number of graph relationship hops to traverse (1 to 5). Defaults to 2.

    Returns:
        Dict[str, Any]: Validated `KnowledgeGraphQueryOutput` dictionary containing
        the executed GQL statement, matched dependency nodes, and recovery instructions
        if the component was not found.
    """
    try:
        validated_input = KnowledgeGraphQueryInput(
            component_name=component_name,
            search_mode=search_mode,  # type: ignore[arg-type]
            max_hops=max_hops,
        )
    except Exception as validation_err:
        return KnowledgeGraphQueryOutput(
            status="RECOVERABLE_ERROR",
            target_component=component_name,
            gql_executed="NONE",
            dependencies=[],
            recovery_suggestion=(
                f"Input schema validation failed: {validation_err}. "
                "RECOVERY ACTION: Retry calling `traverse_spanner_code_graph_gql` with "
                "`component_name` as a non-empty string, `search_mode='HYBRID_GQL_ANN'`, "
                "and `max_hops` between 1 and 5."
            ),
        ).model_dump()

    normalized_key = validated_input.component_name.replace(" ", "")
    gql_query = (
        f"GRAPH SpannerCodeFabric MATCH (c:Component {{name: '{normalized_key}'}})"
        f"-[:CALLS|IMPLEMENTS|VERIFIED_BY*1..{validated_input.max_hops}]->(dep) "
        f"RETURN dep.node_id, dep.node_type, dep.name, dep.file_path, dep.linked_requirement_id"
    )

    matched_records = MOCK_SPANNER_GRAPH_DB.get(normalized_key)
    if not matched_records:
        available_keys = ", ".join(MOCK_SPANNER_GRAPH_DB.keys())
        return KnowledgeGraphQueryOutput(
            status="RECOVERABLE_ERROR",
            target_component=validated_input.component_name,
            gql_executed=gql_query,
            dependencies=[],
            recovery_suggestion=(
                f"Component '{validated_input.component_name}' returned 0 vertices in Spanner Graph. "
                f"RECOVERY ACTION: Retry `traverse_spanner_code_graph_gql` using one of the indexed "
                f"industrial modules ({available_keys}) or broaden `search_mode` to 'SEMANTIC_ANN_ONLY'."
            ),
        ).model_dump()

    nodes = [CodeDependencyNode(**record) for record in matched_records]
    return KnowledgeGraphQueryOutput(
        status="SUCCESS",
        target_component=normalized_key,
        gql_executed=gql_query,
        dependencies=nodes,
    ).model_dump()


@trace_intent_and_outcome("create_modernization_user_stories")
def create_modernization_user_stories(
    component_name: str,
    target_interface: str,
    linked_requirement_ids: List[str],
) -> Dict[str, Any]:
    """
    Generates traceable agile user stories with acceptance criteria linked to legacy
    Spanner Graph requirement nodes.

    Purpose:
        Used by the User Story Agent to translate product owner modernization goals
        into structured user stories anchored to 15-20 year industrial compliance specs.

    Args:
        component_name (str): Name of the legacy module being modernized.
        target_interface (str): Modern target architecture (e.g., "Web-Based React/TypeScript HMI").
        linked_requirement_ids (List[str]): Requirement IDs retrieved from Spanner Graph.

    Returns:
        Dict[str, Any]: Serialized list of `UserStoryItem` objects with acceptance criteria.
    """
    if not linked_requirement_ids:
        return {
            "status": "RECOVERABLE_ERROR",
            "recovery_suggestion": (
                "No `linked_requirement_ids` were provided. RECOVERY ACTION: Call "
                "`traverse_spanner_code_graph_gql` first to extract historical requirement IDs "
                "before generating user stories."
            ),
        }

    story = UserStoryItem(
        story_id="US-MOD-101",
        title=f"Migrate {component_name} to {target_interface}",
        as_a="Industrial Automation Operator",
        i_want=f"to control and monitor {component_name} via a responsive {target_interface}",
        so_that="legacy desktop HMI dependencies are eliminated without violating SIL-3 safety interlocks",
        acceptance_criteria=[
            "Preserve exact torque calculation parity with `CalculateAxisTorqueLimiter`.",
            "Maintain hardwired and software interlock verification for `TriggerSafetyInterlockBus`.",
            f"Verify full traceability against specs: {', '.join(linked_requirement_ids)}.",
        ],
        linked_graph_nodes=linked_requirement_ids,
    )
    return {"status": "SUCCESS", "user_stories": [story.model_dump()]}


@trace_intent_and_outcome("analyze_component_blast_radius")
def analyze_component_blast_radius(
    component_name: str,
    affected_function_names: List[str],
) -> Dict[str, Any]:
    """
    Evaluates architectural side effects and safety compliance blast radius prior to coding.

    Purpose:
        Used by the Architecture Impact Agent to predict downstream regressions across
        modules and flag mandatory Human-in-the-Loop (HITL) engineering approvals.

    Args:
        component_name (str): Target legacy component under analysis.
        affected_function_names (List[str]): Functions identified during graph traversal.

    Returns:
        Dict[str, Any]: Validated `ArchitectureImpactReport` dictionary.
    """
    if not affected_function_names:
        return {
            "status": "RECOVERABLE_ERROR",
            "recovery_suggestion": (
                "Cannot compute blast radius with an empty `affected_function_names` list. "
                "RECOVERY ACTION: Pass the function names returned by `traverse_spanner_code_graph_gql`."
            ),
        }

    report = ArchitectureImpactReport(
        component_under_change=component_name,
        affected_functions=affected_function_names,
        compliance_risks=[
            "IEC 61508 SIL-3 Safety Interlock timing constraints on `TriggerSafetyInterlockBus`",
            "20-year backward telemetry compatibility on `AxisTelemetryWebSocketAdapter`",
        ],
        estimated_blast_radius="HIGH",
        requires_hitl_signoff=True,
    )
    return {"status": "SUCCESS", "impact_report": report.model_dump()}


@trace_intent_and_outcome("decompose_into_atomic_refactoring_tasks")
def decompose_into_atomic_refactoring_tasks(
    component_name: str,
    affected_functions: List[str],
) -> Dict[str, Any]:
    """
    Slices a sweeping refactoring epic into small, context-complete implementation tasks.

    Purpose:
        Implements the core "Slicing the Elephant" pattern by ensuring the Coding Agent
        receives narrow, unambiguous, self-contained engineering tasks.

    Args:
        component_name (str): Name of the component being refactored.
        affected_functions (List[str]): Dependent functions requiring updates.

    Returns:
        Dict[str, Any]: List of serialized `ModernizationTask` objects.
    """
    tasks = [
        ModernizationTask(
            task_id=f"TASK-{idx + 1:03d}",
            title=f"Refactor & wrap `{fn_name}` for Web HMI compatibility",
            target_file=f"modern_web/controllers/{fn_name.lower()}.ts",
            context_summary=(
                f"Expose `{fn_name}` from `{component_name}` via strongly-typed gRPC/WebSocket "
                "contract while preserving legacy C++ safety invariants."
            ),
            verification_steps=[
                f"Run unit parity suite against legacy `{fn_name}` fixture.",
                "Verify zero regression on SIL-3 interlock latency (< 5ms).",
            ],
        ).model_dump()
        for idx, fn_name in enumerate(affected_functions)
    ]
    return {"status": "SUCCESS", "tasks": tasks}
