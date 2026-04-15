"""Views for PromptX API."""

import time
import logging
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import (
    EnhanceRequestSerializer,
    AnalyzeRequestSerializer,
    CompareRequestSerializer,
    FeedbackSerializer,
    BatchEnhanceRequestSerializer,
)
from .core.pipeline import PromptXPipeline
from .core.analyzer import PromptAnalyzer
from .core.quality_scorer import QualityScorer
from .models import PromptHistory
from .utils.text_processing import hash_text

logger = logging.getLogger('enhancer')


class EnhancePromptView(APIView):
    """
    POST /api/v1/enhance/

    Main enhancement endpoint. Runs the complete PromptX pipeline.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EnhanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'INVALID_REQUEST',
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data['prompt']
        level = serializer.validated_data['enhancement_level']
        preferences = serializer.validated_data.get('preferences', {})

        # Check cache
        cache_key = f"promptx:enhance:{hash_text(f'{prompt}:{level}')}"
        cached = cache.get(cache_key)
        if cached:
            cached['from_cache'] = True
            return Response(cached, status=status.HTTP_200_OK)

        # Execute pipeline
        pipeline = PromptXPipeline()
        result = pipeline.execute(
            prompt=prompt,
            enhancement_level=level,
            user_preferences=preferences,
        )

        response_data = result.to_dict()

        if result.success:
            # Save to history
            self._save_history(request, result)

            # Cache for 1 hour
            cache.set(cache_key, response_data, timeout=3600)

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    def _save_history(self, request, result):
        try:
            PromptHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=request.session.session_key or '',
                original_prompt=result.original_prompt,
                enhanced_prompt=result.enhanced_prompt,
                enhancement_level=result.enhancement_level,
                detected_intent=result.intent,
                detected_domain=result.domain,
                detected_task_type=result.task_type,
                complexity_level=result.complexity,
                original_quality_score=result.original_quality,
                enhanced_quality_score=result.enhanced_quality,
                improvement_delta=result.improvement,
                original_scores_detail=result.original_scores,
                enhanced_scores_detail=result.enhanced_scores,
                validation_passed=result.validation_passed,
                validation_issues=result.validation_issues,
                validation_warnings=result.validation_warnings,
                processing_time_ms=result.processing_time_ms,
                enhancement_method=result.enhancement_method,
                pipeline_stages_completed=result.pipeline_stages,
            )
        except Exception as e:
            logger.error(f"Failed to save history: {e}")


class AnalyzePromptView(APIView):
    """
    POST /api/v1/analyze/

    Analyze a prompt without enhancing it. Returns comprehensive analysis.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data['prompt']

        analyzer = PromptAnalyzer()
        analysis = analyzer.analyze(prompt)

        return Response({
            'success': True,
            'prompt': prompt,
            'intent': {
                'primary': analysis.intent.primary_intent,
                'confidence': analysis.intent.confidence,
                'secondary': [
                    {'intent': i, 'confidence': c}
                    for i, c in analysis.intent.secondary_intents
                ],
                'is_multi_intent': analysis.intent.is_multi_intent,
            },
            'domain': {
                'primary': analysis.intent.domain,
                'confidence': analysis.intent.domain_confidence,
            },
            'task_type': analysis.intent.task_type,
            'complexity': {
                'level': analysis.complexity.level,
                'score': analysis.complexity.score,
                'factors': analysis.complexity.factors,
                'estimated_steps': analysis.complexity.estimated_steps,
                'requires_decomposition': analysis.complexity.requires_decomposition,
                'sub_tasks': analysis.complexity.sub_tasks,
            },
            'quality': {
                'overall': analysis.quality.overall,
                'grade': analysis.quality.grade,
                'dimensions': analysis.quality.detail_scores,
                'bonuses': analysis.quality.bonuses,
                'deductions': analysis.quality.deductions,
            },
            'elements': {
                'present': {k: v for k, v in analysis.quality.element_presence.items() if v},
                'missing': analysis.quality.missing_elements,
            },
            'nlp': {
                'entities': analysis.entities,
                'keywords': analysis.keywords,
                'noun_phrases': analysis.noun_phrases,
                'key_verbs': analysis.key_verbs,
                'programming_language': analysis.programming_language,
                'word_count': analysis.word_count,
                'sentence_count': analysis.sentence_count,
            },
            'flags': {
                'has_question': analysis.has_question,
                'has_negation': analysis.has_negation,
                'is_multi_part': analysis.is_multi_part,
                'requires_external_knowledge': analysis.requires_external_knowledge,
            },
            'resources': {
                'urls': analysis.urls,
                'emails': analysis.emails,
                'code_blocks_count': len(analysis.code_blocks),
            },
        }, status=status.HTTP_200_OK)


class ValidatePromptView(APIView):
    """
    POST /api/v1/validate/

    Validate a prompt or enhanced output for correctness.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        from .core.validator import PromptValidator
        from .core.fact_checker import FactChecker

        prompt = serializer.validated_data['prompt']

        validator = PromptValidator()
        validation = validator.validate(prompt)

        fact_checker = FactChecker()
        facts = fact_checker.check(prompt)

        return Response({
            'success': True,
            'prompt': prompt,
            'validation': {
                'is_valid': validation.is_valid,
                'score': validation.score,
                'checks_performed': validation.checks_performed,
                'issues': [
                    {
                        'severity': i.severity,
                        'category': i.category,
                        'message': i.message,
                        'suggestion': i.suggestion,
                    }
                    for i in validation.issues
                ],
                'warnings': [
                    {
                        'severity': w.severity,
                        'category': w.category,
                        'message': w.message,
                        'suggestion': w.suggestion,
                    }
                    for w in validation.warnings
                ],
                'info': [
                    {
                        'severity': i.severity,
                        'category': i.category,
                        'message': i.message,
                        'suggestion': i.suggestion,
                    }
                    for i in validation.info
                ],
                'resources_validated': validation.resources_validated,
            },
            'fact_check': {
                'status': facts.overall_status,
                'items_checked': facts.items_checked,
                'items_verified': facts.items_verified,
                'items_suspicious': facts.items_suspicious,
                'items': [
                    {
                        'claim': item.claim,
                        'status': item.status,
                        'confidence': item.confidence,
                        'details': item.details,
                        'source': item.source,
                    }
                    for item in facts.items
                ],
                'recommendations': facts.recommendations,
            },
        }, status=status.HTTP_200_OK)


class ComparePromptsView(APIView):
    """
    POST /api/v1/compare/

    Compare two prompts side by side.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CompareRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        scorer = QualityScorer()
        analyzer = PromptAnalyzer()

        prompt_a = serializer.validated_data['prompt_a']
        prompt_b = serializer.validated_data['prompt_b']

        analysis_a = analyzer.analyze(prompt_a)
        analysis_b = analyzer.analyze(prompt_b)

        score_a = analysis_a.quality
        score_b = analysis_b.quality

        winner = 'prompt_a' if score_a.overall > score_b.overall else 'prompt_b'
        if abs(score_a.overall - score_b.overall) < 0.02:
            winner = 'tie'

        return Response({
            'success': True,
            'prompt_a': {
                'text': prompt_a,
                'quality': score_a.overall,
                'grade': score_a.grade,
                'scores': score_a.detail_scores,
                'intent': analysis_a.intent.primary_intent,
                'domain': analysis_a.intent.domain,
                'missing_elements': score_a.missing_elements,
            },
            'prompt_b': {
                'text': prompt_b,
                'quality': score_b.overall,
                'grade': score_b.grade,
                'scores': score_b.detail_scores,
                'intent': analysis_b.intent.primary_intent,
                'domain': analysis_b.intent.domain,
                'missing_elements': score_b.missing_elements,
            },
            'comparison': {
                'winner': winner,
                'quality_difference': round(abs(score_a.overall - score_b.overall), 3),
                'dimension_comparison': {
                    dim: {
                        'prompt_a': score_a.detail_scores.get(dim, 0),
                        'prompt_b': score_b.detail_scores.get(dim, 0),
                        'better': 'prompt_a' if score_a.detail_scores.get(dim, 0) > score_b.detail_scores.get(dim, 0) else 'prompt_b',
                    }
                    for dim in ['clarity', 'specificity', 'completeness', 'structure', 'actionability', 'grammar']
                },
            },
        }, status=status.HTTP_200_OK)


class BatchEnhanceView(APIView):
    """
    POST /api/v1/batch-enhance/

    Enhance multiple prompts in one request.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BatchEnhanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        prompts = serializer.validated_data['prompts']
        level = serializer.validated_data['enhancement_level']

        pipeline = PromptXPipeline()
        results = []

        for i, prompt in enumerate(prompts):
            result = pipeline.execute(prompt=prompt, enhancement_level=level)
            results.append({
                'index': i,
                'original': prompt,
                'enhanced': result.enhanced_prompt if result.success else None,
                'success': result.success,
                'quality_before': result.original_quality,
                'quality_after': result.enhanced_quality,
                'improvement': result.improvement,
                'grade_before': result.original_grade,
                'grade_after': result.enhanced_grade,
                'error': result.error,
            })

        return Response({
            'success': True,
            'total': len(results),
            'successful': sum(1 for r in results if r['success']),
            'results': results,
        }, status=status.HTTP_200_OK)


class FeedbackView(APIView):
    """
    POST /api/v1/feedback/

    Submit feedback on an enhanced prompt.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'details': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            history = PromptHistory.objects.get(
                id=serializer.validated_data['prompt_id']
            )
            history.user_rating = serializer.validated_data['rating']
            history.user_feedback = serializer.validated_data.get('feedback', '')
            history.save()

            return Response({
                'success': True,
                'message': 'Feedback recorded successfully',
            }, status=status.HTTP_200_OK)

        except PromptHistory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Prompt not found',
            }, status=status.HTTP_404_NOT_FOUND)


class HealthCheckView(APIView):
    """GET /api/v1/health/ - System health check."""
    permission_classes = [AllowAny]

    def get(self, request):
        # Quick pipeline test
        try:
            pipeline = PromptXPipeline()
            result = pipeline.execute("test prompt for health check", "basic")
            pipeline_ok = result.success
        except Exception:
            pipeline_ok = False

        return Response({
            'status': 'healthy' if pipeline_ok else 'degraded',
            'pipeline': 'operational' if pipeline_ok else 'error',
            'version': '1.0.0',
        }, status=status.HTTP_200_OK)
