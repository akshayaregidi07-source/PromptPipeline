"""
╔══════════════════════════════════════════════════════════════════╗
║  Tasks — All 7 Pipeline Task Definitions                        ║
║  Each task defines: input format, stages, prompts, schemas      ║
╚══════════════════════════════════════════════════════════════════╝
"""

from typing import Any

# ─── Stage Definition ─────────────────────────────────────────
# Each stage has: name, technique, description, prompt_template, input_schema, output_schema

STAGE_INFO = {
    1: {
        "name": "UNDERSTAND",
        "technique": "Role Prompting + Structured Output",
        "technique_short": "role",
        "description": "Extract structured facts from raw input using a role-specific persona. This stage converts unstructured text into a well-defined JSON schema.",
        "purpose": "Transform raw, unstructured input into structured data that downstream stages can reliably process.",
        "best_practice": "Define a clear schema with field descriptions. Use a specific role persona. Instruct the model to return ONLY valid JSON.",
    },
    2: {
        "name": "REASON",
        "technique": "Chain-of-Thought (CoT)",
        "technique_short": "cot",
        "description": "Analyze the structured data step-by-step, showing reasoning before producing the final output.",
        "purpose": "Encourage the model to think through the problem systematically, improving accuracy and explainability.",
        "best_practice": "Ask the model to 'think step by step' internally. Show the reasoning in the output for transparency.",
    },
    3: {
        "name": "PRODUCE",
        "technique": "Goal-Oriented + Constraints",
        "technique_short": "goal",
        "description": "Generate the final output with specific goals and constraints to guide quality and format.",
        "purpose": "Produce the final deliverable with clear quality criteria, length limits, and tone requirements.",
        "best_practice": "Define explicit goals, constraints (word count, tone, format), and success criteria in the prompt.",
    },
    4: {
        "name": "CRITIQUE",
        "technique": "Self-Reflection / Critique",
        "technique_short": "critique",
        "description": "Review the output against a quality checklist. Optionally trigger a redo if standards aren't met.",
        "purpose": "Catch errors, improve quality, and ensure the output meets all requirements before delivery.",
        "best_practice": "Use a specific checklist. Grade each criterion. If failed, provide actionable feedback for improvement.",
    },
}

# ─── All 7 Task Definitions ──────────────────────────────────

TASKS = {
    "support_ticket": {
        "name": "Support Ticket Triage",
        "icon": "🎫",
        "description": "Analyze a customer support message, triage the issue, and draft a professional reply.",
        "input_format": "Raw customer message (free text)",
        "example_input": "My order #ORD-7842 was supposed to arrive 5 days ago. Tracking says it's been 'in transit' for a week. I need this for my daughter's birthday tomorrow. This is really frustrating. — Karen Mitchell",
        "input_placeholder": "Paste a customer support message here...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract structured facts from the raw customer message using a support ticket intake specialist persona.",
                "purpose": "Transform unstructured text into structured JSON that downstream stages can reliably process.",
                "input_schema": "Raw customer message (free text)",
                "output_schema": "{customer_name, contact_info, order_id, issue_type, issue_summary, days_waiting, sentiment, key_phrases}",
                "best_practice": "Define a clear schema with field descriptions. Use a specific role persona. Instruct the model to return ONLY valid JSON.",
                "prompt_template": """You are a support ticket intake specialist. Your ONLY job is to read a raw customer message and extract structured facts from it.

Return a JSON object with these exact fields (use null or "unknown" for anything missing):

{{
  "customer_name": "Full name or username, or 'unknown'",
  "contact_info": "Email or phone if mentioned, else 'unknown'",
  "order_id": "Order / transaction / reference ID, or 'unknown'",
  "issue_type": "One of: billing | shipping | product_defect | account_access | cancellation | general_inquiry | other",
  "issue_summary": "One concise sentence describing the core issue",
  "days_waiting": "Number (0 if not mentioned or same-day)",
  "sentiment": "One of: positive | neutral | frustrated | angry",
  "key_phrases": "Array of 2-4 short phrases that capture the customer's main concerns"
}}

RULES:
- Be factual — do NOT guess or invent details.
- If the message is gibberish, spam, or not in English, set issue_type = "unprocessable" and leave other fields as "unknown" / null / empty array.
- Return ONLY valid JSON. No markdown fences. No extra text.

CUSTOMER MESSAGE:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Analyze the ticket step-by-step to determine priority, routing, and urgency.",
                "purpose": "Apply systematic reasoning to triage the issue correctly.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{priority, route, estimated_effort, urgency_score, reasoning}",
                "best_practice": "Guide the model through explicit reasoning steps. Show the thinking process in the output.",
                "prompt_template": """You are a senior support triage analyst. You will receive a structured ticket brief (JSON) extracted from a customer message.

Your job: think step by step, then decide the priority, the team to route to, and the estimated effort.

Think through these steps internally before you write your answer:
1. What type of issue is this? (billing, shipping, product defect, account, etc.)
2. How severe is the impact on the customer? (blocked from using product? lost money? minor annoyance?)
3. What is the sentiment — angry customers need faster response.
4. How long have they been waiting?
5. Combine these factors into a priority level.
6. Which team or department should handle this?
7. Is this a quick fix or a deep investigation?

Return a JSON object with these exact fields:

{{
  "priority": "P1 | P2 | P3",
  "route": "Name of the team that should handle this",
  "estimated_effort": "low | medium | high",
  "urgency_score": "1-10 (10 = most urgent)",
  "reasoning": "Your full step-by-step reasoning — show every thought"
}}

PRIORITY GUIDE:
- P1 = blocking the customer from working / money lost / angry sentiment / security issue
- P2 = significant inconvenience but workaround exists / frustrated but not angry
- P3 = minor issue / general inquiry / positive or neutral sentiment

Return ONLY valid JSON. No markdown fences. No extra text.

TICKET BRIEF:
---
{input}
---""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Draft a professional support reply based on the ticket and triage decision.",
                "purpose": "Generate the final customer-facing response with specific quality constraints.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Reply text (≤120 words, empathetic, actionable)",
                "best_practice": "Set explicit goals (empathetic, professional) and constraints (word limit, tone matching).",
                "prompt_template": """You are a professional customer support writer. Draft a reply to a customer based on their ticket information and the triage decision.

GOALS:
- Be empathetic and professional.
- Address the customer's core concern directly.
- Set clear expectations — never promise something you can't guarantee (e.g. refund timelines, ship dates).
- Keep it at most 120 words.
- Match the tone to the customer's sentiment (if they're angry, acknowledge the frustration; if neutral, be warm).
- Include a specific next step or what the customer can expect.
- If the issue is unprocessable (gibberish / spam), politely ask for clarification.

Return ONLY the reply text — no JSON, no explanations, no markdown fences.

TICKET INFORMATION:
{ticket}

TRIAGE DECISION:
{decision}""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the reply against a quality checklist. Optionally trigger a redo.",
                "purpose": "Catch errors, improve quality, and ensure the output meets all requirements.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, word_count, issues, suggested_improvements}",
                "best_practice": "Use a specific checklist. Grade each criterion. If failed, provide actionable feedback.",
                "prompt_template": """You are a quality assurance reviewer for customer support replies. Grade the following reply and decide if it's good enough to send.

CHECKLIST (pass all to approve):
1. Under 120 words? (count them)
2. Addresses the customer's specific issue?
3. Empathetic and professional tone?
4. No false promises / unverifiable claims?
5. Includes a clear next step or expectation?
6. Appropriate for the customer's sentiment?

TICKET:
{ticket}

DECISION:
{decision}

DRAFT REPLY:
{reply}

Return a JSON object:
{{
  "passed": true | false,
  "word_count": <number>,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

If NOT passed, I will re-run Stage 3 with your suggestions.
Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "essay_grader": {
        "name": "Essay Grader",
        "icon": "📝",
        "description": "Grade a student essay with structured rubric, detailed feedback, and improvement suggestions.",
        "input_format": "Student essay text",
        "example_input": "Write an essay about the impact of social media on modern society. Discuss both positive and negative effects, and provide your opinion on whether social media has been more beneficial or harmful.\n\nSocial media has fundamentally transformed how we communicate, share information, and build relationships in the 21st century. While platforms like Facebook, Twitter, and Instagram have connected billions of people worldwide, they have also introduced new challenges that society is still grappling with...",
        "input_placeholder": "Paste a student essay here...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract essay structure, thesis, arguments, and quality indicators.",
                "purpose": "Parse the essay into analyzable components for grading.",
                "input_schema": "Raw essay text",
                "output_schema": "{essay_length_words, thesis_statement, main_arguments, evidence_quality, structure, grammar_issues, tone}",
                "best_practice": "Use a teacher/grader persona. Define clear quality criteria.",
                "prompt_template": """You are an experienced essay grader and teaching assistant. Extract the following structured information from the student essay below.

Return a JSON object with these exact fields:

{{
  "essay_length_words": "Estimated word count (number)",
  "thesis_statement": "The main thesis or central argument, or 'not clearly stated'",
  "main_arguments": "Array of 2-4 key arguments presented",
  "evidence_quality": "One of: excellent | good | adequate | poor | none",
  "structure": "One of: well_structured | adequate | disorganized",
  "grammar_issues": "Number of grammar/spelling issues spotted (0 if none)",
  "tone": "One of: academic | persuasive | narrative | informal | mixed",
  "strengths": "Array of 2-3 strengths of the essay",
  "weaknesses": "Array of 2-3 areas for improvement"
}}

RULES:
- Be objective and fair in assessment.
- If the essay is too short or nonsensical, set structure = "unprocessable".
- Return ONLY valid JSON. No markdown fences. No extra text.

ESSAY:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Grade the essay step-by-step using a rubric, then produce scores and feedback.",
                "purpose": "Apply systematic grading with transparent reasoning.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{overall_score, rubric_scores, strengths, weaknesses, grade, feedback}",
                "best_practice": "Use a detailed rubric. Show reasoning for each score component.",
                "prompt_template": """You are a fair and thorough essay grader. You will receive a structured essay analysis (JSON). Your job is to grade the essay step by step.

Think through these steps:
1. Evaluate the thesis: Is it clear, specific, and arguable?
2. Evaluate the arguments: Are they logical, well-supported, and relevant?
3. Evaluate evidence quality: Are claims backed by examples, data, or reasoning?
4. Evaluate structure: Does the essay flow logically with clear transitions?
5. Evaluate grammar and style: Are there errors? Is the tone appropriate?
6. Assign a score out of 10 for each criterion.
7. Calculate an overall score.
8. Identify the top 2 strengths and top 2 weaknesses.

Return a JSON object with these exact fields:

{{
  "overall_score": "Score out of 10 (e.g., 7.5)",
  "rubric": {{
    "thesis_clarity": "Score 1-10",
    "argument_quality": "Score 1-10",
    "evidence_use": "Score 1-10",
    "structure_organization": "Score 1-10",
    "grammar_style": "Score 1-10"
  }},
  "strengths": "Array of 2-3 specific strengths",
  "weaknesses": "Array of 2-3 specific areas for improvement",
  "grade": "One of: A | B | C | D | F",
  "feedback": "Constructive feedback paragraph for the student",
  "reasoning": "Your step-by-step reasoning for each score"
}}

Return ONLY valid JSON. No markdown fences. No extra text.

ESSAY ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate a detailed grading report with scores, feedback, and improvement suggestions.",
                "purpose": "Produce the final grading output with clear, actionable feedback.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Grading report with scores, feedback, and suggestions",
                "best_practice": "Set explicit goals for feedback quality, tone, and actionability.",
                "prompt_template": """You are a helpful and constructive teacher. Based on the essay analysis and grading rubric below, produce a final grading report.

GOALS:
- Be encouraging and constructive in your feedback.
- Provide specific, actionable suggestions for improvement.
- Highlight strengths as well as areas for growth.
- Keep the feedback supportive and professional.
- Format the report clearly with sections.

ESSAY ANALYSIS:
{stage1}

GRADING RUBRIC:
{stage2}

Return a JSON object with these exact fields:

{{
  "overall_score": "Score out of 10 (e.g., 7.5)",
  "letter_grade": "A | B | C | D | F",
  "rubric_breakdown": {{
    "thesis_clarity": "Score 1-10",
    "argument_quality": "Score 1-10",
    "evidence_use": "Score 1-10",
    "organization": "Score 1-10",
    "grammar_style": "Score 1-10"
  }},
  "strengths": "Array of 2-3 specific strengths",
  "weaknesses": "Array of 2-3 specific areas for improvement",
  "feedback": "Detailed, constructive feedback paragraph for the student",
  "improvement_suggestions": "Array of 2-3 actionable improvement suggestions"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the grading report for fairness, accuracy, and completeness.",
                "purpose": "Ensure the grading is fair, constructive, and meets educational standards.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for bias, fairness, and constructive tone in feedback.",
                "prompt_template": """You are a senior educator reviewing a grading report. Evaluate the following grading output for quality and fairness.

CHECKLIST:
1. Is the feedback constructive and encouraging?
2. Are scores justified by the essay analysis?
3. Are improvement suggestions specific and actionable?
4. Is the tone appropriate for a student?
5. Is the overall grade fair based on the rubric?

ESSAY ANALYSIS:
{stage1}

GRADING REPORT:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "bug_report": {
        "name": "Bug Report Triage",
        "icon": "🐛",
        "description": "Analyze a bug report, determine severity, root cause, and suggest a fix approach.",
        "input_format": "Raw bug report (free text)",
        "example_input": "When I click the 'Save' button on the profile page, the page crashes with a white screen. This happens every time I try to save my settings. I'm using Chrome 120 on Windows 11. This is blocking my work. — Priya",
        "input_placeholder": "Paste a bug report here...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract structured bug report data from raw description.",
                "purpose": "Parse the bug report into structured fields for analysis.",
                "input_schema": "Raw bug report text",
                "output_schema": "{reporter, feature, environment, steps_to_reproduce, expected_behavior, actual_behavior, frequency, severity}",
                "best_practice": "Use a QA engineer persona. Extract all technical details precisely.",
                "prompt_template": """You are a senior QA engineer. Extract structured bug report data from the following raw bug description.

Return a JSON object with these exact fields:

{{
  "reporter": "Name or username, or 'unknown'",
  "feature": "The feature or page where the bug occurs",
  "environment": "Browser, OS, device info if mentioned, else 'unknown'",
  "steps_to_reproduce": "Array of step-by-step instructions to reproduce the bug",
  "expected_behavior": "What should happen",
  "actual_behavior": "What actually happens",
  "frequency": "One of: always | sometimes | rarely | once | unknown",
  "severity": "One of: critical | high | medium | low | cosmetic",
  "impact": "Description of the impact on the user or system"
}}

RULES:
- Be precise. Extract only what is stated.
- If the report is unclear, set severity = "unknown".
- Return ONLY valid JSON. No markdown fences. No extra text.

BUG REPORT:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Analyze the bug step-by-step to determine root cause, priority, and fix approach.",
                "purpose": "Apply systematic debugging reasoning to triage the bug correctly.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{root_cause, priority, assigned_team, fix_approach, workaround, reasoning}",
                "best_practice": "Guide the model through debugging steps: reproduce → isolate → identify cause → plan fix.",
                "prompt_template": """You are a senior software engineer debugging a reported bug. Analyze the bug report step by step.

Think through these steps:
1. What component or feature is affected?
2. What could cause this behavior? List possible root causes.
3. How severe is the impact? (blocking users? data loss? cosmetic?)
4. What team should handle this?
5. What is the best approach to fix it?
6. Is there a temporary workaround?

Return a JSON object with these exact fields:

{{
  "root_cause": "Likely root cause of the bug",
  "priority": "P1 | P2 | P3",
  "assigned_team": "Team that should fix this",
  "fix_approach": "Recommended approach to fix the bug",
  "workaround": "Temporary workaround if available, or 'none'",
  "estimated_fix_time": "One of: hours | days | weeks | unknown",
  "reasoning": "Your step-by-step debugging reasoning"
}}

PRIORITY GUIDE:
- P1 = blocking users / data loss / security issue / crash
- P2 = major feature broken but workaround exists
- P3 = minor issue / cosmetic / edge case

Return ONLY valid JSON. No markdown fences. No extra text.

BUG ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate a structured bug report with fix recommendations.",
                "purpose": "Produce a clear, actionable bug report for developers.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Structured bug report with fix recommendations",
                "best_practice": "Set explicit goals for clarity, actionability, and technical accuracy.",
                "prompt_template": """You are a technical lead writing a bug report for your development team. Based on the bug analysis and triage decision below, produce a clear, actionable bug report.

GOALS:
- Be technically precise and clear.
- Include exact steps to reproduce.
- State the root cause clearly.
- Provide a recommended fix approach.
- Note any workarounds.
- Keep it concise but complete.

BUG ANALYSIS:
{stage1}

TRIAGE DECISION:
{stage2}

Return a JSON object with these exact fields:

{{
  "title": "Concise bug title",
  "severity": "critical | high | medium | low | cosmetic",
  "priority": "P1 | P2 | P3",
  "environment": "Affected environment details",
  "steps_to_reproduce": "Array of steps",
  "expected_vs_actual": "Expected vs actual behavior",
  "root_cause": "Likely root cause",
  "fix_recommendation": "Recommended fix approach",
  "workaround": "Temporary workaround if available, or 'none'",
  "assigned_team": "Team to handle this"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the bug report for completeness, clarity, and actionability.",
                "purpose": "Ensure the bug report is complete and actionable for developers.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for missing reproduction steps, unclear environment details, and actionable fix recommendations.",
                "prompt_template": """You are a QA lead reviewing a bug report before it goes to the development team. Evaluate the following bug report.

CHECKLIST:
1. Are steps to reproduce clear and complete?
2. Is the environment specified?
3. Is the root cause analysis plausible?
4. Is the fix recommendation actionable?
5. Is the severity/priority appropriate?

BUG ANALYSIS:
{stage1}

BUG REPORT:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "meeting_notes": {
        "name": "Meeting Notes → Action Items",
        "icon": "📋",
        "description": "Convert meeting notes into structured action items with assignees, priorities, and deadlines.",
        "input_format": "Raw meeting notes (free text)",
        "example_input": "Team standup - 2024-03-15\n\nPresent: Alice, Bob, Charlie, Diana\n\nAlice: Finished the login redesign. Needs design review from Bob.\nBob: Working on API integration. Blocked on auth tokens from DevOps.\nCharlie: Database migration complete. Ready for testing.\nDiana: User testing scheduled for Friday. Need 3 more participants.\n\nDecisions:\n- Sprint review moved to Thursday 3pm\n- Feature freeze starts next Monday",
        "input_placeholder": "Paste meeting notes here...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract participants, topics, decisions, and action items from meeting notes.",
                "purpose": "Parse unstructured meeting notes into structured data for action item extraction.",
                "input_schema": "Raw meeting notes text",
                "output_schema": "{meeting_date, participants, topics_discussed, decisions_made, action_items_raw, blockers}",
                "best_practice": "Use a meeting scribe persona. Capture both explicit and implicit action items.",
                "prompt_template": """You are a professional meeting scribe. Extract structured information from the following meeting notes.

Return a JSON object with these exact fields:

{{
  "meeting_date": "Date if mentioned, else 'unknown'",
  "participants": "Array of participant names, or empty array if none listed",
  "topics_discussed": "Array of 2-5 key topics discussed",
  "decisions_made": "Array of decisions made during the meeting",
  "action_items_raw": "Array of action items mentioned, each as a string",
  "blockers": "Array of blockers or issues raised, or empty array",
  "next_steps": "Array of next steps mentioned"
}}

RULES:
- Extract only what is stated or clearly implied.
- If notes are minimal, use empty arrays for missing fields.
- Return ONLY valid JSON. No markdown fences. No extra text.

MEETING NOTES:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Analyze meeting notes to identify clear action items, assign owners, and set priorities.",
                "purpose": "Convert raw action items into structured, assignable tasks.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{action_items, decisions_summary, follow_up_needed, reasoning}",
                "best_practice": "Infer owners from context. Prioritize based on urgency and dependencies.",
                "prompt_template": """You are a project manager analyzing meeting notes. Convert the raw action items and discussion into structured, assignable tasks.

Think through these steps:
1. What decisions were made that need follow-up?
2. For each action item: who is responsible? What is the task? When is it needed?
3. What is the priority of each action item?
4. Are there any blockers that need escalation?
5. What needs follow-up in the next meeting?

Return a JSON object with these exact fields:

{{
  "action_items": [
    {{
      "task": "Description of the task",
      "assignee": "Assigned person, or 'unassigned'",
      "priority": "high | medium | low",
      "deadline": "Deadline if mentioned, or 'not specified'",
      "dependencies": "Any blockers or dependencies, or 'none'"
    }}
  ],
  "decisions_summary": "Summary of key decisions made",
  "follow_up_needed": "What needs follow-up in the next meeting",
  "unresolved_issues": "Array of unresolved issues or questions",
  "reasoning": "Your step-by-step reasoning for each assignment and priority"
}}

Return ONLY valid JSON. No markdown fences. No extra text.

MEETING ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate a clean action items summary with owners, priorities, and deadlines.",
                "purpose": "Produce a clear, actionable meeting summary for the team.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Formatted action items and meeting summary",
                "best_practice": "Set explicit goals for clarity, actionability, and completeness.",
                "prompt_template": """You are a project manager creating a meeting summary. Based on the meeting analysis and action items below, produce a clean, actionable summary.

GOALS:
- List all action items clearly with owners and priorities.
- Summarize key decisions made.
- Note any blockers or unresolved issues.
- Format for easy reading by the team.
- Be concise but complete.

MEETING ANALYSIS:
{stage1}

ACTION ITEMS:
{stage2}

Return a JSON object with these exact fields:

{{
  "meeting_summary": "Brief 2-3 sentence summary of the meeting",
  "key_decisions": "Array of key decisions made",
  "action_items": [
    {{
      "task": "Description of the task",
      "assignee": "Assigned person",
      "priority": "high | medium | low",
      "deadline": "Deadline if specified, or 'not set'"
    }}
  ],
  "blockers": "Array of blockers that need escalation",
  "next_meeting_agenda": "Suggested agenda items for next meeting"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the meeting summary for completeness and actionability.",
                "purpose": "Ensure all action items are captured and clearly assigned.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for missing assignees, unclear deadlines, and unresolved blockers.",
                "prompt_template": """You are a project manager reviewing a meeting summary. Evaluate the following output.

CHECKLIST:
1. Are all action items clearly stated with owners?
2. Are priorities assigned appropriately?
3. Are blockers and unresolved issues noted?
4. Is the summary concise and actionable?
5. Are decisions clearly documented?

MEETING ANALYSIS:
{stage1}

MEETING SUMMARY:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "recipe_adapter": {
        "name": "Recipe Adapter",
        "icon": "🍳",
        "description": "Adapt a recipe for dietary restrictions, serving size changes, and ingredient substitutions.",
        "input_format": "Recipe description + adaptation requirements",
        "example_input": "Recipe: Classic Chocolate Chip Cookies\n\nIngredients:\n- 2 1/4 cups all-purpose flour\n- 1 cup butter, softened\n- 3/4 cup sugar\n- 3/4 cup brown sugar\n- 2 large eggs\n- 1 tsp vanilla extract\n- 1 tsp baking soda\n- 1/2 tsp salt\n- 2 cups chocolate chips\n\nAdaptation needed: Make it vegan and gluten-free. Serve 4 people instead of 12.",
        "input_placeholder": "Paste a recipe and adaptation requirements...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract recipe structure, ingredients, and adaptation requirements.",
                "purpose": "Parse the recipe into structured components for adaptation.",
                "input_schema": "Raw recipe text + adaptation needs",
                "output_schema": "{recipe_name, ingredients, instructions, original_servings, dietary_restrictions, adaptation_goals, serving_target}",
                "best_practice": "Use a chef persona. Capture all ingredients with precise quantities.",
                "prompt_template": """You are a professional chef and recipe analyst. Extract structured information from the following recipe and adaptation request.

Return a JSON object with these exact fields:

{{
  "recipe_name": "Name of the recipe, or 'unknown'",
  "ingredients": "Array of {name, quantity, unit} objects",
  "instructions": "Array of step-by-step instructions",
  "original_servings": "Number of servings (number, or 0 if unknown)",
  "cooking_time_minutes": "Total cooking time in minutes (number, or 0 if unknown)",
  "dietary_tags": "Array of dietary tags (e.g., vegetarian, contains dairy), or empty array",
  "adaptation_goals": "Array of adaptation requirements (e.g., vegan, gluten-free, serving change)",
  "serving_target": "Target number of servings if specified, or null"
}}

RULES:
- Extract ingredients with their quantities and units precisely.
- If no adaptation is requested, set adaptation_goals to empty array.
- Return ONLY valid JSON. No markdown fences. No extra text.

RECIPE & ADAPTATION REQUEST:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Analyze the recipe and plan adaptations step-by-step.",
                "purpose": "Plan ingredient substitutions, quantity adjustments, and technique modifications.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{substitutions, quantity_adjustments, technique_changes, challenges, reasoning}",
                "best_practice": "Consider dietary science, flavor profiles, and cooking techniques in reasoning.",
                "prompt_template": """You are a creative chef specializing in dietary adaptations. Analyze the recipe and plan the necessary adaptations step by step.

Think through these steps:
1. What ingredients need to be substituted for the dietary restrictions?
2. What are the best substitutes that maintain flavor and texture?
3. How do serving size changes affect quantities?
4. What cooking technique adjustments are needed?
5. What challenges might arise with these substitutions?
6. How will the final result differ from the original?

Return a JSON object with these exact fields:

{{
  "substitutions": [
    {{
      "original": "Original ingredient",
      "replacement": "Replacement ingredient",
      "ratio": "Replacement ratio (e.g., 1:1, 1:2)",
      "reason": "Why this substitution works"
    }}
  ],
  "quantity_adjustments": "Description of quantity changes for serving size",
  "technique_changes": "Array of cooking technique adjustments needed",
  "challenges": "Array of potential challenges with the adaptations",
  "expected_difference": "How the adapted recipe will differ from the original",
  "reasoning": "Your step-by-step reasoning for each adaptation decision"
}}

Return ONLY valid JSON. No markdown fences. No extra text.

RECIPE ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate the adapted recipe with substitutions, modified instructions, and notes.",
                "purpose": "Produce a complete, usable adapted recipe.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Adapted recipe with substitutions and modified instructions",
                "best_practice": "Set explicit goals for usability, clarity, and taste preservation.",
                "prompt_template": """You are a creative chef presenting an adapted recipe. Based on the recipe analysis and adaptation plan, produce the final adapted recipe.

GOALS:
- Present the adapted recipe clearly with all substitutions.
- Include modified quantities for the target serving size.
- Note any changes in cooking technique or timing.
- Explain what to expect in terms of taste/texture differences.
- Be encouraging and helpful for the cook.

RECIPE ANALYSIS:
{stage1}

ADAPTATION PLAN:
{stage2}

Return a JSON object with these exact fields:

{{
  "adapted_recipe_name": "Name of the adapted recipe",
  "servings": "Target serving size",
  "ingredients": "Array of {name, quantity, unit, notes} objects",
  "instructions": "Array of modified step-by-step instructions",
  "substitution_notes": "Array of notes explaining key substitutions",
  "tips": "Array of cooking tips for the adapted recipe",
  "expected_result": "Description of how the final dish should look/taste",
  "challenges": "Array of potential challenges and how to overcome them"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the adapted recipe for feasibility, taste preservation, and completeness.",
                "purpose": "Ensure the adapted recipe is practical and will produce good results.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for realistic substitutions, correct quantities, and clear instructions.",
                "prompt_template": """You are a master chef reviewing an adapted recipe. Evaluate the following adapted recipe.

CHECKLIST:
1. Are the substitutions appropriate for the dietary restrictions?
2. Are the quantities correct for the target serving size?
3. Are the instructions clear and followable?
4. Will the adapted recipe produce a good result?
5. Are potential challenges addressed?

RECIPE ANALYSIS:
{stage1}

ADAPTED RECIPE:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "trip_planner": {
        "name": "Trip Planner",
        "icon": "✈️",
        "description": "Plan a trip based on destination, budget, preferences, and constraints.",
        "input_format": "Trip request with destination, budget, preferences",
        "example_input": "Plan a 5-day trip to Tokyo, Japan. Budget: $2000. Interests: food, technology, culture. I want a mix of modern and traditional experiences. I'm traveling solo.",
        "input_placeholder": "Describe your trip requirements...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Extract trip requirements, preferences, and constraints.",
                "purpose": "Parse the trip request into structured planning data.",
                "input_schema": "Raw trip request text",
                "output_schema": "{destination, duration_days, budget, budget_level, traveler_type, interests, preferences, constraints}",
                "best_practice": "Use a travel planner persona. Capture all explicit and implicit requirements.",
                "prompt_template": """You are an expert travel planner. Extract structured information from the following trip request.

Return a JSON object with these exact fields:

{{
  "destination": "Destination city/country, or 'unknown'",
  "duration_days": "Number of days (number, or 0 if unknown)",
  "budget": "Budget amount and currency if mentioned, or 'not specified'",
  "budget_level": "One of: budget | mid_range | luxury | not_specified",
  "traveler_type": "One of: solo | couple | family | group | business | not_specified",
  "interests": "Array of interests (e.g., food, culture, nature, shopping, technology)",
  "preferences": "Array of specific preferences mentioned",
  "constraints": "Array of constraints (dietary, mobility, time, etc.), or empty array",
  "season": "Preferred travel season if mentioned, or 'not specified'"
}}

RULES:
- Extract only what is stated or clearly implied.
- If the request is vague, use reasonable defaults.
- Return ONLY valid JSON. No markdown fences. No extra text.

TRIP REQUEST:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Plan the trip itinerary step-by-step considering budget, interests, and logistics.",
                "purpose": "Create a well-reasoned itinerary that balances activities, budget, and travel time.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{daily_itinerary, budget_breakdown, recommendations, reasoning}",
                "best_practice": "Consider travel time between locations, budget allocation, and activity variety.",
                "prompt_template": """You are an expert travel planner creating a detailed itinerary. Plan the trip step by step.

Think through these steps:
1. What are the must-see attractions and experiences based on the traveler's interests?
2. How to organize activities by day for logical flow and minimal travel time?
3. How to allocate the budget across accommodation, food, activities, and transport?
4. What are good restaurant recommendations for the traveler's preferences?
5. What practical tips (transport, culture, safety) should be included?
6. What is a realistic pace that doesn't exhaust the traveler?

Return a JSON object with these exact fields:

{{
  "daily_itinerary": [
    {{
      "day": 1,
      "theme": "Theme for the day (e.g., 'Modern Tokyo')",
      "morning": "Morning activity",
      "afternoon": "Afternoon activity",
      "evening": "Evening activity",
      "meals": "Restaurant recommendations for meals",
      "estimated_cost": "Estimated cost for the day"
    }}
  ],
  "budget_breakdown": {{
    "accommodation": "Estimated cost",
    "food": "Estimated cost",
    "activities": "Estimated cost",
    "transport": "Estimated cost",
    "miscellaneous": "Estimated cost",
    "total": "Total estimated cost"
  }},
  "accommodation_recommendations": "Array of 2-3 accommodation suggestions",
  "transport_tips": "Transportation advice for the destination",
  "packing_tips": "Array of packing suggestions based on destination and activities",
  "reasoning": "Your step-by-step planning reasoning"
}}

Return ONLY valid JSON. No markdown fences. No extra text.

TRIP ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate a complete trip itinerary with daily plans, budget, and recommendations.",
                "purpose": "Produce a polished, usable travel itinerary.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Complete trip itinerary with daily plans and budget",
                "best_practice": "Set explicit goals for realism, budget adherence, and activity variety.",
                "prompt_template": """You are a travel consultant presenting a final trip plan. Based on the trip analysis and itinerary plan, produce a complete, polished travel itinerary.

GOALS:
- Present a day-by-day itinerary that's realistic and enjoyable.
- Include specific recommendations (restaurants, attractions, tips).
- Respect the budget constraints.
- Balance activities with free time.
- Include practical travel tips.

TRIP ANALYSIS:
{stage1}

ITINERARY PLAN:
{stage2}

Return a JSON object with these exact fields:

{{
  "destination_overview": "Brief description of the destination",
  "daily_plan": [
    {{
      "day": 1,
      "date": "Day theme or date",
      "morning": "Morning activity with details",
      "afternoon": "Afternoon activity with details",
      "evening": "Evening activity with details",
      "meal_recommendations": "Restaurant or food recommendations",
      "estimated_cost": "Estimated cost for the day"
    }}
  ],
  "budget_summary": {{
    "accommodation": "Estimated cost",
    "food_dining": "Estimated cost",
    "activities": "Estimated cost",
    "transportation": "Estimated cost",
    "miscellaneous": "Estimated cost",
    "total": "Total estimated cost",
    "remaining_budget": "Budget remaining if applicable"
  }},
  "practical_tips": "Array of practical travel tips",
  "packing_list": "Array of recommended items to pack"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the trip plan for realism, budget adherence, and completeness.",
                "purpose": "Ensure the itinerary is practical, enjoyable, and within budget.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for realistic pacing, budget accuracy, and activity variety.",
                "prompt_template": """You are a travel reviewer evaluating a trip itinerary. Review the following trip plan.

CHECKLIST:
1. Is the daily pace realistic (not too packed)?
2. Does it match the traveler's interests?
3. Is the budget allocation reasonable?
4. Are there practical tips for the destination?
5. Is there a good balance of activities?

TRIP ANALYSIS:
{stage1}

TRIP PLAN:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
    "programming_assistant": {
        "name": "Programming Assistant",
        "icon": "💻",
        "description": "Analyze a programming problem, design a solution, and generate code with explanations.",
        "input_format": "Programming problem description",
        "example_input": "Write a Python function that finds the longest palindromic substring in a given string. The function should be efficient (better than O(n^2)) and handle edge cases like empty strings and single characters.",
        "input_placeholder": "Describe the programming problem...",
        "stages": [
            {
                "name": "UNDERSTAND",
                "technique": "Role Prompting + Structured Output",
                "technique_short": "role",
                "description": "Analyze the programming problem and extract requirements.",
                "purpose": "Parse the problem into structured requirements for solution design.",
                "input_schema": "Raw programming problem text",
                "output_schema": "{problem_statement, programming_language, input_format, output_format, constraints, examples, difficulty}",
                "best_practice": "Use a senior developer persona. Capture all technical requirements precisely.",
                "prompt_template": """You are a senior software engineer and technical analyst. Extract structured information from the following programming problem.

Return a JSON object with these exact fields:

{{
  "problem_statement": "Concise restatement of the problem",
  "programming_language": "Language specified, or 'not specified'",
  "input_format": "Description of input format",
  "output_format": "Description of expected output",
  "constraints": "Array of constraints (time complexity, space, edge cases, etc.)",
  "examples": "Array of example inputs/outputs if provided, or empty array",
  "difficulty": "One of: beginner | intermediate | advanced | unknown",
  "key_requirements": "Array of 2-5 key functional requirements"
}}

RULES:
- Be precise about technical requirements.
- If no language is specified, set to 'not specified'.
- Return ONLY valid JSON. No markdown fences. No extra text.

PROBLEM:
---
{input}
---""",
            },
            {
                "name": "REASON",
                "technique": "Chain-of-Thought (CoT)",
                "technique_short": "cot",
                "description": "Design the solution approach step-by-step with algorithm analysis.",
                "purpose": "Develop a well-reasoned solution before writing code.",
                "input_schema": "Stage 1 JSON output",
                "output_schema": "{algorithm_choice, time_complexity, space_complexity, approach, edge_cases, reasoning}",
                "best_practice": "Consider multiple approaches, analyze trade-offs, and justify the chosen solution.",
                "prompt_template": """You are a senior software engineer designing a solution. Analyze the problem and design the approach step by step.

Think through these steps:
1. What is the core problem to solve?
2. What are the possible approaches/algorithms?
3. What are the trade-offs between approaches (time vs space complexity)?
4. Which approach is best and why?
5. What edge cases need to be handled?
6. What data structures are most appropriate?
7. How will the solution be structured?

Return a JSON object with these exact fields:

{{
  "algorithm_choice": "Name of the chosen algorithm/approach",
  "time_complexity": "Big O time complexity (e.g., O(n), O(n log n), O(n^2))",
  "space_complexity": "Big O space complexity",
  "approach_summary": "Brief description of the approach",
  "alternative_approaches": "Array of alternative approaches considered and why they weren't chosen",
  "edge_cases_handled": "Array of edge cases the solution handles",
  "data_structures": "Array of data structures used",
  "reasoning": "Your step-by-step reasoning for the chosen approach"
}}

Return ONLY valid JSON. No markdown fences. No extra text.

PROBLEM ANALYSIS:
{input}""",
            },
            {
                "name": "PRODUCE",
                "technique": "Goal-Oriented + Constraints",
                "technique_short": "goal",
                "description": "Generate the final code solution with explanation and complexity analysis.",
                "purpose": "Produce a complete, well-documented code solution.",
                "input_schema": "Stage 1 JSON + Stage 2 JSON",
                "output_schema": "Code solution with explanation and complexity analysis",
                "best_practice": "Set explicit goals for code quality, documentation, and correctness.",
                "prompt_template": """You are a senior software engineer implementing a solution. Based on the problem analysis and algorithm design, produce the final code.

GOALS:
- Write clean, well-documented code.
- Handle all edge cases mentioned.
- Include time and space complexity analysis.
- Add comments explaining key parts.
- Follow best practices for the language.
- Make the code production-quality.

PROBLEM ANALYSIS:
{stage1}

ALGORITHM DESIGN:
{stage2}

Return a JSON object with these exact fields:

{{
  "language": "Programming language used",
  "code": "The complete code solution as a string",
  "explanation": "Brief explanation of how the code works",
  "time_complexity": "Time complexity analysis",
  "space_complexity": "Space complexity analysis",
  "edge_cases_handled": "Array of edge cases the code handles",
  "usage_example": "Example of how to use the code",
  "alternative_approaches": "Array of alternative approaches with brief notes"
}}

Return ONLY valid JSON. No markdown fences. No extra text.""",
            },
            {
                "name": "CRITIQUE",
                "technique": "Self-Reflection / Critique",
                "technique_short": "critique",
                "description": "Review the code solution for correctness, efficiency, and best practices.",
                "purpose": "Ensure the code is correct, efficient, and follows best practices.",
                "input_schema": "Stage 3 output + original context",
                "output_schema": "{passed, issues, suggested_improvements}",
                "best_practice": "Check for correctness, edge case handling, code quality, and documentation.",
                "prompt_template": """You are a senior engineer reviewing a code solution. Evaluate the following code.

CHECKLIST:
1. Does the code correctly solve the problem?
2. Are all edge cases handled?
3. Is the time/space complexity analysis accurate?
4. Is the code clean and well-documented?
5. Are there any bugs or potential issues?

PROBLEM ANALYSIS:
{stage1}

CODE SOLUTION:
{stage3}

Return a JSON object:
{{
  "passed": true | false,
  "issues": ["list of any issues found, or empty array"],
  "suggested_improvements": "If failed, what to fix. If passed, empty string."
}}

Return ONLY valid JSON. No markdown fences.""",
            },
        ],
    },
}


def get_task(task_id: str) -> dict:
    """Get a task definition by ID."""
    return TASKS.get(task_id)


def get_task_list() -> list:
    """Get list of available tasks with metadata."""
    return [
        {
            "id": task_id,
            "name": task["name"],
            "icon": task["icon"],
            "description": task["description"],
        }
        for task_id, task in TASKS.items()
    ]


def get_stage_count(task_id: str) -> int:
    """Get the number of stages for a task."""
    task = TASKS.get(task_id)
    if task:
        return len(task["stages"])
    return 0


def get_stage_info(task_id: str, stage_index: int) -> dict:
    """Get the prompt template and metadata for a specific stage."""
    task = TASKS.get(task_id)
    if task and 0 <= stage_index < len(task["stages"]):
        return task["stages"][stage_index]
    return None