"""Fact checking module for PromptX."""

import re
import logging
import requests
from typing import Dict, List
from dataclasses import dataclass

from ..utils.helpers import timer, safe_execute

logger = logging.getLogger('enhancer')


@dataclass
class FactCheckItem:
    claim: str
    status: str  # 'verified', 'unverified', 'suspicious', 'error'
    confidence: float
    details: str
    source: str


@dataclass
class FactCheckResult:
    overall_status: str
    items_checked: int
    items_verified: int
    items_suspicious: int
    items: List[FactCheckItem]
    recommendations: List[str]


class FactChecker:
    """
    Verifies factual claims, references, and resources
    mentioned in prompts and enhanced outputs.

    Checks:
    - URL accessibility and validity
    - Referenced technology/library existence
    - Version number validity
    - Basic numerical consistency
    """

    KNOWN_TECH = {
        'python': {'latest': '3.12', 'valid_versions': ['2.7', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13']},
        'django': {'latest': '5.1', 'valid_versions': ['2.2', '3.0', '3.1', '3.2', '4.0', '4.1', '4.2', '5.0', '5.1']},
        'react': {'latest': '18', 'valid_versions': ['16', '17', '18', '19']},
        'node': {'latest': '22', 'valid_versions': ['14', '16', '18', '20', '22']},
        'postgresql': {'latest': '16', 'valid_versions': ['12', '13', '14', '15', '16']},
    }

    @timer
    def check(self, text: str) -> FactCheckResult:
        """Run fact checking on text."""
        items = []
        recommendations = []

        # Check 1: Technology version references
        version_items = self._check_tech_versions(text)
        items.extend(version_items)

        # Check 2: URL references
        url_items = self._check_url_references(text)
        items.extend(url_items)

        # Check 3: Numerical consistency
        num_items = self._check_numerical_claims(text)
        items.extend(num_items)

        # Check 4: Deprecated technology references
        deprecated_items = self._check_deprecated_references(text)
        items.extend(deprecated_items)

        # Summarize
        verified = sum(1 for i in items if i.status == 'verified')
        suspicious = sum(1 for i in items if i.status == 'suspicious')

        if suspicious > 0:
            recommendations.append(
                f"{suspicious} potentially inaccurate reference(s) found. Please verify."
            )

        overall = 'clean'
        if suspicious > 0:
            overall = 'has_warnings'
        if suspicious > len(items) * 0.5:
            overall = 'needs_review'

        return FactCheckResult(
            overall_status=overall,
            items_checked=len(items),
            items_verified=verified,
            items_suspicious=suspicious,
            items=items,
            recommendations=recommendations,
        )

    def _check_tech_versions(self, text: str) -> List[FactCheckItem]:
        """Check if technology version references are valid."""
        items = []

        for tech, info in self.KNOWN_TECH.items():
            # Pattern: "python 3.12" or "Django>=4.2" etc.
            pattern = rf'\b{re.escape(tech)}\s*(?:>=?|<=?|==|~=)?\s*v?(\d+(?:\.\d+)*)\b'
            matches = re.findall(pattern, text, re.IGNORECASE)

            for version in matches:
                # Check major version
                major = version.split('.')[0]
                valid_majors = [v.split('.')[0] for v in info['valid_versions']]

                if version in info['valid_versions'] or major in valid_majors:
                    items.append(FactCheckItem(
                        claim=f"{tech} version {version}",
                        status='verified',
                        confidence=0.9,
                        details=f"Version {version} is a known valid version of {tech}",
                        source='internal_database'
                    ))
                else:
                    items.append(FactCheckItem(
                        claim=f"{tech} version {version}",
                        status='suspicious',
                        confidence=0.7,
                        details=f"Version {version} not recognized. Latest known: {info['latest']}",
                        source='internal_database'
                    ))

        return items

    @safe_execute(default=[])
    def _check_url_references(self, text: str) -> List[FactCheckItem]:
        """Verify URL accessibility."""
        items = []
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)

        for url in urls[:5]:  # Limit to 5 URLs
            try:
                response = requests.head(
                    url, timeout=5, allow_redirects=True,
                    headers={'User-Agent': 'PromptX/1.0'}
                )
                if response.status_code < 400:
                    items.append(FactCheckItem(
                        claim=f"URL: {url}",
                        status='verified',
                        confidence=0.95,
                        details=f"URL is accessible (HTTP {response.status_code})",
                        source='http_check'
                    ))
                else:
                    items.append(FactCheckItem(
                        claim=f"URL: {url}",
                        status='suspicious',
                        confidence=0.8,
                        details=f"URL returned HTTP {response.status_code}",
                        source='http_check'
                    ))
            except Exception as e:
                items.append(FactCheckItem(
                    claim=f"URL: {url}",
                    status='unverified',
                    confidence=0.5,
                    details=f"Could not verify URL: {str(e)[:100]}",
                    source='http_check'
                ))

        return items

    def _check_numerical_claims(self, text: str) -> List[FactCheckItem]:
        """Check numerical claims for reasonableness."""
        items = []

        # Check percentages > 100
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        for pct in percentages:
            value = float(pct)
            if value > 100:
                items.append(FactCheckItem(
                    claim=f"{pct}%",
                    status='suspicious',
                    confidence=0.8,
                    details=f"Percentage value {pct}% exceeds 100%",
                    source='numerical_analysis'
                ))

        return items

    def _check_deprecated_references(self, text: str) -> List[FactCheckItem]:
        """Check for deprecated technology references."""
        items = []
        deprecated = {
            r'\bpython\s*2\b': 'Python 2 is end-of-life since January 2020',
            r'\bjquery\s+1\b': 'jQuery 1.x is very outdated',
            r'\bangularjs\b': 'AngularJS (1.x) is end-of-life',
            r'\bflash\b(?!\s+drive)': 'Adobe Flash is discontinued',
            r'\bwindows\s*xp\b': 'Windows XP is end-of-life',
            r'\bie\s*(?:6|7|8|9|10|11)\b': 'Internet Explorer is discontinued',
        }

        for pattern, message in deprecated.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                items.append(FactCheckItem(
                    claim=match.group(),
                    status='suspicious',
                    confidence=0.9,
                    details=message,
                    source='deprecation_check'
                ))

        return items
