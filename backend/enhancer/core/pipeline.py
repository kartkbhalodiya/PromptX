"""Master pipeline module for PromptX."""

import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field, asdict

from django.conf import settings

from .analyzer import PromptAnalyzer, FullAnalysis
from .context_builder import ContextBuilder
from .template_manager import TemplateManager
from .validator import PromptValidator, ValidationResult
from .fact_checker import FactChecker, FactCheckResult
from .refinement import RefinementEngine, RefinementResult
from ..utils.text_processing import normalize_text, hash_text
from ..utils.helpers import timer
from ..exceptions import PromptTooShortError, PromptTooLongError, EnhancementError

logger = logging.getLogger('enhancer')


@dataclass
class PipelineResult:
    """Complete result from the enhancement pipeline."""
    # Status
    success: bool
    error: Optional[str] = None

    # Prompts
    original_prompt: str = ''
    enhanced_prompt: str = ''
    enhancement_level: str = 'intermediate'
    enhancement_method: str = 'rule_based'

    # Analysis
    intent: str = ''
    intent_confidence: float = 0.0
    secondary_intents: list = field(default_factory=list)
    domain: str = ''
    domain_confidence: float = 0.0
    task_type: str = ''
    complexity: str = ''
    complexity_score: float = 0.0
    complexity_factors: list = field(default_factory=list)

    # Quality Scores
    original_quality: float = 0.0
    enhanced_quality: float = 0.0
    improvement: float = 0.0
    original_grade: str = ''
    enhanced_grade: str = ''

    # Detailed Original Scores
    original_scores: Dict = field(default_factory=dict)
    enhanced_scores: Dict = field(default_factory=dict)

    # Missing Elements
    missing_elements: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)

    # Validation
    validation_passed: bool = True
    validation_score: float = 1.0
    validation_issues: list = field(default_factory=list)
    validation_warnings: list = field(default_factory=list)
    validation_checks: list = field(default_factory=list)
    resources_validated: Dict = field(default_factory=dict)

    # Fact Check
    fact_check_status: str = 'clean'
    fact_check_items: list = field(default_factory=list)

    # Refinement
    refinement_iterations: int = 0
    refinement_improvement: float = 0.0

    # NLP Details
    entities: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    programming_language: Optional[str] = None
    word_count: int = 0
    sentence_count: int = 0

    # Metadata
    processing_time_ms: float = 0.0
    pipeline_stages: list = field(default_factory=list)
    cache_key: str = ''

    def to_dict(self) -> Dict:
        return asdict(self)


class PromptXPipeline:
    """
    Master orchestration pipeline for PromptX.

    Pipeline stages:
    1. INPUT VALIDATION      - Length, format checks
    2. DEEP ANALYSIS         - Intent, quality, NLP
    3. COMPLEXITY ASSESSMENT - Difficulty estimation
    4. CONTEXT BUILDING      - Section generation
    5. TEMPLATE RENDERING    - Assembly
    6. REFINEMENT            - Iterative improvement
    7. VALIDATION            - Output verification
    8. FACT CHECKING         - Resource verification
    9. FINAL SCORING         - Quality measurement
    """

    def __init__(self):
        self.config = settings.PROMPTX
        self.pipeline_config = self.config['PIPELINE']

        self.analyzer = PromptAnalyzer()
        self.context_builder = ContextBuilder()
        self.template_manager = TemplateManager()
        self.validator = PromptValidator()
        self.fact_checker = FactChecker()
        self.refinement_engine = RefinementEngine()

    @timer
    def execute(self, prompt: str, enhancement_level: str = 'intermediate',
                user_preferences: Optional[Dict] = None) -> PipelineResult:
        """
        Execute the complete enhancement pipeline.

        Args:
            prompt: Raw user prompt
            enhancement_level: basic | intermediate | advanced | expert
            user_preferences: Optional user-specific settings

        Returns:
            PipelineResult with complete enhancement data
        """
        start_time = time.perf_counter()
        result = PipelineResult(success=False, original_prompt=prompt)
        stages_completed = []

        try:
            # STAGE 1: INPUT VALIDATION
            logger.info("Pipeline Stage 1: Input Validation")
            self._validate_input(prompt)
            normalized = normalize_text(prompt)
            result.cache_key = hash_text(f"{normalized}:{enhancement_level}")
            stages_completed.append('input_validation')

            # STAGE 2: DEEP ANALYSIS
            logger.info("Pipeline Stage 2: Deep Analysis")
            analysis = self.analyzer.analyze(normalized)
            self._populate_analysis_results(result, analysis)
            stages_completed.append('deep_analysis')

            # STAGE 3: INPUT CONTENT VALIDATION
            logger.info("Pipeline Stage 3: Input Content Validation")
            input_validation = self.validator.validate(normalized)
            if not input_validation.is_valid:
                result.validation_passed = False
                result.validation_issues = [
                    {'severity': i.severity, 'category': i.category,
                     'message': i.message, 'suggestion': i.suggestion}
                    for i in input_validation.issues
                ]
            stages_completed.append('input_content_validation')

            # STAGE 4: CONTEXT BUILDING
            logger.info("Pipeline Stage 4: Context Building")
            sections = self.context_builder.build_sections(
                analysis=analysis,
                complexity_level=analysis.complexity.level,
                user_preferences=user_preferences,
            )
            stages_completed.append('context_building')

            # STAGE 5: TEMPLATE RENDERING
            logger.info("Pipeline Stage 5: Template Rendering")
            enhanced = self.template_manager.render(
                sections=sections,
                enhancement_level=enhancement_level,
            )
            stages_completed.append('template_rendering')

            # STAGE 6: ITERATIVE REFINEMENT
            if self.pipeline_config.get('ENABLE_ITERATIVE_REFINEMENT', True):
                logger.info("Pipeline Stage 6: Iterative Refinement")
                target = self.pipeline_config.get('TARGET_QUALITY_SCORE', 0.85)
                max_iter = self.pipeline_config.get('MAX_REFINEMENT_ITERATIONS', 3)

                refinement_result = self.refinement_engine.refine(
                    text=enhanced,
                    target_score=target,
                    max_iterations=max_iter,
                )
                enhanced = refinement_result.refined_text
                result.refinement_iterations = refinement_result.total_iterations
                result.refinement_improvement = refinement_result.score_improvement
                stages_completed.append('refinement')

            # STAGE 7: OUTPUT VALIDATION
            logger.info("Pipeline Stage 7: Output Validation")
            output_validation = self.validator.validate(enhanced)
            result.validation_passed = output_validation.is_valid
            result.validation_score = output_validation.score
            result.validation_issues = [
                {'severity': i.severity, 'category': i.category,
                 'message': i.message, 'suggestion': i.suggestion}
                for i in output_validation.issues
            ]
            result.validation_warnings = [
                {'severity': w.severity, 'category': w.category,
                 'message': w.message, 'suggestion': w.suggestion}
                for w in output_validation.warnings
            ]
            result.validation_checks = output_validation.checks_performed
            result.resources_validated = output_validation.resources_validated
            stages_completed.append('output_validation')

            # STAGE 8: FACT CHECKING
            if self.pipeline_config.get('ENABLE_FACT_CHECK', True):
                logger.info("Pipeline Stage 8: Fact Checking")
                fact_result = self.fact_checker.check(enhanced)
                result.fact_check_status = fact_result.overall_status
                result.fact_check_items = [
                    {
                        'claim': item.claim,
                        'status': item.status,
                        'confidence': item.confidence,
                        'details': item.details,
                    }
                    for item in fact_result.items
                ]

                # Add fact-check recommendations to suggestions
                result.suggestions.extend(fact_result.recommendations)
                stages_completed.append('fact_checking')

            # STAGE 9: FINAL SCORING
            logger.info("Pipeline Stage 9: Final Scoring")
            from .quality_scorer import QualityScorer
            scorer = QualityScorer()
            final_score = scorer.score(
                enhanced,
                intent=analysis.intent.primary_intent,
                domain=analysis.intent.domain,
            )
            result.enhanced_quality = final_score.overall
            result.enhanced_grade = final_score.grade
            result.enhanced_scores = final_score.detail_scores
            result.improvement = round(
                final_score.overall - analysis.quality.overall, 3
            )
            stages_completed.append('final_scoring')

            # FINALIZE
            result.enhanced_prompt = enhanced
            result.enhancement_level = enhancement_level
            result.success = True
            result.pipeline_stages = stages_completed

        except PromptTooShortError as e:
            result.error = str(e)
            result.success = False
            logger.warning(f"Pipeline failed: {e}")
        except PromptTooLongError as e:
            result.error = str(e)
            result.success = False
            logger.warning(f"Pipeline failed: {e}")
        except EnhancementError as e:
            result.error = str(e)
            result.success = False
            logger.error(f"Pipeline error: {e}")
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            result.success = False
            logger.error(f"Pipeline unexpected error: {e}", exc_info=True)
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = round(elapsed, 2)
            result.pipeline_stages = stages_completed
            logger.info(
                f"Pipeline completed in {elapsed:.2f}ms | "
                f"Stages: {len(stages_completed)} | "
                f"Success: {result.success} | "
                f"Quality: {result.original_quality:.3f} -> {result.enhanced_quality:.3f}"
            )

        return result

    def _validate_input(self, prompt: str):
        """Validate raw input."""
        if not prompt or not prompt.strip():
            raise PromptTooShortError(0, 3)

        length = len(prompt.strip())
        if length < self.config.get('MIN_INPUT_LENGTH', 3):
            raise PromptTooShortError(length, 3)
        if length > self.config.get('MAX_INPUT_LENGTH', 10000):
            raise PromptTooLongError(length, 10000)

    def _populate_analysis_results(self, result: PipelineResult,
                                   analysis: FullAnalysis):
        """Copy analysis results into pipeline result."""
        # Intent
        result.intent = analysis.intent.primary_intent
        result.intent_confidence = analysis.intent.confidence
        result.secondary_intents = [
            {'intent': i, 'confidence': c}
            for i, c in analysis.intent.secondary_intents
        ]
        result.domain = analysis.intent.domain
        result.domain_confidence = analysis.intent.domain_confidence
        result.task_type = analysis.intent.task_type

        # Complexity
        result.complexity = analysis.complexity.level
        result.complexity_score = analysis.complexity.score
        result.complexity_factors = analysis.complexity.factors

        # Quality
        result.original_quality = analysis.quality.overall
        result.original_grade = analysis.quality.grade
        result.original_scores = analysis.quality.detail_scores
        result.missing_elements = analysis.quality.missing_elements

        # Build suggestions from quality deductions
        result.suggestions = list(analysis.quality.deductions)

        # NLP
        result.entities = analysis.entities
        result.keywords = analysis.keywords
        result.programming_language = analysis.programming_language
        result.word_count = analysis.word_count
        result.sentence_count = analysis.sentence_count
