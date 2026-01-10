#!/usr/bin/env python3
"""
Entity Registry for Hyperflow.

Maintains an index of all known entities (people, organizations, concepts)
to prevent duplicates and enable proper wiki-linking.

Features:
- Scans vault directories to build entity index
- Normalizes names for matching (case, titles, suffixes)
- Supports aliases from frontmatter
- Fuzzy matching for similar names

Usage:
    from entity_registry import EntityRegistry

    registry = EntityRegistry(vault_path)
    registry.scan()  # Build index from existing files

    # Check if entity exists
    match = registry.find_person("Dr. Lisa Chang")
    if match:
        print(f"Found: {match.filepath}")  # people/Lisa Chang.md

    # Get wiki-link for entity
    link = registry.get_link("Sarah Chen", "person")
    # Returns: "[[people/Sarah Chen]]"
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class EntityMatch:
    """Result of an entity lookup."""
    name: str  # Canonical name
    filepath: Path  # Path to the entity file
    entity_type: str  # person, organization, concept
    aliases: list[str] = field(default_factory=list)
    confidence: float = 1.0  # Match confidence (1.0 = exact, <1.0 = fuzzy)


class NameNormalizer:
    """Normalizes names for consistent matching."""

    # Common titles to strip for matching
    TITLES = {'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'ms', 'ms.',
              'prof', 'prof.', 'professor', 'sir', 'dame', 'rev', 'rev.'}

    # Common suffixes to strip for matching
    SUFFIXES = {'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v',
                'phd', 'ph.d', 'ph.d.', 'md', 'm.d', 'm.d.', 'esq', 'esq.'}

    @classmethod
    def normalize(cls, name: str) -> str:
        """Normalize a name for matching."""
        if not name:
            return ""

        # Lowercase for comparison
        normalized = name.lower().strip()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove titles from start
        words = normalized.split()
        while words and words[0] in cls.TITLES:
            words.pop(0)

        # Remove suffixes from end
        while words and words[-1] in cls.SUFFIXES:
            words.pop()

        return ' '.join(words)

    @classmethod
    def extract_variants(cls, name: str) -> list[str]:
        """Extract possible name variants for matching."""
        variants = [name]
        normalized = cls.normalize(name)
        if normalized != name.lower():
            variants.append(normalized)

        # Add first-last only variant
        words = normalized.split()
        if len(words) >= 2:
            # First and last name only
            variants.append(f"{words[0]} {words[-1]}")
            # Last name only (for "Chang" matching "Lisa Chang")
            variants.append(words[-1])

        return [v.lower() for v in variants if v]

    @classmethod
    def similarity(cls, name1: str, name2: str) -> float:
        """Calculate similarity between two names (0-1)."""
        n1 = cls.normalize(name1)
        n2 = cls.normalize(name2)

        if n1 == n2:
            return 1.0

        # Check if one contains the other
        if n1 in n2 or n2 in n1:
            return 0.8

        # Check word overlap
        words1 = set(n1.split())
        words2 = set(n2.split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total if total > 0 else 0.0


class EntityRegistry:
    """Registry of all known entities in the vault."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.people_dir = self.vault_path / 'people'
        self.orgs_dir = self.vault_path / 'organizations'
        self.concepts_dir = self.vault_path / 'concepts'

        # Index: normalized_name -> EntityMatch
        self._people: dict[str, EntityMatch] = {}
        self._organizations: dict[str, EntityMatch] = {}
        self._concepts: dict[str, EntityMatch] = {}

        # Reverse index: filepath -> canonical name
        self._filepath_to_name: dict[Path, str] = {}

    def scan(self) -> dict[str, int]:
        """Scan vault directories and build entity index."""
        stats = {'people': 0, 'organizations': 0, 'concepts': 0}

        # Scan people
        if self.people_dir.exists():
            for filepath in self.people_dir.glob('*.md'):
                if filepath.name.startswith('.'):
                    continue
                entity = self._load_entity(filepath, 'person')
                if entity:
                    self._index_entity(entity, self._people)
                    stats['people'] += 1

        # Scan organizations
        if self.orgs_dir.exists():
            for filepath in self.orgs_dir.glob('*.md'):
                if filepath.name.startswith('.'):
                    continue
                entity = self._load_entity(filepath, 'organization')
                if entity:
                    self._index_entity(entity, self._organizations)
                    stats['organizations'] += 1

        # Scan concepts
        if self.concepts_dir.exists():
            for filepath in self.concepts_dir.glob('*.md'):
                if filepath.name.startswith('.'):
                    continue
                entity = self._load_entity(filepath, 'concept')
                if entity:
                    self._index_entity(entity, self._concepts)
                    stats['concepts'] += 1

        return stats

    def _load_entity(self, filepath: Path, entity_type: str) -> Optional[EntityMatch]:
        """Load entity from a markdown file."""
        try:
            content = filepath.read_text(encoding='utf-8')

            # Extract frontmatter
            aliases = []
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                        aliases = frontmatter.get('aliases', [])
                        if isinstance(aliases, str):
                            aliases = [aliases]
                    except yaml.YAMLError:
                        pass

            # Use filename (without .md) as canonical name
            name = filepath.stem

            return EntityMatch(
                name=name,
                filepath=filepath,
                entity_type=entity_type,
                aliases=aliases,
                confidence=1.0
            )
        except Exception:
            return None

    def _index_entity(self, entity: EntityMatch, index: dict[str, EntityMatch]):
        """Add entity to the index with all name variants."""
        # Index by normalized canonical name
        normalized = NameNormalizer.normalize(entity.name)
        index[normalized] = entity

        # Index by all variants of canonical name
        for variant in NameNormalizer.extract_variants(entity.name):
            if variant not in index:
                index[variant] = entity

        # Index by aliases
        for alias in entity.aliases:
            alias_normalized = NameNormalizer.normalize(alias)
            if alias_normalized not in index:
                index[alias_normalized] = entity
            for variant in NameNormalizer.extract_variants(alias):
                if variant not in index:
                    index[variant] = entity

        # Reverse index
        self._filepath_to_name[entity.filepath] = entity.name

    def find_person(self, name: str, min_confidence: float = 0.7) -> Optional[EntityMatch]:
        """Find a person by name."""
        return self._find_in_index(name, self._people, min_confidence)

    def find_organization(self, name: str, min_confidence: float = 0.7) -> Optional[EntityMatch]:
        """Find an organization by name."""
        return self._find_in_index(name, self._organizations, min_confidence)

    def find_concept(self, name: str, min_confidence: float = 0.7) -> Optional[EntityMatch]:
        """Find a concept by name."""
        return self._find_in_index(name, self._concepts, min_confidence)

    def find(self, name: str, entity_type: str = None, min_confidence: float = 0.7) -> Optional[EntityMatch]:
        """Find an entity by name, optionally filtered by type."""
        if entity_type == 'person':
            return self.find_person(name, min_confidence)
        elif entity_type == 'organization':
            return self.find_organization(name, min_confidence)
        elif entity_type == 'concept':
            return self.find_concept(name, min_confidence)
        else:
            # Search all indexes
            for finder in [self.find_person, self.find_organization, self.find_concept]:
                match = finder(name, min_confidence)
                if match:
                    return match
            return None

    def _find_in_index(self, name: str, index: dict[str, EntityMatch],
                       min_confidence: float) -> Optional[EntityMatch]:
        """Search for a name in an index."""
        if not name:
            return None

        # Try exact normalized match
        normalized = NameNormalizer.normalize(name)
        if normalized in index:
            return index[normalized]

        # Try variants
        for variant in NameNormalizer.extract_variants(name):
            if variant in index:
                match = index[variant]
                # Return with slightly lower confidence for variant match
                return EntityMatch(
                    name=match.name,
                    filepath=match.filepath,
                    entity_type=match.entity_type,
                    aliases=match.aliases,
                    confidence=0.9
                )

        # Try fuzzy matching if min_confidence allows
        if min_confidence < 1.0:
            best_match = None
            best_score = min_confidence

            for indexed_name, entity in index.items():
                score = NameNormalizer.similarity(name, indexed_name)
                if score > best_score:
                    best_score = score
                    best_match = EntityMatch(
                        name=entity.name,
                        filepath=entity.filepath,
                        entity_type=entity.entity_type,
                        aliases=entity.aliases,
                        confidence=score
                    )

            return best_match

        return None

    def get_link(self, name: str, entity_type: str = None) -> Optional[str]:
        """Get wiki-link for an entity if it exists."""
        match = self.find(name, entity_type)
        if match:
            # Return relative link from vault root
            rel_path = match.filepath.relative_to(self.vault_path)
            # Remove .md extension for wiki-link
            link_path = str(rel_path.with_suffix(''))
            return f"[[{link_path}]]"
        return None

    def exists(self, name: str, entity_type: str = None) -> bool:
        """Check if an entity exists."""
        return self.find(name, entity_type) is not None

    def get_all_people(self) -> list[str]:
        """Get list of all known people names."""
        return list(set(e.name for e in self._people.values()))

    def get_all_organizations(self) -> list[str]:
        """Get list of all known organization names."""
        return list(set(e.name for e in self._organizations.values()))

    def get_all_concepts(self) -> list[str]:
        """Get list of all known concept names."""
        return list(set(e.name for e in self._concepts.values()))

    def add_alias(self, name: str, alias: str, entity_type: str) -> bool:
        """Add an alias for an existing entity."""
        match = self.find(name, entity_type)
        if not match:
            return False

        # Update file frontmatter
        try:
            content = match.filepath.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    aliases = frontmatter.get('aliases', [])
                    if isinstance(aliases, str):
                        aliases = [aliases]
                    if alias not in aliases:
                        aliases.append(alias)
                        frontmatter['aliases'] = aliases
                        new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---{parts[2]}"
                        match.filepath.write_text(new_content, encoding='utf-8')

                        # Update index
                        match.aliases = aliases
                        index = self._get_index_for_type(entity_type)
                        self._index_entity(match, index)
                        return True
        except Exception:
            pass

        return False

    def _get_index_for_type(self, entity_type: str) -> dict[str, EntityMatch]:
        """Get the appropriate index for an entity type."""
        if entity_type == 'person':
            return self._people
        elif entity_type == 'organization':
            return self._organizations
        else:
            return self._concepts

    def to_json(self) -> str:
        """Export registry to JSON."""
        data = {
            'people': {k: {'name': v.name, 'path': str(v.filepath), 'aliases': v.aliases}
                      for k, v in self._people.items()},
            'organizations': {k: {'name': v.name, 'path': str(v.filepath), 'aliases': v.aliases}
                             for k, v in self._organizations.items()},
            'concepts': {k: {'name': v.name, 'path': str(v.filepath), 'aliases': v.aliases}
                        for k, v in self._concepts.items()},
        }
        return json.dumps(data, indent=2)


# Convenience functions for use in other scripts
_registry_cache: Optional[EntityRegistry] = None

def get_registry(vault_path: Path, refresh: bool = False) -> EntityRegistry:
    """Get or create the entity registry (cached)."""
    global _registry_cache
    if _registry_cache is None or refresh:
        _registry_cache = EntityRegistry(vault_path)
        _registry_cache.scan()
    return _registry_cache


def entity_exists(name: str, entity_type: str, vault_path: Path) -> bool:
    """Check if an entity exists in the vault."""
    registry = get_registry(vault_path)
    return registry.exists(name, entity_type)


def get_entity_link(name: str, entity_type: str, vault_path: Path) -> Optional[str]:
    """Get wiki-link for an entity if it exists."""
    registry = get_registry(vault_path)
    return registry.get_link(name, entity_type)
