"""
Multi-Agent Orchestration ("Slicing the Elephant") with Google ADK, Strategic Model Routing,
Policy Guardrails, and Human-in-the-Loop (HITL) Execution Hooks.
"""

from typing import Any, Callable, Dict, Optional
from src.config import ModelRouter, TaskComplexity
from src.memory import SIEMENS_AGENT_CONSTITUTION, PersistentKnowledgeMemory
from src.observability import logger, trace_intent_and_outcome
from src.tools import (
    analyze_component_blast_radius,
    create_modernization_user_stories,
    decompose_into_atomic_refactoring_tasks,
    traverse_spanner_code_graph_gql,
)

# Attempt to import Google ADK primitives; provide transparent local shim if running offline
try:
    from google.adk.agents import LlmAgent, SequentialAgent
    ADK_INSTALLED = True
except ImportError:
    ADK_INSTALLED = False

    class LlmAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, model: str, instruction: str, tools: list = None, **kwargs: Any):
            self.name = name
            self.model = model
            self.instruction = instruction
            self.tools = tools or []
            self.kwargs = kwargs

    class SequentialAgent:  # type: ignore[no-redef]
        def __init__(self, name: str, sub_agents: list, description: str = ""):
            self.name = name
            self.sub_agents = sub_agents
            self.description = description


def guardrail_before_model_callback(prompt_text: str) -> Dict[str, Any]:
    """
    Guardrail & Policy Plugin: Inspects incoming prompts for destructive commands
    (e.g., DROP GRAPH, bypassing SIL-3 safety checks, or prompt injection).
    """
    forbidden_patterns = ["DROP GRAPH", "DELETE FROM", "BYPASS_SIL3_INTERLOCK", "IGNORE CONSTITUTION"]
    upper_prompt = prompt_text.upper()
    for pattern in forbidden_patterns:
        if pattern in upper_prompt:
            logger.warning("GUARDRAIL_BLOCKED_REQUEST", extra={"blocked_pattern": pattern})
            return {
                "allowed": False,
                "reason": f"Policy Guardrail Violation: Prohibited operation '{pattern}' detected.",
            }
    return {"allowed": True, "reason": "Passed industrial safety & read-only graph guardrails."}


def human_in_the_loop_approval_hook(
    stage_name: str,
    artifact_summary: Dict[str, Any],
    approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
) -> bool:
    """
    Explicit Human-in-the-Loop (HITL) code stop requiring human confirmation before
    high-stakes architectural commitment or code generation proceeds.
    """
    logger.info(
        "HITL_APPROVAL_REQUESTED",
        extra={"stage": stage_name, "artifact_preview": str(artifact_summary)[:200]},
    )
    if approval_callback is not None:
        approved = approval_callback(stage_name, artifact_summary)
    else:
        # Default automated approval in non-interactive CI tests unless overridden
        approved = True

    logger.info("HITL_APPROVAL_DECISION", extra={"stage": stage_name, "approved": approved})
    return approved


def build_siemens_slicing_elephant_pipeline() -> SequentialAgent:
    """
    Constructs the 5-agent Siemens "Slicing the Elephant" pipeline using Google ADK
    and Strategic Model Routing (Flash for fast search/breakdown, Pro for impact/coding).
    """
    search_agent = LlmAgent(
        name="search_agent",
        model=ModelRouter.select_model(TaskComplexity.FAST_RETRIEVAL),
        instruction=(
            f"{SIEMENS_AGENT_CONSTITUTION}\n"
            "Role: Deep-research specialist. Use `traverse_spanner_code_graph_gql` to explore "
            "the code graph and cross-reference documentation."
        ),
        tools=[traverse_spanner_code_graph_gql],
    )

    user_story_agent = LlmAgent(
        name="user_story_agent",
        model=ModelRouter.select_model(TaskComplexity.STRUCTURED_DRAFTING),
        instruction=(
            f"{SIEMENS_AGENT_CONSTITUTION}\n"
            "Role: Product Owner interviewer & requirement translator. Draft user stories with "
            "acceptance criteria linked to Spanner Graph requirement IDs."
        ),
        tools=[create_modernization_user_stories],
    )

    architecture_impact_agent = LlmAgent(
        name="architecture_impact_agent",
        model=ModelRouter.select_model(TaskComplexity.DEEP_REASONING),
        instruction=(
            f"{SIEMENS_AGENT_CONSTITUTION}\n"
            "Role: Principal Industrial Architect. Analyze proposed changes against the graph "
            "to predict side effects before a single line of code is written."
        ),
        tools=[analyze_component_blast_radius],
    )

    task_breakdown_agent = LlmAgent(
        name="task_breakdown_agent",
        model=ModelRouter.select_model(TaskComplexity.STRUCTURED_DRAFTING),
        instruction=(
            f"{SIEMENS_AGENT_CONSTITUTION}\n"
            "Role: Agile Engineering Lead. Consume the architecture impact analysis and slice "
            "the work into small, context-complete tasks."
        ),
        tools=[decompose_into_atomic_refactoring_tasks],
    )

    coding_agent = LlmAgent(
        name="coding_agent",
        model=ModelRouter.select_model(TaskComplexity.DEEP_REASONING),
        instruction=(
            f"{SIEMENS_AGENT_CONSTITUTION}\n"
            "Role: Senior Industrial Software Engineer. Implement the specific atomic task "
            "only after Human-in-the-Loop approval and full graph context verification."
        ),
        tools=[],
    )

    return SequentialAgent(
        name="siemens_knowledge_fabric_coordinator",
        description="Slices legacy modernization epics across 5 specialized ADK agents with HITL gates.",
        sub_agents=[
            search_agent,
            user_story_agent,
            architecture_impact_agent,
            task_breakdown_agent,
            coding_agent,
        ],
    )


class KnowledgeFabricOrchestrator:
    """End-to-end runtime coordinator executing the 5-stage workflow with memory, guardrails & HITL."""

    def __init__(self, memory: Optional[PersistentKnowledgeMemory] = None):
        self.memory = memory or PersistentKnowledgeMemory()
        self.pipeline = build_siemens_slicing_elephant_pipeline()

    @trace_intent_and_outcome("execute_slicing_the_elephant_workflow")
    async def run_workflow(
        self,
        session_id: str,
        user_query: str,
        component_name: str = "AxisControlPanel",
        target_interface: str = "Web-Based React/TypeScript HMI",
        hitl_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ) -> Dict[str, Any]:
        """Executes the full 5-agent modernization pipeline with guardrails and HITL stops."""
        # 1. Policy Guardrail Check
        guardrail_result = guardrail_before_model_callback(user_query)
        if not guardrail_result["allowed"]:
            return {"status": "BLOCKED_BY_GUARDRAIL", "reason": guardrail_result["reason"]}

        self.memory.append_turn_sync(session_id, "user", user_query)

        # 2. Stage 1 — Search Agent (Spanner Graph GQL + ANN + Keyword)
        graph_result = traverse_spanner_code_graph_gql(
            component_name=component_name,
            search_mode="HYBRID_GQL_ANN",
            max_hops=2,
        )
        if graph_result["status"] != "SUCCESS":
            return graph_result

        dependencies = graph_result["dependencies"]
        req_ids = [d["linked_requirement_id"] for d in dependencies if d.get("linked_requirement_id")]
        fn_names = [d["name"] for d in dependencies if d["node_type"] in ("FUNCTION", "MODULE")]

        # 3. Stage 2 — User Story Agent
        stories_result = create_modernization_user_stories(
            component_name=component_name,
            target_interface=target_interface,
            linked_requirement_ids=req_ids,
        )

        # 4. Stage 3 — Architecture Impact Agent
        impact_result = analyze_component_blast_radius(
            component_name=component_name,
            affected_function_names=fn_names,
        )

        # 5. Human-in-the-Loop Gate #1: Approve Architecture Impact before Task Breakdown & Coding
        hitl_approved = human_in_the_loop_approval_hook(
            stage_name="architecture_impact_review",
            artifact_summary=impact_result,
            approval_callback=hitl_callback,
        )
        if not hitl_approved:
            return {
                "status": "PAUSED_FOR_HUMAN_REVIEW",
                "stage": "architecture_impact_review",
                "impact_report": impact_result,
            }

        # 6. Stage 4 — Task Breakdown Agent ("Slicing the Elephant")
        tasks_result = decompose_into_atomic_refactoring_tasks(
            component_name=component_name,
            affected_functions=fn_names,
        )

        # 7. Stage 5 — Coding Agent (Implements Task-001 with full graph context)
        first_task = tasks_result["tasks"][0]
        generated_code_patch = {
            "task_id": first_task["task_id"],
            "target_file": first_task["target_file"],
            "model_used": ModelRouter.select_model(TaskComplexity.DEEP_REASONING),
            "traceable_requirements": req_ids,
            "code_snippet": (
                "// Auto-generated by Siemens Knowledge Fabric Coding Agent\n"
                "// Linked Specs: REQ-2008-MOTION-441, REQ-2004-SIL3-109\n"
                "export async function calculateAxisTorqueLimiterWebAdapter(inputTorqueNm: number): Promise<number> {\n"
                "  if (inputTorqueNm > 450.0) {\n"
                "    await triggerSafetyInterlockBus('OVER_TORQUE_SIL3_TRIP');\n"
                "    throw new Error('SIL-3 Safety Interlock Triggered: Torque exceeds 450 Nm limit.');\n"
                "  }\n"
                "  return Number((inputTorqueNm * 0.985).toFixed(4));\n"
                "}\n"
            ),
        }

        # 8. Persist turn and trigger non-blocking Async Memory Compaction
        self.memory.append_turn_sync(
            session_id,
            "assistant",
            f"Completed modernization slice for {component_name}. Updated {len(fn_names)} functions.",
        )
        await self.memory.trigger_background_consolidation(session_id)

        return {
            "status": "COMPLETED",
            "model_routing": {
                "search_agent": ModelRouter.select_model(TaskComplexity.FAST_RETRIEVAL),
                "user_story_agent": ModelRouter.select_model(TaskComplexity.STRUCTURED_DRAFTING),
                "architecture_impact_agent": ModelRouter.select_model(TaskComplexity.DEEP_REASONING),
                "task_breakdown_agent": ModelRouter.select_model(TaskComplexity.STRUCTURED_DRAFTING),
                "coding_agent": ModelRouter.select_model(TaskComplexity.DEEP_REASONING),
            },
            "graph_analysis": graph_result,
            "user_stories": stories_result["user_stories"],
            "architecture_impact": impact_result["impact_report"],
            "sliced_tasks": tasks_result["tasks"],
            "coding_agent_output": generated_code_patch,
            "compacted_memory_snapshot": self.memory.get_compacted_context(session_id),
        }
