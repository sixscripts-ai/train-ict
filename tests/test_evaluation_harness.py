import unittest
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from experiments.evaluation_harness_v1 import EvaluationSystem

class TestEvaluationSystem(unittest.TestCase):
    def setUp(self):
        self.harness = EvaluationSystem()

    def test_initialization(self):
        """Test that the evaluation system initializes correctly."""
        self.assertIsInstance(self.harness, EvaluationSystem)
        # Check standard paths
        self.assertTrue(str(self.harness.qa_file_path).endswith("ict_concepts_qa.json"))

    def test_metrics_calculation_stub(self):
        """Test the basic metric calculation logic with dummy data."""
        gpt_output = "The answer is about market maker buy model and sell model."
        gold_answer = "Market Maker Buy Model targets sellside liquidity."
        
        metrics = self.harness.calculate_metrics(gpt_output, gold_answer)
        
        # Check keys exist
        self.assertIn("keyword_presence", metrics)
        self.assertIn("cosine_similarity", metrics)
        
        # Check value ranges
        self.assertGreaterEqual(metrics["keyword_presence"], 0.0)
        self.assertLessEqual(metrics["keyword_presence"], 100.0)

    def test_invoke_logic_stub(self):
        """Test the logic invoker returns a string (even if stubbed)."""
        response = self.harness.invoke_logic("Test Question")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

if __name__ == '__main__':
    unittest.main()
