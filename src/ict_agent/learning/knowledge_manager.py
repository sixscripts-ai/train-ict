"""
VEX Knowledge Management System

This is the brain. Everything I learn, store, and recall goes through here.

Sources:
- knowledge_base/ - Static ICT concepts (terminology.yaml, models, etc.)
- data/learning/ - Dynamic learning from trades
- User input - Things Ashton tells me that I need to remember

Everything is interconnected:
- Concepts link to models
- Models link to trade outcomes
- Trade outcomes link back to refine concepts
"""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Concept:
    """An ICT concept with all related information"""
    name: str
    definition: str
    aliases: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    models_that_use_it: List[str] = field(default_factory=list)
    trading_rules: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    my_notes: List[str] = field(default_factory=list)  # What I've learned from trades
    source: str = "knowledge_base"


@dataclass
class Model:
    """An ICT trading model with execution rules"""
    name: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    bias_determination: List[str] = field(default_factory=list)
    entry_rules: List[str] = field(default_factory=list)
    exit_rules: List[str] = field(default_factory=list)
    required_concepts: List[str] = field(default_factory=list)
    best_sessions: List[str] = field(default_factory=list)
    my_win_rate: float = 0.0
    my_notes: List[str] = field(default_factory=list)
    source: str = "knowledge_base"


@dataclass
class UserTeaching:
    """Something Ashton taught me"""
    timestamp: str
    topic: str
    content: str
    category: str  # "rule", "correction", "insight", "preference"
    applied_to: List[str] = field(default_factory=list)  # Concepts/models this affects


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeManager:
    """
    Central knowledge system for VEX.
    
    This loads ALL knowledge from:
    1. terminology.yaml - ICT definitions
    2. ICT_MASTER_LIBRARY.md - Core concepts
    3. extracted/*.md - Model-specific info
    4. data/learning/vex_memory.json - My learned memories
    5. data/learning/user_teachings.json - What Ashton taught me
    
    And provides unified access to query, update, and recall.
    """
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            # Find project root by looking for knowledge_base directory
            current = Path(__file__).resolve()
            while not (current / "knowledge_base").exists() and current.parent != current:
                current = current.parent
            project_root = current
        
        self.project_root = project_root
        self.kb_path = project_root / "knowledge_base"
        self.data_path = project_root / "data" / "learning"
        
        # Knowledge stores
        self.concepts: Dict[str, Concept] = {}
        self.models: Dict[str, Model] = {}
        self.terminology: Dict[str, Any] = {}
        self.user_teachings: List[UserTeaching] = []
        self.memory: Dict[str, Any] = {}
        
        # Concept relationships (the brain wiring)
        self.relationships: Dict[str, Any] = {}
        self.causal_chains: Dict[str, Any] = {}
        self.confluence_weights: Dict[str, float] = {}
        self.anti_patterns: Dict[str, Any] = {}
        self.time_rules: Dict[str, Any] = {}
        
        # FEEDBACK LOOP: Learned confluence statistics
        self.confluence_stats: Dict[str, Any] = {}
        self.confluence_stats_file = self.data_path / "confluence_stats.json"
        
        # Index for fast lookups
        self.alias_to_concept: Dict[str, str] = {}
        self.alias_to_model: Dict[str, str] = {}
        
        # Load everything
        self._load_all()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_all(self):
        """Load all knowledge sources"""
        self._load_terminology()
        self._load_master_library()
        self._load_advanced_concepts()  # NEW: Load advanced concepts
        self._load_extracted_models()
        self._load_relationships()  # NEW: Load concept relationships
        self._load_confluence_stats()  # NEW: Load learned stats
        self._load_memory()
        self._load_user_teachings()
        self._build_indexes()
        stats_count = len(self.confluence_stats.get("combinations", {}))
        print(f"📚 Knowledge loaded: {len(self.concepts)} concepts, {len(self.models)} models, {len(self.relationships.get('concept_requirements', {}))} relationships, {stats_count} learned combos")

    def _load_advanced_concepts(self):
        """Parse ICT_ADVANCED_CONCEPTS.md"""
        lib_file = self.kb_path / "concepts" / "ICT_ADVANCED_CONCEPTS.md"
        if not lib_file.exists():
            return
        
        with open(lib_file) as f:
            content = f.read()
        
        # Simple parser for headers like ## 1. Concept Name
        import re
        sections = re.split(r'\n## \d+\. ', content)
        
        for section in sections[1:]:
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip()
            # Clean title (remove numbering if mistakenly captured)
            name_key = title.lower().split('(')[0].strip().replace(' ', '_')
            
            # Extract definition
            definition = ""
            for i, line in enumerate(lines):
                if line.startswith("**Definition**"):
                    definition = line.replace("**Definition**:", "").strip()
                    break
            
            if name_key not in self.concepts:
                self.concepts[name_key] = Concept(
                    name=title,
                    definition=definition,
                    source="ICT_ADVANCED_CONCEPTS.md"
                )
    
    def _load_terminology(self):
        """Load terminology.yaml into structured concepts"""
        term_file = self.kb_path / "terminology.yaml"
        if not term_file.exists():
            return
        
        with open(term_file) as f:
            self.terminology = yaml.safe_load(f) or {}
        
        # Convert to Concept objects
        for key, data in self.terminology.items():
            if isinstance(data, dict) and "definition" in data:
                concept = Concept(
                    name=data.get("full_name", key),
                    definition=data.get("definition", ""),
                    aliases=data.get("aliases", []) + [key],
                    related_concepts=data.get("related", []),
                    trading_rules=[],
                    source="terminology.yaml"
                )
                
                # Extract trading rules if present
                if "trading_use" in data:
                    if isinstance(data["trading_use"], list):
                        concept.trading_rules = data["trading_use"]
                    else:
                        concept.trading_rules = [data["trading_use"]]
                
                if "trading_implication" in data:
                    concept.trading_rules.append(data["trading_implication"])
                
                self.concepts[key.lower()] = concept
    
    def _load_master_library(self):
        """Parse ICT_MASTER_LIBRARY.md for additional concepts and models"""
        lib_file = self.kb_path / "ICT_MASTER_LIBRARY.md"
        if not lib_file.exists():
            return
        
        with open(lib_file) as f:
            content = f.read()
        
        # Parse sections - this is a simplified parser
        # The library has structure like ## 1.1 Concept Name
        import re
        sections = re.split(r'\n## \d+\.\d+ ', content)
        
        for section in sections[1:]:  # Skip header
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip()
            name_key = title.lower().replace(' ', '_').replace('(', '').replace(')', '')
            
            # Extract definition if present
            definition = ""
            for i, line in enumerate(lines):
                if line.startswith("### Definition"):
                    # Get text until next ### or end
                    def_lines = []
                    for j in range(i+1, len(lines)):
                        if lines[j].startswith("###"):
                            break
                        def_lines.append(lines[j])
                    definition = ' '.join(def_lines).strip()
                    break
            
            if name_key not in self.concepts:
                self.concepts[name_key] = Concept(
                    name=title,
                    definition=definition,
                    source="ICT_MASTER_LIBRARY.md"
                )
            elif definition:
                # Enhance existing concept
                self.concepts[name_key].definition = definition
    
    def _load_extracted_models(self):
        """Load model information from extracted/ folder"""
        extracted_path = self.kb_path / "extracted"
        if not extracted_path.exists():
            return
        
        for md_file in extracted_path.glob("*.md"):
            model_name = md_file.stem.replace("_processed", "").replace("_", " ").title()
            
            with open(md_file) as f:
                content = f.read()
            
            # Create or update model
            model_key = md_file.stem.replace("_processed", "")
            self.models[model_key] = Model(
                name=model_name,
                description=content[:500] + "..." if len(content) > 500 else content,
                source=f"extracted/{md_file.name}"
            )
        
        # Also load from imported/
        imported_path = self.kb_path / "imported"
        if imported_path.exists():
            for md_file in imported_path.glob("*.md"):
                model_key = md_file.stem
                if model_key not in self.models:
                    with open(md_file) as f:
                        content = f.read()
                    self.models[model_key] = Model(
                        name=md_file.stem.replace("_", " ").title(),
                        description=content[:500] + "...",
                        source=f"imported/{md_file.name}"
                    )
    
    def _load_relationships(self):
        """Load concept_relationships.yaml - the brain wiring"""
        rel_file = self.kb_path / "concept_relationships.yaml"
        if not rel_file.exists():
            print("⚠️ concept_relationships.yaml not found")
            return
        
        with open(rel_file) as f:
            self.relationships = yaml.safe_load(f) or {}
        
        # Extract key sections for quick access
        self.causal_chains = self.relationships.get("causal_chains", {})
        self.anti_patterns = self.relationships.get("anti_patterns", {})
        self.time_rules = self.relationships.get("time_rules", {})
        
        # Build confluence weight lookup
        weights = self.relationships.get("confluence_weights", {})
        for level in ["critical", "high", "moderate", "bonuses"]:
            for concept, weight in weights.get(level, {}).items():
                self.confluence_weights[concept] = weight
        for concept, weight in weights.get("penalties", {}).items():
            self.confluence_weights[concept] = weight  # Already negative
        
        # Merge model info from relationships into existing models
        rel_models = self.relationships.get("models", {})
        for model_key, model_data in rel_models.items():
            if model_key in self.models:
                # Enhance existing model
                m = self.models[model_key]
                if "required" in model_data:
                    m.entry_rules.extend(model_data["required"])
                if "best_sessions" in model_data:
                    m.best_sessions = model_data.get("time_windows", [])
            else:
                # Create new model from relationships
                self.models[model_key] = Model(
                    name=model_key.replace("_", " ").title(),
                    description=model_data.get("description", ""),
                    entry_rules=model_data.get("required", []),
                    source="concept_relationships.yaml"
                )
    
    def _load_confluence_stats(self):
        """Load learned confluence statistics from trades"""
        if self.confluence_stats_file.exists():
            with open(self.confluence_stats_file) as f:
                self.confluence_stats = json.load(f)
        else:
            # Initialize empty stats structure
            self.confluence_stats = {
                "combinations": {},  # "fvg+displacement+liquidity_swept": {wins, losses, total, win_rate}
                "singles": {},  # Individual confluence stats
                "models": {},  # Per-model stats
                "sessions": {},  # Per-session stats
                "pairs": {},  # Per-pair stats
                "last_updated": None,
            }
    
    def _save_confluence_stats(self):
        """Save learned confluence statistics"""
        self.confluence_stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.confluence_stats["last_updated"] = datetime.now(NY_TZ).isoformat()
        with open(self.confluence_stats_file, 'w') as f:
            json.dump(self.confluence_stats, f, indent=2)
    
    def _load_memory(self):
        """Load vex_memory.json"""
        memory_file = self.data_path / "vex_memory.json"
        if memory_file.exists():
            with open(memory_file) as f:
                self.memory = json.load(f)
    
    def _load_user_teachings(self):
        """Load what Ashton has taught me"""
        teachings_file = self.data_path / "user_teachings.json"
        if teachings_file.exists():
            with open(teachings_file) as f:
                data = json.load(f)
                self.user_teachings = [
                    UserTeaching(**t) for t in data
                ]
    
    def _build_indexes(self):
        """Build alias lookups for fast search"""
        for key, concept in self.concepts.items():
            self.alias_to_concept[key] = key
            for alias in concept.aliases:
                self.alias_to_concept[alias.lower()] = key
        
        for key, model in self.models.items():
            self.alias_to_model[key] = key
            for alias in model.aliases:
                self.alias_to_model[alias.lower()] = key
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SAVING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_teachings(self):
        """Save user teachings to file"""
        teachings_file = self.data_path / "user_teachings.json"
        teachings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(teachings_file, 'w') as f:
            json.dump([asdict(t) for t in self.user_teachings], f, indent=2)
    
    def _save_memory(self):
        """Save memory to file"""
        memory_file = self.data_path / "vex_memory.json"
        with open(memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LEARNING FROM USER
    # ═══════════════════════════════════════════════════════════════════════════
    
    def learn_from_user(
        self,
        content: str,
        topic: str = "general",
        category: str = "insight",  # rule, correction, insight, preference
        applies_to: List[str] = None,
    ) -> UserTeaching:
        """
        Store something Ashton teaches me.
        
        This is the PRIMARY method for retaining user-provided information.
        """
        teaching = UserTeaching(
            timestamp=datetime.now(NY_TZ).isoformat(),
            topic=topic,
            content=content,
            category=category,
            applied_to=applies_to or [],
        )
        
        self.user_teachings.append(teaching)
        self._save_teachings()
        
        # Also add to memory for quick recall
        if "user_lessons" not in self.memory:
            self.memory["user_lessons"] = []
        
        self.memory["user_lessons"].append({
            "timestamp": teaching.timestamp,
            "topic": topic,
            "content": content,
            "category": category,
        })
        self._save_memory()
        
        print(f"📝 Learned from Ashton: [{category}] {topic}")
        return teaching
    
    def add_rule(self, rule: str, context: str = ""):
        """Add a trading rule I should follow"""
        return self.learn_from_user(
            content=rule,
            topic=context or "trading_rule",
            category="rule"
        )
    
    def add_correction(self, what_i_did_wrong: str, what_to_do_instead: str):
        """Record when Ashton corrects me"""
        content = f"WRONG: {what_i_did_wrong} | CORRECT: {what_to_do_instead}"
        return self.learn_from_user(
            content=content,
            topic="correction",
            category="correction"
        )
    
    def add_concept_note(self, concept_name: str, note: str):
        """Add a note to a specific concept"""
        key = concept_name.lower().replace(' ', '_')
        
        # Try to find the concept
        actual_key = self.alias_to_concept.get(key, key)
        
        if actual_key in self.concepts:
            self.concepts[actual_key].my_notes.append(note)
            # Save the enhanced concept
            self._save_concept_notes()
        
        return self.learn_from_user(
            content=note,
            topic=concept_name,
            category="insight",
            applies_to=[concept_name]
        )
    
    def _save_concept_notes(self):
        """Save concept notes to a separate file"""
        notes_file = self.data_path / "concept_notes.json"
        notes = {}
        for key, concept in self.concepts.items():
            if concept.my_notes:
                notes[key] = concept.my_notes
        
        with open(notes_file, 'w') as f:
            json.dump(notes, f, indent=2)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERYING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_concept(self, name: str) -> Optional[Concept]:
        """Get a concept by name or alias"""
        key = name.lower().replace(' ', '_')
        actual_key = self.alias_to_concept.get(key, key)
        return self.concepts.get(actual_key)
    
    def get_model(self, name: str) -> Optional[Model]:
        """Get a model by name or alias"""
        key = name.lower().replace(' ', '_')
        actual_key = self.alias_to_model.get(key, key)
        return self.models.get(actual_key)
    
    def search(self, query: str) -> Dict[str, List]:
        """Search across all knowledge for a term"""
        query_lower = query.lower()
        results = {
            "concepts": [],
            "models": [],
            "teachings": [],
            "memory": [],
        }
        
        # Search concepts
        for key, concept in self.concepts.items():
            if (query_lower in concept.name.lower() or 
                query_lower in concept.definition.lower() or
                any(query_lower in alias.lower() for alias in concept.aliases)):
                results["concepts"].append(concept)
        
        # Search models
        for key, model in self.models.items():
            if (query_lower in model.name.lower() or 
                query_lower in model.description.lower()):
                results["models"].append(model)
        
        # Search teachings
        for teaching in self.user_teachings:
            if (query_lower in teaching.content.lower() or
                query_lower in teaching.topic.lower()):
                results["teachings"].append(teaching)
        
        # Search memory
        for key, value in self.memory.items():
            if query_lower in key.lower():
                results["memory"].append({key: value})
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if any(query_lower in str(v).lower() for v in item.values()):
                            results["memory"].append(item)
        
        return results
    
    def explain(self, term: str) -> str:
        """Get a full explanation of a term/concept/model"""
        concept = self.get_concept(term)
        if concept:
            lines = [
                f"📖 {concept.name}",
                f"Definition: {concept.definition}",
            ]
            if concept.aliases:
                lines.append(f"Also known as: {', '.join(concept.aliases)}")
            if concept.trading_rules:
                lines.append("Trading Rules:")
                for rule in concept.trading_rules:
                    lines.append(f"  • {rule}")
            if concept.my_notes:
                lines.append("My Notes (from trading):")
                for note in concept.my_notes:
                    lines.append(f"  💡 {note}")
            if concept.related_concepts:
                lines.append(f"Related: {', '.join(concept.related_concepts)}")
            return '\n'.join(lines)
        
        model = self.get_model(term)
        if model:
            lines = [
                f"📊 {model.name}",
                f"Description: {model.description[:300]}...",
            ]
            if model.my_notes:
                lines.append("My Notes:")
                for note in model.my_notes:
                    lines.append(f"  💡 {note}")
            return '\n'.join(lines)
        
        return f"Unknown term: {term}"
    
    def get_all_rules(self) -> List[str]:
        """Get all trading rules I've learned"""
        rules = []
        
        # From memory golden rules
        for rule in self.memory.get("golden_rules", []):
            rules.append(f"[GOLDEN] {rule.get('value', rule)}")
        
        # From user teachings
        for teaching in self.user_teachings:
            if teaching.category == "rule":
                rules.append(f"[USER] {teaching.content}")
        
        return rules
    
    def get_corrections(self) -> List[str]:
        """Get all corrections Ashton has made"""
        return [
            t.content for t in self.user_teachings 
            if t.category == "correction"
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECALL FOR TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def recall_for_setup(
        self,
        model: str,
        concepts_involved: List[str],
        session: str,
    ) -> Dict[str, Any]:
        """
        Recall all relevant knowledge before taking a trade.
        
        NOW RELATIONSHIP-AWARE:
        - Checks if required concepts are present
        - Warns about missing dependencies
        - Flags anti-patterns
        - Validates time rules
        - Calculates confluence score
        
        Returns rules, warnings, and relevant teachings.
        """
        result = {
            "relevant_rules": [],
            "warnings": [],
            "model_info": None,
            "concept_info": [],
            "user_teachings": [],
            "missing_requirements": [],
            "anti_patterns_detected": [],
            "confluence_score": 0.0,
            "time_valid": True,
            "validation_passed": True,
        }
        
        concepts_lower = [c.lower() for c in concepts_involved]
        model_lower = model.lower().replace(" ", "_")
        
        # ===== MODEL REQUIREMENTS CHECK =====
        model_obj = self.get_model(model)
        rel_models = self.relationships.get("models", {})
        
        if model_lower in rel_models:
            model_rel = rel_models[model_lower]
            
            # Check required concepts
            for req in model_rel.get("required", []):
                req_lower = req.lower()
                # Check if any concept matches the requirement
                found = any(req_lower in c or c in req_lower for c in concepts_lower)
                if not found:
                    result["missing_requirements"].append(req)
                    result["warnings"].append(f"⚠️ {model} requires: {req}")
            
            # Check time window
            time_windows = model_rel.get("time_windows", [])
            if time_windows and session:
                session_lower = session.lower()
                valid_time = False
                for tw in time_windows:
                    if isinstance(tw, dict):
                        tw_name = tw.get("name", "").lower()
                        if session_lower in tw_name or tw_name in session_lower:
                            valid_time = True
                            break
                    elif session_lower in str(tw).lower():
                        valid_time = True
                        break
                
                if not valid_time and time_windows:
                    result["time_valid"] = False
                    result["warnings"].append(f"⏰ {model} best during: {', '.join(str(t) for t in time_windows[:2])}")
        
        if model_obj:
            result["model_info"] = {
                "name": model_obj.name,
                "notes": model_obj.my_notes,
                "entry_rules": model_obj.entry_rules,
            }
        
        # ===== CONCEPT REQUIREMENTS CHECK =====
        concept_reqs = self.relationships.get("concept_requirements", {})
        
        for concept_name in concepts_involved:
            concept_key = concept_name.lower().replace(" ", "_")
            
            # Get concept info
            concept = self.get_concept(concept_name)
            if concept:
                result["concept_info"].append({
                    "name": concept.name,
                    "rules": concept.trading_rules,
                    "notes": concept.my_notes,
                })
            
            # Check requirements from relationships
            if concept_key in concept_reqs:
                reqs = concept_reqs[concept_key]
                
                # Check 'requires' dependencies
                for req in reqs.get("requires", []):
                    req_concept = req.get("concept", "") if isinstance(req, dict) else req
                    if req_concept.lower() not in concepts_lower:
                        why = req.get("why", "") if isinstance(req, dict) else ""
                        result["warnings"].append(f"⚠️ {concept_name} requires {req_concept}: {why}")
                        result["missing_requirements"].append(req_concept)
                
                # Get entry rules
                for rule in reqs.get("entry_rules", []):
                    result["relevant_rules"].append(f"[{concept_name}] {rule}")
        
        # ===== ANTI-PATTERN DETECTION =====
        for pattern_key, pattern in self.anti_patterns.items():
            # Check if this anti-pattern might apply
            pattern_concepts = pattern_key.lower().replace("_", " ").split()
            
            # Simple heuristic: if key words from pattern match concepts
            if any(pc in ' '.join(concepts_lower) for pc in pattern_concepts):
                # More specific check for known anti-patterns
                if pattern_key == "fvg_without_displacement":
                    if "fvg" in concepts_lower and "displacement" not in concepts_lower:
                        result["anti_patterns_detected"].append({
                            "pattern": pattern_key,
                            "description": pattern.get("description", ""),
                            "why_fails": pattern.get("why_fails", ""),
                            "fix": pattern.get("fix", ""),
                            "historical_winrate": pattern.get("historical_winrate", 0.25),
                        })
                        result["warnings"].append(f"🚫 ANTI-PATTERN: {pattern.get('description', pattern_key)}")
                
                elif pattern_key == "entry_before_liquidity_sweep":
                    if "liquidity" not in concepts_lower and "liquidity_swept" not in concepts_lower:
                        result["warnings"].append(f"⚠️ No liquidity sweep detected - common failure pattern")
        
        # ===== CONFLUENCE SCORE =====
        score = 0.0
        for concept in concepts_lower:
            # Direct match
            if concept in self.confluence_weights:
                score += self.confluence_weights[concept]
            
            # Partial match (e.g., "htf_bias" matches "htf_bias_aligned")
            for weight_key, weight in self.confluence_weights.items():
                if concept in weight_key or weight_key in concept:
                    score += weight * 0.7  # Partial credit
                    break
        
        # ===== LEARNED ADJUSTMENT (FEEDBACK LOOP) =====
        learned_adj = self.get_learned_adjustment(concepts_lower, model)
        if learned_adj != 0:
            score += learned_adj
            if learned_adj > 0:
                result["relevant_rules"].append(f"📈 +{learned_adj:.1f} from learned win rate")
            else:
                result["warnings"].append(f"📉 {learned_adj:.1f} from learned loss rate")
        
        result["confluence_score"] = round(score, 1)
        result["learned_adjustment"] = learned_adj
        
        # Check against thresholds
        thresholds = self.relationships.get("confluence_weights", {}).get("thresholds", {})
        min_score = thresholds.get("minimum_for_trade", 5.0)
        
        if score < min_score:
            result["warnings"].append(f"📊 Confluence score {score:.1f} below minimum {min_score}")
            result["validation_passed"] = False
        elif score >= thresholds.get("a_plus_setup", 9.0):
            result["relevant_rules"].insert(0, "🌟 A+ SETUP - High confluence score!")
        
        # ===== TIME RULES CHECK =====
        if session:
            avoid_times = self.time_rules.get("avoid_times", [])
            for avoid in avoid_times:
                if isinstance(avoid, dict):
                    time_str = avoid.get("time", "").lower()
                    reason = avoid.get("reason", "")
                    if session.lower() in time_str or time_str in session.lower():
                        result["warnings"].append(f"⏰ Avoid trading now: {reason}")
                        result["time_valid"] = False
        
        # ===== USER TEACHINGS =====
        for teaching in self.user_teachings:
            if (model_lower in teaching.topic.lower() or
                model_lower in teaching.content.lower() or
                session.lower() in teaching.content.lower() if session else False or
                any(c.lower() in teaching.content.lower() for c in concepts_involved)):
                result["user_teachings"].append(teaching.content)
        
        # ===== FINAL VALIDATION =====
        if result["missing_requirements"]:
            result["validation_passed"] = False
        if result["anti_patterns_detected"]:
            result["validation_passed"] = False
        
        # Add general rules from memory
        result["relevant_rules"].extend(self.get_all_rules()[:5])
        
        return result
    
    def validate_setup(
        self,
        confluences: List[str],
        model: str = "",
        session: str = "",
    ) -> Dict[str, Any]:
        """
        Quick validation check for a setup.
        
        Returns a simple pass/fail with reasons.
        """
        recall = self.recall_for_setup(model, confluences, session)
        
        return {
            "valid": recall["validation_passed"],
            "score": recall["confluence_score"],
            "warnings": recall["warnings"],
            "missing": recall["missing_requirements"],
            "anti_patterns": [ap["pattern"] for ap in recall["anti_patterns_detected"]],
        }
    
    def get_model_checklist(self, model: str) -> List[str]:
        """
        Get the complete checklist for a model.
        
        Returns what's required for a valid setup.
        """
        model_lower = model.lower().replace(" ", "_")
        rel_models = self.relationships.get("models", {})
        
        checklist = []
        
        if model_lower in rel_models:
            model_rel = rel_models[model_lower]
            
            # Time windows
            for tw in model_rel.get("time_windows", []):
                if isinstance(tw, dict):
                    checklist.append(f"⏰ Time: {tw.get('start')}-{tw.get('end')} {tw.get('timezone', 'ET')}")
                else:
                    checklist.append(f"⏰ Time: {tw}")
            
            # Requirements
            for req in model_rel.get("required", []):
                checklist.append(f"✓ {req}")
            
            # What to avoid
            for avoid in model_rel.get("avoid_when", []):
                checklist.append(f"✗ Avoid: {avoid}")
        
        return checklist
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FEEDBACK LOOP - Learn from trade outcomes
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_trade_feedback(
        self,
        confluences: List[str],
        outcome: str,  # "win", "loss", "breakeven"
        model: str = "",
        session: str = "",
        pair: str = "",
        rr_achieved: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Record trade outcome to learn which confluence combinations work.
        
        This is THE feedback loop. Every trade teaches us:
        - Which confluence combinations win/lose
        - Which models perform best
        - Which sessions are profitable
        - Pair-specific patterns
        
        Returns summary of what was learned.
        """
        is_win = outcome.lower() == "win"
        learned = {"updated": [], "insights": []}
        
        # Normalize confluences
        confluences_normalized = sorted([c.lower().replace(" ", "_") for c in confluences])
        
        # === 1. Update combination stats ===
        if len(confluences_normalized) >= 2:
            combo_key = "+".join(confluences_normalized)
            
            if combo_key not in self.confluence_stats["combinations"]:
                self.confluence_stats["combinations"][combo_key] = {
                    "wins": 0, "losses": 0, "total": 0, "win_rate": 0.0,
                    "total_rr": 0.0, "avg_rr": 0.0,
                    "confluences": confluences_normalized,
                }
            
            stats = self.confluence_stats["combinations"][combo_key]
            stats["total"] += 1
            stats["total_rr"] += rr_achieved
            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            
            stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            stats["avg_rr"] = stats["total_rr"] / stats["total"] if stats["total"] > 0 else 0
            
            learned["updated"].append(f"combo:{combo_key}")
            
            # Generate insight if enough data
            if stats["total"] >= 5:
                if stats["win_rate"] >= 0.7:
                    learned["insights"].append(f"🌟 Strong combo ({stats['win_rate']:.0%}): {combo_key}")
                elif stats["win_rate"] <= 0.3:
                    learned["insights"].append(f"⚠️ Weak combo ({stats['win_rate']:.0%}): {combo_key}")
        
        # === 2. Update individual confluence stats ===
        for conf in confluences_normalized:
            if conf not in self.confluence_stats["singles"]:
                self.confluence_stats["singles"][conf] = {
                    "wins": 0, "losses": 0, "total": 0, "win_rate": 0.0,
                }
            
            stats = self.confluence_stats["singles"][conf]
            stats["total"] += 1
            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            stats["win_rate"] = stats["wins"] / stats["total"]
        
        # === 3. Update model stats ===
        if model:
            model_key = model.lower().replace(" ", "_")
            if model_key not in self.confluence_stats["models"]:
                self.confluence_stats["models"][model_key] = {
                    "wins": 0, "losses": 0, "total": 0, "win_rate": 0.0,
                    "total_rr": 0.0, "avg_rr": 0.0,
                }
            
            stats = self.confluence_stats["models"][model_key]
            stats["total"] += 1
            stats["total_rr"] += rr_achieved
            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            stats["win_rate"] = stats["wins"] / stats["total"]
            stats["avg_rr"] = stats["total_rr"] / stats["total"]
            learned["updated"].append(f"model:{model_key}")
        
        # === 4. Update session stats ===
        if session:
            session_key = session.lower()
            if session_key not in self.confluence_stats["sessions"]:
                self.confluence_stats["sessions"][session_key] = {
                    "wins": 0, "losses": 0, "total": 0, "win_rate": 0.0,
                }
            
            stats = self.confluence_stats["sessions"][session_key]
            stats["total"] += 1
            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            stats["win_rate"] = stats["wins"] / stats["total"]
            learned["updated"].append(f"session:{session_key}")
        
        # === 5. Update pair stats ===
        if pair:
            pair_key = pair.upper()
            if pair_key not in self.confluence_stats["pairs"]:
                self.confluence_stats["pairs"][pair_key] = {
                    "wins": 0, "losses": 0, "total": 0, "win_rate": 0.0,
                    "total_rr": 0.0,
                }
            
            stats = self.confluence_stats["pairs"][pair_key]
            stats["total"] += 1
            stats["total_rr"] += rr_achieved
            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            stats["win_rate"] = stats["wins"] / stats["total"]
            learned["updated"].append(f"pair:{pair_key}")
        
        # Save updated stats
        self._save_confluence_stats()
        
        print(f"📊 Feedback recorded: {outcome} with {len(confluences)} confluences")
        for insight in learned["insights"]:
            print(f"   {insight}")
        
        return learned
    
    def get_learned_adjustment(self, confluences: List[str], model: str = "") -> float:
        """
        Get score adjustment based on learned statistics.
        
        Returns a modifier to add/subtract from the base confluence score.
        """
        adjustment = 0.0
        confluences_normalized = sorted([c.lower().replace(" ", "_") for c in confluences])
        
        # Check combination stats
        if len(confluences_normalized) >= 2:
            combo_key = "+".join(confluences_normalized)
            if combo_key in self.confluence_stats["combinations"]:
                stats = self.confluence_stats["combinations"][combo_key]
                if stats["total"] >= 3:  # Need at least 3 trades for significance
                    # Adjust based on deviation from 50% win rate
                    deviation = stats["win_rate"] - 0.5
                    adjustment += deviation * 3.0  # Max ±1.5 adjustment
        
        # Check model stats
        if model:
            model_key = model.lower().replace(" ", "_")
            if model_key in self.confluence_stats["models"]:
                stats = self.confluence_stats["models"][model_key]
                if stats["total"] >= 5:
                    deviation = stats["win_rate"] - 0.5
                    adjustment += deviation * 2.0  # Max ±1.0 adjustment
        
        return round(adjustment, 2)
    
    def get_best_combinations(self, min_trades: int = 3) -> List[Dict]:
        """Get best performing confluence combinations"""
        combos = []
        for key, stats in self.confluence_stats.get("combinations", {}).items():
            if stats["total"] >= min_trades:
                combos.append({
                    "combination": key,
                    "win_rate": stats["win_rate"],
                    "trades": stats["total"],
                    "avg_rr": stats.get("avg_rr", 0),
                    "confluences": stats.get("confluences", key.split("+")),
                })
        
        return sorted(combos, key=lambda x: x["win_rate"], reverse=True)
    
    def get_worst_combinations(self, min_trades: int = 3) -> List[Dict]:
        """Get worst performing confluence combinations"""
        return list(reversed(self.get_best_combinations(min_trades)))[:5]
    
    def get_confluence_report(self) -> str:
        """Generate a report of learned confluence statistics"""
        lines = [
            "═" * 50,
            "📊 LEARNED CONFLUENCE STATISTICS",
            "═" * 50,
        ]
        
        # Best combinations
        best = self.get_best_combinations(min_trades=3)[:5]
        if best:
            lines.append("\n🌟 BEST COMBINATIONS:")
            for combo in best:
                lines.append(f"  {combo['win_rate']:.0%} ({combo['trades']} trades): {combo['combination']}")
        
        # Worst combinations
        worst = self.get_worst_combinations(min_trades=3)
        if worst:
            lines.append("\n⚠️ WORST COMBINATIONS:")
            for combo in worst:
                lines.append(f"  {combo['win_rate']:.0%} ({combo['trades']} trades): {combo['combination']}")
        
        # Model stats
        models = self.confluence_stats.get("models", {})
        if models:
            lines.append("\n📈 MODEL PERFORMANCE:")
            for model, stats in sorted(models.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True):
                if stats["total"] >= 2:
                    lines.append(f"  {model}: {stats['win_rate']:.0%} ({stats['total']} trades)")
        
        # Session stats
        sessions = self.confluence_stats.get("sessions", {})
        if sessions:
            lines.append("\n⏰ SESSION PERFORMANCE:")
            for session, stats in sorted(sessions.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True):
                if stats["total"] >= 2:
                    lines.append(f"  {session}: {stats['win_rate']:.0%} ({stats['total']} trades)")
        
        total_trades = sum(s.get("total", 0) for s in self.confluence_stats.get("singles", {}).values()) // max(1, len(self.confluence_stats.get("singles", {})))
        lines.append(f"\n📊 Total trade data points: ~{total_trades}")
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_summary(self) -> str:
        """Get a summary of all knowledge"""
        lines = [
            "═" * 50,
            "📚 VEX KNOWLEDGE SUMMARY",
            "═" * 50,
            f"Concepts loaded: {len(self.concepts)}",
            f"Models loaded: {len(self.models)}",
            f"User teachings: {len(self.user_teachings)}",
            f"Golden rules: {len(self.memory.get('golden_rules', []))}",
            "",
            "📖 Key Concepts:",
        ]
        
        # Show some key concepts
        key_concepts = ['fvg', 'order_block', 'liquidity', 'bos', 'sms']
        for kc in key_concepts:
            if kc in self.concepts:
                lines.append(f"  • {self.concepts[kc].name}")
        
        lines.append("")
        lines.append("📊 Models:")
        for name in list(self.models.keys())[:5]:
            lines.append(f"  • {self.models[name].name}")
        
        if self.user_teachings:
            lines.append("")
            lines.append("💡 Recent User Teachings:")
            for teaching in self.user_teachings[-3:]:
                lines.append(f"  [{teaching.category}] {teaching.content[:50]}...")
        
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_knowledge_manager: Optional[KnowledgeManager] = None

def get_knowledge_manager() -> KnowledgeManager:
    """Get the singleton knowledge manager instance"""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def learn(content: str, topic: str = "general", category: str = "insight"):
    """Quick function to learn from user"""
    return get_knowledge_manager().learn_from_user(content, topic, category)

def add_rule(rule: str, context: str = ""):
    """Quick function to add a rule"""
    return get_knowledge_manager().add_rule(rule, context)

def explain(term: str) -> str:
    """Quick function to explain a term"""
    return get_knowledge_manager().explain(term)

def search(query: str):
    """Quick function to search knowledge"""
    return get_knowledge_manager().search(query)


# Test
if __name__ == "__main__":
    km = KnowledgeManager()
    print(km.get_summary())
    print("\n" + "=" * 50)
    print(km.explain("FVG"))
    print("\n" + "=" * 50)
    print(km.explain("order_block"))
