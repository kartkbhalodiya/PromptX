"""
Production Flask Application - Gemini Powered
Uses Google Gemini API instead of OpenAI
"""

import logging
from functools import wraps
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google import genai
try:
    from backend.services import (
        detect_intent, apply_smart_template,
        analyze_quality_heatmap,
        generate_ab_variations, compare_variations,
        get_client, generate_with_fallback
    )
except ModuleNotFoundError:
    from services import (
        detect_intent, apply_smart_template,
        analyze_quality_heatmap,
        generate_ab_variations, compare_variations,
        get_client, generate_with_fallback
    )

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = os.getenv('CLIENT_API_KEY')
        if api_key:
            client_key = request.headers.get('X-API-Key')
            if client_key != api_key:
                logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
                return jsonify({'error': 'Unauthorized: Invalid or missing API Key', 'success': False}), 401
        return f(*args, **kwargs)
    return decorated_function

def sanitize_input(text):
    """Basic protection against prompt injection and malicious characters"""
    if not text: return text
    lower = text.lower()
    if "ignore all previous instructions" in lower or "ignore previous instructions" in lower:
        return "" # returning empty prompts will trigger length validation
    # Clean non-printable/control characters except newlines/tabs
    sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', str(text))
    return sanitized.strip()

app = Flask(__name__)
CORS(app)

# Security: Add Rate Limiting (10 requests per minute per IP limit)
# NOTE: In-memory storage resets on each Vercel serverless cold start.
# For persistent rate limiting, switch to Redis: storage_uri="redis://..."
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

MASTER_PROMPT = """You are a world-class senior prompt engineer with expertise in AI instruction optimization.

You must transform the user's input into a highly professional, highly structured master prompt using the CREATE Algorithm.

The CREATE Algorithm dictates that a high-quality prompt MUST be structured into these six exact sections using Markdown headers:
1. **[Context]**: Establish the optimal persona, background, and required domain expertise.
2. **[Request]**: State the core task clearly and unambiguously.
3. **[Explanation]**: Explain the logic or process. **CRITICAL:** If the prompt involves technical architecture, coding, workflows, or data pipelines, you MUST include a highly detailed Mermaid.js system diagram (e.g., ```mermaid ... ```) to visually map out the process.
4. **[Action Steps]**: Provide a robust chronological step-by-step breakdown of how the task should execute.
5. **[Tone & Constraints]**: Establish strict boundaries, specific technologies, coding standards, forbidden actions, and overall tone.
6. **[Extras]**: Specify exact output formats (e.g., Markdown, specific JSON schemas) or provide edge case guidance.

Execution Rules:
- Infer missing technical details intelligently to make the prompt fully comprehensive.
- Do NOT ask follow-up questions or explain your reasoning.
- Output ONLY the finalized, enhanced master prompt structure.
- If the generic or user's prompt is completely meaningless or gibberish, return ONLY: "⚠️ The prompt provided is too vague. Please provide a clear request or more context to enhance."
- Do NOT output generic lists; visually structure the prompt professionally so it's ready to be copy-pasted into any LLM."""

# ============================================================================
# CLASSIFICATION & SCORING (same as before)
# ============================================================================

def classify_prompt(prompt):
    keywords = {
        'blog': ['blog', 'article', 'post', 'content', 'seo'],
        'code': ['code', 'function', 'program', 'script', 'debug', 'algorithm'],
        'business': ['business', 'proposal', 'marketing', 'email', 'product', 'sales'],
        'academic': ['research', 'essay', 'paper', 'thesis', 'study', 'analysis'],
        'creative': ['story', 'character', 'world', 'creative', 'fiction', 'design']
    }
    
    prompt_lower = prompt.lower()
    scores = {cat: sum(2 for kw in words if kw in prompt_lower) 
              for cat, words in keywords.items()}
    
    if not scores or max(scores.values()) == 0:
        return {'category': 'general', 'confidence': 0.5}
    
    best = max(scores, key=scores.get)
    confidence = min(scores[best] / 10, 1.0)
    
    return {'category': best, 'confidence': round(confidence, 2)}

def score_prompt(prompt):
    score = 0
    length = len(prompt)
    
    if 50 <= length <= 500:
        score += 2
    elif length > 20:
        score += 1
    
    spec_words = ['specific', 'detailed', 'format', 'tone', 'audience', 'length']
    score += min(sum(0.5 for w in spec_words if w in prompt.lower()), 3)
    
    if any(c in prompt for c in ['\n', ':', '-', '•']):
        score += 1.5
    
    ctx_words = ['context', 'background', 'about', 'purpose']
    if any(w in prompt.lower() for w in ctx_words):
        score += 1
    
    con_words = ['must', 'should', 'avoid', 'requirement']
    if any(w in prompt.lower() for w in con_words):
        score += 1
    
    total = round(min(score, 10), 2)
    percentage = round((total / 10) * 100, 1)
    
    return {
        'total': total,
        'percentage': percentage,
        'quality': 'Excellent' if percentage >= 90 else 'Good' if percentage >= 75 else 'Fair' if percentage >= 60 else 'Poor'
    }

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'version': '1.5.0', 'model': 'gemini-pro'})

@app.route('/api/enhance', methods=['POST'])
@limiter.limit("10 per minute")
@require_api_key
def enhance():
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': 'Invalid JSON or unsupported Content-Type payload'}), 400
        if 'prompt' not in data:
            return jsonify({'error': 'Prompt is missing from payload'}), 400
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            logger.warning(f"Prompt failed sanitization or was empty from {request.remote_addr}")
            return jsonify({'error': 'Prompt is empty or invalid'}), 400
        if len(prompt) > 100000:
            return jsonify({'error': f'Invalid prompt length: {len(prompt)}'}), 400
        
        # Classify and score original
        classification = classify_prompt(prompt)
        original_score = score_prompt(prompt)
        
        # Use multi-model fallback (optionally prefer a specific model)
        preferred_model = data.get('model')  # from frontend model selector
        full_prompt = f"{MASTER_PROMPT}\n\nUser prompt to enhance:\n{prompt}"
        result = generate_with_fallback(full_prompt, max_tokens=2000, preferred_model=preferred_model if preferred_model != 'auto' else None)
        enhanced = result['text']
        model_used = result['model']
        
        enhanced_score = score_prompt(enhanced)
        
        logger.info(f"Enhanced prompt from {request.remote_addr} using {model_used}")
        return jsonify({
            'success': True,
            'original': prompt,
            'enhanced': enhanced,
            'classification': classification,
            'original_score': original_score,
            'enhanced_score': enhanced_score,
            'improvement': round(enhanced_score['total'] - original_score['total'], 2),
            'model': model_used
        })
    
    except Exception as e:
        logger.error(f"Error in enhance endpoint: {str(e)}")
        # Do not expose raw tracebacks to the client
        return jsonify({'error': 'An internal server error occurred processing your request.', 'success': False}), 500

# ============================================================================
# ADVANCED FEATURES (Used by Frontend)
# ============================================================================

@app.route('/api/detect-intent', methods=['POST'])
@limiter.limit("20 per minute")
@require_api_key
def detect_prompt_intent():
    """Auto-detect prompt intent and suggest template"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        if 'prompt' not in data:
            return jsonify({'error': 'Prompt is missing'}), 400
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            logger.warning(f"Intent detection prompt empty or invalid from {request.remote_addr}")
            return jsonify({'error': 'Prompt is empty or invalid'}), 400
            
        intent_data = detect_intent(prompt)
        
        # Optionally apply template
        if data.get('apply_template', False):
            enhanced = apply_smart_template(prompt, intent_data)
            intent_data['enhanced_prompt'] = enhanced
        
        logger.info(f"Intent detected for {request.remote_addr}")
        return jsonify({
            'success': True,
            'data': intent_data
        })
    
    except Exception as e:
        logger.error(f"Error in intent endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quality-heatmap', methods=['POST'])
@limiter.limit("20 per minute")
@require_api_key
def quality_heatmap():
    """Get detailed quality heatmap analysis"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        if 'prompt' not in data:
            return jsonify({'error': 'Prompt is missing'}), 400
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            return jsonify({'error': 'Prompt is empty or invalid'}), 400
            
        analysis = analyze_quality_heatmap(prompt)
        
        logger.info(f"Quality heatmap generated for {request.remote_addr}")
        return jsonify({
            'success': True,
            'data': analysis
        })
    
    except Exception as e:
        logger.error(f"Error in quality endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ab-test', methods=['POST'])
@limiter.limit("5 per minute")
@require_api_key
def ab_test():
    """Generate 3 A/B test variations"""
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        if 'prompt' not in data:
            return jsonify({'error': 'Prompt is missing'}), 400
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            return jsonify({'error': 'Prompt is empty or invalid'}), 400
            
        variations = generate_ab_variations(prompt)
        
        # Optionally include comparison
        if data.get('include_comparison', True):
            comparison = compare_variations(prompt, variations)
            return jsonify({
                'success': True,
                'data': comparison
            })
        
        logger.info(f"A/B variations generated for {request.remote_addr}")
        return jsonify({
            'success': True,
            'data': {'variations': variations}
        })
    
    except Exception as e:
        logger.error(f"Error in AB test endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500



# ============================================================================
# RUN
# ============================================================================

# Vercel serverless handler
app = app

if __name__ == '__main__':
    app.run(debug=False)
