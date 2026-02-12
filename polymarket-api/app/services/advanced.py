# Advanced Features Service
"""
Advanced trading features: trading limits, price history, alerts, etc.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.config import settings
from app.database import get_trades_collection, get_positions_collection
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradeLimit:
    """Trading limit configuration"""
    max_trade_usd: float = 100.0  # Maximum USD per trade
    max_daily_usd: float = 500.0  # Maximum USD per day
    max_position_usd: Optional[float] = None  # Maximum position size
    max_daily_trades: Optional[int] = None  # Maximum trades per day


@dataclass
class DailyStats:
    """Daily trading statistics"""
    date: str
    total_trades: int = 0
    total_volume_usd: float = 0.0
    buy_volume_usd: float = 0.0
    sell_volume_usd: float = 0.0
    realized_pnl: float = 0.0
    trade_ids: List[str] = field(default_factory=list)


class TradingLimitsService:
    """Service for managing trading limits and restrictions"""
    
    def __init__(self, limits: Optional[TradeLimit] = None):
        self.limits = limits or TradeLimit()
        self._today_stats: Optional[DailyStats] = None
    
    def get_daily_stats(self, reload: bool = False) -> DailyStats:
        """Get today's trading statistics"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        if self._today_stats and not reload:
            if self._today_stats.date == today:
                return self._today_stats
        
        # Fetch from database
        trades_collection = get_trades_collection()
        
        start_of_day = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_of_day}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_trades": {"$sum": 1},
                    "total_volume": {"$sum": "$amount"},
                    "buy_volume": {
                        "$sum": {
                            "$cond": [{"$eq": ["$side", "BUY"]}, "$amount", 0]
                        }
                    },
                    "sell_volume": {
                        "$sum": {
                            "$cond": [{"$eq": ["$side", "SELL"]}, "$amount", 0]
                        }
                    },
                    "realized_pnl": {"$sum": "$realized_pnl"}
                }
            }
        ]
        
        try:
            result = list(trades_collection.aggregate(pipeline))
            if result:
                stats = DailyStats(
                    date=today,
                    total_trades=result[0]["total_trades"],
                    total_volume_usd=result[0]["total_volume"],
                    buy_volume_usd=result[0]["buy_volume"],
                    sell_volume_usd=result[0]["sell_volume"],
                    realized_pnl=result[0]["realized_pnl"]
                )
            else:
                stats = DailyStats(date=today)
        except Exception as e:
            logger.error(f"Error fetching daily stats: {e}")
            stats = DailyStats(date=today)
        
        self._today_stats = stats
        return stats
    
    def can_trade(self, amount_usd: float, side: str = "BUY") -> tuple[bool, str]:
        """
        Check if a trade is allowed based on limits.
        
        Returns:
            (allowed, reason)
        """
        stats = self.get_daily_stats()
        
        # Check trade amount limit
        if amount_usd > self.limits.max_trade_usd:
            return False, f"Trade amount ${amount_usd:.2f} exceeds limit of ${self.limits.max_trade_usd:.2f}"
        
        # Check daily volume limit
        if stats.total_volume_usd + amount_usd > self.limits.max_daily_usd:
            remaining = self.limits.max_daily_usd - stats.total_volume_usd
            return False, f"Daily limit exceeded. Remaining: ${remaining:.2f}"
        
        # Check daily trade count limit
        if self.limits.max_daily_trades and stats.total_trades >= self.limits.max_daily_trades:
            return False, f"Daily trade limit reached: {self.limits.max_daily_trades} trades"
        
        return True, "Trade allowed"
    
    def record_trade(self, trade_data: dict) -> None:
        """Record a trade for statistics"""
        trades_collection = get_trades_collection()
        try:
            trades_collection.insert_one({
                **trade_data,
                "recorded_at": datetime.utcnow()
            })
            # Invalidate cache
            self._today_stats = None
            logger.info(f"Trade recorded: {trade_data.get('transaction_hash', 'unknown')}")
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def check_position_limit(self, current_value: float, additional_amount: float = 0) -> tuple[bool, str]:
        """Check if a position would exceed limits"""
        if self.limits.max_position_usd:
            if current_value + additional_amount > self.limits.max_position_usd:
                return False, f"Position size ${current_value + additional_amount:.2f} exceeds limit of ${self.limits.max_position_usd:.2f}"
        return True, "Position allowed"
    
    def get_remaining_limits(self) -> dict:
        """Get remaining trading limits"""
        stats = self.get_daily_stats()
        return {
            "date": stats.date,
            "max_trade_usd": self.limits.max_trade_usd,
            "max_daily_usd": self.limits.max_daily_usd,
            "daily_volume_used": stats.total_volume_usd,
            "daily_volume_remaining": max(0, self.limits.max_daily_usd - stats.total_volume_usd),
            "daily_trades_used": stats.total_trades,
            "daily_trades_limit": self.limits.max_daily_trades or "unlimited",
            "position_limit_usd": self.limits.max_position_usd or "unlimited",
        }


class PriceHistoryService:
    """Service for getting and analyzing price history"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # seconds
    
    async def get_price_history(
        self,
        token_id: str,
        hours: int = 24,
        interval_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a token.
        
        Args:
            token_id: Market token ID
            hours: How many hours of history
            interval_minutes: Data point interval
            
        Returns:
            List of price points with timestamp, price_yes, price_no
        """
        cache_key = f"{token_id}_{hours}_{interval_minutes}"
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        try:
            # Try to get from Polymarket API
            import httpx
            async with httpx.AsyncClient() as client:
                url = f"https://gamma-api.polymarket.com/market/{token_id}/history"
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    self.cache[cache_key] = (time.time(), data)
                    return data
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
        
        # Fallback: generate simulated data based on orderbook
        try:
            from app.clients.polymarket import polymarket_client
            orderbook = await polymarket_client.get_order_book(token_id)
            
            if orderbook:
                # Calculate midpoint
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                
                if bids and asks:
                    best_bid = max(float(b["price"]) for b in bids)
                    best_ask = min(float(a["price"]) for a in asks)
                    mid_price = (best_bid + best_ask) / 2
                    
                    # Generate synthetic history (simplified)
                    data = []
                    base_time = datetime.utcnow()
                    points = (hours * 60) // interval_minutes
                    
                    for i in range(points):
                        # Add small random variation
                        variation = (hash(str(i) + token_id) % 100) / 10000
                        price = max(0.01, min(0.99, mid_price + variation))
                        
                        data.append({
                            "timestamp": (base_time - timedelta(minutes=i * interval_minutes)).isoformat(),
                            "price_yes": price,
                            "price_no": 1.0 - price
                        })
                    
                    data.reverse()
                    return data
        except Exception as e:
            logger.error(f"Error generating price history: {e}")
        
        return []
    
    def analyze_trend(
        self,
        price_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze price trend from history"""
        if not price_history or len(price_history) < 2:
            return {
                "trend": "unknown",
                "change": 0.0,
                "change_percent": 0.0,
                "volatility": 0.0,
                "direction": "neutral"
            }
        
        prices = [p.get("price_yes", 0.5) for p in price_history]
        
        start_price = prices[0]
        end_price = prices[-1]
        change = end_price - start_price
        change_percent = (change / start_price * 100) if start_price > 0 else 0
        
        # Calculate volatility (standard deviation)
        import statistics
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # Determine direction
        if change_percent > 1:
            direction = "up"
        elif change_percent < -1:
            direction = "down"
        else:
            direction = "neutral"
        
        return {
            "trend": "bullish" if change > 0 else "bearish",
            "change": change,
            "change_percent": change_percent,
            "volatility": volatility,
            "direction": direction,
            "start_price": start_price,
            "end_price": end_price
        }


class MarketContextService:
    """Service for getting market context and safeguards"""
    
    def __init__(self):
        self.price_history_service = PriceHistoryService()
    
    async def get_market_context(
        self,
        token_id: str,
        user_position: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get market context with trading safeguards.
        
        Returns:
            Dict with:
            - market: Market details
            - position: Current user position
            - discipline: Trading discipline info
            - slippage: Estimated execution costs
            - warnings: List of warnings
        """
        context = {
            "market": {},
            "position": user_position or {},
            "discipline": {},
            "slippage": {},
            "warnings": [],
        }
        
        try:
            # Get market data
            from app.clients.gamma import gamma_client
            market_data = await gamma_client.get_market_by_token_id(token_id)
            
            if market_data:
                context["market"] = {
                    "question": market_data.question if hasattr(market_data, 'question') else market_data.get("question", ""),
                    "active": market_data.active if hasattr(market_data, 'active') else True,
                    "end_date": market_data.end_date if hasattr(market_data, 'end_date') else None,
                }
                
                # Check if market is about to close
                if hasattr(market_data, 'end_date') and market_data.end_date:
                    end_date = market_data.end_date
                    if isinstance(end_date, str):
                        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        hours_left = (end_dt - datetime.utcnow()).total_seconds() / 3600
                        if hours_left < 2:
                            context["warnings"].append(
                                f"Market resolves in {hours_left:.1f} hours"
                            )
        
        except Exception as e:
            logger.error(f"Error fetching market context: {e}")
        
        # Get orderbook for slippage estimate
        try:
            from app.clients.polymarket import polymarket_client
            orderbook = await polymarket_client.get_order_book(token_id)
            
            if orderbook:
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                
                if bids and asks:
                    best_bid = max(float(b["price"]) for b in bids)
                    best_ask = min(float(a["price"]) for a in asks)
                    spread = best_ask - best_bid
                    mid_price = (best_bid + best_ask) / 2
                    
                    # Estimate slippage
                    context["slippage"] = {
                        "spread": spread,
                        "spread_percent": (spread / mid_price * 100) if mid_price > 0 else 0,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "mid_price": mid_price,
                        "liquidity_rating": "high" if spread < 0.02 else "medium" if spread < 0.05 else "low"
                    }
        
        except Exception as e:
            logger.error(f"Error calculating slippage: {e}")
        
        # Get price history for trend
        try:
            history = await self.price_history_service.get_price_history(token_id, hours=24)
            trend = self.price_history_service.analyze_trend(history)
            context["trend"] = trend
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
        
        # Discipline checks
        if user_position:
            context["discipline"] = {
                "has_position": True,
                "current_exposure": user_position.get("current_value", 0),
            }
        else:
            context["discipline"] = {
                "has_position": False,
                "current_exposure": 0,
            }
        
        return context


class PriceAlertService:
    """Service for managing price alerts"""
    
    def __init__(self):
        self.active_alerts: Dict[str, List[Dict]] = {}
    
    def create_alert(
        self,
        token_id: str,
        side: str,  # "yes" or "no"
        condition: str,  # "above", "below", "crosses_above", "crosses_below"
        threshold: float,
        alert_id: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a price alert"""
        alert = {
            "alert_id": alert_id or f"alert_{int(time.time())}",
            "token_id": token_id,
            "side": side,
            "condition": condition,
            "threshold": threshold,
            "webhook_url": webhook_url,
            "active": True,
            "triggered": False,
            "triggered_at": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if token_id not in self.active_alerts:
            self.active_alerts[token_id] = []
        
        self.active_alerts[token_id].append(alert)
        logger.info(f"Alert created: {alert['alert_id']}")
        
        return alert
    
    def get_alerts(self, include_triggered: bool = False) -> List[Dict[str, Any]]:
        """Get all alerts"""
        alerts = []
        for token_alerts in self.active_alerts.values():
            alerts.extend(token_alerts)
        
        if not include_triggered:
            alerts = [a for a in alerts if not a.get("triggered", False)]
        
        return alerts
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        for token_id, alerts in self.active_alerts.items():
            for i, alert in enumerate(alerts):
                if alert.get("alert_id") == alert_id:
                    alerts.pop(i)
                    logger.info(f"Alert deleted: {alert_id}")
                    return True
        return False
    
    async def check_alerts(self, current_price: float, token_id: str) -> List[Dict[str, Any]]:
        """Check if any alerts should trigger"""
        triggered = []
        
        if token_id not in self.active_alerts:
            return triggered
        
        for alert in self.active_alerts[token_id]:
            if alert.get("triggered", False) or not alert.get("active", False):
                continue
            
            should_trigger = False
            
            if alert["condition"] == "above" and current_price >= alert["threshold"]:
                should_trigger = True
            elif alert["condition"] == "below" and current_price <= alert["threshold"]:
                should_trigger = True
            # crosses_above and crosses_below require previous price tracking
            
            if should_trigger:
                alert["triggered"] = True
                alert["triggered_at"] = datetime.utcnow().isoformat()
                alert["trigger_price"] = current_price
                triggered.append(alert.copy())
                
                # Fire webhook if configured
                if alert.get("webhook_url"):
                    try:
                        import httpx
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                alert["webhook_url"],
                                json={
                                    "alert_id": alert["alert_id"],
                                    "token_id": token_id,
                                    "side": alert["side"],
                                    "condition": alert["condition"],
                                    "threshold": alert["threshold"],
                                    "triggered_price": current_price,
                                    "triggered_at": alert["triggered_at"],
                                },
                                timeout=5.0
                            )
                    except Exception as e:
                        logger.error(f"Error firing alert webhook: {e}")
        
        return triggered


# Singleton instances
trading_limits_service = TradingLimitsService()
price_history_service = PriceHistoryService()
market_context_service = MarketContextService()
price_alert_service = PriceAlertService()
