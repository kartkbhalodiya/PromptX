"""
PromptX API Views
Django equivalents of all Flask endpoints from app.py.
"""

import json
import logging
import re

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from .utils import sanitize_input, classify_prompt, score_prompt, MASTER_PROMPT, WELCOME_SYSTEM_PROMPT, DEEP_RESEARCH_PROMPT
# Import from parent backend directory
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import (
    detect_intent, apply_smart_template,
    analyze_quality_heatmap,
    generate_ab_variations, compare_variations,
    generate_with_fallback,
    scrape_url, scrape_website_deep, web_search,
)

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Extract client IP for logging"""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _parse_json(request):
    """Parse JSON body from request, returns (data, error_response)"""
    try:
        data = json.loads(request.body)
        return data, None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({'error': 'Invalid JSON payload'}, status=400)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@require_http_methods(["GET"])
def health_view(request):
    return JsonResponse({
        'status': 'healthy',
        'version': '2.0.0',
        'framework': 'django',
        'model': 'gemini-pro'
    })


# ============================================================================
# ENHANCE ENDPOINT
# ============================================================================

# Short phrases that are greetings / meta-questions, not prompts to enhance
_GREETING_PATTERNS = {
    'hi', 'hello', 'hey', 'hii', 'helo', 'heya', 'howdy',
    'hi there', 'hello there', 'hey there',
    'what can you do', 'what do you do', 'who are you',
    'help', 'help me', 'what is this', 'how does this work',
    'good morning', 'good afternoon', 'good evening', 'good night',
    'sup', 'yo', 'wassup', 'whats up', "what's up",
}

# Signals that the user wants a deep, exhaustive answer — not just a prompt rewrite
_DEEP_RESEARCH_SIGNALS = [
    'build a', 'build an', 'create a', 'create an', 'make a', 'make an',
    'develop a', 'develop an', 'design a', 'design an',
    'like flipkart', 'like amazon', 'like uber', 'like airbnb', 'like netflix',
    'like instagram', 'like twitter', 'like facebook', 'like youtube',
    'like whatsapp', 'like linkedin', 'like shopify', 'like stripe',
    'same features', 'same as', 'similar to', 'clone of',
    'full website', 'full app', 'full stack', 'full-stack',
    'complete website', 'complete app', 'complete system',
    'e-commerce', 'ecommerce', 'marketplace', 'social media platform',
    'how to build', 'how do i build', 'how to create', 'how to develop',
    'architecture for', 'system design', 'tech stack for',
    'explain in detail', 'explain deeply', 'deep dive', 'in depth',
    'comprehensive guide', 'step by step guide', 'complete guide',
    'everything about', 'tell me everything',
]

def _is_greeting(text: str) -> bool:
    cleaned = text.strip().lower().rstrip('!?.').strip()
    return cleaned in _GREETING_PATTERNS or (
        len(cleaned.split()) <= 2 and
        any(cleaned.startswith(g) for g in ('hi', 'hey', 'hello', 'helo'))
    )

def _needs_deep_research(text: str) -> bool:
    """Detect if the user wants a comprehensive deep-dive answer, not just a prompt rewrite."""
    lower = text.lower()
    signal_count = sum(1 for s in _DEEP_RESEARCH_SIGNALS if s in lower)
    # Trigger deep research if 2+ signals OR the prompt is asking to build something complex
    if signal_count >= 2:
        return True
    # Single strong signal + sufficient length
    if signal_count >= 1 and len(text.split()) >= 8:
        return True
    return False

_URL_PATTERN = re.compile(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', re.IGNORECASE)

def _extract_urls(text: str) -> list:
    """Extract all URLs from a text string."""
    urls = _URL_PATTERN.findall(text)
    return [u if u.startswith('http') else f'https://{u}' for u in urls]


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='20/m', block=True)
def enhance_view(request):
    """Enhance a prompt using AI — with deep research mode for complex requests"""
    try:
        data, err = _parse_json(request)
        if err:
            return err

        if 'prompt' not in data:
            return JsonResponse({'error': 'Prompt is missing from payload'}, status=400)

        prompt = sanitize_input(data['prompt'])
        if not prompt:
            logger.warning(f"Prompt failed sanitization from {_get_client_ip(request)}")
            return JsonResponse({'error': 'Prompt is empty or invalid'}, status=400)
        if len(prompt) > 100000:
            return JsonResponse({'error': f'Prompt too long: {len(prompt)} chars'}, status=400)

        preferred_model = data.get('model')
        model_arg = preferred_model if preferred_model in ('gemini', 'groq') else None

        # ── 1. Greeting → welcome response ───────────────────────────────────
        if _is_greeting(prompt):
            welcome_prompt = (
                f"{WELCOME_SYSTEM_PROMPT}\n\n"
                f"The user just said: \"{prompt}\"\n\n"
                f"Respond with a warm, helpful welcome message."
            )
            result = generate_with_fallback(welcome_prompt, max_tokens=600, preferred_model=model_arg)
            return JsonResponse({
                'success': True,
                'type': 'welcome',
                'enhanced': result['text'],
                'model': result['model'],
                'original': prompt,
                'original_score': {'total': 0, 'percentage': 0, 'quality': 'N/A'},
                'enhanced_score': {'total': 0, 'percentage': 0, 'quality': 'N/A'},
                'improvement': 0,
                'classification': {'category': 'greeting', 'confidence': 1.0},
            })

        # ── 2. URL in prompt → deep multi-page scrape + web search ──────────
        urls_in_prompt = _extract_urls(prompt)
        if urls_in_prompt:
            url = urls_in_prompt[0]
            logger.info(f"URL detected in prompt, deep crawling: {url}")

            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            site_name = domain.split('.')[0].capitalize()

            crawl = scrape_website_deep(url, max_pages=6, chars_per_page=4000)

            # Also run web searches for tech stack info
            search_results = web_search(f"{site_name} {domain} tech stack API features", max_results=4)
            search_text = '\n'.join(
                f"[{r['title']}] {r['url']}\n{r['snippet']}"
                for r in search_results
            ) if search_results else '(no additional search results)'

            if crawl['success']:
                pages_list = '\n'.join(f"  • {p['title']} — {p['url']}" for p in crawl['pages'])
                url_analysis_prompt = f"""You are a world-class product analyst and full-stack architect.

The user shared this website and said: "{prompt}"

You have scraped {crawl['pages_scraped']} pages of the site and gathered web search intelligence.
Provide a deep, exhaustive analysis.

SCRAPED PAGES:
{pages_list}

FULL CONTENT ({crawl['total_chars']:,} chars):
{crawl['combined_text'][:28000]}

WEB SEARCH RESULTS:
{search_text}

Provide a complete analysis:

## 🌐 What This Website Is
Product, audience, business model, value proposition.

## ✨ Complete Feature List
Every feature found across all pages, grouped by category with priority labels.

## 🏗️ Tech Stack & Architecture (inferred + from search)
Frontend, backend, database, hosting, CDN, auth, payments, analytics.
List every third-party API/service detected with evidence.

## 🔌 APIs & Integrations
Table of every API, SDK, or integration found.

## 📊 Business Intelligence
Pricing, tiers, growth signals, competitive positioning.

## 🚀 How to Build Something Like This
Full tech stack recommendation, key components, timeline, team size, cost estimate.

## ⚠️ Key Challenges
The hardest parts to build and common mistakes to avoid.

Use rich markdown. Be specific. Reference actual content from the pages."""

                result = generate_with_fallback(url_analysis_prompt, max_tokens=6000, preferred_model=model_arg)
                classification = classify_prompt(prompt)
                return JsonResponse({
                    'success': True,
                    'type': 'url_analysis',
                    'original': prompt,
                    'enhanced': result['text'],
                    'url': url,
                    'page_title': crawl['site_title'],
                    'pages_scraped': crawl['pages_scraped'],
                    'total_chars': crawl['total_chars'],
                    'pages': [{'url': p['url'], 'title': p['title']} for p in crawl['pages']],
                    'model': result['model'],
                    'classification': classification,
                    'original_score': score_prompt(prompt),
                    'enhanced_score': score_prompt(result['text']),
                    'improvement': 0,
                })
            else:
                # Crawl failed — use AI knowledge about the URL
                logger.warning(f"Crawl failed for {url}: {crawl['error']}")
                fallback_prompt = (
                    f"The user wants to analyze: {url}\n"
                    f"Scraping failed: {crawl['error']}\n\n"
                    f"Web search results:\n{search_text}\n\n"
                    f"Based on the URL and search results, provide what you know about "
                    f"this website/product and what someone would need to build something similar.\n"
                    f"User's message: {prompt}"
                )
                result = generate_with_fallback(fallback_prompt, max_tokens=3000, preferred_model=model_arg)
                return JsonResponse({
                    'success': True,
                    'type': 'url_analysis',
                    'original': prompt,
                    'enhanced': result['text'],
                    'url': url,
                    'page_title': url,
                    'pages_scraped': 0,
                    'total_chars': 0,
                    'pages': [],
                    'scrape_error': crawl['error'],
                    'model': result['model'],
                    'classification': classify_prompt(prompt),
                    'original_score': score_prompt(prompt),
                    'enhanced_score': score_prompt(result['text']),
                    'improvement': 0,
                })

        # ── 3. Complex build/research request → deep research mode ───────────
        if _needs_deep_research(prompt):
            logger.info(f"Deep research mode triggered for: {prompt[:80]}...")

            # Pass 1: Analyze the request and extract structured requirements
            analysis_prompt = f"""You are a senior technical analyst. Analyze this request and extract:
1. The core product/system being requested
2. Key features mentioned (explicit and implied)
3. Target users
4. Scale/complexity level
5. Any reference products mentioned (e.g. "like Flipkart")

Request: "{prompt}"

Respond in 3-5 sentences, very concisely. This is an internal analysis step."""

            analysis_result = generate_with_fallback(analysis_prompt, max_tokens=400, preferred_model=model_arg)
            analysis_text = analysis_result['text']

            # Pass 2: Generate the full deep-dive answer using the analysis
            deep_prompt = (
                f"{DEEP_RESEARCH_PROMPT}\n\n"
                f"═══════════════════════════════════════\n"
                f"USER REQUEST:\n{prompt}\n\n"
                f"INTERNAL ANALYSIS:\n{analysis_text}\n"
                f"═══════════════════════════════════════\n\n"
                f"Now provide the complete, exhaustive expert answer covering ALL 12 sections above. "
                f"Be extremely detailed. Do not skip any section. Minimum 2000 words."
            )

            result = generate_with_fallback(deep_prompt, max_tokens=8000, preferred_model=model_arg)
            enhanced = result['text']
            model_used = result['model']

            original_score = score_prompt(prompt)
            enhanced_score = score_prompt(enhanced)
            classification = classify_prompt(prompt)

            logger.info(f"Deep research completed for [{classification['category']}] via {model_used}")
            return JsonResponse({
                'success': True,
                'type': 'deep_research',
                'original': prompt,
                'enhanced': enhanced,
                'analysis': analysis_text,
                'classification': classification,
                'original_score': original_score,
                'enhanced_score': enhanced_score,
                'improvement': round(enhanced_score['total'] - original_score['total'], 2),
                'model': model_used,
            })

        # ── 4. Normal prompt enhancement ─────────────────────────────────────
        classification = classify_prompt(prompt)
        original_score = score_prompt(prompt)

        category_hints = {
            'code':      "Pay special attention to: language/framework specification, input/output types, error handling, edge cases, and code style requirements.",
            'blog':      "Pay special attention to: target audience, SEO keywords, tone of voice, word count, structure (intro/body/conclusion), and call-to-action.",
            'business':  "Pay special attention to: stakeholder audience, business objective, key metrics, timeline, and professional tone.",
            'academic':  "Pay special attention to: research question, methodology, citation style, academic tone, and argument structure.",
            'creative':  "Pay special attention to: genre, narrative voice, character depth, world-building details, and emotional tone.",
            'data':      "Pay special attention to: data format, analysis method, visualization type, statistical requirements, and output format.",
            'assistant': "Pay special attention to: clarity of the question, expected depth of answer, format of response, and audience expertise level.",
        }
        category = classification.get('category', 'general')
        hint = category_hints.get(category, "Pay special attention to clarity, specificity, and actionable detail.")

        full_prompt = (
            f"{MASTER_PROMPT}\n\n"
            f"Category detected: {category.upper()}\n"
            f"Category-specific guidance: {hint}\n\n"
            f"User prompt to enhance:\n{prompt}"
        )

        result = generate_with_fallback(full_prompt, max_tokens=3000, preferred_model=model_arg)
        enhanced = result['text']
        model_used = result['model']
        enhanced_score = score_prompt(enhanced)

        logger.info(f"Enhanced [{category}] prompt from {_get_client_ip(request)} via {model_used}")
        return JsonResponse({
            'success': True,
            'type': 'enhancement',
            'original': prompt,
            'enhanced': enhanced,
            'classification': classification,
            'original_score': original_score,
            'enhanced_score': enhanced_score,
            'improvement': round(enhanced_score['total'] - original_score['total'], 2),
            'model': model_used,
        })

    except Exception as e:
        logger.error(f"Error in enhance endpoint: {str(e)}")
        return JsonResponse(
            {'error': 'An internal server error occurred.', 'success': False},
            status=500
        )


# ============================================================================
# DETECT INTENT ENDPOINT
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='20/m', block=True)
def detect_intent_view(request):
    """Auto-detect prompt intent and suggest template"""
    try:
        data, err = _parse_json(request)
        if err:
            return err
        
        if 'prompt' not in data:
            return JsonResponse({'error': 'Prompt is missing'}, status=400)
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            logger.warning(f"Intent detection prompt empty or invalid from {_get_client_ip(request)}")
            return JsonResponse({'error': 'Prompt is empty or invalid'}, status=400)
        
        intent_data = detect_intent(prompt)
        
        # Optionally apply template
        if data.get('apply_template', False):
            enhanced = apply_smart_template(prompt, intent_data)
            intent_data['enhanced_prompt'] = enhanced
        
        logger.info(f"Intent detected for {_get_client_ip(request)}")
        return JsonResponse({
            'success': True,
            'data': intent_data
        })
    
    except Exception as e:
        logger.error(f"Error in intent endpoint: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# QUALITY HEATMAP ENDPOINT
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='20/m', block=True)
def quality_heatmap_view(request):
    """Get detailed quality heatmap analysis"""
    try:
        data, err = _parse_json(request)
        if err:
            return err
        
        if 'prompt' not in data:
            return JsonResponse({'error': 'Prompt is missing'}, status=400)
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            return JsonResponse({'error': 'Prompt is empty or invalid'}, status=400)
        
        analysis = analyze_quality_heatmap(prompt)
        
        logger.info(f"Quality heatmap generated for {_get_client_ip(request)}")
        return JsonResponse({
            'success': True,
            'data': analysis
        })
    
    except Exception as e:
        logger.error(f"Error in quality endpoint: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# A/B TEST ENDPOINT
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='5/m', block=True)
def ab_test_view(request):
    """Generate 3 A/B test variations"""
    try:
        data, err = _parse_json(request)
        if err:
            return err
        
        if 'prompt' not in data:
            return JsonResponse({'error': 'Prompt is missing'}, status=400)
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            return JsonResponse({'error': 'Prompt is empty or invalid'}, status=400)
        
        variations = generate_ab_variations(prompt)
        
        # Optionally include comparison
        if data.get('include_comparison', True):
            comparison = compare_variations(prompt, variations)
            return JsonResponse({
                'success': True,
                'data': comparison
            })
        
        logger.info(f"A/B variations generated for {_get_client_ip(request)}")
        return JsonResponse({
            'success': True,
            'data': {'variations': variations}
        })
    
    except Exception as e:
        logger.error(f"Error in AB test endpoint: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# ANALYZE URL ENDPOINT  — deep multi-page crawl + web search
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='5/m', block=True)
def analyze_url_view(request):
    """
    Deep website analysis:
    1. Crawls homepage + up to 8 sub-pages (features, pricing, docs, api, etc.)
    2. Runs 3 parallel web searches for tech stack, docs, and APIs used
    3. Synthesises everything into an exhaustive expert report
    Body: { url, question?, model? }
    """
    try:
        data, err = _parse_json(request)
        if err:
            return err

        url = (data.get('url') or '').strip()
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        if not url.startswith('http'):
            url = f'https://{url}'

        question = sanitize_input(data.get('question', '').strip()) or \
                   'Give a complete deep analysis of this website.'
        model_arg = data.get('model') if data.get('model') in ('gemini', 'groq') else None

        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        site_name = domain.split('.')[0].capitalize()

        logger.info(f"Deep website analysis started: {url}")

        # ── Step 1: Multi-page crawl ──────────────────────────────────────
        crawl = scrape_website_deep(url, max_pages=8, chars_per_page=5000)

        if not crawl['success']:
            return JsonResponse({
                'success': False,
                'error': f"Could not fetch the website: {crawl['error']}",
                'url': url,
            }, status=422)

        pages_summary = '\n'.join(
            f"  • [{p['title']}] {p['url']}"
            for p in crawl['pages']
        )

        # ── Step 2: Parallel web searches ────────────────────────────────
        search_queries = [
            f"{site_name} {domain} tech stack technology used",
            f"{site_name} {domain} API documentation developers",
            f"{site_name} {domain} backend architecture how it works",
        ]
        all_search_results = []
        for q in search_queries:
            results = web_search(q, max_results=4)
            if results:
                all_search_results.append({
                    'query': q,
                    'results': results,
                })

        search_context = ''
        if all_search_results:
            parts = []
            for sr in all_search_results:
                block = f"Search: \"{sr['query']}\"\n"
                block += '\n'.join(
                    f"  [{r['title']}] {r['url']}\n  {r['snippet']}"
                    for r in sr['results']
                )
                parts.append(block)
            search_context = '\n\n'.join(parts)

        # ── Step 3: Build the mega-analysis prompt ────────────────────────
        analysis_prompt = f"""You are a world-class senior software architect, product analyst, reverse-engineer, and technical writer.

You have been given:
1. Full scraped content from {crawl['pages_scraped']} pages of the website "{site_name}" ({url})
2. Web search results about its tech stack, APIs, and documentation

Your job: produce the most comprehensive, detailed, expert-level analysis possible.
The user's specific question: "{question}"

═══════════════════════════════════════════════════════════════
SCRAPED PAGES ({crawl['pages_scraped']} pages, {crawl['total_chars']:,} total chars):
{pages_summary}

FULL SCRAPED CONTENT:
{crawl['combined_text'][:35000]}

═══════════════════════════════════════════════════════════════
WEB SEARCH INTELLIGENCE:
{search_context if search_context else '(No additional search results available)'}

═══════════════════════════════════════════════════════════════
NOW PRODUCE THE COMPLETE ANALYSIS — cover ALL sections below:

## 🌐 1. WEBSITE OVERVIEW
- What this product/service is in precise terms
- Core value proposition (what problem it solves)
- Target audience (primary and secondary users)
- Business model (freemium / SaaS / marketplace / ads / etc.)
- Company/product stage (startup / scale-up / enterprise)
- Geographic focus and market positioning

## ✨ 2. COMPLETE FEATURE LIST
List EVERY feature you can identify, grouped by category. For each feature include:
- Feature name
- What it does (1-2 sentences)
- Which page/section it was found on
- Priority estimate (Core / Secondary / Premium)

Categories to cover: Core Product, User Management & Auth, Dashboard/UI, 
Integrations & APIs, Analytics & Reporting, Admin Panel, Mobile, 
Notifications, Search, Payments, Security, Developer Tools

## 🏗️ 3. TECHNICAL ARCHITECTURE (INFERRED)
Based on scraped content AND web search results:
- **Frontend**: Framework (React/Vue/Angular/Next.js?), UI library, state management
- **Backend**: Language, framework, API style (REST/GraphQL/gRPC)
- **Database**: Primary DB, caching (Redis?), search engine (Elasticsearch?)
- **Infrastructure**: Cloud provider (AWS/GCP/Azure?), CDN, containerisation
- **Authentication**: OAuth providers, SSO, 2FA methods
- **Payments**: Payment gateway(s) detected
- **Analytics**: Tracking tools, monitoring, error reporting
- **Third-party APIs**: Every external service/API mentioned or inferred
- **Mobile**: Native app / PWA / React Native?
- Evidence for each inference (quote from scraped content or search result)

## 🔌 4. APIs & INTEGRATIONS DETECTED
List every API, SDK, or third-party integration you can identify:
| Integration | Type | Purpose | Evidence |
|-------------|------|---------|----------|
(fill in the table)

## 📡 5. DEVELOPER / API DOCUMENTATION
- Does this site have a public API? What endpoints are documented?
- SDK availability (languages supported)
- Authentication method for their API (API key / OAuth / JWT)
- Rate limits mentioned
- Webhook support
- Developer portal URL if found

## 🎨 6. UX & DESIGN ANALYSIS
- Navigation structure and information architecture
- Key user flows (signup → onboarding → core action)
- Design system observations (component library, colour scheme, typography)
- Accessibility features noticed
- Performance optimisations visible (lazy loading, CDN assets, etc.)
- Mobile responsiveness approach

## 📊 7. BUSINESS & PRODUCT INTELLIGENCE
- Pricing model and tiers (exact prices if found)
- Free trial / freemium details
- Enterprise offering
- Key differentiators vs competitors
- Growth signals (customer count, testimonials, case studies found)
- SEO strategy visible from content

## 🔐 8. SECURITY OBSERVATIONS
- Authentication methods (SSO, 2FA, OAuth providers)
- Security certifications mentioned (SOC2, ISO27001, GDPR, HIPAA)
- Data handling and privacy approach
- Security features for users (audit logs, permissions, etc.)

## 🚀 9. HOW TO BUILD SOMETHING SIMILAR — COMPLETE GUIDE
### Recommended Tech Stack
| Layer | Technology | Why |
|-------|-----------|-----|
(fill in the table)

### Core Components to Build
For each component: name, description, estimated complexity (days), key libraries

### Development Phases
- **Phase 1 — MVP (4-8 weeks)**: Minimum features to launch
- **Phase 2 — Growth (2-4 months)**: Scaling features
- **Phase 3 — Scale (6-12 months)**: Enterprise features

### Team Required
- Roles needed, seniority level, estimated headcount

### Estimated Cost
- Development cost range
- Monthly infrastructure cost at different scales

## ⚠️ 10. KEY CHALLENGES & WHAT MAKES THIS HARD
- The 5 hardest technical problems to solve
- Common mistakes teams make building this type of product
- Regulatory/compliance challenges
- Scaling bottlenecks to plan for

## 💡 11. ACTIONABLE RECOMMENDATIONS
If the user wants to build something like this:
- The 3 most important things to get right from day 1
- What to build vs what to buy (use existing services for)
- Open-source alternatives to study
- Specific libraries/frameworks to use for each major feature

═══════════════════════════════════════════════════════════════
FORMATTING RULES:
- Use rich markdown: ## headers, **bold**, `code`, tables, bullet lists
- Be SPECIFIC — reference actual content found on the pages
- Use tables wherever comparison or listing is involved
- Include actual URLs, product names, and technical terms found
- Minimum length: 3000 words
- Do NOT skip any section
- Do NOT say "I cannot determine" — make educated inferences and label them as such"""

        result = generate_with_fallback(analysis_prompt, max_tokens=8000, preferred_model=model_arg)

        logger.info(
            f"Deep URL analysis complete: {url} | "
            f"{crawl['pages_scraped']} pages | "
            f"{crawl['total_chars']:,} chars | "
            f"model={result['model']}"
        )

        return JsonResponse({
            'success': True,
            'url': url,
            'site_title': crawl['site_title'],
            'pages_scraped': crawl['pages_scraped'],
            'pages': [{'url': p['url'], 'title': p['title']} for p in crawl['pages']],
            'total_chars': crawl['total_chars'],
            'search_queries': [sr['query'] for sr in all_search_results],
            'analysis': result['text'],
            'model': result['model'],
        })

    except Exception as e:
        logger.error(f"Error in analyze-url endpoint: {str(e)}")
        return JsonResponse({'error': 'An internal server error occurred.', 'success': False}, status=500)


# ============================================================================
# WEB SEARCH ENDPOINT
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='15/m', block=True)
def web_search_view(request):
    """
    Search the web and return AI-synthesized results.
    Body: { query: string, model?: string }
    """
    try:
        data, err = _parse_json(request)
        if err:
            return err

        query = sanitize_input((data.get('query') or '').strip())
        if not query:
            return JsonResponse({'error': 'Search query is required'}, status=400)

        model_arg = data.get('model') if data.get('model') in ('gemini', 'groq') else None

        logger.info(f"Web search: {query}")
        results = web_search(query, max_results=6)

        if not results:
            return JsonResponse({
                'success': False,
                'error': 'No search results found. Try a different query.',
                'results': [],
            }, status=422)

        # Format results for AI synthesis
        results_text = '\n\n'.join(
            f"[{i+1}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
            for i, r in enumerate(results)
        )

        synthesis_prompt = f"""You are a research analyst. Based on these web search results, provide a comprehensive, well-structured answer to the query.

Query: "{query}"

Search Results:
{results_text}

Provide:
## 📋 Summary
A clear, direct answer to the query based on the search results.

## 🔍 Key Findings
The most important information from the results, with specific details.

## 🔗 Sources
List the relevant URLs found.

## 💡 Additional Context
Any important context, caveats, or related information worth knowing.

Be factual, specific, and cite which results support each point."""

        result = generate_with_fallback(synthesis_prompt, max_tokens=2000, preferred_model=model_arg)

        return JsonResponse({
            'success': True,
            'query': query,
            'raw_results': results,
            'synthesis': result['text'],
            'model': result['model'],
            'result_count': len(results),
        })

    except Exception as e:
        logger.error(f"Error in web-search endpoint: {str(e)}")
        return JsonResponse({'error': 'An internal server error occurred.', 'success': False}, status=500)
