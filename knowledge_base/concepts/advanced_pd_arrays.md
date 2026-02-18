# Advanced PD Arrays

Advanced PD Arrays are nuanced institutional reference points that follow specific rules when standard PD arrays fail or are insufficient. They offer high-precision entries and are critical for understanding price delivery in complex market conditions.

## Volume Imbalance (VI)
**Definition:** A specific type of gap where the bodies of two consecutive candles do not overlap, even though their wicks might. 
- **Identification:** Look for a gap between the *close* of candle 1 and the *open* of candle 2 (or vice versa). The wicks may overlap, filling the price range, but the *bodies* leave a gap.
- **Significance:** It indicates a subtle inefficiency in price delivery. Algorithms often treat the gap between the bodies as a void that needs to be filled or respected as support/resistance.
- **Trading Application:** Price often returns to the origin of the Volume Imbalance to re-spool or find support before continuing.

## Rejection Block
**Definition:** A price candle with a long wick that has swept a level of liquidity (Buy-Side or Sell-Side).
- **Identification:**
    - **Bearish:** A candle with a long wick *above* the body that took out a previous high. The block is defined from the *highest body open/close* to the *high of the wick*.
    - **Bullish:** A candle with a long wick *below* the body that took out a previous low. The block is defined from the *lowest body open/close* to the *low of the wick*.
- **Significance:** Represents institutional rejection of higher/lower prices.
- **Trading Application:** Traders look for entries or distribution inside the wick range, rather than waiting for the body of the Order Block.

## Propulsion Block
**Definition:** An Order Block that forms *after* a previous Order Block, acting as a continuation array.
- **Identification:** A candle that acts as an Order Block (down-close before up-move) which re-tests a prior Order Block and then propels price higher.
- **Significance:** It is a highly sensitive "second stage" rocket. If price closes below the Propulsion Block, the immediate bullish trend is likely over (unlike a standard OB which has more wiggle room).
- **Trading Application:** Used for pyramiding positions or entering strong trends. It should not be violated.

## Suspension Block
**Definition:** A specific type of Order Block that fails to drive price to a new high/low immediately but holds price in a consolidation before the true move. (Note: This is a nuanced/rare concept often conflated with consolidation blocks). 
- **Trading Application:** Acts as a holding level.

## Vacuum Block
**Definition:** A gap in price caused by an event (like a weekend gap or news event) where *no* trading occurred (literally no data).
- **Significance:** Often acts as a magnet to be filled completely.
