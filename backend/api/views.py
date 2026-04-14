"""
PromptX API Views
Django equivalents of all Flask endpoints from app.py.
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from .utils import sanitize_input, classify_prompt, score_prompt, MASTER_PROMPT
from services import (
    detect_intent, apply_smart_template,
    analyze_quality_heatmap,
    generate_ab_variations, compare_variations,
    generate_with_fallback
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

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='10/m', block=True)
def enhance_view(request):
    """Enhance a prompt using AI — equivalent to Flask POST /api/enhance"""
    try:
        data, err = _parse_json(request)
        if err:
            return err
        
        if 'prompt' not in data:
            return JsonResponse({'error': 'Prompt is missing from payload'}, status=400)
        
        prompt = sanitize_input(data['prompt'])
        if not prompt:
            logger.warning(f"Prompt failed sanitization or was empty from {_get_client_ip(request)}")
            return JsonResponse({'error': 'Prompt is empty or invalid'}, status=400)
        if len(prompt) > 100000:
            return JsonResponse({'error': f'Invalid prompt length: {len(prompt)}'}, status=400)
        
        # Classify and score original
        classification = classify_prompt(prompt)
        original_score = score_prompt(prompt)
        
        # Use multi-model fallback (optionally prefer a specific model)
        preferred_model = data.get('model')
        full_prompt = f"{MASTER_PROMPT}\n\nUser prompt to enhance:\n{prompt}"
        result = generate_with_fallback(
            full_prompt,
            max_tokens=2000,
            preferred_model=preferred_model if preferred_model != 'auto' else None
        )
        enhanced = result['text']
        model_used = result['model']
        
        enhanced_score = score_prompt(enhanced)
        
        logger.info(f"Enhanced prompt from {_get_client_ip(request)} using {model_used}")
        return JsonResponse({
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
        return JsonResponse(
            {'error': 'An internal server error occurred processing your request.', 'success': False},
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
