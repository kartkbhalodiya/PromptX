"""Quality scoring module for PromptX."""

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List

from ..utils.constants import QUALITY_ELEMENTS, AMBIGUOUS_WORDS, FILLER_PATTERNS
from ..utils.text_processing import count_sentences, calculate_avg_sentence_length
from ..utils.helpers import timer, clamp

logger = logging.getLogger('enhancer')


@dataclass
class QualityScore:
    overall: float
    clarity: float
    specificity: float
    completeness: float
    structure: float
    actionability: float
    grammar: float
    detail_scores: Dict[str, float] = field(default_factory=dict)
    deductions: List[str] = field(default_factory=list)
    bonuses: List[str] = field(default_factory=list)
    element_presence: Dict[str, bool] = field(default_factory=dict)
    missing_elements: List[str] = field(default_factory=list)
    grade: str = ''  # A, B, C, D, F


class QualityScorer:
    """
    Multi-dimensional quality scoring engine.

    Scores prompts across 6 dimensions:
    1. Clarity     - How clear and unambiguous is the prompt?
    2. Specificity - How specific and detailed is the request?
    3. Completeness - Does it have all necessary elements?
    4. Structure   - Is it well-organized?
    5. Actionability - Can an AI directly act on it?
    6. Grammar     - Is the language correct?
    """

    def __init__(self):
        from django.conf import settings
        self.weights = settings.PROMPTX['SCORING_WEIGHTS']

    @timer
    def score(self, text: str, intent: str = 'general',
              domain: str = 'general') -> QualityScore:
        """Calculate comprehensive quality score."""

        clarity = self._score_clarity(text)
        specificity = self._score_specificity(text)
        completeness, element_presence, missing = self._score_completeness(text)
        structure = self._score_structure(text)
        actionability = self._score_actionability(text, intent)
        grammar = self._score_grammar(text)

        # Weighted overall score
        overall = (
            clarity * self.weights['clarity'] +
            specificity * self.weights['specificity'] +
            completeness * self.weights['completeness'] +
            structure * self.weights['structure'] +
            actionability * self.weights['actionability'] +
            grammar * self.weights['grammar']
        )

        # Collect deductions and bonuses
        deductions = []
        bonuses = []

        if clarity < 0.4:
            deductions.append("Low clarity: prompt contains ambiguous language")
        if specificity < 0.3:
            deductions.append("Low specificity: prompt lacks concrete details")
        if len(missing) >= 5:
            deductions.append(f"Missing {len(missing)} quality elements")
        if grammar < 0.5:
            deductions.append("Grammar issues detected")

        if clarity > 0.8:
            bonuses.append("Excellent clarity")
        if specificity > 0.8:
            bonuses.append("Highly specific request")
        if completeness > 0.8:
            bonuses.append("Very complete prompt with most elements present")
        if structure > 0.7:
            bonuses.append("Well-structured prompt")

        # Grade
        grade = self._calculate_grade(overall)

        return QualityScore(
            overall=round(clamp(overall), 3),
            clarity=round(clamp(clarity), 3),
            specificity=round(clamp(specificity), 3),
            completeness=round(clamp(completeness), 3),
            structure=round(clamp(structure), 3),
            actionability=round(clamp(actionability), 3),
            grammar=round(clamp(grammar), 3),
            detail_scores={
                'clarity': round(clarity, 3),
                'specificity': round(specificity, 3),
                'completeness': round(completeness, 3),
                'structure': round(structure, 3),
                'actionability': round(actionability, 3),
                'grammar': round(grammar, 3),
            },
            deductions=deductions,
            bonuses=bonuses,
            element_presence=element_presence,
            missing_elements=missing,
            grade=grade,
        )

    def _score_clarity(self, text: str) -> float:
        """Score how clear and unambiguous the prompt is."""
        score = 0.7  # Start with decent baseline

        words = text.lower().split()
        word_count = len(words)

        # ── Penalize very short prompts ──
        if word_count < 3:
            score -= 0.5
        elif word_count < 5:
            score -= 0.3
        elif word_count < 10:
            score -= 0.1

        # ── Penalize ambiguous words ──
        ambiguous_count = sum(1 for w in AMBIGUOUS_WORDS if w in text.lower())
        ambiguous_ratio = ambiguous_count / max(word_count, 1)
        score -= ambiguous_ratio * 2.0

        # ── Penalize filler language ──
        filler_count = 0
        for pattern in FILLER_PATTERNS:
            filler_count += len(re.findall(pattern, text, re.IGNORECASE))
        score -= filler_count * 0.05

        # ── Penalize ALL CAPS ──
        if text.isupper() and word_count > 3:
            score -= 0.15

        # ── Reward proper sentence structure ──
        sentence_count = count_sentences(text)
        if sentence_count >= 1:
            score += 0.05
        if sentence_count >= 2:
            score += 0.05

        # ── Reward reasonable sentence length ──
        avg_len = calculate_avg_sentence_length(text)
        if 8 <= avg_len <= 25:
            score += 0.1  # Good sentence length

        # ── Reward clear action verbs at start ──
        first_word = words[0] if words else ''
        action_verbs = [
            'write', 'create', 'build', 'explain', 'analyze',
            'design', 'implement', 'develop', 'generate', 'list',
            'describe', 'compare', 'convert', 'calculate', 'find',
        ]
        if first_word in action_verbs:
            score += 0.1

        return clamp(score)

    def _score_specificity(self, text: str) -> float:
        """Score how specific and detailed the prompt is."""
        score = 0.2  # Low baseline - specificity must be earned

        words = text.split()
        word_count = len(words)

        # ── Reward length (more detail = more specific) ──
        if word_count >= 50:
            score += 0.25
        elif word_count >= 30:
            score += 0.20
        elif word_count >= 20:
            score += 0.15
        elif word_count >= 10:
            score += 0.08

        # ── Reward numbers and quantities ──
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:\s*%|\s*px|\s*em)?\b', text)
        score += min(len(numbers) * 0.05, 0.15)

        # ── Reward quoted strings (specific values) ──
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        score += min(len(quotes) * 0.05, 0.15)

        # ── Reward technical terms ──
        technical_patterns = [
            r'\b[A-Z]{2,}[a-z]*\b',  # Acronyms like API, REST, SQL
            r'\b\w+(?:_\w+)+\b',      # snake_case identifiers
            r'\b\w+(?:[A-Z]\w*)+\b',  # camelCase identifiers
        ]
        tech_count = 0
        for pattern in technical_patterns:
            tech_count += len(re.findall(pattern, text))
        score += min(tech_count * 0.03, 0.15)

        # ── Reward specific file types, versions, etc. ──
        version_pattern = r'\b(?:v|version)?\s*\d+(?:\.\d+)+\b'
        if re.search(version_pattern, text, re.IGNORECASE):
            score += 0.05

        # ── Reward named entities / proper nouns ──
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        score += min(len(proper_nouns) * 0.03, 0.1)

        # ── Reward enumerated requirements ──
        if re.search(r'(?:\d+[\.\)]\s|\-\s|\*\s|•\s)', text):
            score += 0.1

        return clamp(score)

    def _score_completeness(self, text: str) -> tuple:
        """Score prompt completeness and identify missing elements."""
        element_presence = {}
        missing = []
        present_weight = 0.0
        total_weight = 0.0

        for element, config in QUALITY_ELEMENTS.items():
            weight = config['weight']
            total_weight += weight

            is_present = False
            for pattern in config['patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    is_present = True
                    break

            element_presence[element] = is_present
            if is_present:
                present_weight += weight
            else:
                missing.append(element)

        score = present_weight / total_weight if total_weight > 0 else 0.0

        # Bonus for length indicating implicit completeness
        word_count = len(text.split())
        if word_count > 30:
            score += 0.05
        if word_count > 60:
            score += 0.05

        return clamp(score), element_presence, missing

    def _score_structure(self, text: str) -> float:
        """Score the organizational structure of the prompt."""
        score = 0.3

        # ── Reward markdown-style headers ──
        headers = re.findall(r'^#{1,4}\s', text, re.MULTILINE)
        if headers:
            score += min(len(headers) * 0.08, 0.25)

        # ── Reward bullet points / numbered lists ──
        bullets = re.findall(r'^[\s]*[-*•]\s', text, re.MULTILINE)
        numbered = re.findall(r'^[\s]*\d+[\.\)]\s', text, re.MULTILINE)
        if bullets or numbered:
            score += 0.15

        # ── Reward paragraph breaks ──
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.1
        if len(paragraphs) >= 3:
            score += 0.05

        # ── Reward labels / sections ──
        labels = re.findall(
            r'\b(?:context|requirements?|constraints?|output|format|note|important|example)s?\s*:',
            text, re.IGNORECASE
        )
        if labels:
            score += min(len(labels) * 0.08, 0.2)

        # ── Reward code blocks ──
        code_blocks = re.findall(r'```', text)
        if len(code_blocks) >= 2:  # Opening and closing
            score += 0.1

        # ── Penalize wall-of-text ──
        if len(text) > 300 and '\n' not in text:
            score -= 0.15

        return clamp(score)

    def _score_actionability(self, text: str, intent: str) -> float:
        """Score whether an AI can directly act on this prompt."""
        score = 0.4

        words = text.lower().split()

        # ── Reward imperative mood (commands) ──
        imperative_verbs = [
            'write', 'create', 'build', 'explain', 'analyze', 'list',
            'describe', 'compare', 'generate', 'design', 'implement',
            'calculate', 'find', 'show', 'provide', 'make', 'convert',
            'summarize', 'draft', 'review', 'develop', 'optimize',
        ]
        if words and words[0] in imperative_verbs:
            score += 0.2

        has_verb = any(v in words for v in imperative_verbs)
        if has_verb:
            score += 0.1

        # ── Reward clear output specification ──
        output_patterns = [
            r'\b(return|output|produce|give me|provide|show|display)\b',
            r'\b(in the form of|formatted as|as a|in .* format)\b',
        ]
        for pattern in output_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.05

        # ── Penalize questions without clear direction ──
        questions = text.count('?')
        if questions > 0 and not has_verb:
            score -= 0.1

        # ── Reward having a clear subject/object ──
        if len(words) >= 5:
            score += 0.1

        # ── Reward intent-specific actionability ──
        intent_action_words = {
            'code': ['function', 'class', 'module', 'api', 'endpoint', 'script'],
            'generate': ['article', 'email', 'document', 'report', 'content'],
            'analyze': ['data', 'code', 'performance', 'market', 'competitor'],
        }
        if intent in intent_action_words:
            action_matches = sum(
                1 for w in intent_action_words[intent] if w in text.lower()
            )
            score += min(action_matches * 0.05, 0.15)

        return clamp(score)

    def _score_grammar(self, text: str) -> float:
        """Basic grammar quality scoring."""
        score = 0.8

        # ── Check sentence endings ──
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if sentences:
            last_char = text.strip()[-1] if text.strip() else ''
            if last_char not in '.!?:':
                score -= 0.1

        # ── Check capitalization ──
        if text and text[0].islower():
            score -= 0.05

        # ── Penalize excessive punctuation ──
        excessive = re.findall(r'[!?]{3,}', text)
        if excessive:
            score -= len(excessive) * 0.05

        # ── Penalize repeated words ──
        words = text.lower().split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1] and words[i] not in ['the', 'a', 'is', 'to']:
                score -= 0.03

        # ── Reward proper spacing ──
        if not re.search(r'[a-z][A-Z]', text):  # No missing spaces
            score += 0.05

        # ── Check balanced brackets/quotes ──
        for open_char, close_char in [('(', ')'), ('[', ']'), ('{', '}')]:
            if text.count(open_char) != text.count(close_char):
                score -= 0.05

        return clamp(score)

    def _calculate_grade(self, score: float) -> str:
        if score >= 0.90:
            return 'A+'
        elif score >= 0.80:
            return 'A'
        elif score >= 0.70:
            return 'B'
        elif score >= 0.55:
            return 'C'
        elif score >= 0.40:
            return 'D'
        else:
            return 'F'
