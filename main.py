from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import List
import os
import json
import re
import time

from openai import OpenAI

app = FastAPI(title="Lead Qualification API")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -----------------------------
# Request Schema
# -----------------------------
class LeadInput(BaseModel):
    lead_id: str
    full_name: str
    email: str
    company_name: str
    company_website: str
    budget: float
    project_description: str


# -----------------------------
# Response Schema
# -----------------------------
class LeadOutput(BaseModel):
    qualification_score: int = Field(ge=0, le=100)
    ai_confidence: float = Field(ge=0.0, le=1.0)
    needs_manual_review: bool
    company_overview: str
    top_pain_points: List[str] = Field(min_length=3, max_length=3)
    recommended_outreach_angle: str
    qualification_reasoning: str


# -----------------------------
# Health Check
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# Helpers
# -----------------------------
def clean_text(value: str, max_len: int = 2000) -> str:
    """Trim whitespace and cap length."""
    if not value:
        return ""
    value = value.strip()
    return value[:max_len]


def extract_json_object(text: str) -> str:
    """
    Tries to extract a JSON object from model output.
    Handles:
    - plain JSON
    - JSON wrapped in markdown fences
    - extra text before/after JSON
    """
    if not text or not text.strip():
        raise ValueError("Model returned empty content.")

    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try direct parse first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Fallback: extract first object block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")

    candidate = text[start:end + 1]
    json.loads(candidate)  # validate
    return candidate


def normalize_output(data: dict) -> dict:
    """
    Normalize model output into the exact shape we want.
    Handles common edge cases:
    - strings instead of ints/floats/bools
    - too many/few pain points
    - whitespace cleanup
    """
    # Score
    score = data.get("qualification_score", 0)
    try:
        score = int(float(score))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    # Confidence
    confidence = data.get("ai_confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    # needs_manual_review
    review = data.get("needs_manual_review", True)
    if isinstance(review, str):
        review = review.strip().lower() in {"true", "1", "yes", "y"}
    else:
        review = bool(review)

    # Strings
    company_overview = clean_text(str(data.get("company_overview", "")), 1200)
    recommended_outreach_angle = clean_text(
        str(data.get("recommended_outreach_angle", "")), 1200
    )
    qualification_reasoning = clean_text(
        str(data.get("qualification_reasoning", "")), 1200
    )

    # Pain points
    pain_points = data.get("top_pain_points", [])
    if isinstance(pain_points, str):
        # Try splitting comma-separated string
        pain_points = [p.strip() for p in pain_points.split(",") if p.strip()]

    if not isinstance(pain_points, list):
        pain_points = []

    pain_points = [clean_text(str(p), 120) for p in pain_points if str(p).strip()]

    # Deduplicate while preserving order
    deduped = []
    for p in pain_points:
        if p not in deduped:
            deduped.append(p)
    pain_points = deduped

    # Ensure exactly 3 items
    fallback_points = [
        "Unclear process maturity",
        "Potential manual workflow friction",
        "Opportunity for automation improvement",
    ]

    while len(pain_points) < 3:
        for fp in fallback_points:
            if fp not in pain_points:
                pain_points.append(fp)
            if len(pain_points) == 3:
                break

    pain_points = pain_points[:3]

    return {
        "qualification_score": score,
        "ai_confidence": confidence,
        "needs_manual_review": review,
        "company_overview": company_overview,
        "top_pain_points": pain_points,
        "recommended_outreach_angle": recommended_outreach_angle,
        "qualification_reasoning": qualification_reasoning,
    }


def manual_review_fallback(reason: str) -> dict:
    """
    Safe fallback so the workflow does not break if model output is bad.
    """
    return {
        "qualification_score": 50,
        "ai_confidence": 0.25,
        "needs_manual_review": True,
        "company_overview": "Lead requires manual review due to invalid or incomplete AI output.",
        "top_pain_points": [
            "Incomplete lead context",
            "Uncertain automation fit",
            "Requires human verification",
        ],
        "recommended_outreach_angle": "Review manually before deciding next steps.",
        "qualification_reasoning": clean_text(reason, 1000),
    }


def call_openai_with_retries(prompt: str, max_attempts: int = 3) -> str:
    """
    Retry a few times for transient failures.
    """
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict JSON API for AI lead qualification. "
                            "Return only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Model returned empty content.")
            return content

        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                time.sleep(attempt)  # simple backoff
            else:
                raise last_error


# -----------------------------
# Lead Qualification Endpoint
# -----------------------------
@app.post("/qualify-lead", response_model=LeadOutput)
def qualify_lead(lead: LeadInput):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set."
        )

    # Clean / normalize incoming text
    company_name = clean_text(lead.company_name, 300)
    company_website = clean_text(lead.company_website, 500)
    project_description = clean_text(lead.project_description, 2000)

    prompt = f"""
You are an AI sales qualification assistant for AI and automation services.

Analyze this lead:
Full Name: {clean_text(lead.full_name, 200)}
Email: {clean_text(lead.email, 300)}
Company: {company_name}
Website: {company_website}
Budget: {lead.budget}
Project: {project_description}

Return ONLY valid JSON with these exact keys:
- qualification_score (integer from 0 to 100)
- ai_confidence (float from 0.0 to 1.0)
- needs_manual_review (boolean)
- company_overview (string)
- top_pain_points (array of exactly 3 short strings)
- recommended_outreach_angle (string)
- qualification_reasoning (string)

Rules:
- Be conservative
- Do not hallucinate
- Use only the information provided
- Lower confidence if the information is vague, incomplete, or uncertain
- Stronger budgets and clearer automation use cases should generally score higher
- If uncertain, set needs_manual_review to true
- Return JSON only
""".strip()

    try:
        raw_content = call_openai_with_retries(prompt)
        json_text = extract_json_object(raw_content)
        parsed = json.loads(json_text)
        normalized = normalize_output(parsed)
        validated = LeadOutput(**normalized)
        return validated

    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        # Safe fallback so your workflow still completes
        fallback = manual_review_fallback(
            f"Model output validation failed: {str(e)}"
        )
        return LeadOutput(**fallback)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))