"""
VEX AI Chart Analyzer - LLM-powered chart analysis.

Uses Claude/GPT to analyze chart screenshots and provide:
- ICT concept identification (FVG, OB, BOS, etc.)
- Market structure analysis
- Trade recommendations
- Setup grading
"""

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class ChartAnalyzer:
    """
    AI-powered chart analysis using vision LLMs.
    
    Supports:
    - Claude (Anthropic) - PRIMARY
    - GPT-4 Vision (OpenAI) - FALLBACK
    """
    
    ICT_ANALYSIS_PROMPT = """You are VEX, an expert ICT (Inner Circle Trader) analyst. Analyze this forex chart and provide a detailed breakdown.

IDENTIFY AND MARK:
1. **Market Structure**
   - Current trend (bullish/bearish/ranging)
   - Recent BOS (Break of Structure) points
   - CHOCH (Change of Character) if any
   - Key swing highs and lows

2. **PD Arrays (Premium/Discount Arrays)**
   - Fair Value Gaps (FVG) - mark bullish (BISI) and bearish (SIBI)
   - Order Blocks (OB) - identify last down-close candle before up-move (bullish) or vice versa
   - Breaker Blocks if present
   - Mitigation blocks

3. **Liquidity**
   - Equal highs (buy-side liquidity)
   - Equal lows (sell-side liquidity)
   - Recent liquidity sweeps
   - Inducement levels

4. **Key Levels**
   - Recent highs/lows
   - Session highs/lows if visible
   - Round numbers (psychological levels)

5. **Time Context** (if visible)
   - What session this appears to be
   - CBDR range if applicable
   - Asian range if applicable

PROVIDE:
- **Bias**: BULLISH / BEARISH / NEUTRAL with confidence (1-10)
- **Setup Quality**: A+ / A / B+ / B / C / D / F
- **Trade Idea**: If there's a valid setup, describe entry, stop, target
- **Key Levels**: List specific prices for important levels
- **Warnings**: Any reasons NOT to trade

Format your response as JSON:
{
  "pair": "detected or unknown",
  "timeframe": "detected or unknown",
  "bias": "BULLISH/BEARISH/NEUTRAL",
  "bias_confidence": 1-10,
  "market_structure": {
    "trend": "bullish/bearish/ranging",
    "last_bos": "description",
    "choch": "description or null"
  },
  "pd_arrays": {
    "fvgs": ["list of FVGs with approximate locations"],
    "order_blocks": ["list of OBs"],
    "breakers": ["list if any"]
  },
  "liquidity": {
    "buyside": ["equal highs, targets above"],
    "sellside": ["equal lows, targets below"],
    "recent_sweeps": ["description"]
  },
  "key_levels": {
    "resistance": [price1, price2],
    "support": [price1, price2],
    "equilibrium": price
  },
  "trade_idea": {
    "direction": "LONG/SHORT/NONE",
    "entry_zone": "description",
    "entry_price": price or null,
    "stop_loss": price or null,
    "take_profit": [tp1, tp2],
    "rr_ratio": number,
    "reasoning": "why this trade"
  },
  "setup_grade": "A+/A/B+/B/C/D/F",
  "warnings": ["any concerns"],
  "summary": "2-3 sentence summary of the chart"
}
"""

    def __init__(self):
        """Initialize the chart analyzer."""
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        # Determine which API to use
        if self.anthropic_key:
            self.provider = "anthropic"
        elif self.openai_key:
            self.provider = "openai"
        else:
            self.provider = None
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
    
    def _get_media_type(self, image_path: str) -> str:
        """Get media type from file extension."""
        ext = Path(image_path).suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }.get(ext, "image/png")
    
    def analyze_with_claude(self, image_path: str, custom_prompt: str = None) -> Dict:
        """Analyze chart using Claude Vision."""
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        image_data = self._encode_image(image_path)
        media_type = self._get_media_type(image_path)
        prompt = custom_prompt or self.ICT_ANALYSIS_PROMPT
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result["content"][0]["text"]
        
        # Try to parse JSON from response
        try:
            # Find JSON in response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_analysis": content, "parse_error": True}
    
    def analyze_with_openai(self, image_path: str, custom_prompt: str = None) -> Dict:
        """Analyze chart using GPT-4 Vision."""
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        image_data = self._encode_image(image_path)
        media_type = self._get_media_type(image_path)
        prompt = custom_prompt or self.ICT_ANALYSIS_PROMPT
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ]
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Try to parse JSON from response
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_analysis": content, "parse_error": True}
    
    def analyze(self, image_path: str, custom_prompt: str = None) -> Dict:
        """
        Analyze a chart image using available LLM.
        
        Args:
            image_path: Path to chart screenshot
            custom_prompt: Optional custom analysis prompt
            
        Returns:
            Analysis results as dictionary
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if self.provider == "anthropic":
            return self.analyze_with_claude(image_path, custom_prompt)
        elif self.provider == "openai":
            return self.analyze_with_openai(image_path, custom_prompt)
        else:
            raise ValueError(
                "No AI API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY"
            )
    
    def format_analysis(self, analysis: Dict) -> str:
        """Format analysis results for CLI display."""
        lines = []
        
        if analysis.get("parse_error"):
            lines.append("\n" + "=" * 60)
            lines.append("  AI CHART ANALYSIS (Raw)")
            lines.append("=" * 60)
            lines.append(analysis.get("raw_analysis", "No analysis"))
            return "\n".join(lines)
        
        lines.append("\n" + "═" * 60)
        lines.append("  🤖 AI CHART ANALYSIS")
        lines.append("═" * 60)
        
        # Basic Info
        pair = analysis.get("pair", "Unknown")
        tf = analysis.get("timeframe", "Unknown")
        bias = analysis.get("bias", "Unknown")
        confidence = analysis.get("bias_confidence", "?")
        grade = analysis.get("setup_grade", "?")
        
        lines.append(f"\n  📊 {pair} | {tf}")
        lines.append(f"  📈 Bias: {bias} (Confidence: {confidence}/10)")
        lines.append(f"  ⭐ Setup Grade: {grade}")
        
        # Market Structure
        ms = analysis.get("market_structure", {})
        if ms:
            lines.append(f"\n  📐 MARKET STRUCTURE")
            lines.append(f"     Trend: {ms.get('trend', 'Unknown')}")
            if ms.get("last_bos"):
                lines.append(f"     Last BOS: {ms['last_bos']}")
            if ms.get("choch"):
                lines.append(f"     CHOCH: {ms['choch']}")
        
        # PD Arrays
        pd = analysis.get("pd_arrays", {})
        if pd:
            lines.append(f"\n  🎯 PD ARRAYS")
            if pd.get("fvgs"):
                lines.append(f"     FVGs: {', '.join(pd['fvgs'][:3])}")
            if pd.get("order_blocks"):
                lines.append(f"     OBs: {', '.join(pd['order_blocks'][:3])}")
        
        # Liquidity
        liq = analysis.get("liquidity", {})
        if liq:
            lines.append(f"\n  💧 LIQUIDITY")
            if liq.get("buyside"):
                lines.append(f"     Buy-side: {', '.join(str(x) for x in liq['buyside'][:3])}")
            if liq.get("sellside"):
                lines.append(f"     Sell-side: {', '.join(str(x) for x in liq['sellside'][:3])}")
            if liq.get("recent_sweeps"):
                lines.append(f"     Recent Sweeps: {', '.join(liq['recent_sweeps'][:2])}")
        
        # Key Levels
        levels = analysis.get("key_levels", {})
        if levels:
            lines.append(f"\n  📍 KEY LEVELS")
            if levels.get("resistance"):
                lines.append(f"     Resistance: {', '.join(str(x) for x in levels['resistance'][:3])}")
            if levels.get("support"):
                lines.append(f"     Support: {', '.join(str(x) for x in levels['support'][:3])}")
            if levels.get("equilibrium"):
                lines.append(f"     Equilibrium: {levels['equilibrium']}")
        
        # Trade Idea
        trade = analysis.get("trade_idea", {})
        if trade and trade.get("direction") != "NONE":
            lines.append(f"\n  💡 TRADE IDEA")
            lines.append(f"     Direction: {trade.get('direction', '?')}")
            if trade.get("entry_zone"):
                lines.append(f"     Entry Zone: {trade['entry_zone']}")
            if trade.get("entry_price"):
                lines.append(f"     Entry: {trade['entry_price']}")
            if trade.get("stop_loss"):
                lines.append(f"     Stop: {trade['stop_loss']}")
            if trade.get("take_profit"):
                lines.append(f"     Targets: {', '.join(str(x) for x in trade['take_profit'])}")
            if trade.get("rr_ratio"):
                lines.append(f"     R:R: {trade['rr_ratio']}:1")
            if trade.get("reasoning"):
                lines.append(f"     Reasoning: {trade['reasoning']}")
        
        # Warnings
        warnings = analysis.get("warnings", [])
        if warnings:
            lines.append(f"\n  ⚠️  WARNINGS")
            for w in warnings:
                lines.append(f"     • {w}")
        
        # Summary
        if analysis.get("summary"):
            lines.append(f"\n  📝 SUMMARY")
            lines.append(f"     {analysis['summary']}")
        
        lines.append("\n" + "═" * 60)
        
        return "\n".join(lines)
    
    def analyze_and_print(self, image_path: str) -> Dict:
        """Analyze chart and print formatted results."""
        print(f"\n  🔍 Analyzing chart: {Path(image_path).name}...")
        
        try:
            analysis = self.analyze(image_path)
            print(self.format_analysis(analysis))
            return analysis
        except Exception as e:
            print(f"\n  ❌ Analysis failed: {e}")
            return {"error": str(e)}
    
    def quick_bias(self, image_path: str) -> Dict:
        """Quick analysis - just bias and key levels."""
        prompt = """Analyze this forex chart and provide a QUICK assessment.

Return JSON only:
{
  "bias": "BULLISH/BEARISH/NEUTRAL",
  "confidence": 1-10,
  "key_resistance": [price1, price2],
  "key_support": [price1, price2],
  "trade_now": true/false,
  "reason": "one sentence explanation"
}
"""
        return self.analyze(image_path, prompt)


def main():
    """CLI entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chart_analyzer.py <image_path>")
        print("\nExamples:")
        print("  python chart_analyzer.py screenshots/EURUSD_H4.png")
        print("  python chart_analyzer.py ~/Desktop/chart.png")
        return
    
    image_path = sys.argv[1]
    
    analyzer = ChartAnalyzer()
    analyzer.analyze_and_print(image_path)


if __name__ == "__main__":
    main()
