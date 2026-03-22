# AI Lead Qualification System

A production-ready AI-powered lead qualification pipeline that automatically scores, enriches, and routes inbound leads in real time.

This system replaces manual lead research and qualification with structured AI outputs, enabling faster sales decisions and consistent evaluation.

---

## Overview

This project processes inbound leads from a form and transforms them into structured, actionable insights using AI.

### End-to-End Flow

Form Submission → n8n → FastAPI (Railway) → OpenAI → Supabase → Slack


---

## Core Capabilities

- AI-powered lead scoring (0–100)
- Confidence-based evaluation
- Company analysis and summarization
- Pain point extraction
- Recommended outreach strategy
- Structured reasoning for transparency
- Real-time Slack notifications
- Persistent storage in Supabase (CRM-style)
- Fully automated workflow orchestration

---

## Architecture

### Components

#### 1. Form (Input Layer)

Captures:
- `full_name`
- `email`
- `company_name`
- `company_website`
- `budget`
- `project_description`

---

#### 2. n8n (Orchestration Layer)

- Receives form submissions  
- Inserts data into Supabase  
- Calls AI API  
- Updates database with AI results  
- Sends Slack notifications  

---

#### 3. FastAPI (AI Service Layer)

**Deployed on Railway**

Responsibilities:
- Accept structured lead data  
- Call OpenAI API  
- Enforce strict JSON output  
- Validate and normalize responses  
- Handle edge cases and retries  
- Return machine-parseable results  

---

#### 4. OpenAI (Intelligence Layer)

Analyzes:
- Company  
- Website  
- Budget  
- Project description  

Returns:
- `qualification_score`  
- `ai_confidence`  
- `company_overview`  
- `pain points`  
- `outreach recommendations`  
- `reasoning`  

---

#### 5. Supabase (Data Layer)

Acts as a lightweight CRM.

Stores:
- Raw lead data  
- AI-enriched fields  
- Processing metadata  

---

#### 6. Slack (Notification Layer)

- Sends real-time alerts  
- Displays lead summary and AI insights  
- Supports rapid sales response  

---

## API

### Endpoint

POST /qualify-lead


### Request Schema

```json
{
  "lead_id": "string",
  "full_name": "string",
  "email": "string",
  "company_name": "string",
  "company_website": "string",
  "budget": number,
  "project_description": "string"
}

Response Schema

{
  "qualification_score": 0-100,
  "ai_confidence": 0.0-1.0,
  "needs_manual_review": boolean,
  "company_overview": "string",
  "top_pain_points": ["string", "string", "string"],
  "recommended_outreach_angle": "string",
  "qualification_reasoning": "string"
}

```
## Reliability & Edge Case Handling

LLMs are inherently non-deterministic and can produce inconsistent outputs. This system is designed to handle that.

### Prompt-Level Safeguards:
- Strict JSON-only output instructions
- Retry guidance for malformed responses
- Conservative reasoning rules
- Explicit structure enforcement

### Backend Safeguards:
- JSON parsing and validation
- Type normalization
- Range enforcement (score, confidence)
- Schema alignment for downstream systems

### Fallback Behavior

If AI output is invalid:

```json
{
  "needs_manual_review": true,
  "ai_confidence": 0.0,
  "qualification_reasoning": "Model output invalid"
}

```

### Result
- Prevents workflow failures
- Eliminates malformed database entries
- Enables stable end-to-end automation

## Automation Workflow (n8n)
1. Form submission received
2. Insert lead into Supabase
3. Call AI API (/qualify-lead)
4. Parse response
5. Update record with AI enrichment
6. Send Slack notification

## Database Schema (Supabase)

### Raw Fields
- id
- created_at
- full_name
- email
- company_name
- company_website
- budget
- project_description

### AI Fields
- qualification_score
- ai_confidence
- needs_manual_review
- company_overview
- top_pain_points
- recommended_outreach_angle
- qualification_reasoning

### Operational Fields
- status
- prompt_version
- processed_at
- error_message

## Deployment
- Platform: Railway

## Testing

### Local
- Swagger UI (/docs)
- Manual JSON testing

### Production
- Form submissions
- n8n workflow execution
- Slack verification

## Key Engineering Decisions

### Separation of Concerns
- AI logic isolated in API
- Workflow handled by n8n

### Structured Output Design
- Strict JSON contracts
- Enables deterministic automation

### Reliability-First Approach
- Handles malformed AI output
- Prevents system failure

### Decoupled Architecture
- Independently scalable components
- Flexible integration

## Challenges and Solutions

### Invalid JSON from LLM
→ Solution: structured prompts and validation layer

### Railway deployment issues
→ Solution: runtime.txt and correct $PORT usage

### Schema mismatches (form → API → DB)
→ Solution: unified schema and strict mapping

### Budget type errors
→ Solution: explicit numeric conversion in n8n

## Future Improvements
- Lead classification (HOT / WARM / COLD)
- Automated email follow-ups
- Analytics dashboard
- Retry queue for failed AI calls
- Multi-model evaluation

## Why This Project Matters

This project demonstrates:
- Production-ready AI API development
- End-to-end workflow automation
- Integration across multiple cloud services
- Reliable handling of non-deterministic AI systems
- Structuring AI outputs for real business use

## Author
Dennis Hanton | AI Automation Engineer
