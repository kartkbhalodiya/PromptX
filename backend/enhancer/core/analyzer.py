"""Deep prompt analysis module for PromptX."""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

try:
    import spacy
    nlp_available = True
except ImportError:
    nlp_available = False

from .intent_classifier import IntentClassifier, IntentResult
from .quality_scorer import QualityScorer, QualityScore
from .complexity_assessor import ComplexityAssessor, ComplexityResult
from ..utils.text_processing import (
    normalize_text, extract_urls, extract_code_blocks,
    extract_emails, extract_numbers, detect_language_in_text,
)
from ..utils.helpers import timer

logger = logging.getLogger('enhancer')


@dataclass
class FullAnalysis:
    """Complete analysis result combining all sub-analyzers."""
    original_text: str
    normalized_text: str
    intent: IntentResult
    quality: QualityScore
    complexity: ComplexityResult
    entities: List[Dict]
    noun_phrases: List[str]
    key_verbs: List[str]
    keywords: List[str]
    urls: List[str]
    code_blocks: List[tuple]
    emails: List[str]
    numbers: List[str]
    programming_language: Optional[str]
    sentence_count: int
    word_count: int
    avg_sentence_length: float
    has_question: bool
    has_negation: bool
    is_multi_part: bool
    requires_external_knowledge: bool


class PromptAnalyzer:
    """
    Deep prompt analysis engine that combines intent classification,
    quality scoring, complexity assessment, and NLP analysis.
    """

    def __init__(self):
        if nlp_available:
            try:
                self.nlp = spacy.load("en_core_web_md")
            except OSError:
                logger.warning("spacy model not found, using simple tokenizer")
                self.nlp = None
        else:
            self.nlp = None
        self.intent_classifier = IntentClassifier()
        self.quality_scorer = QualityScorer()
        self.complexity_assessor = ComplexityAssessor()

    @timer
    def analyze(self, text: str) -> FullAnalysis:
        """Perform comprehensive prompt analysis."""
        normalized = normalize_text(text)
        
        if self.nlp:
            doc = self.nlp(normalized)
        else:
            doc = None

        # Sub-analyses
        intent_result = self.intent_classifier.classify(normalized)
        quality_result = self.quality_scorer.score(
            normalized, intent_result.primary_intent, intent_result.domain
        )
        complexity_result = self.complexity_assessor.assess(
            normalized, intent_result.primary_intent, intent_result.domain
        )

        # NLP extraction
        if doc:
            entities = self._extract_entities(doc)
            noun_phrases = self._extract_noun_phrases(doc)
            key_verbs = self._extract_key_verbs(doc)
            keywords = self._extract_keywords(doc)
            sentences = list(doc.sents)
            words = [t for t in doc if not t.is_space]
        else:
            entities = []
            noun_phrases = []
            key_verbs = []
            keywords = self._simple_keyword_extraction(normalized)
            sentences = normalized.split('. ')
            words = normalized.split()

        # Resource extraction
        urls = extract_urls(normalized)
        code_blocks = extract_code_blocks(normalized)
        emails = extract_emails(normalized)
        numbers = extract_numbers(normalized)
        prog_lang = detect_language_in_text(normalized)

        # Linguistic features
        sentence_count = len(sentences)
        word_count = len(words)
        avg_sent_len = word_count / sentence_count if sentence_count > 0 else 0

        # Flags
        has_question = '?' in normalized
        if doc:
            has_negation = any(t.dep_ == 'neg' for t in doc)
        else:
            has_negation = any(neg in normalized.lower() for neg in ['not', 'no', 'never', "don't", "doesn't"])
        is_multi_part = (
            sentence_count >= 3 or
            bool(re.search(r'\b(also|additionally|and also|plus)\b', normalized, re.I))
        )
        requires_external = bool(urls) or bool(
            re.search(r'\b(current|latest|recent|today|2024|2025)\b', normalized, re.I)
        )

        return FullAnalysis(
            original_text=text,
            normalized_text=normalized,
            intent=intent_result,
            quality=quality_result,
            complexity=complexity_result,
            entities=entities,
            noun_phrases=noun_phrases,
            key_verbs=key_verbs,
            keywords=keywords,
            urls=urls,
            code_blocks=code_blocks,
            emails=emails,
            numbers=numbers,
            programming_language=prog_lang,
            sentence_count=sentence_count,
            word_count=word_count,
            avg_sentence_length=round(avg_sent_len, 1),
            has_question=has_question,
            has_negation=has_negation,
            is_multi_part=is_multi_part,
            requires_external_knowledge=requires_external,
        )

    def _extract_entities(self, doc) -> List[Dict]:
        entities = []
        if hasattr(doc, 'ents'):
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'description': '',
                })
        return entities

    def _extract_noun_phrases(self, doc) -> List[str]:
        if hasattr(doc, 'noun_chunks'):
            return list(set(
                chunk.text.lower() for chunk in doc.noun_chunks
                if len(chunk.text.split()) <= 4
            ))
        return []

    def _extract_key_verbs(self, doc) -> List[str]:
        verbs = []
        for token in doc:
            if hasattr(token, 'pos_') and token.pos_ == 'VERB' and not token.is_stop and len(token.text) > 2:
                verbs.append(token.lemma_.lower())
        return list(set(verbs))

    def _extract_keywords(self, doc) -> List[str]:
        keywords = []
        for token in doc:
            if (
                hasattr(token, 'pos_') and 
                token.pos_ in ['NOUN', 'PROPN', 'ADJ']
                and not token.is_stop
                and len(token.text) > 2
                and not token.is_punct
            ):
                keywords.append(token.lemma_.lower())
        return list(set(keywords))[:20]

    def _simple_keyword_extraction(self, text: str) -> List[str]:
        """Simple keyword extraction when spacy is not available."""
        words = text.lower().split()
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'to', 'of', 'in',
                      'for', 'on', 'with', 'at', 'by', 'from', 'as', 'and', 'or', 'but'}
        filtered = [w.strip('.,!?;:()[]{}') for w in words if w.lower() not in stop_words and len(w) > 3]
        return list(set(filtered))[:20]
