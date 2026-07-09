"""
╔══════════════════════════════════════════════════════════════════╗
║  Prompt Pipeline — Streamlit Application                        ║
║  Three-column UI: Config | Input | Execution                    ║
║  Dark theme, glassmorphism, animated pipeline visualization     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import streamlit as st
from datetime import datetime

# ── Page config MUST be first ────────────────────────────────
st.set_page_config(
    page_title="Prompt Pipeline — AI Workflow Designer",
    page_icon="🔁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load custom CSS ──────────────────────────────────────────
with open("styles/theme.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Imports ──────────────────────────────────────────────────
from tasks import get_task, get_task_list, get_stage_info, STAGE_INFO
from pipeline import run_pipeline, generate_reflection
from llm import DEFAULT_MODEL, REASON_MODEL

# ── Session State Initialization ─────────────────────────────
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "pipeline_history" not in st.session_state:
    st.session_state.pipeline_history = []
if "executing" not in st.session_state:
    st.session_state.executing = False
if "selected_task" not in st.session_state:
    st.session_state.selected_task = "support_ticket"
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("OPENROUTER_API_KEY", "")

# ── Helper Functions ─────────────────────────────────────────

def format_time(seconds: float) -> str:
    """Format seconds into human-readable string."""
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"


def get_status_emoji(status: str) -> str:
    return {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
    }.get(status, "❓")


def get_technique_color(technique: str) -> str:
    colors = {
        "role": "#4f8cff",
        "cot": "#8b5cf6",
        "goal": "#22c55e",
        "critique": "#f97316",
    }
    return colors.get(technique, "#6b6b80")


def render_stage_card(stage: dict, index: int, expanded: bool = False):
    """Render a single stage result card."""
    status = stage.get("status", "pending")
    stage_name = stage.get("stage_name", f"Stage {index + 1}")
    technique = stage.get("technique", "")
    technique_short = stage.get("technique_short", "")
    latency = stage.get("latency", 0)
    tokens = stage.get("tokens", 0)
    error = stage.get("error", None)
    parse_attempts = stage.get("parse_attempts", [])

    # Status badge
    status_emoji = get_status_emoji(status)
    status_colors = {
        "pending": ("#6b6b80", "rgba(107,107,128,0.15)"),
        "running": ("#4f8cff", "rgba(79,140,255,0.15)"),
        "completed": ("#22c55e", "rgba(34,197,94,0.15)"),
        "failed": ("#ef4444", "rgba(239,68,68,0.15)"),
    }
    sc = status_colors.get(status, ("#6b6b80", "rgba(107,107,128,0.15)"))

    # Technique badge color
    tc = get_technique_color(technique_short)

    # Card header
    header_html = f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:20px;font-weight:700;color:var(--text-primary);">#{index + 1}</span>
            <span style="font-size:16px;font-weight:600;color:var(--text-primary);">{stage_name}</span>
            <span style="font-size:11px;padding:3px 10px;border-radius:12px;background:{tc}22;color:{tc};font-weight:600;text-transform:uppercase;letter-spacing:0.3px;">
                {technique_short.upper() if technique_short else "N/A"}
            </span>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:12px;color:var(--text-muted);">
                {format_time(latency)} · {tokens or 0} tokens
            </span>
            <span style="font-size:12px;padding:3px 10px;border-radius:12px;background:{sc[1]};color:{sc[0]};font-weight:600;">
                {status_emoji} {status.upper()}
            </span>
        </div>
    </div>
    """

    st.markdown(header_html, unsafe_allow_html=True)

    if status == "failed":
        st.error(f"**Error:** {error}")
        return

    if status == "pending":
        st.info("⏳ Waiting to execute...")
        return

    if status == "running":
        st.info("🔄 Executing...")
        return

    # Completed - show details
    with st.expander("📖 **Educational Info**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Technique:** `{technique}`")
            st.markdown(f"**Purpose:** {stage.get('purpose', 'N/A')}")
            st.markdown(f"**Input Schema:** `{stage.get('input_schema', 'N/A')}`")
        with col2:
            st.markdown(f"**Output Schema:** `{stage.get('output_schema', 'N/A')}`")
            st.markdown(f"**Best Practice:** {stage.get('best_practice', 'N/A')}")
            st.markdown(f"**Model:** `{stage.get('model_used', 'N/A')}`")

    with st.expander("📝 **Prompt Sent**", expanded=False):
        st.code(stage.get("prompt_sent", ""), language="text")

    with st.expander("📥 **Raw Model Response**", expanded=False):
        st.code(stage.get("raw_response", ""), language="text")

    with st.expander("🔍 **Parsed JSON Output**", expanded=True):
        parsed = stage.get("parsed_json", {})
        if parsed:
            st.json(parsed)
        else:
            st.info("No parsed JSON available.")

    if parse_attempts:
        with st.expander("🔄 **Parse Retry Attempts**", expanded=False):
            for attempt in parse_attempts:
                st.markdown(f"**Attempt {attempt.get('attempt', '?')}:** {attempt.get('error', 'Unknown error')}")
                if attempt.get("preview"):
                    st.code(attempt["preview"][:300], language="text")


def render_pipeline_flow(stages: list):
    """Render a visual pipeline flow diagram."""
    html = '<div style="display:flex;align-items:center;justify-content:center;gap:4px;padding:12px 0;flex-wrap:wrap;">'
    for i, stage in enumerate(stages):
        status = stage.get("status", "pending")
        name = stage.get("stage_name", f"S{i+1}")
        colors = {
            "completed": ("#22c55e", "rgba(34,197,94,0.15)"),
            "running": ("#4f8cff", "rgba(79,140,255,0.15)"),
            "failed": ("#ef4444", "rgba(239,68,68,0.15)"),
            "pending": ("#6b6b80", "rgba(107,107,128,0.08)"),
        }
        c = colors.get(status, colors["pending"])
        html += f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
            <div style="width:48px;height:48px;border-radius:50%;background:{c[1]};border:2px solid {c[0]};
                        display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:{c[0]};">
                {i + 1}
            </div>
            <span style="font-size:10px;color:{c[0]};font-weight:600;text-align:center;">{name}</span>
        </div>
        """
        if i < len(stages) - 1:
            arrow_color = "#22c55e" if stage.get("status") == "completed" else "#6b6b80"
            html += f'<div style="font-size:20px;color:{arrow_color};padding:0 2px;margin-bottom:20px;">→</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_statistics(result: dict):
    """Render pipeline statistics."""
    stages = result.get("stages", [])
    completed = sum(1 for s in stages if s["status"] == "completed")
    failed = sum(1 for s in stages if s["status"] == "failed")
    total_tokens = result.get("total_tokens", 0)
    total_latency = result.get("total_latency", 0)

    cols = st.columns(5)
    cols[0].metric("Stages", f"{completed}/{len(stages)}")
    cols[1].metric("Status", "✅ Completed" if result["status"] == "completed" else "❌ Failed")
    cols[2].metric("Total Time", format_time(total_latency))
    cols[3].metric("Total Tokens", f"{total_tokens:,}" if total_tokens else "N/A")
    cols[4].metric("Model", result.get("model", "N/A").split("/")[-1][:20])


def render_reflection(result: dict):
    """Render the reflection/educational section."""
    reflection = generate_reflection(result)

    st.markdown("### 🔬 Pipeline Reflection")
    st.markdown("Analysis of the weakest stage and how future GenAI concepts could improve it.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Weakest Stage:** {reflection['weakest_stage']}")
        st.markdown(f"**Why it's weak:** {reflection['why_weak']}")
    with col2:
        st.markdown("**Potential Improvements:**")
        st.markdown(reflection["improvements"])

    st.markdown("### 🚀 Future Enhancement Concepts")
    tabs = st.tabs(["📚 RAG", "🔧 Tool Calling", "🤖 Agents"])
    with tabs[0]:
        st.markdown(reflection["rag_improvement"])
    with tabs[1]:
        st.markdown(reflection["tool_calling_improvement"])
    with tabs[2]:
        st.markdown(reflection["agent_improvement"])


def render_history():
    """Render execution history."""
    if not st.session_state.pipeline_history:
        st.info("No execution history yet.")
        return

    for i, entry in enumerate(reversed(st.session_state.pipeline_history[-5:])):
        ts = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%H:%M:%S")
        status = entry.get("status", "unknown")
        emoji = "✅" if status == "completed" else "❌"
        task_name = entry.get("task_name", "Unknown")
        latency = entry.get("total_latency", 0)

        with st.expander(f"{emoji} **{task_name}** — {ts} ({format_time(latency)})", expanded=False):
            st.markdown(f"**Input:** {entry.get('input_text', '')[:200]}...")
            st.markdown(f"**Status:** {status}")
            st.markdown(f"**Stages:** {len(entry.get('stages', []))}")
            st.markdown(f"**Total Time:** {format_time(latency)}")
            st.markdown(f"**Tokens:** {entry.get('total_tokens', 0)}")


# ═══════════════════════════════════════════════════════════════
#  MAIN UI — Three Column Layout
# ═══════════════════════════════════════════════════════════════

# ── Top Bar ──────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0 16px 0;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:20px;">
    <div>
        <span class="app-title">🔁 Prompt Pipeline</span>
        <span class="app-subtitle" style="display:block;margin-top:2px;">Multi-Stage Prompt Engineering Workflow Designer</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:12px;color:var(--text-muted);">⚡ Day 2 Homework · GenAI & Agentic AI Engineering</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Three Column Layout ──────────────────────────────────────
left_col, mid_col, right_col = st.columns([1.2, 1.2, 2.2])

# ═══════════════════════════════════════════════════════════════
#  LEFT PANEL — Pipeline Configuration
# ═══════════════════════════════════════════════════════════════
with left_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configuration")

    # API Key - Backend only (environment variable)
    st.markdown("#### 🔑 API Key")
    api_key = st.session_state.api_key
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key
        st.success("✅ API Key loaded from environment")
    else:
        st.error("❌ OPENROUTER_API_KEY not set. Set it as an environment variable and restart.")

    st.markdown("---")

    # Task Selector
    st.markdown("#### 📋 Task Selector")
    task_list = get_task_list()
    task_options = {f"{t['icon']} {t['name']}": t["id"] for t in task_list}
    selected_task_label = st.selectbox(
        "Select a task",
        options=list(task_options.keys()),
        index=0,
        label_visibility="collapsed",
    )
    selected_task = task_options[selected_task_label]
    st.session_state.selected_task = selected_task

    # Show task info
    task_info = get_task(selected_task)
    if task_info:
        st.markdown(
            f'<p style="font-size:13px;color:var(--text-secondary);">{task_info["description"]}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="font-size:12px;color:var(--text-muted);">📥 Input: {task_info["input_format"]}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="font-size:12px;color:var(--text-muted);">📊 Stages: {len(task_info["stages"])}</p>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Pipeline Visualization
    st.markdown("#### 🔄 Pipeline Flow")
    if task_info:
        stages = task_info["stages"]
        flow_html = '<div style="padding:8px 0;">'
        for i, s in enumerate(stages):
            tc = get_technique_color(s.get("technique_short", ""))
            flow_html += f"""
            <div style="display:flex;align-items:center;gap:10px;padding:6px 0;">
                <div style="width:28px;height:28px;border-radius:50%;background:{tc}22;border:2px solid {tc};
                            display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:{tc};flex-shrink:0;">
                    {i + 1}
                </div>
                <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:var(--text-primary);">{s['name']}</div>
                    <div style="font-size:11px;color:var(--text-muted);">{s.get('technique_short', '').upper()}</div>
                </div>
            </div>
            """
            if i < len(stages) - 1:
                flow_html += '<div style="text-align:center;color:var(--text-muted);font-size:14px;padding:0 0 0 14px;">↓</div>'
        flow_html += "</div>"
        st.markdown(flow_html, unsafe_allow_html=True)

    st.markdown("---")

    # Model Selection
    st.markdown("#### 🤖 Model Settings")
    model_options = {
        "Gemini 2.5 Flash Lite (Fast)": "google/gemini-2.5-flash-lite",
        "Gemini 2.5 Flash (Balanced)": "google/gemini-2.5-flash",
        "GPT-4o Mini (Fallback)": "openai/gpt-4o-mini",
    }
    selected_model_label = st.selectbox(
        "Model",
        options=list(model_options.keys()),
        index=0,
        label_visibility="collapsed",
    )
    selected_model = model_options[selected_model_label]

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.05,
        help="Higher = more creative, Lower = more deterministic",
    )

    enable_critique = st.checkbox("Enable Stage 4 (Critique)", value=True)

    st.markdown("---")

    # Run / Reset Buttons
    can_run = bool(st.session_state.api_key)
    if st.button(
        "🚀 Run Pipeline",
        type="primary",
        use_container_width=True,
        disabled=not can_run or st.session_state.executing,
        help="" if can_run else "Enter an API key first",
    ):
        st.session_state.executing = True

    if st.button(
        "🔄 Reset",
        use_container_width=True,
        disabled=st.session_state.executing,
    ):
        st.session_state.pipeline_result = None
        st.rerun()

    # Progress indicator
    if st.session_state.executing or st.session_state.pipeline_result:
        st.markdown("---")
        st.markdown("#### 📊 Progress")
        if st.session_state.pipeline_result:
            stages = st.session_state.pipeline_result.get("stages", [])
            completed = sum(1 for s in stages if s["status"] == "completed")
            total = len(stages)
            pct = int((completed / total) * 100) if total > 0 else 0
            st.markdown(
                f"""
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width:{pct}%;"></div>
                </div>
                <p style="font-size:12px;color:var(--text-muted);text-align:center;margin-top:4px;">
                    {completed}/{total} stages completed
                </p>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  MIDDLE PANEL — User Input
# ═══════════════════════════════════════════════════════════════
with mid_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📝 User Input")

    if task_info:
        st.markdown(
            f'<p style="font-size:13px;color:var(--text-secondary);">{task_info["description"]}</p>',
            unsafe_allow_html=True,
        )

        # Example inputs
        st.markdown("#### 💡 Example Inputs")
        example = task_info.get("example_input", "")
        st.markdown(
            f'<div style="background:rgba(79,140,255,0.06);border:1px solid rgba(79,140,255,0.15);border-radius:8px;padding:12px;font-size:12px;color:var(--text-secondary);line-height:1.5;margin-bottom:12px;">'
            f'📌 <strong>Example:</strong> {example[:200]}{"..." if len(example) > 200 else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Text input
        st.markdown("#### ✏️ Your Input")
        placeholder = task_info.get("input_placeholder", "Enter your input here...")
        user_input = st.text_area(
            label="Input",
            value="",
            height=200,
            placeholder=placeholder,
            label_visibility="collapsed",
            key="user_input",
        )

        # Quick fill buttons
        st.markdown("##### Quick Fill")
        col1, col2 = st.columns(2)
        if col1.button("📋 Load Example", use_container_width=True):
            st.session_state.user_input = example
            st.rerun()
        if col2.button("🗑️ Clear", use_container_width=True):
            st.session_state.user_input = ""
            st.rerun()

    st.markdown("---")

    # Current Stage Info
    st.markdown("#### 📍 Current Stage Info")
    if st.session_state.pipeline_result:
        stages = st.session_state.pipeline_result.get("stages", [])
        for i, stage in enumerate(stages):
            status = stage.get("status", "pending")
            name = stage.get("stage_name", f"Stage {i+1}")
            technique = stage.get("technique", "")
            emoji = get_status_emoji(status)
            color = {"completed": "#22c55e", "running": "#4f8cff", "failed": "#ef4444", "pending": "#6b6b80"}.get(status, "#6b6b80")

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:8px;
                            background:{'rgba(34,197,94,0.06)' if status == 'completed' else 'transparent'};
                            border-left:3px solid {color};margin-bottom:4px;">
                    <span style="font-size:14px;">{emoji}</span>
                    <span style="font-size:13px;font-weight:500;color:var(--text-primary);flex:1;">{name}</span>
                    <span style="font-size:11px;color:var(--text-muted);">{technique[:30]}</span>
                    <span style="font-size:11px;color:{color};font-weight:600;">{status.upper()}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("👈 Configure and run the pipeline to see stage progress here.")

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  RIGHT PANEL — Pipeline Execution
# ═══════════════════════════════════════════════════════════════
with right_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🎬 Pipeline Execution")

    # ── Execute Pipeline ──────────────────────────────────────
    if st.session_state.executing:
        if not user_input.strip():
            st.error("Please enter some input text.")
            st.session_state.executing = False
        else:
            with st.spinner("🔄 Running pipeline stages..."):
                try:
                    result = run_pipeline(
                        task_id=selected_task,
                        input_text=user_input.strip(),
                        api_key=st.session_state.api_key,
                        model=selected_model,
                        temperature=temperature,
                        enable_critique=enable_critique,
                    )
                    st.session_state.pipeline_result = result
                    st.session_state.pipeline_history.append(result)
                except Exception as e:
                    st.error(f"Pipeline execution failed: {e}")
                finally:
                    st.session_state.executing = False
            st.rerun()

    # ── Display Results ───────────────────────────────────────
    if st.session_state.pipeline_result:
        result = st.session_state.pipeline_result

        # Pipeline flow visualization
        render_pipeline_flow(result.get("stages", []))

        st.markdown("---")

        # Statistics
        render_statistics(result)

        st.markdown("---")

        # Stage cards
        st.markdown("#### 📦 Stage Results")
        stages = result.get("stages", [])
        for i, stage in enumerate(stages):
            st.markdown(f'<div class="stage-card {stage.get("status", "pending")}">', unsafe_allow_html=True)
            render_stage_card(stage, i)
            st.markdown('</div>', unsafe_allow_html=True)

        # Final Output
        st.markdown("---")
        st.markdown("#### 🏁 Final Output")
        final_output = result.get("final_output", None)
        if final_output:
            if isinstance(final_output, dict):
                st.json(final_output)
            else:
                st.markdown(
                    f'<div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.15);border-radius:12px;padding:16px;font-size:14px;line-height:1.6;color:var(--text-primary);">'
                    f'{final_output}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No final output produced.")

        # Reflection
        st.markdown("---")
        render_reflection(result)

        # Download / Copy buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        if col1.button("📥 Download Report", use_container_width=True):
            report = {
                "task": result.get("task_name", ""),
                "input": result.get("input_text", ""),
                "status": result.get("status", ""),
                "total_latency": result.get("total_latency", 0),
                "total_tokens": result.get("total_tokens", 0),
                "stages": [
                    {
                        "name": s.get("stage_name"),
                        "technique": s.get("technique"),
                        "status": s.get("status"),
                        "latency": s.get("latency"),
                        "tokens": s.get("tokens"),
                        "parsed_json": s.get("parsed_json"),
                    }
                    for s in result.get("stages", [])
                ],
                "final_output": result.get("final_output"),
                "timestamp": datetime.now().isoformat(),
            }
            report_json = json.dumps(report, indent=2, default=str)
            st.download_button(
                "💾 Save JSON",
                data=report_json,
                file_name=f"pipeline_report_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
            )

        if col2.button("📋 Copy JSON", use_container_width=True):
            result_json = json.dumps(result, indent=2, default=str)
            st.code(result_json[:2000] + "...", language="json")
            st.info("JSON copied to clipboard (truncated in display)")

        if col3.button("📊 View History", use_container_width=True):
            st.session_state.show_history = not st.session_state.get("show_history", False)

        # History section
        if st.session_state.get("show_history", False):
            st.markdown("---")
            st.markdown("#### 📜 Execution History")
            render_history()

    else:
        # Empty state
        st.info("""
        ### 👋 Welcome to Prompt Pipeline!

        **Get started:**
        1. Set **OPENROUTER_API_KEY** as an environment variable and restart
        2. Select a **task** from the dropdown
        3. Enter or load an **example input**
        4. Click **Run Pipeline** to execute

        This application demonstrates how complex tasks can be solved by decomposing them into multiple LLM prompts, where each stage performs a single responsibility and passes structured JSON to the next stage.
        """)

        # Show educational overview
        with st.expander("🎓 **How Prompt Pipelines Work**", expanded=True):
            st.markdown("""
            ### The Architecture

            A **prompt pipeline** decomposes a complex task into multiple stages, where each stage:

            1. **Receives** structured JSON from the previous stage
            2. **Processes** it with a carefully engineered prompt
            3. **Outputs** structured JSON for the next stage

            ### The 4 Stages

            | Stage | Technique | Purpose |
            |-------|-----------|---------|
            | **1. UNDERSTAND** | Role + Structured Output | Parse raw input into structured data |
            | **2. REASON** | Chain-of-Thought | Analyze and reason step-by-step |
            | **3. PRODUCE** | Goal-Oriented + Constraints | Generate the final output |
            | **4. CRITIQUE** | Self-Reflection | Review and improve quality |

            ### Key Principles

            - **JSON Handoff**: Every stage outputs valid JSON that becomes input for the next
            - **Single Responsibility**: Each stage does one thing well
            - **Transparency**: Every prompt, response, and parsed output is visible
            - **Validation**: JSON parsing with automatic retry on failure
            """)

        with st.expander("📚 **Available Tasks**", expanded=False):
            for t in task_list:
                st.markdown(f"**{t['icon']} {t['name']}** — {t['description']}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ──────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:20px 0 10px 0;border-top:1px solid rgba(255,255,255,0.06);margin-top:20px;">
    <p style="font-size:12px;color:var(--text-muted);">
        🔁 Prompt Pipeline · Built with Streamlit + OpenRouter · 
        GenAI & Agentic AI Engineering · Day 2 Homework
    </p>
</div>
""", unsafe_allow_html=True)