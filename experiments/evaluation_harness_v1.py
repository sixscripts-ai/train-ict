#!/usr/bin/env python3
"""
Evaluation Harness V1
Systematically QA_Banks key V9 logic.
Requirements:
1. Load standard validation_QA set.
2. Invoke current LLaMA / Oanda / Adapter logic.
3. Compare outputs against Keyword Presence metric + cosine similarity score against gold_answers.
4. Output precise percentage 0.0-100 accy per concept category.
5. Save runs metadata in .CSV summary rows.
"""

import json
import csv
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    logger.warning("numpy or scikit-learn not found. Cosine similarity will be disabled.")
    np = None
    cosine_similarity = None

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    logger.warning("sentence-transformers not found. Semantic similarity will be disabled.")
    HAS_SENTENCE_TRANSFORMERS = False


class EvaluationSystem:
    def __init__(self, qa_file_path: Optional[str] = None, output_csv_path: Optional[str] = None):
        self.project_root = Path(__file__).resolve().parent.parent
        self.qa_file_path = Path(qa_file_path) if qa_file_path else self.project_root / "data" / "training" / "qa" / "ict_concepts_qa.json"
        self.output_csv_path = Path(output_csv_path) if output_csv_path else self.project_root / "experiments" / "evaluation_summary.csv"
        
        # Determine model for embeddings if available
        self.embedding_model = None
        if HAS_SENTENCE_TRANSFORMERS:
            # We use a small model for speed, avoiding massive downloads if possible
            # But the user asked to avoid loading inference. We establish the *architecture* here.
            # Lazy loading in invoke if needed
            pass

        self.results_history = []
        self.current_run_metrics = {}

    def load_qa_data(self) -> List[Dict[str, Any]]:
        """Loads the standard validation QA set."""
        if not self.qa_file_path.exists():
            logger.error(f"QA file not found: {self.qa_file_path}")
            return []
        
        try:
            with open(self.qa_file_path, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} QA pairs from {self.qa_file_path}")
                return data
        except Exception as e:
            logger.error(f"Failed to load QA data: {e}")
            return []

    def load_embedding_model(self):
        """Loads embedding model only when needed to avoid overhead during initialization."""
        if HAS_SENTENCE_TRANSFORMERS and self.embedding_model is None:
            logger.info("Loading embedding model (architecture only - actual load would happen here)...")
            # self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2') 
            # Commented out to avoid 'excessively executing slow 4bit loading inference now' as requested.
            pass

    def invoke_logic(self, question: str, context: Optional[str] = None) -> str:
        """
        Invokes current LLaMA / Oanda / Adapter logic.
        Valid implementation would bridge into `src/ict_agent`.
        For now, this is a placeholder stub to allow architectural validation.
        """
        # TODO: Integrate with src.ict_agent.core.inference or similar
        # from src.ict_agent import ...
        
        # Placeholder mock response
        return f"Mock response for: {question} (Logic not connected yet)"

    def calculate_metrics(self, model_output: str, gold_answer: str) -> Dict[str, float]:
        """
        Compares outputs against Keyword Presence metric + cosine similarity score against gold_answers.
        """
        metrics = {
            "keyword_presence": 0.0,
            "cosine_similarity": 0.0
        }

        # 1. Keyword Presence (Simple implementation)
        # Tokenize gold answer and check presence in model output
        gold_tokens = set(gold_answer.lower().split())
        output_lower = model_output.lower()
        if gold_tokens:
            present_count = sum(1 for token in gold_tokens if token in output_lower)
            metrics["keyword_presence"] = (present_count / len(gold_tokens)) * 100.0

        # 2. Cosine Similarity
        if HAS_SENTENCE_TRANSFORMERS and np is not None:
             self.load_embedding_model()
             # Logic to encode and compare:
             # embeddings = self.embedding_model.encode([model_output, gold_answer])
             # metrics["cosine_similarity"] = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0] * 100.0
             pass
        else:
             # Fallback or stub
             metrics["cosine_similarity"] = 0.0

        return metrics

    def run_evaluation(self):
        """
        Main execution loop.
        """
        qa_data = self.load_qa_data()
        if not qa_data:
            return

        run_timestamp = datetime.now().isoformat()
        category_metrics = {}
        
        logger.info("Starting Evaluation Run...")

        for item in qa_data:
            category = item.get("category", "Unknown")
            question = item.get("question", "")
            # Assuming 'options' and 'correct_answer' or 'explanation' constitutes the gold answer
            gold_answer = item.get("explanation", "")
            if not gold_answer:
                 # fallback to correct option text if explanation missing
                 correct_opt_key = item.get("correct_answer")
                 if correct_opt_key and "options" in item:
                     gold_answer = item["options"].get(correct_opt_key, "")

            # Invoke Logic
            model_output = self.invoke_logic(question)

            # Calculate metrics
            metrics = self.calculate_metrics(model_output, gold_answer)

            # Aggregate per category
            if category not in category_metrics:
                category_metrics[category] = {"count": 0, "keyword_sum": 0.0, "cosine_sum": 0.0}
            
            category_metrics[category]["count"] += 1
            category_metrics[category]["keyword_sum"] += metrics["keyword_presence"]
            category_metrics[category]["cosine_sum"] += metrics["cosine_similarity"]

        # Calculate final category accuracy
        final_results = {}
        print("\n--- Evaluation Results ---")
        for category, data in category_metrics.items():
            count = data["count"]
            if count > 0:
                avg_keyword = data["keyword_sum"] / count
                avg_cosine = data["cosine_sum"] / count
                # Setup a blended score or report both
                final_results[category] = {
                    "avg_keyword_presence": avg_keyword,
                    "avg_cosine_similarity": avg_cosine,
                    "samples": count
                }
                print(f"Category: {category} | Keyword: {avg_keyword:.1f}% | Cosine: {avg_cosine:.1f}% | Samples: {count}")
        
        self.save_results(run_timestamp, final_results)

    def save_results(self, timestamp: str, results: Dict[str, Dict[str, float]]):
        """
        Save runs metadata in .CSV summary rows.
        It should handle history over time too.
        """
        file_exists = self.output_csv_path.exists()
        
        # Flatten results for CSV
        rows = []
        for category, metrics in results.items():
            row = {
                "timestamp": timestamp,
                "category": category,
                "keyword_accuracy": f"{metrics['avg_keyword_presence']:.2f}",
                "cosine_similarity": f"{metrics['avg_cosine_similarity']:.2f}",
                "samples": metrics['samples']
            }
            rows.append(row)

        if not rows:
            logger.warning("No results to save.")
            return

        fieldnames = ["timestamp", "category", "keyword_accuracy", "cosine_similarity", "samples"]
        
        try:
            with open(self.output_csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Results saved to {self.output_csv_path}")
        except Exception as e:
            logger.error(f"Failed to save CSV results: {e}")

if __name__ == "__main__":
    harness = EvaluationSystem()
    harness.run_evaluation()
