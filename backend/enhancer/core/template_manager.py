"""Template manager module for PromptX."""

import logging
import re
from typing import List
from .context_builder import PromptSection
from ..utils.helpers import timer

logger = logging.getLogger('enhancer')


class TemplateManager:
    """
    Assembles final enhanced prompt from sections.
    Handles section ordering, formatting, and rendering.
    """

    @timer
    def render(self, sections: List[PromptSection],
               enhancement_level: str = 'intermediate') -> str:
        """Render sections into final enhanced prompt."""

        # Sort sections by priority (highest first)
        sorted_sections = sorted(sections, key=lambda s: s.priority, reverse=True)

        # Filter based on enhancement level
        if enhancement_level == 'basic':
            sorted_sections = [s for s in sorted_sections if s.is_essential]
        elif enhancement_level == 'intermediate':
            sorted_sections = [s for s in sorted_sections if s.priority >= 40]
        # 'advanced' and 'expert' keep all sections

        # Render
        parts = []
        for section in sorted_sections:
            if section.content.strip():
                parts.append(f"## {section.header}\n{section.content}")

        rendered = '\n\n'.join(parts)

        # Clean up
        rendered = self._clean_output(rendered)

        return rendered

    def _clean_output(self, text: str) -> str:
        """Clean and normalize the final output."""
        # Remove triple+ blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Ensure single trailing newline
        text = text.strip() + '\n'

        return text
