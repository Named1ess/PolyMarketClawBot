# X Sentiment Skill - Build Context

## Overview

Real-time Twitter/X sentiment analysis for Polymarket trading. Alert when social sentiment diverges significantly from market odds — catch moves before prices adjust.

## Why This Skill

From user research:
> "Every 60 seconds per market: Scrapes 100 latest X tweets by keywords, Claude NLP → Bullish/Neutral/Bearish scores, Compares vs current odds, Alerts when divergence >20%. Example signal: 'Tesla robotaxi event' market: 62¢ YES, X sentiment: 82% bullish (vs 62% implied) → BUY signal @ +20% edge"

Social signals often lead price action — catch them early.

## Skill Pattern

**Trigger:** Periodic scan (cron) or real-time monitoring
**Input:** X/Twitter data for configured keywords
**Analysis:** NLP sentiment scoring
**Output:** Divergence alerts + optional trade execution

## Core Features

### 1. Tweet Collection
```python
# For each configured market/keyword:
tweets = fetch_tweets(
    query="tesla robotaxi",
    count=100,
    since="1h"
)
```

### 2. Sentiment Analysis
```python
def analyze_sentiment(tweets: list) -> dict:
    # Use Claude or simple NLP
    scores = [classify(tweet) for tweet in tweets]
    return {
        'bullish': count(scores, 'bullish') / len(scores),
        'bearish': count(scores, 'bearish') / len(scores),
        'neutral': count(scores, 'neutral') / len(scores),
        'sample_size': len(tweets),
        'confidence': calculate_confidence(scores)
    }
```

### 3. Divergence Detection
```python
def check_divergence(sentiment: dict, market_price: float) -> dict:
    implied_bullish = market_price  # YES price = implied probability
    actual_bullish = sentiment['bullish']
    
    divergence = actual_bullish - implied_bullish
    
    if abs(divergence) > 0.20:  # 20% threshold
        return {
            'signal': 'bullish' if divergence > 0 else 'bearish',
            'divergence': divergence,
            'market_price': implied_bullish,
            'sentiment': actual_bullish,
            'trade_direction': 'buy_yes' if divergence > 0 else 'buy_no'
        }
    return {'signal': None}
```

### 4. Alert/Trade
- Send alert via Telegram/Discord
- Optionally execute trade if confidence high enough

## X/Twitter Data Sources

### Option 1: X API (Official)
- Requires X Developer account
- Rate limits apply
- Most reliable

### Option 2: Nitter/RSS
- No API key needed
- Convert X searches to RSS
- Less reliable, may break

### Option 3: Web Scraping
- Browserless scraping
- Most fragile
- Use as fallback

### Option 4: Third-party APIs
- SocialBlade, Tweet Binder, etc.
- May have costs
- More stable than scraping

## File Structure

```
skills/xsentiment/
├── README.md (SKILL.md content)
├── SKILL.md
├── xsentiment.py            # Main script
├── sentiment.py             # NLP analysis module
├── twitter.py               # X data fetching module
├── scripts/
│   └── status.py
└── data/
    ├── config.json          # Market/keyword mappings
    └── sentiment_history.json
```

## CLI Interface

```bash
# Check sentiment for a keyword
python xsentiment.py --query "tesla robotaxi" --market "abc123"

# Scan all configured markets
python xsentiment.py --scan

# Continuous monitoring
python xsentiment.py --monitor --interval 60

# Dry run (alerts only, no trades)
python xsentiment.py --scan --dry-run

# Show sentiment history
python xsentiment.py --history

# Configure market/keyword mapping
python xsentiment.py --config add --market "abc123" --keywords "tesla,robotaxi,elon"
```

## Configuration

```json
{
  "markets": [
    {
      "market_id": "abc123",
      "name": "Tesla Robotaxi Launch 2025",
      "keywords": ["tesla robotaxi", "tesla autonomous", "elon fsd"],
      "min_divergence": 0.20,
      "trade_enabled": true,
      "max_trade_usd": 25
    }
  ],
  "settings": {
    "tweets_per_scan": 100,
    "scan_interval_seconds": 60,
    "sentiment_model": "claude",  // or "simple"
    "min_sample_size": 20
  }
}
```

## Sentiment Models

### Simple (No LLM)
```python
BULLISH_WORDS = ['moon', 'bullish', 'buy', 'pump', '🚀', '📈']
BEARISH_WORDS = ['dump', 'bearish', 'sell', 'crash', '📉', '💀']

def simple_sentiment(tweet):
    text = tweet.lower()
    bull_score = sum(1 for w in BULLISH_WORDS if w in text)
    bear_score = sum(1 for w in BEARISH_WORDS if w in text)
    if bull_score > bear_score: return 'bullish'
    if bear_score > bull_score: return 'bearish'
    return 'neutral'
```

### Claude (LLM)
```python
def claude_sentiment(tweets: list) -> dict:
    prompt = f"""
    Analyze these tweets about {topic}.
    Rate overall sentiment: bullish/bearish/neutral
    Confidence: 0.0-1.0
    
    Tweets:
    {tweets}
    """
    # Call Claude API
    return parse_response(response)
```

## Integration with Signal Sniper

X Sentiment complements Signal Sniper:
- Signal Sniper = news RSS (formal, slower)
- X Sentiment = social buzz (informal, faster)

Could coordinate:
```python
if signal_sniper.has_signal(market) and x_sentiment.bullish(market):
    confidence *= 1.2  # Reinforced signal
```

## Challenges

### 1. X API Access
- Official API is expensive/restricted
- May need alternative data sources
- Rate limits constrain real-time scanning

### 2. Bot/Spam Filtering
- Many X accounts are bots
- Need to filter quality signals
- Check account age, followers, engagement

### 3. Sentiment Accuracy
- Sarcasm detection is hard
- Context matters
- May need market-specific tuning

### 4. Timing
- Sentiment can be early OR late
- Need to distinguish leading vs lagging signals
- Track sentiment → price correlation over time

## Cron Suggestion

```yaml
metadata: {"clawdbot":{"emoji":"🐦","requires":{"env":["SIMMER_API_KEY"]},"cron":"*/10 * * * *"}}
```
Every 10 minutes — balance freshness vs API limits.

## Success Metrics

1. Sentiment accuracy vs actual outcomes
2. Divergence signals that lead price moves
3. P&L from sentiment-based trades
4. False positive rate

## Implementation Order

1. Simple keyword sentiment (no API)
2. Manual tweet input for testing
3. X API or Nitter integration
4. Divergence detection
5. Alert system
6. Trade execution
7. Claude sentiment analysis (upgrade)

## MVP Approach

Start simple:
1. User provides tweets manually or via RSS
2. Simple word-based sentiment
3. Compare to market price
4. Alert on divergence

Then iterate:
- Add X API when needed
- Upgrade to Claude sentiment
- Add trade execution

---

## Ready to Build

Start with `xsentiment.py`:
1. Simple sentiment function (word matching)
2. Divergence calculator
3. Manual tweet input mode
4. Alert output

Later: Add X API integration, Claude analysis

Reference: `/tmp/simmer-sdk/skills/signalsniper/signal_sniper.py` for RSS/alert pattern
