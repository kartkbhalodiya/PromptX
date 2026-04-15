"""Intent classification module for PromptX."""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from ..utils.constants import INTENT_PATTERNS, DOMAIN_PATTERNS
from ..utils.helpers import timer

logger = logging.getLogger('enhancer')


@dataclass
class IntentResult:
    primary_intent: str
    confidence: float
    secondary_intents: List[Tuple[str, float]]
    domain: str
    domain_confidence: float
    task_type: str
    is_multi_intent: bool
    raw_scores: Dict[str, float] = field(default_factory=dict)


class IntentClassifier:
    """
    Multi-signal intent classification system.

    Uses weighted keyword matching, positional analysis,
    and verb-structure analysis to determine what the user wants.
    """

    def __init__(self):
        self.intent_patterns = INTENT_PATTERNS
        self.domain_patterns = DOMAIN_PATTERNS

    @timer
    def classify(self, text: str) -> IntentResult:
        """Full intent classification pipeline."""
        text_lower = text.lower()
        words = text_lower.split()

        # Score each intent
        intent_scores = self._score_intents(text_lower, words)

        # Score each domain
        domain_scores = self._score_domains(text_lower)

        # Determine primary and secondary intents
        sorted_intents = sorted(
            intent_scores.items(), key=lambda x: x[1], reverse=True
        )

        primary_intent = sorted_intents[0][0] if sorted_intents else 'general'
        primary_confidence = sorted_intents[0][1] if sorted_intents else 0.0

        # Normalize confidence to 0-1
        max_possible = max(intent_scores.values()) if intent_scores else 1.0
        if max_possible > 0:
            primary_confidence = min(primary_confidence / (max_possible * 1.5), 1.0)

        # Secondary intents (those with >40% of primary score)
        threshold = (sorted_intents[0][1] * 0.4) if sorted_intents else 0
        secondary = [
            (intent, min(score / (max_possible * 1.5), 1.0))
            for intent, score in sorted_intents[1:]
            if score > threshold
        ]

        # Domain
        sorted_domains = sorted(
            domain_scores.items(), key=lambda x: x[1], reverse=True
        )
        primary_domain = sorted_domains[0][0] if sorted_domains and sorted_domains[0][1] > 0 else 'general'
        domain_conf = sorted_domains[0][1] if sorted_domains else 0.0
        max_domain = max(domain_scores.values()) if domain_scores else 1.0
        if max_domain > 0:
            domain_conf = min(domain_conf / (max_domain * 1.5), 1.0)

        # Task type
        task_type = self._determine_task_type(text_lower, primary_intent, primary_domain)

        # Multi-intent detection
        is_multi = len(secondary) >= 2 and secondary[0][1] > 0.3

        return IntentResult(
            primary_intent=primary_intent,
            confidence=round(primary_confidence, 3),
            secondary_intents=secondary[:3],
            domain=primary_domain,
            domain_confidence=round(domain_conf, 3),
            task_type=task_type,
            is_multi_intent=is_multi,
            raw_scores=intent_scores,
        )

    def _score_intents(self, text: str, words: List[str]) -> Dict[str, float]:
        """Score each intent using multiple signals."""
        scores = {}

        for intent, config in self.intent_patterns.items():
            score = 0.0
            keywords = config['keywords']
            weight = config['weight']

            for keyword in keywords:
                # Exact word boundary match
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text, re.IGNORECASE)
                match_count = len(matches)

                if match_count > 0:
                    # Base score per match
                    score += match_count * 1.0

                    # Position bonus: keywords at the start are more important
                    first_pos = text.find(keyword)
                    if first_pos < len(text) * 0.25:
                        score += 0.5  # Early mention bonus
                    if first_pos < 20:
                        score += 0.3  # Very early mention bonus

            scores[intent] = score * weight

        return scores

    def _score_domains(self, text: str) -> Dict[str, float]:
        """Score domain relevance."""
        scores = {}

        for domain, config in self.domain_patterns.items():
            score = 0.0
            for keyword in config['keywords']:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches) * config['weight']
            scores[domain] = score

        return scores

    def _determine_task_type(self, text: str, intent: str, domain: str) -> str:
        """Determine specific task sub-type."""
        task_subtypes = {
            'generate': {
                'email': r'\b(email|mail|message|letter|memo)\b',
                'article': r'\b(article|blog|post|essay|paper)\b',
                'code': r'\b(code|function|script|program|class|module)\b',
                'document': r'\b(document|report|proposal|specification|readme)\b',
                'copy': r'\b(copy|ad|headline|tagline|slogan|description)\b',
                'template': r'\b(template|boilerplate|scaffold|starter)\b',
            },
            'explain': {
                'concept': r'\b(concept|theory|principle|idea|term)\b',
                'process': r'\b(process|how|steps|procedure|workflow)\b',
                'comparison': r'\b(difference|compare|versus|vs|between)\b',
                'troubleshoot': r'\b(error|issue|problem|bug|failure)\b',
            },
            'code': {
                'web_frontend': r'\b(html|css|react|vue|angular|frontend|ui|ux)\b',
                'web_backend': r'\b(api|rest|graphql|server|endpoint|backend|django|flask|express)\b',
                'data': r'\b(data|pandas|numpy|analysis|ml|ai|model|training)\b',
                'devops': r'\b(docker|deploy|ci|cd|cloud|aws|azure|gcp|terraform)\b',
                'database': r'\b(database|sql|query|schema|migration|orm)\b',
                'testing': r'\b(test|testing|unittest|pytest|jest|coverage)\b',
                'mobile': r'\b(mobile|ios|android|flutter|react native|swift|kotlin)\b',
            },
            'analyze': {
                'data_analysis': r'\b(data|dataset|metrics|statistics|numbers)\b',
                'code_review': r'\b(code|review|refactor|quality|smell)\b',
                'competitive': r'\b(competitor|market|industry|benchmark)\b',
                'performance': r'\b(performance|speed|latency|throughput|optimization)\b',
            },
        }

        if intent in task_subtypes:
            for subtype, pattern in task_subtypes[intent].items():
                if re.search(pattern, text, re.IGNORECASE):
                    return f"{intent}_{subtype}"

        return f"{intent}_general"
