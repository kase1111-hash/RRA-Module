# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Ingestion layer for repository parsing and knowledge base generation."""

from rra.ingestion.repo_ingester import RepoIngester
from rra.ingestion.knowledge_base import KnowledgeBase

__all__ = ["RepoIngester", "KnowledgeBase"]
