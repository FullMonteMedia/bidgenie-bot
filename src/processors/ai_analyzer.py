"""
BidGenie AI - AI Scope Analyzer
Uses Claude (Anthropic) or GPT to intelligently parse construction documents
and generate structured scope breakdowns, clarifying questions, and proposals.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────

ESTIMATOR_SYSTEM_PROMPT = """You are a senior construction estimator and plumbing contractor with 20+ years of experience. 
You work for Ace Plumbing, a professional plumbing and construction company.

Your role is to:
1. Analyze construction documents, scope descriptions, and bid specifications
2. Extract structured line items with quantities, units, and cost estimates
3. Identify missing information and ask targeted clarifying questions
4. Generate professional, client-ready bid proposals

Rules:
- Think like a contractor estimator, not a chatbot
- Prioritize accuracy over creativity
- Never guess measurements without clearly stating they are assumptions
- Label all estimated values with [EST] and user-provided values with [CONFIRMED]
- Always use plumbing-industry standard terminology
- Suggest commonly overlooked items (permits, cleanup, mobilization, etc.)
- Be concise but thorough — contractors are busy people

Output format: Always respond with valid JSON when asked for structured data."""


# ─── SCOPE EXTRACTION PROMPT ─────────────────────────────────────────────────

def build_scope_extraction_prompt(raw_text: str, trade_type: str, project_type: str) -> str:
    return f"""Analyze this construction/plumbing document and extract a structured scope of work.

Trade Type: {trade_type}
Project Type: {project_type}

Document Text:
---
{raw_text[:4000]}
---

Return a JSON object with this exact structure:
{{
  "project_summary": "2-3 sentence summary of the project",
  "scope_items": [
    {{
      "description": "Item description",
      "quantity": 1.0,
      "unit": "each",
      "material_cost": 0.0,
      "labor_hours": 1.0,
      "notes": "Any relevant notes",
      "is_estimated": true,
      "category": "Fixtures|Rough-In|Drain|Specialty|General"
    }}
  ],
  "missing_info": ["List of missing information needed for accurate estimate"],
  "suggested_additions": ["Items commonly needed but not mentioned"],
  "timeline_estimate": "X weeks",
  "complexity": "simple|moderate|complex",
  "clarifying_questions": ["Question 1?", "Question 2?"]
}}

For plumbing projects, include line items for:
- All fixtures mentioned (toilets, sinks, showers, etc.)
- Rough-in work for each fixture
- Supply and drain piping (estimate linear footage if not stated)
- Water heater if applicable
- Permits and inspections
- Any specialty items

Use realistic material costs and labor hours based on current market rates.
Mark all estimated values with is_estimated: true."""


def build_proposal_prompt(session_data: Dict[str, Any]) -> str:
    line_items_text = json.dumps(session_data.get("line_items", []), indent=2)
    return f"""Generate a professional contractor bid proposal for Ace Plumbing.

Company: {session_data.get('company_name', 'Ace Plumbing')}
Client: {session_data.get('client_name', 'Valued Client')}
Project: {session_data.get('project_name', 'Plumbing Project')}
Project Type: {session_data.get('project_type', 'Residential')}
Trade: {session_data.get('trade_type', 'Plumbing')}
Timeline: {session_data.get('timeline_notes', 'To be determined')}

Project Summary: {session_data.get('project_summary', '')}

Line Items:
{line_items_text}

Total Cost: ${session_data.get('total_cost', 0):,.2f}
Suggested Bid: ${session_data.get('suggested_bid', 0):,.2f}

Write a professional, client-ready proposal with:
1. Professional greeting and project introduction
2. Detailed scope of work (paragraph form)
3. What IS included in this bid
4. What is NOT included (exclusions)
5. Timeline and project phases
6. Payment terms (standard: 30% deposit, 40% at rough-in, 30% at completion)
7. Warranty information (1 year labor, manufacturer warranty on materials)
8. Professional closing

Tone: Professional, confident, contractor-grade. Not robotic or overly formal.
Length: 400-600 words for the narrative sections.
Do NOT include the pricing table in the text — it will be added separately."""


def build_clarifying_questions_prompt(scope_text: str, missing_items: List[str]) -> str:
    return f"""Based on this plumbing/construction scope, generate 3-5 targeted clarifying questions 
that would help produce a more accurate bid estimate.

Scope: {scope_text[:1000]}
Already identified as missing: {', '.join(missing_items)}

Return a JSON array of question objects:
[
  {{
    "question": "The actual question text?",
    "reason": "Why this matters for pricing",
    "options": ["Option A", "Option B", "Option C"]  // optional multiple choice
  }}
]

Focus on questions that would significantly impact the cost estimate.
Examples: material grade preference, existing conditions, access difficulty, permit requirements."""


# ─── AI CLIENT ───────────────────────────────────────────────────────────────

def call_claude(prompt: str, system: str = ESTIMATOR_SYSTEM_PROMPT) -> str:
    """Call Anthropic Claude API."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise


def call_openai(prompt: str, system: str = ESTIMATOR_SYSTEM_PROMPT) -> str:
    """Call OpenAI GPT API as fallback."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise


def call_ai(prompt: str, system: str = ESTIMATOR_SYSTEM_PROMPT) -> str:
    """Call AI with automatic fallback: Claude → OpenAI."""
    if ANTHROPIC_API_KEY:
        try:
            return call_claude(prompt, system)
        except Exception as e:
            logger.warning(f"Claude failed, trying OpenAI: {e}")

    if OPENAI_API_KEY:
        return call_openai(prompt, system)

    raise RuntimeError("No AI API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")


def parse_json_response(response: str) -> Any:
    """Extract and parse JSON from AI response."""
    # Try to find JSON block
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', response)
    if json_match:
        return json.loads(json_match.group(1))

    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object/array
    json_match = re.search(r'(\{[\s\S]+\}|\[[\s\S]+\])', response)
    if json_match:
        return json.loads(json_match.group(1))

    raise ValueError(f"Could not parse JSON from response: {response[:200]}")


# ─── HIGH-LEVEL FUNCTIONS ─────────────────────────────────────────────────────

async def analyze_scope(
    raw_text: str,
    trade_type: str = "Plumbing",
    project_type: str = "residential",
) -> Dict[str, Any]:
    """
    AI-powered scope analysis. Returns structured scope breakdown.
    """
    prompt = build_scope_extraction_prompt(raw_text, trade_type, project_type)
    try:
        response = call_ai(prompt)
        result = parse_json_response(response)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Scope analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "project_summary": "Unable to auto-analyze. Please describe the project manually.",
                "scope_items": [],
                "missing_info": ["Full project description"],
                "suggested_additions": [],
                "timeline_estimate": "TBD",
                "complexity": "unknown",
                "clarifying_questions": [
                    "Can you describe the scope of work in your own words?",
                    "How many fixtures are involved?",
                    "Is this new construction or a renovation?",
                ],
            },
        }


async def generate_proposal_text(session_data: Dict[str, Any]) -> str:
    """Generate professional proposal narrative text."""
    prompt = build_proposal_prompt(session_data)
    try:
        return call_ai(prompt)
    except Exception as e:
        logger.error(f"Proposal generation error: {e}")
        return _fallback_proposal_text(session_data)


async def get_clarifying_questions(scope_text: str, missing_items: List[str]) -> List[Dict]:
    """Get AI-generated clarifying questions."""
    prompt = build_clarifying_questions_prompt(scope_text, missing_items)
    try:
        response = call_ai(prompt)
        return parse_json_response(response)
    except Exception as e:
        logger.error(f"Clarifying questions error: {e}")
        return [
            {"question": "Is this new construction or renovation/repair?", "reason": "Affects labor complexity", "options": ["New construction", "Renovation", "Repair/replacement"]},
            {"question": "What is your preferred material grade?", "reason": "Significantly impacts material costs", "options": ["Standard", "Mid-grade", "Premium/luxury"]},
            {"question": "Are permits required for this project?", "reason": "Adds cost and timeline", "options": ["Yes", "No", "Not sure"]},
        ]


def _fallback_proposal_text(session_data: Dict[str, Any]) -> str:
    """Fallback proposal text if AI is unavailable."""
    company = session_data.get("company_name", "Ace Plumbing")
    client = session_data.get("client_name", "Valued Client")
    project = session_data.get("project_name", "Plumbing Project")
    total = session_data.get("suggested_bid", 0)

    return f"""Dear {client},

Thank you for the opportunity to submit this proposal for your {project}. {company} is pleased to provide the following bid for the plumbing work described herein.

Our team of licensed, experienced plumbers will complete all work in accordance with local building codes and manufacturer specifications. We take pride in delivering quality workmanship and professional service on every project.

SCOPE OF WORK:
All work as detailed in the line-item breakdown attached to this proposal. All materials will be new and of professional grade unless otherwise specified.

INCLUSIONS:
All labor, materials, and equipment necessary to complete the described scope of work. Final cleanup of all work areas upon project completion.

EXCLUSIONS:
Any work not specifically listed in the scope above. Unforeseen conditions discovered during construction. Patching or painting of walls/surfaces after rough-in work.

PAYMENT TERMS:
30% deposit required to schedule work. 40% due upon completion of rough-in inspection. 30% balance due upon final completion and walkthrough.

WARRANTY:
All labor is warranted for one (1) year from date of completion. All materials carry manufacturer warranty.

We look forward to working with you on this project. Please don't hesitate to contact us with any questions.

Sincerely,
{company}
Licensed & Insured"""
