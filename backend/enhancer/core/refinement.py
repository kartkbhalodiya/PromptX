"""Refinement engine module for PromptX."""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from .quality_scorer import QualityScorer, QualityScore
from ..utils.helpers import timer, clamp

logger = logging.getLogger('enhancer')


@dataclass
class RefinementIteration:
    iteration: int
    action: str
    score_before: float
    score_after: float
    changes_made: List[str]


@dataclass
class RefinementResult:
    original_text: str
    refined_text: str
    iterations: List[RefinementIteration]
    total_iterations: int
    score_improvement: float
    final_score: float


class RefinementEngine:
    """
    Iteratively refines the enhanced prompt until it meets
    the quality threshold or max iterations is reached.

    Refinement strategies:
    1. Remove redundancy
    2. Improve section ordering
    3. Add missing connectors
    4. Strengthen weak sections
    5. Remove empty/weak sections
    """

    def __init__(self):
        self.scorer = QualityScorer()

    @timer
    def refine(self, text: str, target_score: float = 0.85,
               max_iterations: int = 3) -> RefinementResult:
        """Iteratively refine text until quality threshold is met."""
        current_text = text
        iterations = []

        current_score = self.scorer.score(current_text)

        for i in range(max_iterations):
            if current_score.overall >= target_score:
                logger.info(f"Refinement target reached at iteration {i}")
                break

            # Select refinement strategy based on weakest dimension
            strategy, action_name = self._select_strategy(current_score)

            # Apply refinement
            refined_text = strategy(current_text, current_score)

            # Score the refined version
            new_score = self.scorer.score(refined_text)

            # Only keep if it improved
            if new_score.overall > current_score.overall:
                changes = self._diff_changes(current_text, refined_text)
                iterations.append(RefinementIteration(
                    iteration=i + 1,
                    action=action_name,
                    score_before=current_score.overall,
                    score_after=new_score.overall,
                    changes_made=changes,
                ))
                current_text = refined_text
                current_score = new_score
                logger.debug(
                    f"Refinement iteration {i+1}: {action_name} "
                    f"({current_score.overall:.3f} -> {new_score.overall:.3f})"
                )
            else:
                logger.debug(f"Refinement iteration {i+1}: {action_name} - no improvement, skipped")

        improvement = current_score.overall - self.scorer.score(text).overall

        return RefinementResult(
            original_text=text,
            refined_text=current_text,
            iterations=iterations,
            total_iterations=len(iterations),
            score_improvement=round(improvement, 3),
            final_score=current_score.overall,
        )

    def _select_strategy(self, score: QualityScore):
        """Select the best refinement strategy based on weakest dimension."""
        dimensions = {
            'clarity': (score.clarity, self._refine_clarity, 'improve_clarity'),
            'structure': (score.structure, self._refine_structure, 'improve_structure'),
            'completeness': (score.completeness, self._refine_completeness, 'improve_completeness'),
            'specificity': (score.specificity, self._refine_specificity, 'improve_specificity'),
            'actionability': (score.actionability, self._refine_actionability, 'improve_actionability'),
        }

        weakest = min(dimensions.items(), key=lambda x: x[1][0])
        return weakest[1][1], weakest[1][2]

    def _refine_clarity(self, text: str, score: QualityScore) -> str:
        """Improve prompt clarity."""
        lines = text.split('\n')
        refined_lines = []

        for line in lines:
            # Remove filler words
            line = re.sub(r'\b(basically|actually|really|very|just|quite|rather)\b', '', line)
            line = re.sub(r'\s{2,}', ' ', line)

            # Clean up empty lines
            if line.strip():
                refined_lines.append(line)
            elif refined_lines and refined_lines[-1].strip():
                refined_lines.append('')  # Keep single blank lines

        return '\n'.join(refined_lines)

    def _refine_structure(self, text: str, score: QualityScore) -> str:
        """Improve prompt structure."""
        # Add section headers if missing
        if '##' not in text and len(text) > 200:
            sections = text.split('\n\n')
            if len(sections) >= 3:
                # Try to add headers to unlabeled sections
                for i, section in enumerate(sections):
                    if section.strip() and not section.strip().startswith('#'):
                        # Guess header based on content
                        header = self._guess_section_header(section)
                        if header:
                            sections[i] = f"## {header}\n{section}"
                return '\n\n'.join(sections)

        return text

    def _refine_completeness(self, text: str, score: QualityScore) -> str:
        """Add missing elements."""
        additions = []

        if 'constraints' in score.missing_elements:
            additions.append(
                "## Constraints\n"
                "- Be thorough but concise\n"
                "- Stay focused on the specific request\n"
                "- State any assumptions explicitly"
            )

        if 'output_format' in score.missing_elements:
            additions.append(
                "## Output Format\n"
                "Provide a well-structured response with clear organization and relevant examples."
            )

        if additions:
            return text + '\n\n' + '\n\n'.join(additions)

        return text

    def _refine_specificity(self, text: str, score: QualityScore) -> str:
        """Improve specificity of the prompt."""
        # Add specificity markers to vague sections
        replacements = {
            r'\bgood\b': 'high-quality',
            r'\bnice\b': 'well-crafted',
            r'\bsome\b': 'specific, relevant',
            r'\bstuff\b': 'content',
            r'\bthings\b': 'elements',
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _refine_actionability(self, text: str, score: QualityScore) -> str:
        """Make the prompt more actionable."""
        # Ensure there's a clear action directive
        return text

    def _guess_section_header(self, content: str) -> Optional[str]:
        """Try to guess an appropriate header for a section."""
        content_lower = content.lower()

        header_patterns = [
            (r'\b(act as|you are|role|expert)\b', 'Role'),
            (r'\b(context|background|situation)\b', 'Context'),
            (r'\b(must|should|constraint|limit|require)\b', 'Requirements'),
            (r'\b(format|structure|output)\b', 'Output Format'),
            (r'\b(avoid|do not|never)\b', 'Constraints'),
            (r'\b(example|sample|instance)\b', 'Examples'),
        ]

        for pattern, header in header_patterns:
            if re.search(pattern, content_lower):
                return header

        return None

    def _diff_changes(self, original: str, refined: str) -> List[str]:
        """Describe what changed between versions."""
        changes = []

        if len(refined) > len(original):
            changes.append(f"Added {len(refined) - len(original)} characters")
        elif len(refined) < len(original):
            changes.append(f"Removed {len(original) - len(refined)} characters")

        orig_sections = original.count('##')
        new_sections = refined.count('##')
        if new_sections > orig_sections:
            changes.append(f"Added {new_sections - orig_sections} section headers")

        return changes if changes else ["Minor text refinements"]
