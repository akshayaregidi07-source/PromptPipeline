"""
╔══════════════════════════════════════════════════════════════════╗
║  Pipeline — Multi-Stage Prompt Pipeline Engine                  ║
║  Orchestrates stages, manages JSON handoff, retry, & logging    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import time
from typing import Any, Optional

from llm import call_llm, DEFAULT_MODEL, REASON_MODEL
from parser import parse_json
from tasks import get_task, get_stage_info


def run_stage(
    stage_config: dict,
    stage_index: int,
    input_data: Any,
    previous_stages: list,
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    enable_critique: bool = True,
) -> dict:
    """
    Run a single pipeline stage.

    Returns:
        {
            "stage_index": int,
            "stage_name": str,
            "technique": str,
            "technique_short": str,
            "description": str,
            "purpose": str,
            "input_schema": str,
            "output_schema": str,
            "best_practice": str,
            "prompt_sent": str,
            "raw_response": str,
            "parsed_json": dict | None,
            "parse_attempts": list,
            "parse_success": bool,
            "model_used": str,
            "latency": float,
            "tokens": int | None,
            "error": str | None,
            "status": "pending" | "running" | "completed" | "failed",
            "timestamp": float,
        }
    """
    stage_name = stage_config.get("name", f"Stage {stage_index + 1}")
    technique = stage_config.get("technique", "")
    prompt_template = stage_config.get("prompt_template", "")

    result = {
        "stage_index": stage_index,
        "stage_name": stage_name,
        "technique": technique,
        "technique_short": stage_config.get("technique_short", ""),
        "description": stage_config.get("description", ""),
        "purpose": stage_config.get("purpose", ""),
        "input_schema": stage_config.get("input_schema", ""),
        "output_schema": stage_config.get("output_schema", ""),
        "best_practice": stage_config.get("best_practice", ""),
        "prompt_sent": "",
        "raw_response": "",
        "parsed_json": None,
        "parse_attempts": [],
        "parse_success": False,
        "model_used": model,
        "latency": 0,
        "tokens": None,
        "error": None,
        "status": "running",
        "timestamp": time.time(),
    }

    try:
        # Format the prompt
        if stage_index == 0:
            # Stage 1: takes raw input
            prompt = prompt_template.format(input=input_data)
        elif stage_index == 1:
            # Stage 2: takes stage 1 JSON
            input_json = json.dumps(input_data, indent=2)
            prompt = prompt_template.format(input=input_json)
        elif stage_index == 2:
            # Stage 3: takes stage 1 and stage 2
            stage1_data = previous_stages[0].get("parsed_json", {})
            stage2_data = previous_stages[1].get("parsed_json", {})
            prompt = prompt_template.format(
                stage1=json.dumps(stage1_data, indent=2),
                stage2=json.dumps(stage2_data, indent=2),
                ticket=json.dumps(stage1_data, indent=2),
                decision=json.dumps(stage2_data, indent=2),
            )
        elif stage_index == 3:
            # Stage 4: Critique - takes previous stages
            stage1_data = previous_stages[0].get("parsed_json", {})
            stage2_data = previous_stages[1].get("parsed_json", {})
            stage3_data = previous_stages[2].get("raw_response", "")
            if previous_stages[2].get("parsed_json"):
                stage3_data = previous_stages[2].get("parsed_json", "")
            prompt = prompt_template.format(
                stage1=json.dumps(stage1_data, indent=2),
                stage2=json.dumps(stage2_data, indent=2),
                stage3=json.dumps(stage3_data, indent=2) if isinstance(stage3_data, dict) else stage3_data,
                ticket=json.dumps(stage1_data, indent=2),
                decision=json.dumps(stage2_data, indent=2),
                reply=stage3_data if isinstance(stage3_data, str) else json.dumps(stage3_data, indent=2),
            )
        else:
            prompt = prompt_template.format(input=str(input_data))

        result["prompt_sent"] = prompt

        # Determine model for this stage
        stage_model = model
        if stage_index == 1:
            # Use reasoning model for CoT stages
            stage_model = REASON_MODEL

        # Call LLM
        llm_result = call_llm(prompt, model=stage_model, temperature=temperature, api_key=api_key)
        result["model_used"] = llm_result.get("model", stage_model)
        result["latency"] = llm_result.get("latency", 0)
        result["tokens"] = llm_result.get("tokens", None)

        if not llm_result.get("success"):
            result["error"] = llm_result.get("error", "Unknown LLM error")
            result["status"] = "failed"
            result["raw_response"] = llm_result.get("text", "")
            return result

        raw_text = llm_result.get("text", "")
        result["raw_response"] = raw_text

        # Parse JSON (except for Stage 3 which may produce free text)
        if stage_index == 2:
            # Stage 3 (PRODUCE) may return free text or JSON depending on task
            # Try to parse as JSON first
            parse_result = parse_json(raw_text, repair_fn=lambda p: call_llm(p, temperature=0.0, api_key=api_key))
            if parse_result.get("success"):
                result["parsed_json"] = parse_result["data"]
                result["parse_success"] = True
                result["parse_attempts"] = parse_result.get("attempts", [])
            else:
                # Use raw text as the output
                result["parsed_json"] = {"output": raw_text}
                result["parse_success"] = True  # Free text is valid
                result["parse_attempts"] = []
        else:
            # Stages 1, 2, 4 must return JSON
            parse_result = parse_json(raw_text, repair_fn=lambda p: call_llm(p, temperature=0.0, api_key=api_key))
            result["parse_attempts"] = parse_result.get("attempts", [])

            if parse_result.get("success"):
                result["parsed_json"] = parse_result["data"]
                result["parse_success"] = True
            else:
                result["error"] = parse_result.get("error", "Failed to parse JSON")
                result["status"] = "failed"
                return result

        result["status"] = "completed"

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"

    return result


def run_pipeline(
    task_id: str,
    input_text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    enable_critique: bool = True,
) -> dict:
    """
    Run the full pipeline for a given task.

    Returns:
        {
            "task_id": str,
            "task_name": str,
            "input_text": str,
            "stages": [stage_result, ...],
            "final_output": Any,
            "status": "completed" | "failed",
            "total_latency": float,
            "total_tokens": int | None,
            "timestamp": float,
            "error": str | None,
        }
    """
    task = get_task(task_id)
    if not task:
        return {
            "task_id": task_id,
            "task_name": "Unknown",
            "input_text": input_text,
            "stages": [],
            "final_output": None,
            "status": "failed",
            "total_latency": 0,
            "total_tokens": 0,
            "timestamp": time.time(),
            "error": f"Unknown task: {task_id}",
        }

    stages_config = task["stages"]
    stage_results = []
    total_tokens = 0
    start_time = time.time()

    for i, stage_config in enumerate(stages_config):
        # Skip critique stage if disabled
        if i == 3 and not enable_critique:
            break

        # Determine input for this stage
        if i == 0:
            stage_input = input_text
        else:
            stage_input = stage_results[-1].get("parsed_json", stage_results[-1].get("raw_response", ""))

        # Run stage
        stage_result = run_stage(
            stage_config=stage_config,
            stage_index=i,
            input_data=stage_input,
            previous_stages=stage_results,
            api_key=api_key,
            model=model,
            temperature=temperature,
            enable_critique=enable_critique,
        )

        stage_results.append(stage_result)

        if stage_result.get("tokens"):
            total_tokens += stage_result["tokens"]

        # If stage failed, stop pipeline
        if stage_result["status"] == "failed":
            break

    total_latency = round(time.time() - start_time, 2)

    # Determine final output
    final_output = None
    if stage_results:
        if stage_results[-1].get("parsed_json"):
            final_output = stage_results[-1]["parsed_json"]
        elif stage_results[-1].get("raw_response"):
            final_output = stage_results[-1]["raw_response"]

    pipeline_status = "completed"
    pipeline_error = None
    for sr in stage_results:
        if sr["status"] == "failed":
            pipeline_status = "failed"
            pipeline_error = sr.get("error", "Stage failed")
            break

    return {
        "task_id": task_id,
        "task_name": task["name"],
        "task_icon": task.get("icon", ""),
        "input_text": input_text,
        "stages": stage_results,
        "final_output": final_output,
        "status": pipeline_status,
        "error": pipeline_error,
        "total_latency": total_latency,
        "total_tokens": total_tokens,
        "timestamp": start_time,
        "enable_critique": enable_critique,
        "model": model,
        "temperature": temperature,
    }


def generate_reflection(pipeline_result: dict) -> dict:
    """
    Generate reflection analysis on the pipeline execution.

    Returns:
        {
            "weakest_stage": str,
            "why_weak": str,
            "improvements": str,
            "rag_improvement": str,
            "tool_calling_improvement": str,
            "agent_improvement": str,
        }
    """
    stages = pipeline_result.get("stages", [])
    if not stages:
        return {
            "weakest_stage": "N/A",
            "why_weak": "No stages executed.",
            "improvements": "N/A",
            "rag_improvement": "N/A",
            "tool_calling_improvement": "N/A",
            "agent_improvement": "N/A",
        }

    # Find the weakest stage (failed or lowest quality)
    weakest = None
    for s in stages:
        if s["status"] == "failed":
            weakest = s
            break

    if not weakest:
        # Pick the stage with the most parse attempts
        max_attempts = 0
        for s in stages:
            attempts = len(s.get("parse_attempts", []))
            if attempts > max_attempts:
                max_attempts = attempts
                weakest = s

    if not weakest:
        weakest = stages[-1]

    stage_name = weakest.get("stage_name", "Unknown")
    technique = weakest.get("technique", "Unknown")

    reflection = {
        "weakest_stage": f"{stage_name} ({technique})",
        "why_weak": (
            f"This stage had the most difficulty in the pipeline. "
            f"It required precise {technique.lower()} which can be challenging for LLMs. "
            f"The complexity of the task and the need for structured output parsing "
            f"introduced potential failure points."
        ),
        "improvements": (
            f"1. Use a more specific role description to guide the model.\n"
            f"2. Provide few-shot examples in the prompt.\n"
            f"3. Reduce the number of output fields to minimize complexity.\n"
            f"4. Use a more capable model (e.g., GPT-4, Claude 3) for this stage."
        ),
        "rag_improvement": (
            "RAG (Retrieval-Augmented Generation) could improve this stage by "
            "retrieving relevant examples, past successful outputs, or domain-specific "
            "knowledge from a vector database. For example, retrieving similar "
            "support tickets and their resolutions could help the model produce "
            "more accurate and contextually appropriate outputs."
        ),
        "tool_calling_improvement": (
            "Tool calling could improve this stage by allowing the model to "
            "call external functions for specific tasks. For example, calling a "
            "database lookup for customer information, an order tracking API, "
            "or a sentiment analysis tool. This would offload specific reasoning "
            "steps to deterministic tools, reducing the burden on the LLM."
        ),
        "agent_improvement": (
            "An agent-based approach could improve this stage by allowing the "
            "model to iterate, reflect, and refine its output. The agent could "
            "run multiple cycles of generation and critique, use tools to gather "
            "additional information, and maintain a running memory of the conversation. "
            "This would enable more complex reasoning and better handling of edge cases."
        ),
    }

    return reflection