"""
Knowledge Base Search Module

Provides search and retrieval functionality for the ICT knowledge base,
including models, concepts, transcripts, and terminology.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import yaml


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
KNOWLEDGE_BASE = PROJECT_ROOT / "knowledge_base"


@dataclass
class SearchResult:
    """A search result from the knowledge base"""
    file_path: str
    file_name: str
    category: str  # models, concepts, transcripts, etc.
    title: str
    snippet: str
    relevance_score: float
    line_number: int = 0


class KnowledgeBaseSearch:
    """
    Search and retrieve content from the ICT knowledge base.
    
    Directories:
    - models/: ICT trading models (Model 9, Model 12, etc.)
    - concepts/: ICT concepts (CBDR, SIBI/BISI, etc.)
    - resources/documents/transcripts/: Episode transcripts
    - definitions/: Terminology YAML files
    """
    
    SEARCHABLE_EXTENSIONS = {'.md', '.txt', '.yaml', '.yml'}
    
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.kb_path = knowledge_base_path or KNOWLEDGE_BASE
        self._index: Dict[str, Dict] = {}
        self._terminology: Dict[str, str] = {}
        self._build_index()
    
    def _build_index(self):
        """Build search index of knowledge base files"""
        if not self.kb_path.exists():
            return
        
        for file_path in self.kb_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.SEARCHABLE_EXTENSIONS:
                rel_path = file_path.relative_to(self.kb_path)
                category = str(rel_path.parts[0]) if rel_path.parts else "root"
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    title = self._extract_title(content, file_path.name)
                    
                    self._index[str(rel_path)] = {
                        "path": str(file_path),
                        "rel_path": str(rel_path),
                        "name": file_path.name,
                        "category": category,
                        "title": title,
                        "content": content,
                        "size": len(content)
                    }
                except Exception as e:
                    pass  # Skip unreadable files
        
        # Load terminology
        self._load_terminology()
    
    def _extract_title(self, content: str, filename: str) -> str:
        """Extract title from markdown content"""
        # Look for # heading
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Fall back to filename
        return filename.replace('.md', '').replace('_', ' ').title()
    
    def _load_terminology(self):
        """Load terminology YAML files"""
        term_files = [
            self.kb_path / "definitions" / "terminology.yaml",
            self.kb_path / "terminology.yaml",
        ]
        
        for term_file in term_files:
            if term_file.exists():
                try:
                    with open(term_file) as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            # Handle different YAML structures
                            if 'terms' in data:
                                for term in data['terms']:
                                    name = term.get('name', term.get('term', ''))
                                    definition = term.get('definition', term.get('description', ''))
                                    if name:
                                        self._terminology[name.lower()] = definition
                            else:
                                for key, value in data.items():
                                    if isinstance(value, str):
                                        self._terminology[key.lower()] = value
                                    elif isinstance(value, dict):
                                        self._terminology[key.lower()] = value.get('definition', str(value))
                except Exception as e:
                    pass
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search the knowledge base.
        
        Args:
            query: Search query
            category: Optional category filter (models, concepts, etc.)
            max_results: Maximum results to return
        
        Returns:
            List of SearchResult objects
        """
        query_lower = query.lower()
        query_words = query_lower.split()
        results = []
        
        for rel_path, doc in self._index.items():
            if category and doc["category"] != category:
                continue
            
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()
            
            # Calculate relevance score
            score = 0.0
            
            # Title match is highest priority
            if query_lower in title_lower:
                score += 10.0
            
            # Word matches in title
            for word in query_words:
                if word in title_lower:
                    score += 3.0
            
            # Exact phrase match in content
            if query_lower in content_lower:
                score += 5.0
            
            # Word frequency in content
            for word in query_words:
                if len(word) >= 3:  # Skip short words
                    count = content_lower.count(word)
                    score += min(count * 0.5, 5.0)  # Cap at 5 points per word
            
            if score > 0:
                # Find snippet with query
                snippet, line_num = self._extract_snippet(doc["content"], query)
                
                results.append(SearchResult(
                    file_path=doc["path"],
                    file_name=doc["name"],
                    category=doc["category"],
                    title=doc["title"],
                    snippet=snippet,
                    relevance_score=score,
                    line_number=line_num
                ))
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: -x.relevance_score)
        return results[:max_results]
    
    def _extract_snippet(self, content: str, query: str, context_lines: int = 2) -> Tuple[str, int]:
        """Extract a snippet around the query match"""
        lines = content.split('\n')
        query_lower = query.lower()
        
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snippet = '\n'.join(lines[start:end])
                return snippet[:500] + "..." if len(snippet) > 500 else snippet, i + 1
        
        # No exact match, return first few lines
        snippet = '\n'.join(lines[:5])
        return snippet[:500] + "..." if len(snippet) > 500 else snippet, 1
    
    def get_model(self, model_name: str) -> Optional[Dict]:
        """
        Get a specific ICT model by name.
        
        Args:
            model_name: Model name (e.g., "model_9", "one_shot_one_kill")
        
        Returns:
            Dict with model info and content
        """
        model_name_lower = model_name.lower().replace(' ', '_').replace('-', '_')
        
        for rel_path, doc in self._index.items():
            if doc["category"] != "models":
                continue
            
            name_lower = doc["name"].lower()
            if model_name_lower in name_lower or name_lower.replace('.md', '') in model_name_lower:
                return {
                    "name": doc["title"],
                    "file": doc["name"],
                    "path": doc["path"],
                    "content": doc["content"]
                }
        
        return None
    
    def get_concept(self, concept_name: str) -> Optional[Dict]:
        """
        Get a specific ICT concept by name.
        
        Args:
            concept_name: Concept name (e.g., "cbdr", "sibi_bisi")
        
        Returns:
            Dict with concept info and content
        """
        concept_name_lower = concept_name.lower().replace(' ', '_').replace('-', '_')
        
        for rel_path, doc in self._index.items():
            if doc["category"] != "concepts":
                continue
            
            name_lower = doc["name"].lower()
            if concept_name_lower in name_lower or name_lower.replace('.md', '') in concept_name_lower:
                return {
                    "name": doc["title"],
                    "file": doc["name"],
                    "path": doc["path"],
                    "content": doc["content"]
                }
        
        return None
    
    def get_transcript(self, episode: int) -> Optional[Dict]:
        """
        Get a specific episode transcript.
        
        Args:
            episode: Episode number
        
        Returns:
            Dict with transcript info and content
        """
        episode_str = f"episode_{episode:02d}" if episode < 10 else f"episode_{episode}"
        
        for rel_path, doc in self._index.items():
            if "transcript" not in rel_path.lower():
                continue
            
            if episode_str in doc["name"].lower() or f"episode_{episode}" in doc["name"].lower():
                return {
                    "episode": episode,
                    "file": doc["name"],
                    "path": doc["path"],
                    "content": doc["content"]
                }
        
        return None
    
    def lookup_term(self, term: str) -> Optional[str]:
        """
        Look up a term definition.
        
        Args:
            term: Term to look up
        
        Returns:
            Definition string or None
        """
        term_lower = term.lower()
        
        # Direct match
        if term_lower in self._terminology:
            return self._terminology[term_lower]
        
        # Partial match
        for key, definition in self._terminology.items():
            if term_lower in key or key in term_lower:
                return definition
        
        return None
    
    def list_models(self) -> List[Dict]:
        """List all available ICT models"""
        models = []
        for rel_path, doc in self._index.items():
            if doc["category"] == "models":
                models.append({
                    "name": doc["title"],
                    "file": doc["name"],
                    "path": doc["path"]
                })
        return models
    
    def list_concepts(self) -> List[Dict]:
        """List all available ICT concepts"""
        concepts = []
        for rel_path, doc in self._index.items():
            if doc["category"] == "concepts":
                concepts.append({
                    "name": doc["title"],
                    "file": doc["name"],
                    "path": doc["path"]
                })
        return concepts
    
    def list_transcripts(self) -> List[Dict]:
        """List all available transcripts"""
        transcripts = []
        for rel_path, doc in self._index.items():
            if "transcript" in rel_path.lower():
                transcripts.append({
                    "name": doc["title"],
                    "file": doc["name"],
                    "path": doc["path"]
                })
        return transcripts
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        stats = {
            "total_files": len(self._index),
            "by_category": {},
            "total_terms": len(self._terminology),
            "total_size_kb": 0
        }
        
        for doc in self._index.values():
            category = doc["category"]
            if category not in stats["by_category"]:
                stats["by_category"][category] = 0
            stats["by_category"][category] += 1
            stats["total_size_kb"] += doc["size"] / 1024
        
        stats["total_size_kb"] = round(stats["total_size_kb"], 1)
        return stats
    
    def format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results as readable text"""
        if not results:
            return "No results found"
        
        lines = [
            f"═══════════════════════════════════════",
            f"  Found {len(results)} result(s)",
            f"═══════════════════════════════════════",
            ""
        ]
        
        for i, result in enumerate(results, 1):
            category_emoji = {
                "models": "📊",
                "concepts": "💡",
                "resources": "📚",
                "definitions": "📖",
                "journal": "📓"
            }.get(result.category, "📄")
            
            lines.extend([
                f"{i}. {category_emoji} {result.title}",
                f"   Category: {result.category}",
                f"   File: {result.file_name}",
                f"   Relevance: {result.relevance_score:.1f}",
                f"   ─────────────────────────────",
                f"   {result.snippet[:200]}...",
                ""
            ])
        
        return "\n".join(lines)
