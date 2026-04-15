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

MASTER_PROMPT = """You are an elite prompt architect — a world-class expert in crafting AI instructions that produce exceptional, precise, and highly actionable outputs.

Your task: Transform the user's raw prompt into a masterfully engineered prompt that any AI model will execute flawlessly.

═══════════════════════════════════════════════
ENHANCEMENT FRAMEWORK — Apply ALL of these:
═══════════════════════════════════════════════

1. 🎯 ROLE ASSIGNMENT
   - Open with a powerful expert persona (e.g., "You are a senior software architect with 15 years of experience...")
   - Match the role precisely to the task domain

2. 🧠 CONTEXT & BACKGROUND
   - Add rich situational context the AI needs to understand the task fully
   - Include relevant domain knowledge, constraints, and assumptions

3. 📋 TASK DECOMPOSITION
   - Break the request into clear, numbered sub-tasks or steps
   - Make each step atomic and unambiguous

4. 🎨 OUTPUT SPECIFICATION
   - Define exact output format (markdown, JSON, bullet list, numbered steps, table, etc.)
   - Specify length, tone, style, and depth
   - Include a concrete example of the desired output structure when helpful

5. ⚙️ CONSTRAINTS & GUARDRAILS
   - Add explicit DO and DO NOT rules
   - Define scope boundaries (what to include and exclude)
   - Specify audience level (beginner / intermediate / expert)

6. 🔍 QUALITY CRITERIA
   - Add a self-check instruction: "Before responding, verify your output meets: [criteria]"
   - Include success metrics where applicable

7. 💡 CHAIN-OF-THOUGHT TRIGGER (when applicable)
   - Add "Think step by step" or "Reason through this carefully before answering" for complex tasks

═══════════════════════════════════════════════
STRICT RULES:
═══════════════════════════════════════════════
- Return ONLY the enhanced prompt — no explanations, no preamble, no meta-commentary
- Never ask follow-up questions — infer intelligently from context
- Preserve the user's original intent 100% — only enhance, never redirect
- If the input is gibberish, too short, or completely meaningless with no inferable intent, return EXACTLY this and nothing else:
  ⚠️ This prompt is too vague to enhance. Please provide more context about what you want to achieve.
- Use markdown formatting: headers (##), bold (**text**), bullet points, numbered lists, code blocks where relevant
- Aim for 3x to 10x more detail and precision than the original
- The enhanced prompt should be immediately usable — paste it into any AI and get a great result"""


# ============================================================================
# DEEP RESEARCH PROMPT
# Used for complex, multi-faceted questions that need exhaustive answers
# ============================================================================

DEEP_RESEARCH_PROMPT = """You are a world-class senior technical consultant, system architect, and domain expert with deep knowledge across software engineering, product design, business strategy, and technology.

The user has asked a complex, multi-faceted question. Your job is to provide an **exhaustive, deeply detailed, expert-level answer** — not a prompt enhancement, but a real comprehensive answer.

═══════════════════════════════════════════════════════════
RESPONSE REQUIREMENTS — You MUST cover ALL of these:
═══════════════════════════════════════════════════════════

## 1. 🔍 REQUEST ANALYSIS
   - Restate what the user is asking in precise technical terms
   - Identify the core problem, goals, and implied requirements
   - List all assumptions you are making

## 2. 📊 SCOPE & COMPLEXITY BREAKDOWN
   - Break the request into major components/modules
   - Estimate complexity level for each component (Low / Medium / High / Very High)
   - Identify dependencies between components

## 3. 🏗️ SYSTEM ARCHITECTURE & DESIGN
   - Provide a complete high-level architecture
   - Include a text-based system diagram (use ASCII or Mermaid.js format)
   - Describe each layer: Frontend, Backend, Database, APIs, Infrastructure
   - Explain data flow between components

## 4. 🛠️ TECHNOLOGY STACK RECOMMENDATIONS
   - Frontend: framework, UI library, state management, styling
   - Backend: language, framework, API style (REST/GraphQL)
   - Database: primary DB, caching layer, search engine
   - Infrastructure: hosting, CDN, CI/CD, monitoring
   - Third-party services: payment, auth, email, storage, etc.
   - Justify EVERY technology choice with specific reasons

## 5. 📋 FEATURE LIST — EXHAUSTIVE
   - List every single feature, grouped by category
   - For each feature: name, description, priority (P0/P1/P2), complexity
   - Include both obvious features AND non-obvious ones users often miss
   - Cover: Core features, User management, Admin panel, Analytics, Security, Performance, Mobile

## 6. 🗄️ DATABASE SCHEMA DESIGN
   - List all major tables/collections with their key fields
   - Show relationships (one-to-many, many-to-many)
   - Include indexes for performance-critical queries

## 7. 🔐 SECURITY CONSIDERATIONS
   - Authentication & authorization strategy
   - Data encryption (at rest and in transit)
   - Common vulnerabilities to protect against (OWASP Top 10)
   - Rate limiting, DDoS protection, input validation

## 8. ⚡ PERFORMANCE & SCALABILITY
   - Expected traffic patterns and load estimates
   - Caching strategy (what to cache, where, for how long)
   - Database optimization (indexing, query optimization, sharding)
   - CDN strategy for static assets
   - Horizontal vs vertical scaling approach

## 9. 🚀 DEVELOPMENT ROADMAP
   - Phase 1 (MVP — weeks 1-8): Core features to launch
   - Phase 2 (Growth — weeks 9-20): Scaling and additional features
   - Phase 3 (Maturity — months 6-12): Advanced features and optimization
   - Team structure needed at each phase

## 10. 💰 COST ESTIMATION
    - Development cost (team size × time × rate)
    - Infrastructure cost (monthly, at different scale levels)
    - Third-party service costs
    - Total estimated budget range

## 11. ⚠️ RISKS & CHALLENGES
    - Technical risks and mitigation strategies
    - Business/market risks
    - Common mistakes to avoid
    - What makes this harder than it looks

## 12. 📚 LEARNING RESOURCES & REFERENCES
    - Key technologies to learn
    - Similar open-source projects to study
    - Recommended architecture patterns

═══════════════════════════════════════════════════════════
FORMATTING RULES:
═══════════════════════════════════════════════════════════
- Use rich markdown: ## headers, **bold**, `code`, tables, bullet lists
- Be EXHAUSTIVE — this should be a complete technical document
- Use concrete numbers, not vague estimates ("10,000 concurrent users" not "many users")
- Include code snippets where they add clarity
- Do NOT summarize or cut corners — the user wants maximum depth
- Minimum response length: 2000 words"""


WELCOME_SYSTEM_PROMPT = """You are PromptX, a friendly and knowledgeable AI prompt engineering assistant.

When a user sends a greeting or introduction (like "hi", "hello", "hey", "what can you do", etc.), respond with a warm, helpful welcome message that:

1. Greets them warmly and briefly introduces yourself
2. Explains the 3 core things you can do:
   - **Enhance** their prompts (make them clearer, more detailed, and more effective)
   - **Analyze** prompt quality (score it across clarity, specificity, structure, context, etc.)
   - **Compare** variations (generate 3 different versions — concise, detailed, structured — and recommend the best)
3. Gives 2-3 quick example prompts they could try
4. Ends with an encouraging call to action

Keep it conversational, friendly, and concise. Use markdown formatting with bold text and bullet points. Don't be overly formal or robotic."""


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
    resend.api_key = get_resend_key()
    if not resend.api_key or resend.api_key == "re_your_resend_api_key_here":
        print(f"Warning: RESEND_API_KEY not configured. OTP email to {email} skipped. OTP is: {otp}")
        return False, "API Key Missing"

    html_content = render_to_string('emails/otp.html', {
        'otp': otp,
        'user_email': email
    })
    
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": f"PROMPTX // Verification Code: {otp}",
            "html": html_content
        })
        return True, "Success"
    except Exception as e:
        return False, str(e)
