"""  
Minimal services for PromptX - Multi-model fallback support
"""
from google import genai
import os
import requests
from dotenv import load_dotenv

load_dotenv()

import concurrent.futures
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
    """Handles automatic fallback between AI models"""
    
    def __init__(self):
        self.models = [
            {'name': 'gemini', 'priority': 1},
            {'name': 'nvidia_mistral', 'priority': 2},
            {'name': 'nvidia_qwen', 'priority': 3},
            {'name': 'huggingface', 'priority': 4}
        ]
    
    def generate(self, prompt, max_tokens=2000, preferred_model=None):
        """Try models in order until one succeeds.
        If preferred_model is set, try it first before the fallback chain."""
        errors = []
        
        # Build model order: preferred first (if specified), then remaining
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
        """Call specific model"""
        if model_name == 'gemini':
            return self._call_gemini(prompt)
        elif model_name == 'nvidia_mistral':
            return self._call_nvidia_mistral(prompt, max_tokens)
        elif model_name == 'nvidia_qwen':
            return self._call_nvidia_qwen(prompt, max_tokens)
        elif model_name == 'huggingface':
            return self._call_huggingface(prompt, max_tokens)
    
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
    
    def _split_prompt(self, prompt):
        """Helper to separate system and user prompts if combined."""
        delimiter = "\n\nUser prompt to enhance:\n"
        if delimiter in prompt:
            parts = prompt.split(delimiter, 1)
            return [
                {'role': 'system', 'content': parts[0].strip()},
                {'role': 'user', 'content': parts[1].strip()}
            ]
        # Same for conciseness logic if any other delimited form comes through
        if ":\n" in prompt and ("Make this prompt concise" in prompt or "Rewrite this prompt" in prompt or "Expand this prompt" in prompt):
            parts = prompt.split(":\n", 1)
            return [
                {'role': 'system', 'content': parts[0].strip()},
                {'role': 'user', 'content': parts[1].strip()}
            ]
        return [{'role': 'user', 'content': prompt}]

    def _call_nvidia_mistral(self, prompt, max_tokens):
        api_key = os.getenv('NVIDIA_MISTRAL_API_KEY')
        if not api_key:
            raise ValueError("NVIDIA_MISTRAL_API_KEY not found")
        
        response = requests.post(
            'https://integrate.api.nvidia.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'mistralai/mistral-small-4-119b-2603',
                'messages': self._split_prompt(prompt),
                'max_tokens': min(max_tokens, 16384),
                'reasoning_effort': 'high',
                'temperature': 0.10,
                'top_p': 1.00
            },
            timeout=60
        )
        response.raise_for_status()
        msg = response.json().get('choices', [{}])[0].get('message', {})
        content = msg.get('content') or msg.get('reasoning_content') or ""
        return str(content).strip()

    def _call_nvidia_qwen(self, prompt, max_tokens):
        api_key = os.getenv('NVIDIA_QWEN_API_KEY')
        if not api_key:
            raise ValueError("NVIDIA_QWEN_API_KEY not found")
        
        response = requests.post(
            'https://integrate.api.nvidia.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'qwen/qwen3.5-122b-a10b',
                'messages': self._split_prompt(prompt),
                'max_tokens': min(max_tokens, 16384),
                'temperature': 0.60,
                'top_p': 0.95,
                'chat_template_kwargs': {"enable_thinking": True}
            },
            timeout=60
        )
        response.raise_for_status()
        msg = response.json().get('choices', [{}])[0].get('message', {})
        content = msg.get('content') or msg.get('reasoning_content') or ""
        return str(content).strip()
    
    def _call_huggingface(self, prompt, max_tokens):
        api_key = os.getenv('HUGGINGFACE_API_KEY')
        if not api_key:
            raise ValueError("HUGGINGFACE_API_KEY not found")
        
        response = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'Qwen/Qwen2.5-72B-Instruct',
                'messages': self._split_prompt(prompt),
                'max_tokens': max_tokens,
                'temperature': 0.7
            },
            timeout=60
        )
        response.raise_for_status()
        msg = response.json().get('choices', [{}])[0].get('message', {})
        content = msg.get('content') or ""
        return str(content).strip()

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
    """Generate text with automatic model fallback.
    If preferred_model is set, try it first before the fallback chain."""
    return _fallback.generate(prompt, max_tokens, preferred_model=preferred_model)

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
