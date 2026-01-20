# ICT Knowledge Sources & Expansion Plan

## Official Resources
To expand your Inner Circle Trader (ICT) knowledge, always prioritize the source material from Michael J. Huddleston.

### 1. YouTube Channels (The Source)
* **The Inner Circle Trader** (Main Channel): [youtube.com/InnerCircleTrader](https://www.youtube.com/c/InnerCircleTrader)
  * **Must-Watch Playlists**:
    * **2022 ICT Mentorship**: The most modern, concise, and widely used model suitable for all asset classes (Indices, Forex, Futures).
    * **ICT Market Maker Primer Course**: Foundational understanding of how market makers operate.
    * **ICT Forex - Market Maker Series**: Advanced breakdown of the MMBM and MMSM models.
    * **Ends Series**: Specific series on "End of Day" or "End of Trends".
    * **Core Content (Months 1-12)**: *Note: Only available in re-uploads or specific archives as the original private mentorship is closed, but Michael often references these concepts in public videos.*

### 2. Social Media
* **Twitter (X)**: [@I_Am_The_ICT](https://twitter.com/I_Am_The_ICT)
  * **Why follow**: Michael posts real-time market commentary, "tape reading" examples, and marked-up charts. He often drops "gems" about specific daily bias validities here that aren't in videos.
  * **Action**: Turn on notifications during NY Session (9:30 AM - 11:00 AM EST) to see live calls.

### 3. Websites
* **The Inner Circle Trader (Official)**: [theinnercircletrader.com](https://theinnercircletrader.com/)
  * Often contains links to his private mentorship sign-ups (when open) or key announcements.

## Recommended Community Resources
While "The Source" is best, these community resources help digest the dense information:

* **ICT Charter (Twitter/YouTube)**: Often provides summarized, clean diagrams of complex models.
* **TTrades (YouTube)**: Excellent for visualizing concepts like "Daily Bias" and "Market Structure".
* **Casper SMC (YouTube)**: Good breakdowns of Silver Bullet and 2022 models.
* **ICT Indexes (YouTube)**: Focuses specifically on NQ/ES execution of ICT concepts.

## Structured Learning Path (The "Curriculum")

If you want to systematically increase your knowledge base, follow this order:

### Phase 1: The Foundation (Speed Run)
1. **2022 Mentorship (Episodes 1-41)**
   * *Focus*: Liquidity Sweeps, MSS, Displacement, FVG.
   * *Goal*: Learn to take one specific trade setup repeatedly.
2. **Market Structure & Order Flow**
   * *Focus*: Swing points, internal vs external structure.

### Phase 2: The Deep Dive (Core Concepts)
1. **PD Arrows & Matrix**: Learn Premium/Discount arrays deeply.
   * *Missing from your DB*: Inversion FVGs, Balanced Price Ranges (BPR), Volume Imbalances.
2. **Time & Price**: detailed study of "Macro" times.
   * *Focus*: 20-minute windows where algorithms run specific delivery macros.

### Phase 3: Mastery (Algorithmic Theory)
1. **Market Maker Models**: MMBM and MMSM specifics.
   * *Focus*: The "Curve" (Buy-side curve vs Sell-side curve).
2. **Intermarket Analysis (SMT)**: Using DXY, Yields, and other correlated assets to confirm trade entries.

## How to "Ingest" this into your Agent
To make *me* (Antigravity) smarter about these topics:

1. **Transcripts**: Download YouTube transcripts of key episodes (e.g., using a tool like generic web scrapers or YouTube transcript APIs).
2. **Summarization**: Feed the transcripts to this agent to "extract patterns and potential rules".
3. **Chart Markups**: Take screenshots of valid setups, name them `setup_YYYY-MM-DD_pair_session.png`, and place them in `knowledge_base/resources/charts/`.
4. **Backtesting Logs**: Create a JSON log of trades taken with these concepts. I can analyze them to find *your* edge.

## Code & Automation Resources
For the "Villain" who likes to automate:

1. **GitHub Repositories**:
   * Search for `smart-money-concepts` or `ICT-trading-indicators` on GitHub.
   * key libraries often include detectors for: `fvg`, `order_blocks`, `swing_points`.

2. **Python Libraries**:
   * `pandas`: For handling price data.
   * `technical`: (from Freqtrade) often has indicators.
   * Custom implementations: You can feed me (Antigravity) logic to write custom detectors in `src/analysis/ict_detectors.py`.
