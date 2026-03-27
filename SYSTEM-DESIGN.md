🏗️ System Design Architecture — PromptX v1.0
Tailored to Your Actual Codebase, Stack & Features
1. 🔭 High-Level System Overview (Current State)

text

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            PROMPTX — SYSTEM OVERVIEW                            │
│                                                                                  │
│                                                                                  │
│   ┌──────────────────────┐         HTTP (REST)        ┌─────────────────────┐   │
│   │                      │◄──────────────────────────▶│                     │   │
│   │   FRONTEND (Static)  │    localhost:5000/api/*     │   FLASK BACKEND    │   │
│   │                      │                             │     (app.py)       │   │
│   │  • index.html        │                             │                     │   │
│   │  • index.css         │                             │  ┌───────────────┐  │   │
│   │  • index.js          │                             │  │  services.py  │  │   │
│   │                      │                             │  │  (AI Engine)  │  │   │
│   └──────────┬───────────┘                             │  └───────┬───────┘  │   │
│              │                                          │          │          │   │
│              ▼                                          └──────────┼──────────┘   │
│   ┌──────────────────────┐                                        │              │
│   │   localStorage       │                                        │              │
│   │   (Prompt History)   │                         ┌──────────────┼───────┐      │
│   └──────────────────────┘                         │   FALLBACK CHAIN     │      │
│                                                     │              │       │      │
│                                                     │    ┌────────▼─────┐ │      │
│                                                     │    │   Gemini 2.0 │ │      │
│                                                     │    │   (Primary)  │ │      │
│                                                     │    └──────┬──────┘ │      │
│                                                     │      fail │        │      │
│                                                     │    ┌──────▼──────┐ │      │
│                                                     │    │   OpenAI    │ │      │
│                                                     │    └──────┬──────┘ │      │
│                                                     │      fail │        │      │
│                                                     │    ┌──────▼──────┐ │      │
│                                                     │    │  DeepSeek   │ │      │
│                                                     │    └──────┬──────┘ │      │
│                                                     │      fail │        │      │
│                                                     │    ┌──────▼──────┐ │      │
│                                                     │    │ HuggingFace │ │      │
│                                                     │    └─────────────┘ │      │
│                                                     └────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘

2. 🧩 Component Architecture (Detailed)
Component 1: Frontend Layer

text

┌────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Static SPA)                        │
│                    /frontend/                                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     index.html                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              CHAT INTERFACE LAYOUT                     │  │ │
│  │  │                                                        │  │ │
│  │  │  ┌──────────────────────────────────┐                  │  │ │
│  │  │  │   📜 Scrollable Prompt Body     │  ◀── Responses   │  │ │
│  │  │  │   (Endless scroll area)          │      rendered    │  │ │
│  │  │  │                                  │      as chat     │  │ │
│  │  │  │   • Enhanced prompt cards        │      bubbles     │  │ │
│  │  │  │   • Quality heatmap visuals      │                  │  │ │
│  │  │  │   • A/B test comparison cards    │                  │  │ │
│  │  │  │   • Intent detection results     │                  │  │ │
│  │  │  │   • Error messages (400/429)     │                  │  │ │
│  │  │  └──────────────────────────────────┘                  │  │ │
│  │  │                                                        │  │ │
│  │  │  ┌──────────────────────────────────┐                  │  │ │
│  │  │  │   📌 Pinned Bottom Input Bar    │  ◀── User types  │  │ │
│  │  │  │   [Model Dropdown ▼] [Input] [▶]│      prompt here │  │ │
│  │  │  └──────────────────────────────────┘                  │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  index.css     │  │  index.js      │  │  Public/         │  │
│  │                │  │                │  │  • star.gif      │  │
│  │  • Chat layout │  │  • API calls   │  │  • bob.gif       │  │
│  │  • Heatmap CSS │  │  • DOM render  │  │  • favicon.svg   │  │
│  │  • Animations  │  │  • localStorage│  │  • star.svg      │  │
│  │  • Dark theme  │  │  • Error handle│  │                  │  │
│  │  • Responsive  │  │  • Model select│  │                  │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │             CLIENT-SIDE DATA LAYER                          │ │
│  │                                                              │ │
│  │   localStorage Schema:                                       │ │
│  │   ┌────────────────────────────────────────────────────┐    │ │
│  │   │  key: "promptx_history"                             │    │ │
│  │   │  value: [                                           │    │ │
│  │   │    {                                                │    │ │
│  │   │      id: "uuid-timestamp",                          │    │ │
│  │   │      original_prompt: "make a website",             │    │ │
│  │   │      enhanced_prompt: "You are a senior...",        │    │ │
│  │   │      model_used: "gemini",                          │    │ │
│  │   │      timestamp: "2025-06-15T10:30:00Z",             │    │ │
│  │   │      quality_scores: { clarity: 8, ... }            │    │ │
│  │   │    }, ...                                           │    │ │
│  │   │  ]                                                  │    │ │
│  │   └────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘

Component 2: Flask Backend (app.py)

text

┌─────────────────────────────────────────────────────────────────────┐
│                     FLASK BACKEND (app.py)                           │
│                     Port: 5000                                       │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    MIDDLEWARE STACK                             │  │
│  │                                                                │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐    │  │
│  │  │  CORS    │  │  JSON Parse  │  │  Error Handler       │    │  │
│  │  │  (flask- │──▶│  (force=True │──▶│  (400, 429, 500     │    │  │
│  │  │   cors)  │  │   bypass)    │  │   routed to client)  │    │  │
│  │  └──────────┘  └──────────────┘  └──────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     ROUTE HANDLERS                             │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  GET  /health                                            │  │  │
│  │  │  └─▶ Return: { status: "ok", models_available: [...] }  │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  POST /api/enhance                                       │  │  │
│  │  │  └─▶ Input:  { prompt, model_preference? }               │  │  │
│  │  │  └─▶ Action: services.enhance_prompt(prompt)             │  │  │
│  │  │  └─▶ Output: { enhanced_prompt, model_used, metadata }  │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  POST /api/detect-intent                                 │  │  │
│  │  │  └─▶ Input:  { prompt }                                  │  │  │
│  │  │  └─▶ Action: services.detect_intent(prompt)              │  │  │
│  │  │  └─▶ Output: { intent, tone, confidence, suggestions }  │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  POST /api/quality-heatmap                               │  │  │
│  │  │  └─▶ Input:  { prompt }                                  │  │  │
│  │  │  └─▶ Action: services.analyze_quality(prompt)            │  │  │
│  │  │  └─▶ Output: { scores: { clarity, specificity,          │  │  │
│  │  │               structure, context, constraints, format }, │  │  │
│  │  │               overall_score, suggestions[] }             │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  POST /api/ab-test                                       │  │  │
│  │  │  └─▶ Input:  { prompt }                                  │  │  │
│  │  │  └─▶ Action: services.generate_variations(prompt)        │  │  │
│  │  │  └─▶ Output: { variations: [                             │  │  │
│  │  │         { type: "concise",    enhanced: "..." },         │  │  │
│  │  │         { type: "detailed",   enhanced: "..." },         │  │  │
│  │  │         { type: "structured", enhanced: "..." }          │  │  │
│  │  │       ], model_used }                                    │  │  │
│  │  │  └─▶ ⚠️ Sequential generation (rate-limit safe)         │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

Component 3: AI Services Engine (services.py) — THE BRAIN

text

┌──────────────────────────────────────────────────────────────────────────┐
│                       services.py — AI ENGINE                            │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                   MODEL REGISTRY                                    │  │
│  │                                                                     │  │
│  │   models = {                                                        │  │
│  │     "gemini": {                                                     │  │
│  │        provider: "Google",                                          │  │
│  │        model: "gemini-2.0-flash",                                   │  │
│  │        api_key: env.GEMINI_API_KEY,                                 │  │
│  │        priority: 1,  ◀── PRIMARY                                    │  │
│  │        max_tokens: 100_000,                                         │  │
│  │        status: "active"                                             │  │
│  │     },                                                              │  │
│  │     "openai": {                                                     │  │
│  │        provider: "OpenAI",                                          │  │
│  │        model: "gpt-3.5-turbo / gpt-4",                             │  │
│  │        api_key: env.OPENAI_API_KEY,                                 │  │
│  │        priority: 2,  ◀── FALLBACK #1                                │  │
│  │        status: "standby"                                            │  │
│  │     },                                                              │  │
│  │     "deepseek": {                                                   │  │
│  │        provider: "DeepSeek",                                        │  │
│  │        api_key: env.DEEPSEEK_API_KEY,                               │  │
│  │        priority: 3,  ◀── FALLBACK #2                                │  │
│  │        status: "standby"                                            │  │
│  │     },                                                              │  │
│  │     "huggingface": {                                                │  │
│  │        provider: "HuggingFace",                                     │  │
│  │        api_key: env.HUGGINGFACE_API_KEY,                            │  │
│  │        priority: 4,  ◀── FALLBACK #3 (Last Resort)                  │  │
│  │        status: "standby"                                            │  │
│  │     }                                                               │  │
│  │   }                                                                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │               PROMPT ENGINEERING TEMPLATES                          │  │
│  │                                                                     │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐   │  │
│  │  │  ENHANCE PROMPT  │  │  INTENT DETECT   │  │  QUALITY SCORE │   │  │
│  │  │                  │  │                  │  │                │   │  │
│  │  │  System: "You    │  │  System: "Analyze│  │  System: "Score│   │  │
│  │  │  are a prompt    │  │  this prompt and │  │  this prompt   │   │  │
│  │  │  engineering     │  │  detect: intent, │  │  on 6 axes:    │   │  │
│  │  │  expert..."      │  │  tone, confidence│  │  clarity 0-10, │   │  │
│  │  │                  │  │  level..."       │  │  specificity..."│  │  │
│  │  └──────────────────┘  └──────────────────┘  └────────────────┘   │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  A/B TEST PROMPTS (3 templates)                               │  │  │
│  │  │                                                                │  │  │
│  │  │  Template A — "Concise":                                      │  │  │
│  │  │    "Rewrite this prompt to be short, direct, and minimal..."  │  │  │
│  │  │                                                                │  │  │
│  │  │  Template B — "Detailed":                                     │  │  │
│  │  │    "Expand with Mermaid.js diagrams, step-by-step docs,      │  │  │
│  │  │     constraint engineering, detailed context..."              │  │  │
│  │  │                                                                │  │  │
│  │  │  Template C — "Structured":                                   │  │  │
│  │  │    "Rewrite with clear sections: Role, Context, Task,        │  │  │
│  │  │     Constraints, Output Format, Examples..."                  │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                  FALLBACK CHAIN ENGINE                               │  │
│  │                  (Core Resilience Logic)                             │  │
│  │                                                                     │  │
│  │   def call_with_fallback(prompt, system_template):                  │  │
│  │                                                                     │  │
│  │     for model in sorted(models, key=priority):                      │  │
│  │       ┌─────────────────────────────────────┐                       │  │
│  │       │  if model.api_key is None:          │                       │  │
│  │       │     skip → next model               │ ── Key not configured │  │
│  │       │                                     │                       │  │
│  │       │  try:                               │                       │  │
│  │       │     response = model.call(prompt)   │ ── Attempt API call   │  │
│  │       │     return {                        │                       │  │
│  │       │       result: response,             │                       │  │
│  │       │       model_used: model.name    ────┼─▶ ✅ SUCCESS          │  │
│  │       │     }                               │                       │  │
│  │       │                                     │                       │  │
│  │       │  except RateLimitError (429):       │                       │  │
│  │       │     log("Rate limited")             │ ── Quota exhausted    │  │
│  │       │     continue → next model           │                       │  │
│  │       │                                     │                       │  │
│  │       │  except AuthError (401/403):        │                       │  │
│  │       │     log("Invalid key")              │ ── Bad API key        │  │
│  │       │     disable_model(model)            │                       │  │
│  │       │     continue → next model           │                       │  │
│  │       │                                     │                       │  │
│  │       │  except TimeoutError:               │                       │  │
│  │       │     log("Timeout")                  │ ── Model too slow     │  │
│  │       │     continue → next model           │                       │  │
│  │       │                                     │                       │  │
│  │       │  except Exception:                  │                       │  │
│  │       │     log("Unknown error")            │ ── Catch-all          │  │
│  │       │     continue → next model           │                       │  │
│  │       └─────────────────────────────────────┘                       │  │
│  │                                                                     │  │
│  │     raise AllModelsFailedError()  ◀── ❌ TOTAL FAILURE              │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

3. 🔄 Request Lifecycle — Complete Flow
Flow 1: /api/enhance — Prompt Enhancement

text

 USER                    FRONTEND                    FLASK                     SERVICES                 EXTERNAL API
  │                        │                          │                          │                         │
  │  1. Types prompt       │                          │                          │                         │
  │  "make a website"     │                          │                          │                         │
  │───────────────────────▶│                          │                          │                         │
  │                        │                          │                          │                         │
  │                        │  2. POST /api/enhance    │                          │                         │
  │                        │  { prompt: "make..." }   │                          │                         │
  │                        │─────────────────────────▶│                          │                         │
  │                        │                          │                          │                         │
  │                        │                          │  3. Validate input       │                         │
  │                        │                          │  (empty? too long?)      │                         │
  │                        │                          │                          │                         │
  │                        │                          │  4. enhance_prompt()     │                         │
  │                        │                          │─────────────────────────▶│                         │
  │                        │                          │                          │                         │
  │                        │                          │                          │  5. Build system prompt │
  │                        │                          │                          │  + user prompt          │
  │                        │                          │                          │                         │
  │                        │                          │                          │  6. Try Gemini 2.0      │
  │                        │                          │                          │─────────────────────────▶
  │                        │                          │                          │                         │
  │                        │                          │                          │         ┌───────┐       │
  │                        │                          │                          │         │Success│       │
  │                        │                          │                          │◀────────┴───────┘───────│
  │                        │                          │                          │                         │
  │                        │                          │  7. Return result        │                         │
  │                        │                          │◀─────────────────────────│                         │
  │                        │                          │  { enhanced_prompt,      │                         │
  │                        │                          │    model_used:"gemini" } │                         │
  │                        │                          │                          │                         │
  │                        │  8. JSON Response        │                          │                         │
  │                        │◀─────────────────────────│                          │                         │
  │                        │                          │                          │                         │
  │                        │  9. Render chat bubble   │                          │                         │
  │                        │  10. Save to localStorage│                          │                         │
  │  11. See enhanced      │                          │                          │                         │
  │      prompt            │                          │                          │                         │
  │◀───────────────────────│                          │                          │                         │

Flow 2: /api/enhance — WITH FALLBACK TRIGGERED

text

 SERVICES                  GEMINI API              OPENAI API            DEEPSEEK API
    │                          │                       │                      │
    │  1. Try Gemini           │                       │                      │
    │─────────────────────────▶│                       │                      │
    │                          │                       │                      │
    │  ❌ 429 Rate Limited     │                       │                      │
    │◀─────────────────────────│                       │                      │
    │                          │                       │                      │
    │  📝 Log: "Gemini rate    │                       │                      │
    │   limited, trying OpenAI"│                       │                      │
    │                          │                       │                      │
    │  2. Try OpenAI           │                       │                      │
    │──────────────────────────┼──────────────────────▶│                      │
    │                          │                       │                      │
    │  ❌ 401 Invalid Key      │                       │                      │
    │◀─────────────────────────┼───────────────────────│                      │
    │                          │                       │                      │
    │  📝 Log: "OpenAI auth    │                       │                      │
    │   failed, trying DeepSeek"                       │                      │
    │                          │                       │                      │
    │  3. Try DeepSeek         │                       │                      │
    │──────────────────────────┼───────────────────────┼─────────────────────▶│
    │                          │                       │                      │
    │  ✅ 200 Success          │                       │                      │
    │◀─────────────────────────┼───────────────────────┼──────────────────────│
    │                          │                       │                      │
    │  Return {                │                       │                      │
    │    enhanced_prompt: "...",│                       │                      │
    │    model_used: "deepseek" ◀── User sees which model was actually used  │
    │  }                       │                       │                      │

Flow 3: /api/ab-test — Sequential A/B Generation

text

 FLASK                       SERVICES                        GEMINI API
   │                            │                                │
   │  1. ab_test(prompt)        │                                │
   │───────────────────────────▶│                                │
   │                            │                                │
   │                            │  2. Generate "Concise"         │
   │                            │  (system_prompt_A + prompt)    │
   │                            │───────────────────────────────▶│
   │                            │         ✅ Response A          │
   │                            │◀───────────────────────────────│
   │                            │                                │
   │                            │  ⏱️ WAIT (rate-limit safe)     │
   │                            │                                │
   │                            │  3. Generate "Detailed"        │
   │                            │  (system_prompt_B + prompt)    │
   │                            │───────────────────────────────▶│
   │                            │         ✅ Response B          │
   │                            │◀───────────────────────────────│
   │                            │                                │
   │                            │  ⏱️ WAIT (rate-limit safe)     │
   │                            │                                │
   │                            │  4. Generate "Structured"      │
   │                            │  (system_prompt_C + prompt)    │
   │                            │───────────────────────────────▶│
   │                            │         ✅ Response C          │
   │                            │◀───────────────────────────────│
   │                            │                                │
   │  5. Return 3 variations    │                                │
   │◀───────────────────────────│                                │
   │  { variations: [A, B, C],  │                                │
   │    model_used: "gemini" }  │                                │
   │                            │                                │
   │  ⚠️ Sequential NOT parallel│                                │
   │  (prevents free-tier       │                                │
   │   rate exhaustion)         │                                │

4. 📊 Quality Heatmap Scoring Engine

text

┌──────────────────────────────────────────────────────────────────┐
│            QUALITY HEATMAP ENGINE (/api/quality-heatmap)         │
│                                                                   │
│   Input: "make a website"                                         │
│                                                                   │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  SYSTEM PROMPT TO GEMINI:                                  │  │
│   │  "Analyze this prompt and score on 6 dimensions (0-10):   │  │
│   │   1. Clarity — Is it unambiguous?                          │  │
│   │   2. Specificity — Does it have enough detail?             │  │
│   │   3. Structure — Is it well-organized?                     │  │
│   │   4. Context — Is background provided?                     │  │
│   │   5. Constraints — Are boundaries defined?                 │  │
│   │   6. Format — Is output format specified?                  │  │
│   │   Return JSON with scores + suggestions for each."         │  │
│   └───────────────────────────────────────────────────────────┘  │
│                           │                                       │
│                           ▼                                       │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  OUTPUT:                                                    │  │
│   │                                                             │  │
│   │   scores: {                                                 │  │
│   │     clarity:     3  ██████░░░░░░░░░░░░░░  (30%)            │  │
│   │     specificity: 2  ████░░░░░░░░░░░░░░░░  (20%)            │  │
│   │     structure:   2  ████░░░░░░░░░░░░░░░░  (20%)            │  │
│   │     context:     1  ██░░░░░░░░░░░░░░░░░░  (10%)            │  │
│   │     constraints: 1  ██░░░░░░░░░░░░░░░░░░  (10%)            │  │
│   │     format:      1  ██░░░░░░░░░░░░░░░░░░  (10%)            │  │
│   │   }                                                         │  │
│   │   overall: 1.7 / 10                                         │  │
│   │                                                             │  │
│   │   suggestions: [                                            │  │
│   │     "Specify what type of website (portfolio, e-commerce)", │  │
│   │     "Define tech stack (React, Vue, plain HTML)",           │  │
│   │     "Add design preferences (modern, minimal, colorful)",   │  │
│   │     "Specify desired sections (hero, about, contact)",      │  │
│   │     "Define responsive requirements",                       │  │
│   │     "Specify output format (code, wireframe, plan)"         │  │
│   │   ]                                                         │  │
│   └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

5. 🔐 Environment & Configuration Architecture

text

┌──────────────────────────────────────────────────────────────┐
│                CONFIGURATION LAYER                            │
│                                                               │
│   .env file (loaded by python-dotenv)                         │
│   ┌───────────────────────────────────────────────────────┐  │
│   │                                                        │  │
│   │  ┌──────────────────────────────────┐                  │  │
│   │  │  REQUIRED                        │                  │  │
│   │  │  GEMINI_API_KEY=AIza...          │ ◀── Must have    │  │
│   │  │  PORT=5000                       │                  │  │
│   │  └──────────────────────────────────┘                  │  │
│   │                                                        │  │
│   │  ┌──────────────────────────────────┐                  │  │
│   │  │  OPTIONAL (Fallback keys)        │                  │  │
│   │  │  OPENAI_API_KEY=sk-...           │ ◀── If missing,  │  │
│   │  │  DEEPSEEK_API_KEY=ds-...         │     model is     │  │
│   │  │  HUGGINGFACE_API_KEY=hf_...      │     skipped in   │  │
│   │  └──────────────────────────────────┘     fallback     │  │
│   │                                            chain       │  │
│   └───────────────────────────────────────────────────────┘  │
│                                                               │
│   Config Validation (on startup):                             │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  ✅ Check GEMINI_API_KEY exists → else FATAL ERROR     │  │
│   │  ⚠️ Check OPENAI_API_KEY     → warn if missing        │  │
│   │  ⚠️ Check DEEPSEEK_API_KEY   → warn if missing        │  │
│   │  ⚠️ Check HUGGINGFACE_API_KEY→ warn if missing        │  │
│   │  📋 Log available model count                          │  │
│   └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

6. 🛡️ Error Handling Architecture

text

┌──────────────────────────────────────────────────────────────────────┐
│                     ERROR HANDLING FLOW                               │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │                    ERROR TAXONOMY                             │    │
│   │                                                              │    │
│   │  CLIENT ERRORS (4xx)                                         │    │
│   │  ┌──────────┬────────────────────────────────────────────┐  │    │
│   │  │  400     │  Empty prompt / Invalid JSON / Too long    │  │    │
│   │  │  429     │  Rate limit (from upstream LLM API)        │  │    │
│   │  └──────────┴────────────────────────────────────────────┘  │    │
│   │                                                              │    │
│   │  SERVER ERRORS (5xx)                                         │    │
│   │  ┌──────────┬────────────────────────────────────────────┐  │    │
│   │  │  500     │  All fallback models failed                │  │    │
│   │  │  502     │  Upstream API returned invalid response    │  │    │
│   │  │  503     │  No API keys configured                    │  │    │
│   │  └──────────┴────────────────────────────────────────────┘  │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│   Error Flow:                                                         │
│                                                                       │
│   Flask Route                                                         │
│     │                                                                 │
│     ├── Input Validation Failed?                                      │
│     │   └── Return 400 { error: "Prompt is required" }               │
│     │                                                                 │
│     ├── services.py throws RateLimitError?                            │
│     │   └── Return 429 { error: "Rate limited", retry_after: 60 }    │
│     │                                                                 │
│     ├── services.py throws AllModelsFailedError?                      │
│     │   └── Return 500 { error: "All AI models unavailable" }        │
│     │                                                                 │
│     └── Unexpected exception?                                         │
│         └── Return 500 { error: "Internal server error" }            │
│                                                                       │
│   Frontend Handling:                                                  │
│     │                                                                 │
│     ├── 400 → Show in chat: "❌ Bad Request: [message]"              │
│     ├── 429 → Show in chat: "⏱️ Rate limited. Wait & retry."        │
│     ├── 500 → Show in chat: "🔥 Server error. Try again later."     │
│     └── Network Error → Show: "📡 Cannot connect to server."         │
└──────────────────────────────────────────────────────────────────────┘

7. 📦 Dependency Graph

text

┌──────────────────────────────────────────────────────────────┐
│                 DEPENDENCY GRAPH (4 packages)                  │
│                 requirements.txt                               │
│                                                               │
│                    ┌──────────┐                                │
│                    │  app.py  │                                │
│                    └────┬─────┘                                │
│                         │                                     │
│            ┌────────────┼────────────┐                        │
│            │            │            │                        │
│            ▼            ▼            ▼                        │
│     ┌──────────┐ ┌──────────┐ ┌────────────┐                │
│     │  Flask   │ │flask-cors│ │python-dotenv│               │
│     │          │ │          │ │            │                │
│     │  Routes, │ │  Cross-  │ │  Load .env │                │
│     │  Server  │ │  Origin  │ │  variables │                │
│     └──────────┘ └──────────┘ └────────────┘                │
│                                                               │
│                    ┌──────────┐                                │
│                    │services. │                                │
│                    │   py     │                                │
│                    └────┬─────┘                                │
│                         │                                     │
│                         ▼                                     │
│              ┌─────────────────────┐                          │
│              │  google-generativeai│  (+ requests for         │
│              │  (Gemini SDK)       │   OpenAI/DeepSeek/HF)   │
│              └─────────────────────┘                          │
│                                                               │
│   Total: ~4 direct dependencies ⚡                            │
│   (Ultra-lightweight)                                         │
└──────────────────────────────────────────────────────────────┘

8. 🗂️ Data Flow Architecture (Complete)

text

┌─────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE DATA FLOW                                │
│                                                                          │
│                                                                          │
│   ┌──────────┐     ┌───────────┐     ┌───────────┐     ┌────────────┐  │
│   │          │     │           │     │           │     │            │  │
│   │  USER    │────▶│  BROWSER  │────▶│  FLASK    │────▶│  services  │  │
│   │  INPUT   │     │  (JS)     │     │  (app.py) │     │  .py       │  │
│   │          │     │           │     │           │     │            │  │
│   └──────────┘     └─────┬─────┘     └───────────┘     └──────┬─────┘  │
│                          │                                      │        │
│                          │                                      │        │
│                          │                                      ▼        │
│                          │                              ┌──────────────┐ │
│                          │                              │  FALLBACK    │ │
│                          │                              │  CHAIN       │ │
│                          │                              │              │ │
│                          │                              │ Gemini ─────▶│ │
│                          │                              │ OpenAI ─────▶│ │
│                          │                              │ DeepSeek ───▶│ │
│                          │                              │ HuggingFace ▶│ │
│                          │                              └──────┬───────┘ │
│                          │                                      │        │
│                          │                                      │        │
│                          │     ◀────── JSON Response ◀──────────┘        │
│                          │                                               │
│                          ▼                                               │
│                   ┌─────────────┐                                        │
│                   │ localStorage│                                        │
│                   │             │                                        │
│                   │ Save:       │                                        │
│                   │ • prompt    │                                        │
│                   │ • enhanced  │                                        │
│                   │ • model     │                                        │
│                   │ • timestamp │                                        │
│                   │ • scores    │                                        │
│                   └─────────────┘                                        │
│                                                                          │
│   DATA PERSISTENCE:                                                      │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │  Server (Flask)  →  ❌ NO persistent storage (stateless)       │    │
│   │  Client (Browser)→  ✅ localStorage (prompt history)           │    │
│   │  Logs            →  ✅ Console/stdout (server-side)            │    │
│   └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

9. 🏗️ Current Architecture Strengths & Limitations

text

┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   ✅ STRENGTHS OF CURRENT DESIGN                                     │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │  • Ultra-lightweight (4 deps, ~50KB frontend)                  │ │
│   │  • Zero database overhead (localStorage)                       │ │
│   │  • Stateless backend (easy to scale horizontally)              │ │
│   │  • Multi-model resilience (4-tier fallback)                    │ │
│   │  • < 3 second startup                                          │ │
│   │  • < 2 second response time                                    │ │
│   │  • Works with just 1 API key (others optional)                 │ │
│   │  • No build step (vanilla HTML/CSS/JS)                         │ │
│   │  • Sequential A/B generation (rate-limit safe)                 │ │
│   └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│   ⚠️ LIMITATIONS / TRADE-OFFS                                        │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │  • No authentication (anyone can use the API)                  │ │
│   │  • No rate limiting on Flask side (relies on LLM limits)       │ │
│   │  • localStorage = data lost on browser clear                   │ │
│   │  • No server-side caching (repeated prompts re-call LLM)      │ │
│   │  • Single-threaded Flask (not production WSGI)                 │ │
│   │  • No request queuing (concurrent users may bottleneck)        │ │
│   │  • A/B test is 3 sequential API calls (slower)                 │ │
│   │  • No prompt injection protection                              │ │
│   └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

10. 🚀 Evolution Roadmap Architecture (v2.0 → v3.0)
Phase 1 → v1.5 (Quick Wins)

text

┌──────────────────────────────────────────────────────────────────────┐
│  v1.5 IMPROVEMENTS (Minimal Code Changes)                            │
│                                                                       │
│  ┌─────────────────────────────┬──────────────────────────────────┐  │
│  │  Change                     │  Impact                          │  │
│  ├─────────────────────────────┼──────────────────────────────────┤  │
│  │  Add Gunicorn/Waitress      │  Multi-worker production server  │  │
│  │  Add Flask-Limiter          │  Server-side rate limiting       │  │
│  │  Add in-memory LRU cache    │  Avoid re-calling for same prompt│  │
│  │  Add API key auth header    │  Basic access control            │  │
│  │  Add request logging        │  Observability                   │  │
│  │  Add input sanitization     │  Prompt injection defense        │  │
│  │  Export history (JSON/CSV)  │  Data portability (roadmap item) │  │
│  └─────────────────────────────┴──────────────────────────────────┘  │
│                                                                       │
│  New Architecture Delta:                                              │
│                                                                       │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌────────────┐   │
│  │Gunicorn  │───▶│Flask-Limit│───▶│LRU Cache │───▶│ services   │   │
│  │(4 workers│    │(10 req/min│    │(maxsize= │    │ .py        │   │
│  │ prod)    │    │ per IP)   │    │  500)    │    │            │   │
│  └──────────┘    └───────────┘    └──────────┘    └────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

Phase 2 → v2.0 (Database + Users)

text

┌──────────────────────────────────────────────────────────────────────┐
│  v2.0 — ADD PERSISTENCE & AUTH                                       │
│                                                                       │
│                                                                       │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌────────────┐ │
│  │ Frontend │────▶│  Flask   │────▶│  SQLite/ │     │  services  │ │
│  │ (Vanilla │     │  + JWT   │     │  Postgres│     │  .py       │ │
│  │  or React│     │  Auth    │     │          │     │            │ │
│  │  migrate)│     │          │     │ • users  │     │ + Redis    │ │
│  └──────────┘     └──────────┘     │ • history│     │   cache    │ │
│                                     │ • api_keys│    └────────────┘ │
│                                     └──────────┘                     │
│                                                                       │
│  New Features:                                                        │
│  ✅ User accounts & login                                            │
│  ✅ Server-side prompt history (persistent)                          │
│  ✅ Redis cache layer (semantic or exact match)                      │
│  ✅ API key management per user                                      │
│  ✅ Usage analytics dashboard                                        │
│  ✅ Prompt templates library                                         │
└──────────────────────────────────────────────────────────────────────┘

Phase 3 → v3.0 (Scale + Extensions)

text

┌──────────────────────────────────────────────────────────────────────┐
│  v3.0 — PLATFORM SCALE                                               │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    MULTI-CLIENT SUPPORT                         │  │
│  │                                                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │  Web App │  │  Chrome  │  │  VS Code │  │  Mobile App  │  │  │
│  │  │ (React)  │  │Extension │  │Extension │  │  (React      │  │  │
│  │  │          │  │          │  │          │  │   Native)    │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │  │
│  │       │              │             │               │           │  │
│  │       └──────────────┴──────┬──────┴───────────────┘           │  │
│  │                             │                                   │  │
│  │                             ▼                                   │  │
│  │                    ┌─────────────────┐                          │  │
│  │                    │   API Gateway   │                          │  │
│  │                    │  (Kong/Nginx)   │                          │  │
│  │                    └────────┬────────┘                          │  │
│  │                             │                                   │  │
│  │              ┌──────────────┼──────────────┐                   │  │
│  │              ▼              ▼              ▼                    │  │
│  │        ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │        │  Flask    │  │  Flask   │  │  Worker  │              │  │
│  │        │  Pod 1   │  │  Pod 2   │  │  (Async  │              │  │
│  │        │          │  │          │  │   Jobs)  │              │  │
│  │        └──────────┘  └──────────┘  └──────────┘              │  │
│  │                                                                │  │
│  │        ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │        │PostgreSQL│  │  Redis   │  │ Pinecone │              │  │
│  │        │          │  │  Cache   │  │ (Vector  │              │  │
│  │        │          │  │  + Queue │  │  Search) │              │  │
│  │        └──────────┘  └──────────┘  └──────────┘              │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  New Features:                                                        │
│  ✅ Claude (Anthropic) model support                                 │
│  ✅ Chrome extension                                                 │
│  ✅ Team collaboration (shared prompt libraries)                     │
│  ✅ Semantic caching (vector similarity)                             │
│  ✅ Async job queue for A/B tests                                    │
│  ✅ Horizontal auto-scaling                                          │
│  ✅ Webhook notifications                                            │
│  ✅ Mobile app                                                       │
└──────────────────────────────────────────────────────────────────────┘

11. 🧪 Testing Architecture

text

┌──────────────────────────────────────────────────────────────┐
│                    TESTING STRATEGY                            │
│                                                               │
│  CURRENT (v1.0):                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  test_fallback.py                                       │  │
│  │  └── Tests the 4-tier fallback chain                    │  │
│  │      • Gemini success path                              │  │
│  │      • Gemini fail → OpenAI success                     │  │
│  │      • All fail → error handling                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  RECOMMENDED (v1.5+):                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  Unit Tests (pytest)                                    │  │
│  │  ├── test_services.py     → AI service logic           │  │
│  │  ├── test_fallback.py     → Fallback chain ✅ exists   │  │
│  │  ├── test_validators.py   → Input validation           │  │
│  │  └── test_templates.py    → Prompt template integrity  │  │
│  │                                                         │  │
│  │  Integration Tests                                      │  │
│  │  ├── test_api_enhance.py  → /api/enhance endpoint      │  │
│  │  ├── test_api_quality.py  → /api/quality-heatmap       │  │
│  │  ├── test_api_abtest.py   → /api/ab-test               │  │
│  │  └── test_api_intent.py   → /api/detect-intent         │  │
│  │                                                         │  │
│  │  E2E Tests (Playwright/Selenium)                        │  │
│  │  ├── test_enhance_flow.py → Full user flow             │  │
│  │  └── test_history.py      → localStorage persistence   │  │
│  │                                                         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

12. 🖥️ Deployment Options (Current → Production)

text

┌──────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT OPTIONS                                  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OPTION A: Local Development (Current ✅)                      │  │
│  │                                                                 │  │
│  │  ./start.sh                                                     │  │
│  │    └── python3 app.py                                           │  │
│  │         └── Flask dev server @ localhost:5000                    │  │
│  │  Browser → frontend/index.html (file:// or served)              │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OPTION B: Single VPS (Recommended for v1.0 deploy)            │  │
│  │                                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │           VPS (DigitalOcean / Railway / Render)          │   │  │
│  │  │                                                          │   │  │
│  │  │  ┌──────────┐     ┌───────────────┐                     │   │  │
│  │  │  │  Nginx   │────▶│  Gunicorn     │                     │   │  │
│  │  │  │ (reverse │     │  (4 workers)  │                     │   │  │
│  │  │  │  proxy + │     │  running      │                     │   │  │
│  │  │  │  static  │     │  app.py       │                     │   │  │
│  │  │  │  files)  │     │               │                     │   │  │
│  │  │  └──────────┘     └───────────────┘                     │   │  │
│  │  │       │                                                  │   │  │
│  │  │       ├── /              → frontend/index.html (static) │   │  │
│  │  │       ├── /api/*         → proxy to Gunicorn :5000      │   │  │
│  │  │       └── /Public/*      → static files                 │   │  │
│  │  │                                                          │   │  │
│  │  │  SSL: Let's Encrypt (certbot)                            │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OPTION C: Docker (Recommended for portability)                │  │
│  │                                                                 │  │
│  │  docker-compose.yml:                                            │  │
│  │  ┌────────────────────────────────────────────────────────┐    │  │
│  │  │  services:                                              │    │  │
│  │  │    promptx-api:                                         │    │  │
│  │  │      build: .                                           │    │  │
│  │  │      ports: ["5000:5000"]                               │    │  │
│  │  │      env_file: .env                                     │    │  │
│  │  │      volumes: ["./frontend:/app/frontend"]              │    │  │
│  │  └────────────────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OPTION D: Free-Tier Hosting (Budget-Friendly)                 │  │
│  │                                                                 │  │
│  │  Frontend → Vercel / Netlify / GitHub Pages (free static)      │  │
│  │  Backend  → Railway / Render / Fly.io (free tier Flask)        │  │
│  │                                                                 │  │
│  │  ⚠️ Update API_BASE_URL in index.js to point to deployed      │  │
│  │     backend URL instead of localhost:5000                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

13. 📐 Architecture Summary Card

text

╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   PromptX v1.0 — Architecture Summary                                ║
║                                                                      ║
║   Type:          Monolithic (Client-Server)                          ║
║   Frontend:      Static SPA (Vanilla HTML/CSS/JS)                    ║
║   Backend:       Flask (Python) — Stateless                          ║
║   AI Engine:     Gemini 2.0 Flash (Primary)                          ║
║   Fallback:      Gemini → OpenAI → DeepSeek → HuggingFace           ║
║   Storage:       Client-side only (localStorage)                     ║
║   Database:      None (stateless backend)                            ║
║   Auth:          None (open access)                                  ║
║   Caching:       None (every request calls LLM)                      ║
║   Dependencies:  4 Python packages                                   ║
║   API Endpoints: 5 (health, enhance, intent, quality, ab-test)       ║
║   Startup Time:  < 3 seconds                                         ║
║   Response Time: < 2 seconds (avg)                                   ║
║   Bundle Size:   ~50KB                                               ║
║                                                                      ║
║   Key Pattern:   CHAIN OF RESPONSIBILITY (Fallback)                  ║
║   Key Strength:  Ultra-lightweight + Multi-model resilience          ║
║   Key Risk:      No auth, no caching, no persistence                 ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝