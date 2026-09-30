"""Interactive CLI Demo for the Siemens 'Slicing the Elephant' Multi-Agent System."""

import asyncio
import json
from src.agents import KnowledgeFabricOrchestrator


def interactive_hitl_prompt(stage_name: str, artifact_summary: dict) -> bool:
    print("\n" + "=" * 75)
    print(f"🛑 HUMAN-IN-THE-LOOP (HITL) GATE TRIGGERED AT STAGE: [{stage_name}]")
    print("=" * 75)
    print(json.dumps(artifact_summary, indent=2))
    print("-" * 75)
    print("✅ Auto-approving for demo execution (pass custom callback for manual CLI prompt).")
    return True


async def main() -> None:
    orchestrator = KnowledgeFabricOrchestrator()
    query = (
        "Which functions need to be updated if I change the logic in the Axis Control Panel, "
        "and can you generate the modernized Web HMI TypeScript adapter? "
        "(Requested by engineer hans.mueller@siemens.com)"
    )

    print("\n🚀 Launching Siemens Knowledge Fabric ('Slicing the Elephant') Workflow...\n")
    result = await orchestrator.run_workflow(
        session_id="demo-session-001",
        user_query=query,
        component_name="AxisControlPanel",
        target_interface="Web-Based React/TypeScript HMI",
        hitl_callback=interactive_hitl_prompt,
    )

    print("\n" + "=" * 75)
    print("🎯 FINAL MULTI-AGENT WORKFLOW OUTPUT")
    print("=" * 75)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
