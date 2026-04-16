"""
PromptX API Utils
Sanitization, classification, scoring, and system prompts.
Extracted from the original Flask app.py.
"""

import re
import os
import resend
import random
import string
from django.template.loader import render_to_string

# Environment variables are loaded at module level, but we check again in functions
# to ensure changes in .env are picked up if autoreloader is active.
# Email configuration
FROM_EMAIL = "PromptX <auth@janhelps.in>" 

def get_resend_key():
    return os.getenv("RESEND_API_KEY")

resend.api_key = get_resend_key()


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

MASTER_PROMPT = """You are an elite AI prompt engineer. 
Your singular goal is to transform the user's raw input into the absolute best possible prompt that any LLM can execute flawlessly.

CRITICAL DIRECTIVE: Do NOT use a rigid, repetitive template for every enhancement. The user hates seeing the same "You are a seasoned expert..." or the same repeating headers (Context, Task Decomposition, etc.) every single time.

Instead, deeply analyze what the user is truly asking for, and construct a bespoke, fresh, and perfectly tailored prompt structure that fits THEIR specific request. 

HOW TO CRAFT THE PERFECT ENHANCED PROMPT:
1. Deeply Analyze: Understand the implicit goals, audience, and required output.
2. Adapt the Persona Dynamically: Instead of always starting with "You are...", you can start directly with the objective, or seamlessly weave the persona into the instructions (e.g. "Act as...", or "Writing from the perspective of..."). Keep it fresh and highly specific.
3. Tailor the Structure: Use headers and structure only when they actually benefit the output. A coding prompt shouldn't look identical to a creative writing prompt. 
4. Inject Missing Context: Add constraints, edge-case handling, tone instructions, and format requirements that the user forgot to include.
5. Provide Examples (if needed): Give the LLM a framework to follow without making the prompt overly bloated.

STRICT RULES:
- Return ONLY the enhanced prompt. No preamble, no meta-commentary (do not say "Here is your enhanced prompt").
- Never ask the user follow-up questions — infer intelligently from context.
- Preserve the user's original intent 100% — only enhance, never redirect.
- If the input is gibberish, return EXACTLY: WARNING: This prompt is too vague to enhance. Please provide more context about what you want to achieve.
- Aim for 3x to 5x more detail and precision than the original, but make it feel natural, human-driven, and custom-written.
- Do NOT output the exact same structural template for every request.
- 📐 DIAGRAMS: If the user asks for a diagram or if explaining a complex system/process, you MUST include a D2 diagram block.
  CRITICAL: Wrap D2 code in triple backticks with 'd2' identifier.
  D2 Syntax: `User: { shape: person; label: "👤 User" } \n User -> System: "Action"`. NO ASCII ART. """


# ============================================================================
# DEEP RESEARCH PROMPT
# Used for complex, multi-faceted questions that need exhaustive answers
# ============================================================================

DEEP_RESEARCH_PROMPT = """You are a world-class senior technical consultant and expert developer. Adapt your response based on what the user asks.

================================================
CRITICAL: MATCH YOUR RESPONSE TO THE QUESTION TYPE
================================================

**IF USER ASKS "how to make", "step by step", "build", "create", "implement":**
→ Give a BRIEF overview (2-3 sentences)
→ Then provide ACTUAL CODE with numbered steps: Step 1, Step 2, Step 3
→ Include complete, working code snippets
→ Be practical and hands-on

**IF USER ASKS FOR ANALYSIS of a website/platform:**
→ Analyze what exists (features, tech stack, architecture)
→ Do NOT generate implementation code
→ Focus on understanding, not building

**IF USER ASKS A GENERAL QUESTION:**
→ Answer directly and concisely
→ Provide examples if helpful
→ Keep it focused

================================================
FOR "HOW TO BUILD" QUESTIONS - USE THIS FORMAT:
================================================

## Quick Overview
[2-3 sentences about what we're building]

## Step 1: [First Step Title]

**📄 filename.ext** (put filename OUTSIDE code block)

```html
[actual code here - NO filename inside]
```

Explanation of what this code does.

## Step 2: [Second Step Title]

**📄 styles.css**

```css
[actual code here]
```

Explanation of what this code does.

## Step 3: [Third Step Title]

**📄 script.js**

```javascript
[actual code here]
```

Explanation of what this code does.

[Continue with more steps as needed]

## Final Result
Brief summary of what was built.

================================================
IMPORTANT CODE FORMATTING RULES:
================================================
- Put filename OUTSIDE the code block using: **📄 filename.ext**
- Code blocks should ONLY contain code, NO filenames inside
- Use proper language tags: ```html, ```css, ```javascript, ```python
- Do NOT put comments like "// server.js" inside the code block
- The filename should be bold with an emoji: **📄 filename.ext**

================================================
FOR WEBSITE ANALYSIS - USE THIS FORMAT:
================================================

## Overview
[What the platform does]

## Key Features
- Feature 1
- Feature 2

## Tech Stack
[Technologies used]

================================================
FORMATTING RULES:
================================================
- Use code blocks with language: ```html, ```css, ```javascript, ```python
- Be concise and practical
- Give working code, not descriptions of code
- Adapt to the question - don't use the same structure every time
- Maximum 1500 words for analysis, unlimited for code tutorials"""


WELCOME_SYSTEM_PROMPT = """You are PromptX, a friendly and knowledgeable AI prompt engineering assistant.

When a user sends a greeting or introduction (like "hi", "hello", "hey", "what can you do", etc.), respond with a short, warm, and helpful welcome message.

CRITICAL INSTRUCTION: DO NOT write a full paragraph! 
Just say: "Hello! I'm PromptX. How can I help you today?" or a very similar 1-2 sentence greeting. Keep it extremely brief and natural."""


# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def sanitize_input(text):
    """Basic protection against prompt injection and malicious characters"""
    if not text:
        return text
    lower = text.lower()
    if "ignore all previous instructions" in lower or "ignore previous instructions" in lower:
        return ""  # returning empty prompts will trigger length validation
    # Clean non-printable/control characters except newlines/tabs
    sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', str(text))
    return sanitized.strip()


# ============================================================================
# CLASSIFICATION & SCORING
# ============================================================================

def classify_prompt(prompt):
    keywords = {
        'code':      ['code', 'function', 'program', 'script', 'debug', 'algorithm', 'api',
                      'class', 'method', 'bug', 'error', 'implement', 'build', 'develop',
                      'python', 'javascript', 'typescript', 'sql', 'html', 'css', 'react',
                      'django', 'flask', 'database', 'backend', 'frontend', 'deploy'],
        'blog':      ['blog', 'article', 'post', 'content', 'seo', 'write', 'newsletter',
                      'copywriting', 'headline', 'introduction', 'conclusion', 'paragraph'],
        'business':  ['business', 'proposal', 'marketing', 'email', 'product', 'sales',
                      'strategy', 'pitch', 'investor', 'startup', 'revenue', 'customer',
                      'brand', 'campaign', 'launch', 'growth', 'monetize', 'b2b', 'b2c'],
        'academic':  ['research', 'essay', 'paper', 'thesis', 'study', 'analysis', 'report',
                      'literature', 'hypothesis', 'methodology', 'citation', 'abstract',
                      'survey', 'experiment', 'findings', 'conclusion', 'academic'],
        'creative':  ['story', 'character', 'world', 'creative', 'fiction', 'design',
                      'poem', 'novel', 'screenplay', 'dialogue', 'plot', 'narrative',
                      'fantasy', 'sci-fi', 'horror', 'romance', 'genre', 'scene'],
        'data':      ['data', 'dataset', 'csv', 'excel', 'chart', 'graph', 'visualization',
                      'statistics', 'machine learning', 'ml', 'ai model', 'training',
                      'prediction', 'classification', 'regression', 'neural', 'pandas'],
        'assistant': ['help', 'explain', 'what is', 'how to', 'guide', 'tutorial',
                      'summarize', 'translate', 'compare', 'list', 'give me', 'show me'],
    }

    prompt_lower = prompt.lower()
    scores = {}
    for cat, words in keywords.items():
        score = sum(2 if f' {kw} ' in f' {prompt_lower} ' else 1
                    for kw in words if kw in prompt_lower)
        scores[cat] = score

    if not scores or max(scores.values()) == 0:
        return {'category': 'general', 'confidence': 0.5}

    best = max(scores, key=scores.get)
    confidence = min(scores[best] / 8, 1.0)
    return {'category': best, 'confidence': round(confidence, 2)}


def score_prompt(prompt):
    """
    Score a prompt across 6 dimensions, each worth up to 10 points.
    Returns a weighted total out of 10.
    """
    words = prompt.split()
    word_count = len(words)
    char_count = len(prompt)
    lower = prompt.lower()

    # ── 1. LENGTH & SUBSTANCE (0–2) ──────────────────────────────────────────
    if 80 <= char_count <= 800:
        length_score = 2.0
    elif 40 <= char_count < 80 or 800 < char_count <= 2000:
        length_score = 1.5
    elif 20 <= char_count < 40:
        length_score = 0.8
    else:
        length_score = 0.3

    # ── 2. SPECIFICITY (0–2) ─────────────────────────────────────────────────
    spec_words = ['specific', 'detailed', 'format', 'tone', 'audience', 'length',
                  'style', 'example', 'include', 'exclude', 'focus', 'avoid',
                  'ensure', 'make sure', 'requirement', 'criteria', 'goal']
    spec_hits = sum(1 for w in spec_words if w in lower)
    specificity_score = min(spec_hits * 0.4, 2.0)

    # ── 3. STRUCTURE (0–2) ───────────────────────────────────────────────────
    structure_score = 0.0
    if '\n' in prompt:           structure_score += 0.6
    if any(c in prompt for c in [':', '-', '•', '*', '–']):
        structure_score += 0.5
    if any(f'{i}.' in prompt or f'{i})' in prompt for i in range(1, 8)):
        structure_score += 0.5
    if '##' in prompt or '**' in prompt:
        structure_score += 0.4
    structure_score = min(structure_score, 2.0)

    # ── 4. CONTEXT (0–2) ─────────────────────────────────────────────────────
    ctx_words = ['context', 'background', 'about', 'purpose', 'goal', 'objective',
                 'because', 'since', 'for', 'in order to', 'so that', 'the reason',
                 'i am', "i'm", 'we are', 'my', 'our', 'the project', 'the task']
    ctx_hits = sum(1 for w in ctx_words if w in lower)
    context_score = min(ctx_hits * 0.35, 2.0)

    # ── 5. CONSTRAINTS (0–1) ─────────────────────────────────────────────────
    con_words = ['must', 'should', 'avoid', 'do not', "don't", 'never', 'always',
                 'only', 'limit', 'maximum', 'minimum', 'at least', 'no more than',
                 'requirement', 'constraint', 'rule', 'important']
    con_hits = sum(1 for w in con_words if w in lower)
    constraint_score = min(con_hits * 0.25, 1.0)

    # ── 6. OUTPUT DEFINITION (0–1) ───────────────────────────────────────────
    out_words = ['output', 'response', 'answer', 'result', 'format', 'return',
                 'provide', 'give me', 'list', 'table', 'json', 'markdown',
                 'bullet', 'numbered', 'paragraph', 'summary', 'report']
    out_hits = sum(1 for w in out_words if w in lower)
    output_score = min(out_hits * 0.25, 1.0)

    # ── TOTAL ─────────────────────────────────────────────────────────────────
    total = length_score + specificity_score + structure_score + context_score + constraint_score + output_score
    total = round(min(total, 10.0), 2)
    percentage = round((total / 10) * 100, 1)

    if percentage >= 85:
        quality = 'Excellent'
    elif percentage >= 70:
        quality = 'Good'
    elif percentage >= 50:
        quality = 'Fair'
    elif percentage >= 30:
        quality = 'Weak'
    else:
        quality = 'Poor'

    return {
        'total': total,
        'percentage': percentage,
        'quality': quality,
        'breakdown': {
            'length':      round(length_score, 2),
            'specificity': round(specificity_score, 2),
            'structure':   round(structure_score, 2),
            'context':     round(context_score, 2),
            'constraints': round(constraint_score, 2),
            'output_def':  round(output_score, 2),
        }
    }


# ============================================================================
# EMAIL NOTIFICATIONS (RESEND)
# ============================================================================

def send_welcome_email(user_email, user_name):
    """Sends a cyberpunk-themed welcome email via Resend"""
    resend.api_key = get_resend_key()
    if not resend.api_key or resend.api_key == "re_your_resend_api_key_here":
        print(f"Warning: RESEND_API_KEY not configured. Email to {user_email} skipped.")
        return False
    
    html_content = render_to_string('emails/welcome.html', {
        'user_name': user_name,
        'user_email': user_email
    })
    
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": user_email,
            "subject": "PROMPTX // Identity Confirmed",
            "html": html_content
        })
        print(f"Welcome email successfully dispatched to {user_email}")
        return True
    except Exception as e:
        print(f"FAILED dispatching email to {user_email}: {str(e)}")
        return False


def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    """Send OTP verification email with cyberpunk theme"""
    api_key = get_resend_key()
    resend.api_key = api_key
    
    print(f"DEBUG: RESEND_API_KEY present: {bool(api_key)}")
    print(f"DEBUG: FROM_EMAIL: {FROM_EMAIL}")
    
    if not api_key or api_key == "re_your_resend_api_key_here":
        print(f"Warning: RESEND_API_KEY not configured. OTP for {email}: {otp}")
        return False, "API Key Missing"

    html_content = render_to_string('emails/otp.html', {
        'otp': otp,
        'user_email': email
    })
    
    try:
        result = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": f"PROMPTX // Verification Code: {otp}",
            "html": html_content
        })
        print(f"Email sent successfully to {email}: {result}")
        return True, "Success"
    except Exception as e:
        print(f"ERROR sending email to {email}: {str(e)}")
        return False, str(e)
