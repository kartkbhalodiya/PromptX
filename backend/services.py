"""  
PromptX Services - Gemini + Groq fallback, web scraping, search
"""
from google import genai
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

import copy
from functools import wraps
from collections import OrderedDict

class DeepCopyLRUCache:
    """An LRU Cache wrapper that returns deep copies of cached values to prevent mutation side-effects."""
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            if key in self.cache:
                self.cache.move_to_end(key)
                return copy.deepcopy(self.cache[key])
            result = func(*args, **kwargs)
            self.cache[key] = copy.deepcopy(result)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            return result
        return wrapper

# ============================================================================
# MULTI-MODEL FALLBACK SYSTEM
# ============================================================================

class AIModelFallback:
    """Handles automatic fallback between Gemini and Groq"""
    
    def __init__(self):
        self.models = [
            {'name': 'gemini', 'priority': 1},
            {'name': 'groq',   'priority': 2},
        ]
    
    def generate(self, prompt, max_tokens=2000, preferred_model=None):
        """Try models in order until one succeeds."""
        errors = []
        
        if preferred_model:
            model_order = [m for m in self.models if m['name'] == preferred_model]
            model_order += [m for m in self.models if m['name'] != preferred_model]
        else:
            model_order = self.models
        
        for model in model_order:
            try:
                result = self._call_model(model['name'], prompt, max_tokens)
                if result:
                    return {'text': result, 'model': model['name'], 'success': True}
            except Exception as e:
                errors.append(f"{model['name']}: {str(e)}")
                continue
        
        raise Exception(f"All models failed. Errors: {'; '.join(errors)}")
    
    def _call_model(self, model_name, prompt, max_tokens):
        if model_name == 'gemini':
            return self._call_gemini(prompt)
        elif model_name == 'groq':
            return self._call_groq(prompt, max_tokens)
    
    def _call_gemini(self, prompt):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text.strip()

    def _call_groq(self, prompt, max_tokens):
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': self._split_prompt(prompt),
                'max_tokens': min(max_tokens, 8192),
                'temperature': 0.7,
            },
            timeout=60
        )
        response.raise_for_status()
        msg = response.json().get('choices', [{}])[0].get('message', {})
        return str(msg.get('content', '')).strip()

    def _split_prompt(self, prompt):
        """Separate system and user parts if combined."""
        delimiter = "\n\nUser prompt to enhance:\n"
        if delimiter in prompt:
            parts = prompt.split(delimiter, 1)
            return [
                {'role': 'system', 'content': parts[0].strip()},
                {'role': 'user',   'content': parts[1].strip()}
            ]
        if ":\n" in prompt and any(k in prompt for k in ["Make this prompt concise", "Rewrite this prompt", "Expand this prompt"]):
            parts = prompt.split(":\n", 1)
            return [
                {'role': 'system', 'content': parts[0].strip()},
                {'role': 'user',   'content': parts[1].strip()}
            ]
        return [{'role': 'user', 'content': prompt}]


# Global fallback instance
_fallback = AIModelFallback()

def get_client():
    """Legacy function - returns Gemini client"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    return genai.Client(api_key=api_key)

@DeepCopyLRUCache(capacity=500)
def generate_with_fallback(prompt, max_tokens=2000, preferred_model=None):
    """Generate text with automatic model fallback."""
    return _fallback.generate(prompt, max_tokens, preferred_model=preferred_model)


# ============================================================================
# WEB SCRAPING & SEARCH
# ============================================================================

_SCRAPE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Pages worth crawling on any website
_VALUABLE_PATHS = [
    '/', '/about', '/about-us', '/features', '/pricing', '/docs',
    '/documentation', '/api', '/api-docs', '/developers', '/tech',
    '/blog', '/careers', '/team', '/product', '/solutions',
    '/how-it-works', '/integrations', '/security', '/enterprise',
]


def _clean_html(html: str, max_chars: int = 8000) -> tuple:
    """Strip HTML and return (title, clean_text)."""
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''

    # Remove noise tags
    html = re.sub(
        r'<(script|style|noscript|nav|footer|header|aside|iframe|svg|'
        r'form|button|input|select|textarea|meta|link)[^>]*>.*?</\1>',
        '', html, flags=re.IGNORECASE | re.DOTALL
    )
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    for ent, ch in [
        ('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),
        ('&#39;',"'"),('&nbsp;',' '),('&mdash;','—'),('&ndash;','–'),
        ('&hellip;','...'),('&copy;','©'),('&reg;','®'),
    ]:
        text = text.replace(ent, ch)

    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(l.strip() for l in text.splitlines() if l.strip())

    if len(text) > max_chars:
        text = text[:max_chars] + f'\n[truncated at {max_chars} chars]'

    return title, text


def _extract_internal_links(html: str, base_url: str) -> list:
    """Extract unique internal links from HTML."""
    from urllib.parse import urljoin, urlparse
    base = urlparse(base_url)
    base_root = f"{base.scheme}://{base.netloc}"

    hrefs = re.findall(r'<a[^>]+href=["\']([^"\'#?]+)["\']', html, re.IGNORECASE)
    seen = set()
    links = []
    for href in hrefs:
        full = urljoin(base_root, href)
        parsed = urlparse(full)
        # Only same-domain, no files
        if (parsed.netloc == base.netloc and
                not re.search(r'\.(pdf|jpg|png|gif|svg|zip|css|js|ico|woff)$', parsed.path, re.I) and
                full not in seen):
            seen.add(full)
            links.append(full)
    return links


def scrape_url(url: str, max_chars: int = 8000) -> dict:
    """Scrape a single URL. Returns { success, url, title, text, char_count, links, error }."""
    try:
        resp = requests.get(url, headers=_SCRAPE_HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        title, text = _clean_html(html, max_chars)
        links = _extract_internal_links(html, url)
        return {
            'success': True, 'url': url, 'title': title or url,
            'text': text, 'char_count': len(text),
            'links': links, 'error': None,
        }
    except requests.exceptions.Timeout:
        return {'success': False, 'url': url, 'title': '', 'text': '',
                'char_count': 0, 'links': [], 'error': 'Timed out after 12s'}
    except requests.exceptions.HTTPError as e:
        return {'success': False, 'url': url, 'title': '', 'text': '',
                'char_count': 0, 'links': [], 'error': f'HTTP {e.response.status_code}'}
    except Exception as e:
        return {'success': False, 'url': url, 'title': '', 'text': '',
                'char_count': 0, 'links': [], 'error': str(e)}


def scrape_website_deep(base_url: str, max_pages: int = 8, chars_per_page: int = 6000) -> dict:
    """
    Multi-page website crawler.
    Scrapes the homepage + up to max_pages valuable sub-pages.
    Returns aggregated content with per-page breakdown.
    """
    from urllib.parse import urlparse, urljoin

    parsed = urlparse(base_url)
    base_root = f"{parsed.scheme}://{parsed.netloc}"

    # Step 1: Scrape homepage
    home = scrape_url(base_url, chars_per_page)
    if not home['success']:
        return {
            'success': False,
            'base_url': base_url,
            'pages_scraped': 0,
            'pages': [],
            'combined_text': '',
            'total_chars': 0,
            'error': home['error'],
        }

    pages = [{'url': base_url, 'title': home['title'], 'text': home['text']}]

    # Step 2: Build candidate URLs — valuable paths + links found on homepage
    candidates = []
    for path in _VALUABLE_PATHS:
        candidates.append(urljoin(base_root, path))
    for link in home.get('links', [])[:30]:
        if link not in candidates:
            candidates.append(link)

    # Step 3: Scrape candidates until we hit max_pages
    scraped_urls = {base_url}
    for candidate in candidates:
        if len(pages) >= max_pages:
            break
        if candidate in scraped_urls:
            continue
        scraped_urls.add(candidate)

        result = scrape_url(candidate, chars_per_page)
        if result['success'] and result['char_count'] > 200:
            pages.append({
                'url': candidate,
                'title': result['title'],
                'text': result['text'],
            })

    # Step 4: Combine all page text
    combined_parts = []
    for p in pages:
        combined_parts.append(
            f"=== PAGE: {p['title']} ===\n"
            f"URL: {p['url']}\n\n"
            f"{p['text']}"
        )
    combined_text = '\n\n' + ('\n\n' + '─'*60 + '\n\n').join(combined_parts)

    return {
        'success': True,
        'base_url': base_url,
        'site_title': home['title'],
        'pages_scraped': len(pages),
        'pages': pages,
        'combined_text': combined_text,
        'total_chars': sum(p['text'].__len__() for p in pages),
        'error': None,
    }


def web_search(query: str, max_results: int = 6) -> list:
    """
    Search the web using DuckDuckGo HTML (no API key required).
    Returns list of { title, url, snippet }
    """
    try:
        params = {'q': query, 'kl': 'us-en', 'kp': '-1'}
        resp = requests.get(
            'https://html.duckduckgo.com/html/',
            params=params, headers=_SCRAPE_HEADERS, timeout=10
        )
        resp.raise_for_status()
        html = resp.text
        results = []

        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for url, title_html, snippet_html in blocks[:max_results]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
            real_url_match = re.search(r'uddg=([^&]+)', url)
            if real_url_match:
                from urllib.parse import unquote
                url = unquote(real_url_match.group(1))
            if title and url.startswith('http'):
                results.append({'title': title, 'url': url, 'snippet': snippet})

        return results
    except Exception as e:
        print(f"Web search error: {e}")
        return []

# ============================================================================
# INTENT DETECTION
# ============================================================================

@DeepCopyLRUCache(capacity=500)
def detect_intent(prompt):
    """Detect prompt intent"""
    keywords = {
        'content': ['blog', 'article', 'write', 'content'],
        'code': ['code', 'function', 'program', 'debug'],
        'analysis': ['analyze', 'research', 'study'],
        'creative': ['story', 'creative', 'design']
    }
    
    prompt_lower = prompt.lower()
    for intent, words in keywords.items():
        if any(w in prompt_lower for w in words):
            return {
                'intent': intent,
                'confidence': 0.8,
                'tone': 'professional'
            }
    
    return {'intent': 'general', 'confidence': 0.5, 'tone': 'neutral'}

def apply_smart_template(prompt, intent_data):
    """Apply template based on intent"""
    return prompt  # Simple passthrough

# ============================================================================
# QUALITY ANALYZER
# ============================================================================

@DeepCopyLRUCache(capacity=500)
def analyze_quality_heatmap(prompt):
    """Analyze prompt quality"""
    length = len(prompt)
    
    # Calculate scores
    clarity = min(10, (length / 50) * 2)
    specificity = min(10, len(prompt.split()) / 10)
    structure = 8 if '\n' in prompt else 4
    context = 7 if length > 100 else 3
    constraints = 6 if any(w in prompt.lower() for w in ['must', 'should']) else 3
    output_format = 7 if any(w in prompt.lower() for w in ['format', 'structure']) else 4
    
    overall = round((clarity + specificity + structure + context + constraints + output_format) / 6, 1)
    
    # Generate suggestions
    suggestions = []
    if clarity < 5:
        suggestions.append({
            'category': 'Clarity',
            'issue': 'Prompt is too vague',
            'fix': 'Add specific details about what you want'
        })
    if specificity < 5:
        suggestions.append({
            'category': 'Specificity',
            'issue': 'Lacks specific requirements',
            'fix': 'Specify tone, length, and format'
        })
    
    grade = 'A' if overall >= 9 else 'B' if overall >= 7 else 'C' if overall >= 5 else 'D' if overall >= 3 else 'F'
    
    return {
        'overall': overall,
        'grade': grade,
        'metrics': {
            'clarity': {'score': round(clarity, 1)},
            'specificity': {'score': round(specificity, 1)},
            'structure': {'score': round(structure, 1)},
            'context': {'score': round(context, 1)},
            'constraints': {'score': round(constraints, 1)},
            'output_format': {'score': round(output_format, 1)}
        },
        'suggestions': suggestions
    }

# ============================================================================
# A/B TESTING
# ============================================================================

@DeepCopyLRUCache(capacity=500)
def generate_ab_variations(prompt):
    """Generate 3 variations with fallback concurrently to prevent Vercel Application Timeouts"""
    
    def fetch_variation(style_prompt, max_tokens, preferred_model=None):
        result = generate_with_fallback(style_prompt, max_tokens, preferred_model=preferred_model)
        return {'text': result['text'], 'length': len(result['text']), 'model': result['model']}

    try:
        # Prepare prompts
        c_prompt = f"Make this prompt concise and direct (max 150 words) focusing only on core deliverables:\n{prompt}"
        
        d_prompt = f"""Expand this prompt into a comprehensive, highly-detailed technical specification.
You MUST include:
1. Deep technical requirements and functional constraints.
2. A system architecture or data flow breakdown.
3. How different components and integrations will work together.
4. Edge cases, performance considerations, and scalability.
Make it as detailed and exhaustive as possible:\n{prompt}"""

        s_prompt = f"""Rewrite this prompt using the advanced CREATE Prompt Engineering Algorithm.
Structure the final output as a comprehensive, highly-organized technical document. It MUST include:

1. **Context & Role**: Set the precise persona and background information.
2. **Request**: The core task defined with unambiguous clarity.
3. **Explanation (Diagram)**: Provide a visual architecture or logic flow using a Mermaid.js diagram (e.g. ```mermaid ...```). This is mandatory to elaborate and explain complex structures.
4. **Action Steps**: Step-by-step breakdown of how the task should be executed.
5. **Tone & Constraints**: Explicit boundaries, technologies, and styling rules.
6. **Extras/Examples**: Include edge cases or output format specifications.

Ensure the final output is exceptionally professional and visually structured using Markdown headers and bullet points. Here is the original prompt to enhance:\n{prompt}"""

        # Fetch variations routing to different models to avoid free-tier API rate limits (HTTP 429)
        concise = fetch_variation(c_prompt, 800, preferred_model='gemini')
        detailed = fetch_variation(d_prompt, 2048, preferred_model='nvidia_mistral')
        structured = fetch_variation(s_prompt, 2048, preferred_model='nvidia_qwen')
        
        return {
            'concise': concise,
            'detailed': detailed,
            'structured': structured
        }
            
    except Exception as e:
        print(f"Variation generation failed: {e}")
        return {
            'concise': {'text': prompt, 'length': len(prompt), 'model': 'fallback'},
            'detailed': {'text': prompt, 'length': len(prompt), 'model': 'fallback'},
            'structured': {'text': prompt, 'length': len(prompt), 'model': 'fallback'}
        }

def compare_variations(original, variations):
    """Compare variations and recommend best"""
    # Score each variation
    for key in variations:
        quality = analyze_quality_heatmap(variations[key]['text'])
        variations[key]['quality'] = quality
    
    # Find best
    best = max(variations.keys(), key=lambda k: variations[k]['quality']['overall'])
    
    return {
        'variations': variations,
        'recommendation': {
            'best_variation': best,
            'reason': f'{best.capitalize()} version has the highest quality score'
        }
    }
