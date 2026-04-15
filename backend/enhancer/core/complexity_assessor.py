"""Complexity assessment module for PromptX."""

import re
import logging
from dataclasses import dataclass
from typing import List

from ..utils.constants import COMPLEXITY_INDICATORS
from ..utils.helpers import timer, clamp

logger = logging.getLogger('enhancer')


@dataclass
class ComplexityResult:
    level: str  # 'low', 'medium', 'high', 'expert'
    score: float  # 0.0 - 1.0
    factors: List[str]
    estimated_steps: int
    requires_decomposition: bool
    sub_tasks: List[str]


class ComplexityAssessor:
    """
    Determines the complexity of a user's request to calibrate
    the depth and structure of the enhanced prompt.
    """

    @timer
    def assess(self, text: str, intent: str, domain: str) -> ComplexityResult:
        text_lower = text.lower()
        factors = []
        score = 0.3  # Base complexity

        # ── Factor 1: Length and detail ──
        word_count = len(text.split())
        if word_count > 100:
            score += 0.15
            factors.append(f"Detailed request ({word_count} words)")
        elif word_count > 50:
            score += 0.10
            factors.append(f"Moderate detail ({word_count} words)")
        elif word_count < 10:
            score -= 0.1
            factors.append(f"Very brief request ({word_count} words)")

        # ── Factor 2: High complexity keywords ──
        high_kw = COMPLEXITY_INDICATORS['high']['keywords']
        high_matches = sum(1 for kw in high_kw if kw in text_lower)
        if high_matches >= 3:
            score += 0.25
            factors.append(f"Multiple advanced concepts ({high_matches} indicators)")
        elif high_matches >= 1:
            score += 0.15
            factors.append(f"Advanced concepts present ({high_matches} indicators)")

        # ── Factor 3: Low complexity keywords ──
        low_kw = COMPLEXITY_INDICATORS['low']['keywords']
        low_matches = sum(1 for kw in low_kw if kw in text_lower)
        if low_matches >= 2:
            score -= 0.15
            factors.append("Simplicity indicators present")

        # ── Factor 4: Multi-step detection ──
        multi_patterns = COMPLEXITY_INDICATORS['high']['multi_step_patterns']
        multi_count = 0
        for pattern in multi_patterns:
            multi_count += len(re.findall(pattern, text_lower))
        if multi_count >= 3:
            score += 0.2
            factors.append(f"Multi-step task ({multi_count} step indicators)")
        elif multi_count >= 1:
            score += 0.1
            factors.append("Contains sequential steps")

        # ── Factor 5: Multiple requirements ──
        requirement_markers = re.findall(
            r'\b(and|also|additionally|plus|moreover|with|include|must|should)\b',
            text_lower
        )
        if len(requirement_markers) >= 4:
            score += 0.15
            factors.append(f"Multiple requirements ({len(requirement_markers)} markers)")

        # ── Factor 6: Questions count ──
        question_count = text.count('?')
        if question_count >= 3:
            score += 0.1
            factors.append(f"Multiple questions ({question_count})")

        # ── Factor 7: Domain-specific complexity ──
        complex_domains = ['data_science', 'technology', 'finance', 'legal']
        if domain in complex_domains:
            score += 0.05
            factors.append(f"Complex domain: {domain}")

        # ── Factor 8: Code-specific complexity ──
        if intent == 'code':
            if re.search(r'\b(database|api|auth|deploy|test|docker)\b', text_lower):
                score += 0.1
                factors.append("Code task involves infrastructure")

        score = clamp(score)

        # Determine level
        if score >= 0.75:
            level = 'expert'
        elif score >= 0.55:
            level = 'high'
        elif score >= 0.35:
            level = 'medium'
        else:
            level = 'low'

        # Estimate steps
        estimated_steps = max(1, int(score * 10))

        # Decompose into sub-tasks if complex
        sub_tasks = []
        requires_decomposition = score >= 0.6
        if requires_decomposition:
            sub_tasks = self._decompose_task(text, intent)

        return ComplexityResult(
            level=level,
            score=round(score, 3),
            factors=factors,
            estimated_steps=estimated_steps,
            requires_decomposition=requires_decomposition,
            sub_tasks=sub_tasks,
        )

    def _decompose_task(self, text: str, intent: str) -> List[str]:
        """Break down a complex task into sub-tasks."""
        sub_tasks = []

        # Split by conjunctions and sequential markers
        parts = re.split(
            r'\b(?:and then|then|after that|also|additionally|next|finally|first|second|third)\b',
            text, flags=re.IGNORECASE
        )

        for part in parts:
            part = part.strip().strip(',').strip()
            if len(part.split()) >= 3:
                sub_tasks.append(part)

        # If no natural decomposition, split by sentences
        if len(sub_tasks) <= 1:
            sentences = re.split(r'[.!?]+', text)
            sub_tasks = [s.strip() for s in sentences if len(s.strip().split()) >= 3]

        return sub_tasks[:8]  # Cap at 8 sub-tasks
