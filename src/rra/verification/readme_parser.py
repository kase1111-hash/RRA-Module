# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
README parser module.

Extracts structured information from README files including:
- Project description
- Features and capabilities
- Installation instructions
- Usage examples
- Requirements and dependencies
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ReadmeMetadata:
    """Structured metadata extracted from a README file."""
    title: str = ""
    description: str = ""
    short_description: str = ""  # One-line summary
    features: List[str] = field(default_factory=list)
    installation: str = ""
    usage: str = ""
    requirements: List[str] = field(default_factory=list)
    badges: List[Dict[str, str]] = field(default_factory=list)
    links: Dict[str, str] = field(default_factory=dict)
    sections: Dict[str, str] = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    license_mentioned: Optional[str] = None
    has_examples: bool = False
    has_api_docs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "short_description": self.short_description,
            "features": self.features,
            "installation": self.installation,
            "usage": self.usage,
            "requirements": self.requirements,
            "badges": self.badges,
            "links": self.links,
            "sections": list(self.sections.keys()),
            "technologies": self.technologies,
            "license_mentioned": self.license_mentioned,
            "has_examples": self.has_examples,
            "has_api_docs": self.has_api_docs,
        }


class ReadmeParser:
    """
    Parses README files to extract structured metadata.

    Supports Markdown (.md) and reStructuredText (.rst) formats.
    """

    # Common section headers for README files
    SECTION_PATTERNS = {
        "description": r'(?:description|about|overview|introduction)',
        "features": r'(?:features|capabilities|highlights|what.*does)',
        "installation": r'(?:installation|install|setup|getting started|quick start)',
        "usage": r'(?:usage|how to use|examples?|getting started)',
        "requirements": r'(?:requirements|prerequisites|dependencies)',
        "configuration": r'(?:configuration|config|settings|options)',
        "api": r'(?:api|reference|documentation)',
        "contributing": r'(?:contributing|contribution|development)',
        "license": r'(?:license|licensing)',
        "changelog": r'(?:changelog|changes|history|release notes)',
    }

    # Technology/framework detection patterns
    TECHNOLOGY_PATTERNS = [
        (r'\bpython\b', "Python"),
        (r'\bjavascript\b|\bjs\b', "JavaScript"),
        (r'\btypescript\b|\bts\b', "TypeScript"),
        (r'\breact\b', "React"),
        (r'\bvue\b', "Vue.js"),
        (r'\bangular\b', "Angular"),
        (r'\bnode\.?js\b', "Node.js"),
        (r'\brust\b', "Rust"),
        (r'\bgo\b|\bgolang\b', "Go"),
        (r'\bjava\b', "Java"),
        (r'\bdocker\b', "Docker"),
        (r'\bkubernetes\b|\bk8s\b', "Kubernetes"),
        (r'\bfastapi\b', "FastAPI"),
        (r'\bflask\b', "Flask"),
        (r'\bdjango\b', "Django"),
        (r'\bexpress\b', "Express.js"),
        (r'\bnext\.?js\b', "Next.js"),
        (r'\bpostgres(?:ql)?\b', "PostgreSQL"),
        (r'\bmongodb\b', "MongoDB"),
        (r'\bredis\b', "Redis"),
        (r'\bgraphql\b', "GraphQL"),
        (r'\brest\s*api\b', "REST API"),
        (r'\bwebsocket\b', "WebSocket"),
        (r'\baws\b', "AWS"),
        (r'\bgcp\b', "GCP"),
        (r'\bazure\b', "Azure"),
        (r'\bterraform\b', "Terraform"),
        (r'\bweb3\b|\bblockchain\b', "Blockchain"),
        (r'\bethereum\b|\bsolidity\b', "Ethereum"),
    ]

    def __init__(self):
        """Initialize the README parser."""
        pass

    def parse(self, readme_path: Path) -> ReadmeMetadata:
        """
        Parse a README file and extract structured metadata.

        Args:
            readme_path: Path to the README file

        Returns:
            ReadmeMetadata with extracted information
        """
        if not readme_path.exists():
            return ReadmeMetadata()

        try:
            content = readme_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return ReadmeMetadata()

        is_rst = readme_path.suffix.lower() == '.rst'

        metadata = ReadmeMetadata()

        # Extract title
        metadata.title = self._extract_title(content, is_rst)

        # Extract description
        metadata.description = self._extract_description(content, is_rst)
        metadata.short_description = self._create_short_description(metadata.description)

        # Extract sections
        metadata.sections = self._extract_sections(content, is_rst)

        # Extract features
        metadata.features = self._extract_features(content, metadata.sections)

        # Extract installation
        if "installation" in metadata.sections:
            metadata.installation = metadata.sections["installation"]

        # Extract usage
        if "usage" in metadata.sections:
            metadata.usage = metadata.sections["usage"]

        # Extract requirements
        metadata.requirements = self._extract_requirements(content, metadata.sections)

        # Extract badges
        metadata.badges = self._extract_badges(content)

        # Extract links
        metadata.links = self._extract_links(content)

        # Detect technologies
        metadata.technologies = self._detect_technologies(content)

        # Check for license mention
        metadata.license_mentioned = self._detect_license(content)

        # Check for examples and API docs
        metadata.has_examples = bool(re.search(r'```|example|usage', content, re.IGNORECASE))
        metadata.has_api_docs = bool(re.search(r'api|endpoint|reference', content, re.IGNORECASE))

        return metadata

    def parse_from_content(self, content: str, filename: str = "README.md") -> ReadmeMetadata:
        """
        Parse README content directly.

        Args:
            content: README content as string
            filename: Original filename to determine format

        Returns:
            ReadmeMetadata with extracted information
        """
        # Create a temporary path-like for format detection
        is_rst = filename.lower().endswith('.rst')

        metadata = ReadmeMetadata()

        # Extract title
        metadata.title = self._extract_title(content, is_rst)

        # Extract description
        metadata.description = self._extract_description(content, is_rst)
        metadata.short_description = self._create_short_description(metadata.description)

        # Extract sections
        metadata.sections = self._extract_sections(content, is_rst)

        # Extract features
        metadata.features = self._extract_features(content, metadata.sections)

        # Extract installation
        if "installation" in metadata.sections:
            metadata.installation = metadata.sections["installation"]

        # Extract usage
        if "usage" in metadata.sections:
            metadata.usage = metadata.sections["usage"]

        # Extract requirements
        metadata.requirements = self._extract_requirements(content, metadata.sections)

        # Extract badges
        metadata.badges = self._extract_badges(content)

        # Extract links
        metadata.links = self._extract_links(content)

        # Detect technologies
        metadata.technologies = self._detect_technologies(content)

        # Check for license mention
        metadata.license_mentioned = self._detect_license(content)

        # Check for examples and API docs
        metadata.has_examples = bool(re.search(r'```|example|usage', content, re.IGNORECASE))
        metadata.has_api_docs = bool(re.search(r'api|endpoint|reference', content, re.IGNORECASE))

        return metadata

    def _extract_title(self, content: str, is_rst: bool = False) -> str:
        """Extract the title from README content."""
        if is_rst:
            # RST format: title with underline
            match = re.match(r'^([^\n]+)\n[=]+\n', content)
            if match:
                return match.group(1).strip()
        else:
            # Markdown format: # Title
            match = re.match(r'^#\s+(.+?)(?:\n|$)', content)
            if match:
                return match.group(1).strip()

            # Alternative: first line if it looks like a title
            first_line = content.split('\n')[0].strip()
            if first_line and not first_line.startswith(('!', '[', '<', '-', '*')):
                return first_line[:100]

        return ""

    def _extract_description(self, content: str, is_rst: bool = False) -> str:
        """Extract the main description from README content."""
        # Remove badges and initial title
        if is_rst:
            # Remove RST title
            content = re.sub(r'^[^\n]+\n[=]+\n', '', content)
        else:
            # Remove markdown title
            content = re.sub(r'^#\s+.+?\n', '', content)

        # Remove badge lines
        content = re.sub(r'^\[!\[.+?\]\(.+?\)\]\(.+?\)\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\!\[.+?\]\(.+?\)\s*$', '', content, flags=re.MULTILINE)

        # Find the first paragraph(s) before any section header
        paragraphs = []
        lines = content.strip().split('\n')

        in_paragraph = False
        current_para = []

        for line in lines:
            # Stop at section headers
            if re.match(r'^#{1,3}\s+', line) or (is_rst and re.match(r'^[=\-~]+$', line)):
                break

            # Skip empty lines between paragraphs
            if not line.strip():
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []
                continue

            # Skip code blocks
            if line.strip().startswith('```'):
                in_paragraph = not in_paragraph
                continue

            if not in_paragraph:
                # Skip list items for description
                if re.match(r'^[-*]\s+', line):
                    continue
                current_para.append(line.strip())

        if current_para:
            paragraphs.append(' '.join(current_para))

        # Return first few paragraphs
        description = '\n\n'.join(paragraphs[:3])
        return description[:2000]  # Limit length

    def _create_short_description(self, description: str) -> str:
        """Create a one-line summary from the description."""
        if not description:
            return ""

        # Get first sentence
        first_sentence = re.split(r'[.!?]\s', description)[0]

        # Clean up and limit length
        short = first_sentence.strip()
        if len(short) > 150:
            short = short[:147] + "..."

        return short

    def _extract_sections(self, content: str, is_rst: bool = False) -> Dict[str, str]:
        """Extract named sections from README content."""
        sections = {}

        if is_rst:
            # RST section pattern
            section_pattern = r'^([^\n]+)\n([=\-~]+)\n([\s\S]*?)(?=\n[^\n]+\n[=\-~]+\n|$)'
        else:
            # Markdown section pattern
            section_pattern = r'^(#{1,3})\s+([^\n]+)\n([\s\S]*?)(?=\n#{1,3}\s+|$)'

        matches = re.finditer(section_pattern, content, re.MULTILINE)

        for match in matches:
            if is_rst:
                header = match.group(1).strip().lower()
                section_content = match.group(3).strip()
            else:
                header = match.group(2).strip().lower()
                section_content = match.group(3).strip()

            # Normalize header to known section types
            for section_type, pattern in self.SECTION_PATTERNS.items():
                if re.search(pattern, header, re.IGNORECASE):
                    sections[section_type] = section_content
                    break
            else:
                # Store with original header
                sections[header] = section_content

        return sections

    def _extract_features(self, content: str, sections: Dict[str, str]) -> List[str]:
        """Extract feature list from README content."""
        features = []

        # Look in features section first
        features_content = sections.get("features", "")
        if not features_content:
            # Try to find features in the main content
            features_match = re.search(
                r'(?:features?|capabilities|highlights)[:\s]*\n((?:[-*]\s+.+\n?)+)',
                content,
                re.IGNORECASE
            )
            if features_match:
                features_content = features_match.group(1)

        if features_content:
            # Extract list items
            list_items = re.findall(r'^[-*]\s+(.+)$', features_content, re.MULTILINE)
            features.extend([item.strip() for item in list_items[:20]])

        return features

    def _extract_requirements(self, content: str, sections: Dict[str, str]) -> List[str]:
        """Extract requirements/dependencies from README content."""
        requirements = []

        # Look in requirements section
        req_content = sections.get("requirements", "")
        if req_content:
            # Extract list items
            list_items = re.findall(r'^[-*]\s+(.+)$', req_content, re.MULTILINE)
            requirements.extend([item.strip() for item in list_items[:20]])

        # Also look for version requirements
        version_matches = re.findall(
            r'(?:requires?|needs?|depends on)\s+([A-Za-z]+)\s*(?:>=?|<=?|==?)\s*(\d+\.?\d*)',
            content,
            re.IGNORECASE
        )
        for pkg, version in version_matches:
            requirements.append(f"{pkg} >= {version}")

        return requirements

    def _extract_badges(self, content: str) -> List[Dict[str, str]]:
        """Extract badge information from README content."""
        badges = []

        # Match markdown badge pattern: [![alt](img_url)](link_url)
        badge_pattern = r'\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)'
        matches = re.finditer(badge_pattern, content)

        for match in matches:
            alt_text = match.group(1)
            img_url = match.group(2)
            link_url = match.group(3)

            # Identify badge type from URL or alt text
            badge_type = "other"
            if "travis" in img_url.lower():
                badge_type = "build"
            elif "codecov" in img_url.lower() or "coverage" in alt_text.lower():
                badge_type = "coverage"
            elif "pypi" in img_url.lower() or "npm" in img_url.lower():
                badge_type = "package"
            elif "license" in alt_text.lower():
                badge_type = "license"
            elif "version" in alt_text.lower():
                badge_type = "version"

            badges.append({
                "type": badge_type,
                "alt": alt_text,
                "image": img_url,
                "link": link_url,
            })

        return badges[:10]  # Limit

    def _extract_links(self, content: str) -> Dict[str, str]:
        """Extract important links from README content."""
        links = {}

        # Match markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.finditer(link_pattern, content)

        for match in matches:
            text = match.group(1).lower()
            url = match.group(2)

            # Skip badge images
            if url.startswith('https://img.') or url.endswith(('.svg', '.png', '.jpg')):
                continue

            # Categorize links
            if "doc" in text:
                links["documentation"] = url
            elif "demo" in text:
                links["demo"] = url
            elif "api" in text:
                links["api"] = url
            elif "home" in text or "website" in text:
                links["homepage"] = url
            elif "issue" in text or "bug" in text:
                links["issues"] = url
            elif "contribut" in text:
                links["contributing"] = url

        return links

    def _detect_technologies(self, content: str) -> List[str]:
        """Detect technologies/frameworks mentioned in README."""
        technologies = set()
        content_lower = content.lower()

        for pattern, tech_name in self.TECHNOLOGY_PATTERNS:
            if re.search(pattern, content_lower):
                technologies.add(tech_name)

        return sorted(list(technologies))

    def _detect_license(self, content: str) -> Optional[str]:
        """Detect license type mentioned in README."""
        license_patterns = {
            "MIT": r'\bMIT\s+License\b',
            "Apache-2.0": r'\bApache\s+(?:License\s+)?2\.0\b',
            "GPL-3.0": r'\bGPL(?:-3\.0)?\b',
            "BSD-3-Clause": r'\bBSD\s+3-Clause\b',
            "ISC": r'\bISC\s+License\b',
            "FSL-1.1-ALv2": r'\bFSL-1\.1-ALv2\b',
        }

        for license_name, pattern in license_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                return license_name

        return None
