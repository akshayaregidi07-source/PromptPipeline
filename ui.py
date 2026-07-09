"""
Prompt Pipeline — Interactive UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A Streamlit interface for the Support Ticket Triage Pipeline.
Lets you type or paste a customer message, run all 4 stages, and
inspect every output — glass-box visibility in a clean UI.

Run with:  streamlit run ui.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import json
import streamlit as st

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Prompt Pipeline — Ticket Triage",
    page_icon="🔁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar: API key & settings ─────────────────────────────

with st.sidebar:
    st.title("🔁 Prompt Pipeline")
    st.caption("Support Ticket Triage · 4-stage LLM chain")

    st.divider()
    st.subheader("🔑 API Key")

    env_key = os.environ.get("OPENROUTER_API_KEY", "")
    if env_key:
        st.success("✅ Key loaded from environment")
        api_key = env_key
    else:
        api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
            help="Your OpenRouter API key. Not stored — only used for this session.",
        )
        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key

    st.divider()
    st.subheader("⚙️ Options")
    enable_critique = st.checkbox("Enable Stage 4 (Critique + redo)", value=True)
    show_raw_json = st.checkbox("Show raw JSON in stage outputs", value=False)

    st.divider()
    st.caption("Built with Streamlit + OpenRouter")
    st.caption("Models: gemini-2.5-flash-lite / gemini-2.5-flash")


# ── Main area ────────────────────────────────────────────────

st.title("📋 Support Ticket Triage Pipeline")
st.markdown(
    "Paste a raw customer message below and run the pipeline. "
    "Each stage hands structured JSON to the next — inspect every step."
)

PRESETS = {
    "✏️ Custom message (type your own)": "",
    "📦 Normal — Shipping delay": (
        "My order #ORD-7842 was supposed to arrive 5 days ago. Tracking says "
        "it's been 'in transit' for a week. I need this for my daughter's birthday "
        "tomorrow. This is really frustrating. — Karen Mitchell"
    ),
    "🔥 Tricky — Angry, account locked + billing": (
        "I CANNOT log into my account for the THIRD time this month! First it was "
        "billing (you charged me twice for order #ORD-9912 and still haven't refunded), "
        "then the mobile app crashed, and NOW I'm locked out. I've spent 4 hours on "
        "this. DO SOMETHING. — Alex Chen, alex@example.com"
    ),
    "💔 Product defect — Damaged item": (
        "Hey, I just received my package #SHIP-5531 and the screen is cracked. "
        "Like, visibly broken. I paid $299 for this. What are you going to do about it? "
        "— Maria Garcia"
    ),
    "🤷 Gibberish — Unprocessable": (
        "ajklds flkajsd lfkjas dflkja sdlfk jasdlfk jasdlfk j"
    ),
    "😊 Positive — General inquiry": (
        "Hi! I was wondering if you guys plan to restock the blue variant of the "
        "ErgoChair Pro? I've been waiting for it. Thanks! — Sam Wilson"
    ),
}

preset_choice = st.selectbox(
    "Choose a preset example (or select Custom):",
    list(PRESETS.keys()),
    index=0,
)

if preset_choice == "✏️ Custom message (type your own)":
    default_text = ""
else:
    default_text = PRESETS[preset_choice]

user_input = st.text_area(
    "Customer message:",
    value=default_text,
    height=150,
    placeholder="Type or paste a customer support message here...",
)

run_disabled = not api_key or not user_input.strip()
run_help = ""
if not api_key:
    run_help = "Enter an API key in the sidebar first."
elif not user_input.strip():
    run_help = "Enter a customer message first."

if st.button(
    "🚀 Run Pipeline",
    type="primary",
    use_container_width=True,
    disabled=run_disabled,
    help=run_help,
):
    if not api_key:
        st.error("Please provide an OpenRouter API key in the sidebar.")
        st.stop()
    if not user_input.strip():
        st.error("Please enter a customer message.")
        st.stop()

    os.environ["OPENROUTER_API_KEY"] = api_key

    import importlib
    import pipeline as pl
    importlib.reload(pl)

    status = st.empty()
    results = st.container()

    with st.spinner("Running pipeline — calling 3-4 LLMs (~20-60s)..."):

        # Stage 1
        status.info("🔍 Stage 1: UNDERSTAND — Parsing message...")
        ticket = pl.stage1_understand(user_input.strip())
        with results:
            with st.expander("📥 **Stage 1: UNDERSTAND** (role + structured output)", expanded=True):
                ca, cb = st.columns([1, 1])
                with ca:
                    for k, v in ticket.items():
                        if k == "key_phrases":
                            st.markdown(f"**{k}:** _{', '.join(v) if v else '(none)'}_")
                        elif k == "reasoning":
                            continue
                        else:
                            st.markdown(f"**{k}:** `{v}`")
                with cb:
                    sent = ticket.get("sentiment", "?")
                    emoji = {"positive": "😊", "neutral": "😐", "frustrated": "😤", "angry": "😡"}.get(sent, "🤷")
                    st.markdown(f"**Sentiment:** {emoji} {sent}")
                    st.markdown(f"**Issue:** `{ticket.get('issue_type', '?')}`")
                    if show_raw_json:
                        st.code(json.dumps(ticket, indent=2, ensure_ascii=False), language="json")

        # Stage 2
        status.info("🧠 Stage 2: REASON — Analyzing with chain-of-thought...")
        decision = pl.stage2_reason(ticket)
        with results:
            with st.expander("🧠 **Stage 2: REASON** (chain-of-thought)", expanded=True):
                ca, cb = st.columns([1, 1])
                with ca:
                    p = decision.get("priority", "?")
                    p_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🟢"}.get(p, "⚪")
                    st.markdown(f"**Priority:** {p_emoji} **{p}**")
                    st.markdown(f"**Route:** `{decision.get('route', '?')}`")
                    st.markdown(f"**Urgency:** {decision.get('urgency_score', '?')}/10")
                with cb:
                    st.markdown(f"**Effort:** `{decision.get('estimated_effort', '?')}`")
                    if show_raw_json:
                        st.code(json.dumps(decision, indent=2, ensure_ascii=False), language="json")
                st.markdown("**Reasoning:**")
                st.info(decision.get("reasoning", "No reasoning provided."))

        # Stage 3
        status.info("✍️ Stage 3: PRODUCE — Drafting reply...")
        reply = pl.stage3_produce(ticket, decision)
        with results:
            with st.expander("✍️ **Stage 3: PRODUCE** (goal-oriented + constraints)", expanded=True):
                st.markdown("**Drafted reply:**")
                wc = len(reply.split())
                st.markdown(
                    f'<div style="background:#f0f2f6;padding:1.2rem;border-radius:0.5rem;'
                    f'border-left:4px solid #4CAF50;font-size:1.05rem;line-height:1.6;">'
                    f'{reply}</div>',
                    unsafe_allow_html=True,
                )

        # Stage 4
        if enable_critique:
            status.info("📋 Stage 4: CRITIQUE — Self-checking reply...")
            passed, improved = pl.stage4_critique(ticket, decision, reply)
            with results:
                label = "📋 **Stage 4: CRITIQUE** (self-check)" + (" ✅ Passed" if passed else " 🔄 Redone")
                with st.expander(label, expanded=True):
                    if passed:
                        st.success("✅ Reply passed quality check!")
                    else:
                        st.warning("⚠️ Failed first check — re-ran with suggestions")
                    st.markdown("**Final reply:**")
                    wc = len(improved.split())
                    st.markdown(
                        f'<div style="background:#f0f2f6;padding:1.2rem;border-radius:0.5rem;'
                        f'border-left:4px solid #2196F3;font-size:1.05rem;line-height:1.6;">'
                        f'{improved}</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"📝 {wc} words  ·  {'✅ Under 120' if wc <= 120 else '⚠️ Over 120'}")
            reply = improved

    status.success("✅ Pipeline complete!")
    st.divider()
    st.subheader("📊 Summary")

    sc = st.columns(4)
    p = decision.get("priority", "?")
    p_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🟢"}.get(p, "⚪")
    sc[0].metric("Priority", f"{p_emoji} {p}")
    sc[1].metric("Issue", ticket.get("issue_type", "?").replace("_", " ").title())
    s = ticket.get("sentiment", "?")
    s_emoji = {"positive": "😊", "neutral": "😐", "frustrated": "😤", "angry": "😡"}.get(s, "🤷")
    sc[2].metric("Sentiment", f"{s_emoji} {s.title()}")
    sc[3].metric("Route", decision.get("route", "?"))

    st.markdown("---")
    st.markdown("**Raw data (JSON):**")
    t1, t2, t3 = st.tabs(["Ticket 📥", "Decision 🧠", "Reply ✍️"])
    with t1:
        st.json(ticket)
    with t2:
        st.json(decision)
    with t3:
        st.json({"reply": reply, "word_count": len(reply.split())})

    status.empty()

else:
    st.info(
        "👈 **Get started:** Enter your API key in the sidebar, "
        "choose a preset example, then click **Run Pipeline**."
    )
    with st.expander("💡 What is this?"):
        st.markdown("""
        A **prompt-only task completer** — a chain of 3-4 LLM prompts that
        turn a raw customer message into a structured triage + drafted reply.

        **Stages:**
        1. **UNDERSTAND** (role + structured output) — extracts facts → JSON
        2. **REASON** (chain-of-thought) — analyzes → priority + route
        3. **PRODUCE** (goal-oriented + constraints) — writes reply ≤120 words
        4. **CRITIQUE** (self-check) — grades the reply, can trigger redo

        Each stage is a separate LLM call. JSON is the currency between them.
        """)
    with st.expander("🔐 How is my API key handled?"):
        st.markdown("""
        Your API key is:
        - Only stored in memory for this session
        - Never written to disk or logged
        - Only sent to OpenRouter's API
        - Cleared when you close the browser tab
        """)
                st.caption(f"📝 {wc} words  ·  {'✅ Under 120' if wc <= 120 else '⚠️ Over 120'}")
