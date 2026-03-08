"""
ChatService — Omni-Intelligence Bot backend.

Provides:
  - 8 callable intelligence tools (schema + handlers)
  - stream_chat() async generator that drives an LLM agent loop with
    multi-turn tool calling and SSE event emission

SSE event types:
  tool_start  {"name": str, "args": dict}
  tool_result {"name": str, "viz": {"type": str, "data": any}, "sources": list[str]}
  text_delta  {"delta": str}
  done        {"confidence": float | None, "sources": list[str], "message_id": str}
  error       {"message": str}
"""

from __future__ import annotations

import json
import logging
import asyncio
import uuid
from datetime import date, timedelta, datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, or_, cast, Date as SqlDate

from intelligence_api.core.config import settings
from intelligence_api.domain.models import (
    Entity,
    ScrapedEvent,
    DailyTrend,
    EntityMention,
    EntityRelationship,
    ScrapeTarget,
    TickerMapping,
    ConversationSession,
    ConversationMessage,
)
from intelligence_api.infrastructure.ai_service import AIClient

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
#  Tool schemas (OpenAI function-calling format)
# ─────────────────────────────────────────────────────────

CHAT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_intelligence",
            "description": (
                "Perform a semantic search over the intelligence database using Pinecone. "
                "Returns the top matching articles/events with sentiment, category, "
                "source, and entity information. USE THIS for broad questions about "
                "recent events, news, or intelligence on any topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to embed and search.",
                    },
                    "entity_filter": {
                        "type": "string",
                        "description": "Optional entity label to restrict results to (e.g. 'Tesla').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_intelligence",
            "description": (
                "Retrieve a full intelligence profile for a tracked entity: "
                "sector, description, event count, latest sentiment, and relationship count. "
                "USE THIS when asking about a specific company or person."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity (e.g. 'Apple', 'Elon Musk').",
                    }
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sentiment_timeline",
            "description": (
                "Get the daily sentiment trend for an entity over the last N days. "
                "Returns a line chart dataset. USE THIS when asked about sentiment "
                "history, trends, or 'how is X performing over time'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Entity label to fetch sentiment for.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many days back to include (default 30).",
                        "default": 30,
                    },
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_graph",
            "description": (
                "Fetch the entity relationship graph (nodes + edges) from the knowledge "
                "store. Shows co-occurrence relationships between entities. USE THIS "
                "when asked about connections, relationships, or the knowledge graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Center the graph on this entity. If omitted, returns top relationships.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of edges to return (default 50).",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_correlation",
            "description": (
                "Compute the Pearson correlation between an entity's sentiment timeline "
                "and its stock price movement. Returns a dual-axis chart and a lag "
                "analysis. USE THIS when asked about market correlation, stock price "
                "impact, or sentiment-price relationship."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Company entity label to analyse (must be a public company).",
                    }
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_heatmap",
            "description": (
                "Get a sentiment heatmap aggregated by sector. Shows which industry "
                "sectors are trending positive or negative. USE THIS for market-wide "
                "overviews or sector comparisons."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "How many days back to aggregate (default 7).",
                        "default": 7,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_entities",
            "description": (
                "Search for tracked entities by name. Returns entity labels, types, "
                "sectors and descriptions. USE THIS to discover what entities are "
                "being tracked, or to find entities whose exact name is unknown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Partial name or keyword to search for.",
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["COMPANY", "PERSON", "TOPIC", "USER"],
                        "description": "Optional entity type filter.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_events",
            "description": (
                "Fetch the most recent scraped intelligence events from the database. "
                "Can be filtered by entity, category, or source. Returns article "
                "summaries with sentiment and source attribution. USE THIS when asked "
                "about recent news, latest events, or specific categories of intelligence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Filter by entity label.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by event category (e.g. 'Financial Move', 'Product Launch').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of events to return (default 10, max 20).",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_article",
            "description": (
                "Fetch and read the full text content of an article or web page by URL. "
                "USE THIS when the user asks for more details about a specific article, "
                "or when you have a URL from a previous search and the user wants to dive deeper."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full http/https URL of the article to read.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_entity_tracker",
            "description": (
                "Add a new entity to the Omnisight tracking system. Creates the entity record "
                "and sets up scrape targets so intelligence will be collected going forward. "
                "USE THIS when a user asks to track, monitor, or add an entity that does not "
                "yet exist in the database, or when get_entity_intelligence returns not-found."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Display name of the entity to track (e.g. 'Tesla', 'Elon Musk').",
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["COMPANY", "PERSON", "TOPIC"],
                        "description": "Type of entity. Defaults to COMPANY.",
                        "default": "COMPANY",
                    },
                    "sector": {
                        "type": "string",
                        "description": "Industry sector, e.g. 'Technology', 'Finance', 'Energy'. Optional.",
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["Google News", "Reddit Subreddit", "Nitter/X User"],
                        },
                        "description": "Data sources to scrape. Options: 'Google News', 'Reddit Subreddit', 'Nitter/X User'. Defaults to ['Google News', 'Reddit Subreddit'].",
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "How often to scrape in minutes. Defaults to 60.",
                        "default": 60,
                    },
                },
                "required": ["entity_name"],
            },
        },
    },
    # ── Category A: Comparison & Competitive Intelligence ────────────────────
    {
        "type": "function",
        "function": {
            "name": "compare_entities",
            "description": (
                "Compare two or three entities side-by-side: overlaid sentiment timelines, "
                "event volume per day, and category breakdown. "
                "USE THIS for competitive analysis, head-to-head comparisons, or 'who is doing better'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_a": {"type": "string", "description": "First entity label."},
                    "entity_b": {"type": "string", "description": "Second entity label."},
                    "entity_c": {"type": "string", "description": "Optional third entity label."},
                    "days": {"type": "integer", "description": "Lookback window in days (default 30).", "default": 30},
                },
                "required": ["entity_a", "entity_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cross_entity_events",
            "description": (
                "Find intelligence events where BOTH entities are mentioned together — "
                "surfaces partnerships, lawsuits, deals, or shared coverage. "
                "USE THIS when asked about interactions or shared news between two specific entities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_a": {"type": "string", "description": "First entity label."},
                    "entity_b": {"type": "string", "description": "Second entity label."},
                    "days": {"type": "integer", "description": "Lookback window in days (default 30).", "default": 30},
                    "limit": {"type": "integer", "description": "Max events to return (default 10).", "default": 10},
                },
                "required": ["entity_a", "entity_b"],
            },
        },
    },
    # ── Category B: Anomaly & Risk Detection ─────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "detect_sentiment_spike",
            "description": (
                "Detect statistically significant sentiment anomalies for an entity using Z-score analysis. "
                "Flags dates with unusual positive or negative sentiment swings and retrieves context events. "
                "USE THIS when asked about unusual activity, sudden sentiment changes, or anomalies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity to analyse."},
                    "days": {"type": "integer", "description": "Lookback window in days (default 60).", "default": 60},
                    "z_threshold": {"type": "number", "description": "Z-score threshold for spike detection (default 2.0).", "default": 2.0},
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_signals",
            "description": (
                "Scan ALL tracked entities for recent negative or high-risk intelligence: "
                "legal/regulatory events, sharp sentiment drops, and unusual activity. "
                "USE THIS for morning risk briefs, portfolio risk reviews, or 'anything I should be worried about'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Lookback window in days (default 7).", "default": 7},
                    "sentiment_threshold": {"type": "number", "description": "Flag events with sentiment below this value (default -0.3).", "default": -0.3},
                    "limit": {"type": "integer", "description": "Maximum risk signals to return (default 15).", "default": 15},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending_entities",
            "description": (
                "Rank all tracked entities by recent activity — which entities had the biggest increase "
                "in events (velocity) or sentiment shift this period vs the previous period. "
                "USE THIS for 'what's hot/trending', 'most active entities', or momentum checks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Window size to compare (e.g. 7 = this week vs last week). Default 7.", "default": 7},
                    "limit": {"type": "integer", "description": "Number of top entities to return (default 10).", "default": 10},
                    "metric": {
                        "type": "string",
                        "enum": ["velocity", "sentiment_shift", "event_count"],
                        "description": "Ranking metric. 'velocity' = event count delta, 'sentiment_shift' = sentiment delta, 'event_count' = raw count. Default 'velocity'.",
                        "default": "velocity",
                    },
                },
                "required": [],
            },
        },
    },
    # ── Category C: Tracker & Pipeline Management ────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_trackers",
            "description": (
                "List all active scrape targets with status, interval, last run time, and recent event counts. "
                "USE THIS when asked about active trackers, what is being monitored, or tracker configuration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status: 'all', 'active', 'paused', 'error'. Default 'all'.",
                        "default": "all",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_tracker_status",
            "description": (
                "Pause or resume a scrape tracker for an entity. "
                "IMPORTANT: Only call this AFTER the user has explicitly confirmed the action. "
                "USE THIS when user asks to pause, resume, enable, or disable tracking for an entity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity whose trackers to update."},
                    "action": {
                        "type": "string",
                        "enum": ["pause", "resume"],
                        "description": "'pause' to stop scraping, 'resume' to restart.",
                    },
                    "source_type": {
                        "type": "string",
                        "description": "Optional: only affect a specific source type (e.g. 'REDDIT'). Omit to affect all sources.",
                    },
                },
                "required": ["entity_name", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_entity_tracker",
            "description": (
                "Permanently deactivate all scrape trackers for an entity (historical events are preserved). "
                "IMPORTANT: Only call this AFTER the user has explicitly confirmed the removal by name. "
                "Ask: 'Are you sure you want to stop tracking [entity]? Historical data will be preserved.' "
                "USE THIS when user wants to stop monitoring an entity entirely."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity to stop tracking."},
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scrape_health",
            "description": (
                "Show the overall health of the scraping pipeline: overdue trackers, events ingested "
                "in the last 24h/7d, source type breakdown, and stuck jobs. "
                "USE THIS for platform health checks, diagnosing silent failures, or 'is the system collecting data?'."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Category D: Live / External Research ─────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Perform a live web search using DuckDuckGo. Returns titles, URLs, and snippets. "
                "USE THIS when the user asks about topics or entities not yet in the database, "
                "or for live/breaking news. Chain with fetch_url to read full articles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string."},
                    "max_results": {"type": "integer", "description": "Number of results to return (default 5, max 10).", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch and extract clean text from any URL — Wikipedia, SEC filings, company pages, news. "
                "More thorough than read_article (uses trafilatura for accurate extraction). "
                "USE THIS for deep-dive background research on any URL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http/https URL to fetch."},
                },
                "required": ["url"],
            },
        },
    },
    # ── Category E: Market & Financial Data ──────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": (
                "Get current stock market data for a company: live price, 52-week range, market cap, "
                "P/E ratio, volume, and 30-day price change. "
                "USE THIS for quick market snapshots or 'what is X trading at'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker_or_company": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g. 'AAPL') or company name (e.g. 'Apple').",
                    },
                },
                "required": ["ticker_or_company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_sentiment_vs_sector",
            "description": (
                "Compare an entity's daily sentiment against its sector aggregate average to see "
                "if it is an outlier or tracking the sector. "
                "USE THIS when asked how an entity compares to its industry, or whether a trend is company-specific vs sector-wide."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity to analyse."},
                    "days": {"type": "integer", "description": "Lookback window in days (default 30).", "default": 30},
                },
                "required": ["entity_name"],
            },
        },
    },
    # ── Category F: Deep Intelligence ────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "find_related_entities",
            "description": (
                "List the top entities most closely co-occurring with a given entity, "
                "ranked by co-occurrence count with average sentiment. "
                "USE THIS for conversational relationship queries like 'who is connected to X?', "
                "'what companies are mentioned with Y?', or network queries without needing a visual graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity to find connections for."},
                    "limit": {"type": "integer", "description": "Max related entities to return (default 10).", "default": 10},
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_entity_brief",
            "description": (
                "Generate a comprehensive AI-written intelligence brief for an entity covering: "
                "recent event themes, sentiment narrative, top risk signals, key relationships, "
                "and analyst recommendations. "
                "USE THIS when asked for a 'briefing', 'summary', 'report', or 'overview' of an entity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Entity to brief."},
                    "days": {"type": "integer", "description": "Intelligence window in days (default 30).", "default": 30},
                },
                "required": ["entity_name"],
            },
        },
    },
]

_TOOL_LABELS = {
    # Original tools
    "search_intelligence": "Searching intelligence database...",
    "get_entity_intelligence": "Loading entity profile...",
    "get_sentiment_timeline": "Fetching sentiment timeline...",
    "get_knowledge_graph": "Building knowledge graph...",
    "get_market_correlation": "Computing market correlation...",
    "get_sector_heatmap": "Aggregating sector heatmap...",
    "search_entities": "Searching tracked entities...",
    "get_recent_events": "Retrieving recent events...",
    "read_article": "Reading article content...",
    "add_entity_tracker": "Adding entity to tracker...",
    # Category A: Comparison
    "compare_entities": "Comparing entities side-by-side...",
    "get_cross_entity_events": "Finding cross-entity events...",
    # Category B: Anomaly & Risk
    "detect_sentiment_spike": "Running anomaly detection...",
    "get_risk_signals": "Scanning for risk signals...",
    "get_trending_entities": "Ranking trending entities...",
    # Category C: Tracker Management
    "list_trackers": "Listing scrape trackers...",
    "set_tracker_status": "Updating tracker status...",
    "remove_entity_tracker": "Removing entity tracker...",
    "get_scrape_health": "Checking pipeline health...",
    # Category D: Live Research
    "web_search": "Searching the web...",
    "fetch_url": "Fetching and extracting URL...",
    # Category E: Market & Financial
    "get_stock_info": "Fetching stock data...",
    "compare_sentiment_vs_sector": "Comparing entity vs sector sentiment...",
    # Category F: Deep Intelligence
    "find_related_entities": "Finding related entities...",
    "summarize_entity_brief": "Generating intelligence brief...",
}

_SYSTEM_PROMPT = """\
You are the Omni-Intelligence Bot for Omnisight v2.4 — a senior intelligence analyst \
with access to real-time scraped intelligence data, entity profiles, market correlation \
analysis, and a knowledge graph.

Current date: {today}
Tracked entities: {entity_list}

Operating instructions:
- Always use the available tools to retrieve live data before answering analytical questions.
- Be precise and concise. Use analyst terminology (bearish/bullish, signal strength, correlation, etc.).
- When you generate a chart or graph, briefly describe what it shows and the key takeaways.
- Cite sources and confidence levels when available.
- If get_entity_intelligence returns 'not found', FIRST call web_search to research the entity \
(e.g. "What is [entity]? company industry overview"). Use the search results to determine the entity type \
(COMPANY, PERSON, or TOPIC), its sector/industry, and provide a brief factual summary to the user. \
THEN offer to add it to the tracking system: \
"Would you like me to add **[entity]** to the tracking system? If so, which sources would you prefer?" \
Present the options as a short list: 1) Google News  2) Reddit Subreddit  3) Nitter/X User (pick any combination). \
Also ask: "How often should I check? (every 15 min / 30 min / 60 min / 3 hours / 12 hours / 24 hours)". \
Only call add_entity_tracker after the user explicitly confirms with their chosen sources and interval.
- For market questions, always attempt get_market_correlation before answering.
- You may call multiple tools in a single turn when the question requires it.
- For comparing two entities, use compare_entities. For events mentioning both together, use get_cross_entity_events.
- For anomaly/spike detection on a single entity, use detect_sentiment_spike. For a cross-portfolio risk scan, use get_risk_signals.
- For momentum/trending questions, use get_trending_entities. To compare an entity vs its sector, use compare_sentiment_vs_sector.
- For tracker management (list, pause, resume, remove, health), use list_trackers, set_tracker_status, remove_entity_tracker, or get_scrape_health. \
ALWAYS ask the user to confirm before calling set_tracker_status with action='pause' or remove_entity_tracker.
- For live web research on topics not yet in the database, use web_search followed by fetch_url for full content.
- For quick stock snapshots, use get_stock_info. For full sentiment-price correlation, use get_market_correlation.
- For conversational relationship queries ("who is connected to X?"), use find_related_entities (text list) rather than get_knowledge_graph (visual).
- For comprehensive entity briefings, use summarize_entity_brief — it synthesises profile, events, relationships, and anomalies into a structured analyst brief.
- When a tool returns a table, list, or articles viz type, ALWAYS present ALL rows in full — never summarise, truncate, or say "here is one example". \
The frontend renders the complete dataset; your role is to introduce the table briefly and highlight any notable rows, not to restate every row in prose.
- When list_trackers returns results, introduce them with a one-line count summary, then state that the full table is shown above. Do NOT restate each tracker as a bullet point.
"""


# ─────────────────────────────────────────────────────────
#  ChatService
# ─────────────────────────────────────────────────────────

class ChatService:
    def __init__(self, db: Session, user_id=None):
        self.db = db
        self.ai = AIClient()
        self.user_id = user_id  # uuid.UUID | None — None for unauthenticated/legacy

    # ── Tool handlers ──────────────────────────────────────

    def _tool_search_intelligence(
        self,
        query: str,
        entity_filter: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        from intelligence_api.infrastructure.ai_service import SemanticCache

        limit = min(int(limit), 10)
        try:
            ai = AIClient()
            embedding = ai.get_embedding(query)

            cache = SemanticCache()
            index = cache.index
            kwargs: Dict[str, Any] = {
                "vector": embedding,
                "top_k": limit,
                "include_metadata": True,
            }
            if entity_filter:
                kwargs["filter"] = {"entity_label": {"$eq": entity_filter}}

            results = index.query(**kwargs)
            items = []
            sources: List[str] = []
            for match in results.matches:
                meta = dict(match.metadata)
                source = meta.get("source_type") or meta.get("entity_label") or "Unknown"
                if source not in sources:
                    sources.append(source)
                items.append(
                    {
                        "entity": meta.get("entity_label", "Unknown"),
                        "summary": meta.get("summary", ""),
                        "sentiment": float(meta.get("sentiment", 0)),
                        "category": meta.get("category", ""),
                        "source": source,
                        "score": round(float(match.score), 3),
                    }
                )
            return {
                "viz": {"type": "articles", "data": items},
                "sources": sources,
                "count": len(items),
            }
        except Exception as e:
            logger.warning(f"search_intelligence error: {e}")
            return {"viz": {"type": "articles", "data": []}, "sources": [], "error": str(e)}

    def _tool_get_entity_intelligence(self, entity_name: str) -> Dict[str, Any]:
        entity = (
            self.db.query(Entity)
            .filter(Entity.label.ilike(f"%{entity_name}%"))
            .first()
        )
        if not entity:
            return {"error": f"Entity '{entity_name}' not found in tracked entities."}

        event_count = (
            self.db.query(sa_func.count(ScrapedEvent.id))
            .filter(ScrapedEvent.entity_id == entity.id)
            .scalar()
            or 0
        )
        latest_trend = (
            self.db.query(DailyTrend)
            .filter(DailyTrend.entity_id == entity.id)
            .order_by(DailyTrend.observation_date.desc())
            .first()
        )
        relationship_count = (
            self.db.query(sa_func.count(EntityRelationship.id))
            .filter(
                or_(
                    EntityRelationship.entity_a_name.ilike(f"%{entity.label}%"),
                    EntityRelationship.entity_b_name.ilike(f"%{entity.label}%"),
                )
            )
            .scalar()
            or 0
        )

        card = {
            "label": entity.label,
            "type": entity.type,
            "sector": entity.sector,
            "description": entity.description,
            "event_count": event_count,
            "relationship_count": relationship_count,
            "latest_sentiment": (
                float(latest_trend.avg_sentiment)
                if latest_trend and latest_trend.avg_sentiment
                else None
            ),
            "latest_trend_date": (
                latest_trend.observation_date.isoformat()
                if latest_trend
                else None
            ),
        }
        return {
            "viz": {"type": "entity_card", "data": card},
            "sources": [entity.label],
        }

    def _tool_get_sentiment_timeline(
        self, entity_name: str, days: int = 30
    ) -> Dict[str, Any]:
        entity = (
            self.db.query(Entity)
            .filter(Entity.label.ilike(f"%{entity_name}%"))
            .first()
        )
        if not entity:
            return {"error": f"Entity '{entity_name}' not found."}

        cutoff = date.today() - timedelta(days=int(days))
        rows = (
            self.db.query(DailyTrend)
            .filter(
                DailyTrend.entity_id == entity.id,
                DailyTrend.observation_date >= cutoff,
            )
            .order_by(DailyTrend.observation_date)
            .all()
        )
        data = [
            {
                "date": r.observation_date.isoformat(),
                "sentiment": float(r.avg_sentiment) if r.avg_sentiment else 0.0,
                "event_count": r.event_count or 0,
            }
            for r in rows
        ]
        return {
            "viz": {
                "type": "chart:line",
                "data": data,
                "config": {
                    "title": f"{entity.label} – Sentiment Timeline ({days}d)",
                    "xKey": "date",
                    "lines": [
                        {"key": "sentiment", "color": "#ec5b13", "name": "Avg Sentiment"},
                        {"key": "event_count", "color": "#f59e0b", "name": "Event Count", "yAxisId": "right"},
                    ],
                },
            },
            "sources": [entity.label],
        }

    def _tool_get_knowledge_graph(
        self, entity_name: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        limit = min(int(limit), 100)
        query = self.db.query(EntityRelationship).order_by(
            EntityRelationship.co_occurrence_count.desc()
        )
        if entity_name:
            query = query.filter(
                or_(
                    EntityRelationship.entity_a_name.ilike(f"%{entity_name}%"),
                    EntityRelationship.entity_b_name.ilike(f"%{entity_name}%"),
                )
            )
        rels = query.limit(limit).all()

        node_map: Dict[str, Dict] = {}
        edges = []
        for r in rels:
            for name, ntype in [
                (r.entity_a_name, r.entity_a_type),
                (r.entity_b_name, r.entity_b_type),
            ]:
                if name not in node_map:
                    node_map[name] = {"id": name, "label": name, "type": ntype or "UNKNOWN"}
            edges.append(
                {
                    "source": r.entity_a_name,
                    "target": r.entity_b_name,
                    "weight": r.co_occurrence_count,
                    "sentiment": float(r.avg_sentiment) if r.avg_sentiment else 0.0,
                }
            )

        return {
            "viz": {
                "type": "graph",
                "data": {"nodes": list(node_map.values()), "edges": edges},
                "config": {
                    "title": f"Knowledge Graph{f' — {entity_name}' if entity_name else ''}"
                },
            },
            "sources": ["Knowledge Graph DB"],
        }

    def _tool_get_market_correlation(self, entity_name: str) -> Dict[str, Any]:
        try:
            from intelligence_api.application.correlation import CorrelationEngine

            engine_corr = CorrelationEngine(self.db)
            result = engine_corr.compute_correlation(entity_name)
            rd = result.to_dict()
            return {
                "viz": {
                    "type": "chart:composed",
                    "data": rd.get("aligned_data", []),
                    "config": {
                        "title": f"{entity_name} — Sentiment vs. Stock Price",
                        "xKey": "date",
                        "lines": [
                            {"key": "sentiment", "color": "#ec5b13", "name": "Sentiment", "yAxisId": "left"},
                        ],
                        "bars": [
                            {"key": "close_price", "color": "#f59e0b", "name": "Close Price", "yAxisId": "right"},
                        ],
                    },
                    "summary": {
                        "pearson_r": rd.get("pearson_r"),
                        "best_lag_days": rd.get("best_lag_days"),
                        "signal_strength": rd.get("signal_strength"),
                        "insight": rd.get("insight"),
                        "ticker": rd.get("ticker_symbol"),
                    },
                },
                "sources": [rd.get("ticker_symbol", entity_name), "Market Data"],
            }
        except Exception as e:
            return {"error": str(e)}

    def _tool_get_sector_heatmap(self, days: int = 7) -> Dict[str, Any]:
        cutoff = date.today() - timedelta(days=int(days))
        rows = (
            self.db.query(
                Entity.sector,
                sa_func.avg(DailyTrend.avg_sentiment).label("avg_sentiment"),
                sa_func.count(Entity.id.distinct()).label("entity_count"),
                sa_func.sum(DailyTrend.event_count).label("total_events"),
            )
            .join(DailyTrend, DailyTrend.entity_id == Entity.id)
            .filter(
                Entity.sector.isnot(None),
                DailyTrend.observation_date >= cutoff,
            )
            .group_by(Entity.sector)
            .order_by(sa_func.avg(DailyTrend.avg_sentiment).desc())
            .all()
        )
        data = [
            {
                "sector": r.sector,
                "sentiment": round(float(r.avg_sentiment), 4) if r.avg_sentiment else 0.0,
                "entity_count": r.entity_count,
                "total_events": r.total_events or 0,
            }
            for r in rows
        ]
        return {
            "viz": {
                "type": "chart:bar",
                "data": data,
                "config": {
                    "title": f"Sector Sentiment Heatmap ({days}d)",
                    "xKey": "sector",
                    "bars": [{"key": "sentiment", "color": "#ec5b13", "name": "Avg Sentiment"}],
                },
            },
            "sources": ["Intelligence DB"],
        }

    def _tool_search_entities(
        self, query: str, entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        q = self.db.query(Entity).filter(Entity.label.ilike(f"%{query}%"))
        if entity_type:
            q = q.filter(Entity.type == entity_type)
        entities = q.limit(10).all()
        data = [
            {
                "label": e.label,
                "type": e.type,
                "sector": e.sector,
                "description": e.description,
            }
            for e in entities
        ]
        return {
            "viz": {"type": "entity_list", "data": data},
            "sources": ["Intelligence DB"],
            "count": len(data),
        }

    def _tool_get_recent_events(
        self,
        entity_name: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        limit = min(int(limit), 20)
        q = (
            self.db.query(ScrapedEvent, Entity.label.label("entity_label"))
            .join(Entity, ScrapedEvent.entity_id == Entity.id)
            .order_by(ScrapedEvent.created_at.desc())
        )
        if entity_name:
            q = q.filter(Entity.label.ilike(f"%{entity_name}%"))
        if category:
            q = q.filter(ScrapedEvent.category.ilike(f"%{category}%"))

        rows = q.limit(limit).all()
        data = []
        sources: List[str] = []
        for event, label in rows:
            src = event.source_type or label
            if src not in sources:
                sources.append(src)
            data.append(
                {
                    "entity": label,
                    "summary": event.summary or "",
                    "sentiment": float(event.sentiment_score) if event.sentiment_score else 0.0,
                    "category": event.category or "",
                    "source": event.source_type or "",
                    "url": event.raw_url or "",
                    "published_at": (
                        event.published_at.isoformat() if event.published_at else ""
                    ),
                }
            )
        return {
            "viz": {"type": "articles", "data": data},
            "sources": sources,
        }

    # ── Tool dispatch ──────────────────────────────────────

    def _tool_read_article(self, url: str) -> Dict[str, Any]:
        """Fetch an article URL and return extracted plain text (max ~4 KB)."""
        import re
        import html as html_module

        if not url.startswith(("http://", "https://")):
            return {"error": "Invalid URL: only http/https URLs are supported."}
        try:
            import httpx

            response = httpx.get(
                url,
                timeout=12.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Omnisight-Bot/1.0)"},
            )
            response.raise_for_status()
            content = response.text
            # Strip noisy blocks first
            content = re.sub(
                r"<(script|style|head|nav|footer|aside|form)[^>]*>.*?</\1>",
                " ",
                content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            # Remove remaining HTML tags
            content = re.sub(r"<[^>]+>", " ", content)
            # Unescape entities
            content = html_module.unescape(content)
            # Collapse whitespace
            content = re.sub(r"\s+", " ", content).strip()
            truncated = len(content) > 4000
            content = content[:4000]
            if truncated:
                content += " ...[truncated]"
            return {
                "content": content,
                "url": url,
                "char_count": len(content),
            }
        except Exception as e:
            return {"error": f"Failed to read article: {e}"}

    def _tool_add_entity_tracker(
        self,
        entity_name: str,
        entity_type: str = "COMPANY",
        sector: Optional[str] = None,
        sources: Optional[List[str]] = None,
        interval_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Subscribe the current user to track entity + create ScrapeTargets if needed."""
        from intelligence_api.application.subscription_service import subscribe_user_to_entity
        from intelligence_api.domain.models import User

        entity_name = entity_name.strip()
        entity_type = entity_type.upper() if entity_type else "COMPANY"
        sources = sources or ["Google News", "Reddit Subreddit"]
        interval_minutes = max(15, int(interval_minutes))

        # Resolve the User object if we have a user_id
        user = None
        if self.user_id is not None:
            user = self.db.query(User).filter(User.id == self.user_id).first()

        if user is None:
            # Fallback: legacy unauthenticated path (create entity + targets without subscription)
            existing = (
                self.db.query(Entity)
                .filter(Entity.label.ilike(entity_name))
                .first()
            )
            if existing:
                return {
                    "viz": {
                        "type": "tracker_added",
                        "data": {
                            "entity_name": existing.label,
                            "entity_type": existing.type,
                            "sector": existing.sector,
                            "sources": sources,
                            "interval_minutes": interval_minutes,
                            "already_existed": True,
                        },
                    },
                    "sources": [entity_name],
                }
            new_entity = Entity(label=entity_name, type=entity_type, sector=sector, is_pii=False)
            self.db.add(new_entity)
            self.db.flush()
            from sqlalchemy.sql import func as sqlfunc
            created_targets = []
            for source in sources:
                target = ScrapeTarget(
                    target_name=entity_name,
                    source_type=source,  # preserve original casing for scheduler matching
                    scrape_interval_minutes=interval_minutes,
                    campaign="Chat-Added",
                    status="Pending",
                    metadata_json={"entity_type": entity_type},
                    next_scrape_at=sqlfunc.now(),
                )
                self.db.add(target)
                created_targets.append(source.upper())
            self.db.commit()
            return {
                "viz": {
                    "type": "tracker_added",
                    "data": {
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "sector": sector,
                        "sources": created_targets,
                        "interval_minutes": interval_minutes,
                        "already_existed": False,
                    },
                },
                "sources": [entity_name],
            }

        # Authenticated path: use subscription service
        result = subscribe_user_to_entity(
            db=self.db,
            user=user,
            entity_label=entity_name,
            entity_type=entity_type,
            sources=sources,
            interval_minutes=interval_minutes,
            campaign="Chat-Added",
        )
        if sector:
            entity = self.db.query(Entity).filter(Entity.id == result["entity_id"]).first()
            if entity and not entity.sector:
                entity.sector = sector
                self.db.commit()

        already_existed = len(result["created_targets"]) == 0
        return {
            "viz": {
                "type": "tracker_added",
                "data": {
                    "entity_name": result["entity_label"],
                    "entity_type": result["entity_type"],
                    "sector": sector,
                    "sources": sources,
                    "interval_minutes": interval_minutes,
                    "already_existed": already_existed,
                    "existing_events": result["existing_events"],
                },
            },
            "sources": [entity_name],
        }

    # ── Category A: Comparison & Competitive Intelligence ─────────────────

    def _tool_compare_entities(
        self,
        entity_a: str,
        entity_b: str,
        entity_c: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Side-by-side sentiment timelines and category breakdown for 2-3 entities."""
        labels = [entity_a, entity_b] + ([entity_c] if entity_c else [])
        cutoff = date.today() - timedelta(days=int(days))
        cutoff_dt = datetime(cutoff.year, cutoff.month, cutoff.day, tzinfo=timezone.utc)
        series: List[Dict] = []
        category_breakdown: Dict[str, List] = {}
        sources: List[str] = []
        colors = ["#00d0ff", "#00FF87", "#FF4B2B"]

        for i, label in enumerate(labels):
            entity = (
                self.db.query(Entity)
                .filter(Entity.label.ilike(f"%{label}%"))
                .first()
            )
            if not entity:
                continue
            sources.append(entity.label)

            rows = (
                self.db.query(DailyTrend)
                .filter(
                    DailyTrend.entity_id == entity.id,
                    DailyTrend.observation_date >= cutoff,
                )
                .order_by(DailyTrend.observation_date)
                .all()
            )
            series.append({
                "label": entity.label,
                "color": colors[i % len(colors)],
                "data": [
                    {
                        "date": r.observation_date.isoformat(),
                        "sentiment": float(r.avg_sentiment) if r.avg_sentiment else 0.0,
                        "event_count": r.event_count or 0,
                    }
                    for r in rows
                ],
            })

            cat_rows = (
                self.db.query(
                    ScrapedEvent.category,
                    sa_func.count(ScrapedEvent.id).label("count"),
                )
                .filter(
                    ScrapedEvent.entity_id == entity.id,
                    ScrapedEvent.created_at >= cutoff_dt,
                )
                .group_by(ScrapedEvent.category)
                .all()
            )
            category_breakdown[entity.label] = [
                {"category": r.category or "Unknown", "count": r.count}
                for r in cat_rows
            ]

        return {
            "viz": {
                "type": "chart:multi_line",
                "data": series,
                "config": {
                    "title": f"Entity Comparison — {', '.join(labels)} ({days}d)",
                    "xKey": "date",
                    "yKey": "sentiment",
                    "category_breakdown": category_breakdown,
                },
            },
            "sources": sources,
            "entity_count": len(series),
        }

    def _tool_get_cross_entity_events(
        self,
        entity_a: str,
        entity_b: str,
        days: int = 30,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Events that mention both entities simultaneously via EntityMention table."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
        limit = min(int(limit), 20)

        ids_a = {
            row.event_id
            for row in self.db.query(EntityMention.event_id)
            .filter(EntityMention.mentioned_name.ilike(f"%{entity_a}%"))
            .all()
        }
        ids_b = {
            row.event_id
            for row in self.db.query(EntityMention.event_id)
            .filter(EntityMention.mentioned_name.ilike(f"%{entity_b}%"))
            .all()
        }

        shared_ids = list(ids_a & ids_b)
        if not shared_ids:
            return {
                "viz": {"type": "articles", "data": []},
                "sources": [],
                "message": f"No events found mentioning both '{entity_a}' and '{entity_b}'.",
            }

        rows = (
            self.db.query(ScrapedEvent, Entity.label.label("entity_label"))
            .join(Entity, ScrapedEvent.entity_id == Entity.id)
            .filter(
                ScrapedEvent.id.in_(shared_ids),
                ScrapedEvent.created_at >= cutoff,
            )
            .order_by(ScrapedEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        data = [
            {
                "entity": label,
                "summary": ev.summary or "",
                "sentiment": float(ev.sentiment_score) if ev.sentiment_score else 0.0,
                "category": ev.category or "",
                "source": ev.source_type or "",
                "url": ev.raw_url or "",
                "published_at": ev.published_at.isoformat() if ev.published_at else "",
            }
            for ev, label in rows
        ]
        return {
            "viz": {
                "type": "articles",
                "data": data,
                "config": {"title": f"Events Mentioning Both: {entity_a} & {entity_b}"},
            },
            "sources": [entity_a, entity_b],
        }

    # ── Category B: Anomaly & Risk Detection ───────────────────────────────

    def _tool_detect_sentiment_spike(
        self,
        entity_name: str,
        days: int = 60,
        z_threshold: float = 2.0,
    ) -> Dict[str, Any]:
        """Z-score anomaly detection on daily sentiment from DailyTrend."""
        import statistics as _stats

        entity = (
            self.db.query(Entity)
            .filter(Entity.label.ilike(f"%{entity_name}%"))
            .first()
        )
        if not entity:
            return {"error": f"Entity '{entity_name}' not found."}

        cutoff = date.today() - timedelta(days=int(days))
        trends = (
            self.db.query(DailyTrend)
            .filter(
                DailyTrend.entity_id == entity.id,
                DailyTrend.observation_date >= cutoff,
            )
            .order_by(DailyTrend.observation_date)
            .all()
        )
        if len(trends) < 5:
            return {
                "viz": {"type": "articles", "data": []},
                "sources": [entity.label],
                "message": f"Insufficient data for spike detection (found {len(trends)} data points, need at least 5).",
            }

        sentiments = [float(t.avg_sentiment) if t.avg_sentiment else 0.0 for t in trends]
        mean_s = _stats.mean(sentiments)
        stdev_s = _stats.stdev(sentiments) if len(sentiments) > 1 else 0.0001
        z_threshold = float(z_threshold)

        timeline_data = []
        spike_dates = []
        for t, s in zip(trends, sentiments):
            z = (s - mean_s) / stdev_s if stdev_s > 0 else 0.0
            is_spike = abs(z) >= z_threshold
            if is_spike:
                spike_dates.append(t.observation_date)
            timeline_data.append({
                "date": t.observation_date.isoformat(),
                "sentiment": round(s, 4),
                "z_score": round(z, 3),
                "is_spike": is_spike,
                "event_count": t.event_count or 0,
            })

        # Fetch context events on up to 3 spike dates
        spike_events = []
        for spike_date in spike_dates[:3]:
            spike_start = datetime(spike_date.year, spike_date.month, spike_date.day, tzinfo=timezone.utc)
            spike_end = spike_start + timedelta(days=1)
            events = (
                self.db.query(ScrapedEvent)
                .filter(
                    ScrapedEvent.entity_id == entity.id,
                    ScrapedEvent.created_at >= spike_start,
                    ScrapedEvent.created_at < spike_end,
                )
                .order_by(ScrapedEvent.sentiment_score.asc())
                .limit(3)
                .all()
            )
            for ev in events:
                spike_events.append({
                    "date": spike_date.isoformat(),
                    "summary": ev.summary or "",
                    "sentiment": float(ev.sentiment_score) if ev.sentiment_score else 0.0,
                    "category": ev.category or "",
                    "url": ev.raw_url or "",
                })

        return {
            "viz": {
                "type": "chart:spike",
                "data": timeline_data,
                "config": {
                    "title": f"{entity.label} — Sentiment Spike Detection ({days}d)",
                    "xKey": "date",
                    "lines": [
                        {"key": "sentiment", "color": "#00d0ff", "name": "Sentiment"},
                        {"key": "z_score", "color": "#FF4B2B", "name": "Z-Score", "yAxisId": "right"},
                    ],
                    "spike_threshold": z_threshold,
                },
                "spike_events": spike_events,
                "summary": {
                    "spike_count": len(spike_dates),
                    "mean_sentiment": round(mean_s, 4),
                    "stdev_sentiment": round(stdev_s, 4),
                    "z_threshold": z_threshold,
                },
            },
            "sources": [entity.label],
            "spike_count": len(spike_dates),
        }

    def _tool_get_risk_signals(
        self,
        days: int = 7,
        sentiment_threshold: float = -0.3,
        limit: int = 15,
    ) -> Dict[str, Any]:
        """Cross-entity risk scan: negative sentiment events + legal/regulatory signals."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
        limit = min(int(limit), 30)
        risk_categories = ["Legal/Regulatory", "Market Rumor"]

        rows = (
            self.db.query(
                ScrapedEvent,
                Entity.label.label("entity_label"),
                Entity.sector.label("sector"),
            )
            .join(Entity, ScrapedEvent.entity_id == Entity.id)
            .filter(
                ScrapedEvent.created_at >= cutoff,
                or_(
                    ScrapedEvent.sentiment_score <= float(sentiment_threshold),
                    ScrapedEvent.category.in_(risk_categories),
                ),
            )
            .order_by(ScrapedEvent.sentiment_score.asc())
            .limit(limit)
            .all()
        )
        data = []
        sources: List[str] = []
        for ev, label, sector in rows:
            if label not in sources:
                sources.append(label)
            data.append({
                "entity": label,
                "sector": sector or "Unknown",
                "summary": ev.summary or "",
                "sentiment": float(ev.sentiment_score) if ev.sentiment_score else 0.0,
                "category": ev.category or "",
                "source": ev.source_type or "",
                "url": ev.raw_url or "",
                "published_at": ev.published_at.isoformat() if ev.published_at else "",
            })

        return {
            "viz": {
                "type": "articles",
                "data": data,
                "config": {"title": f"Risk Signals — Last {days} Days"},
            },
            "sources": sources,
            "signal_count": len(data),
        }

    def _tool_get_trending_entities(
        self,
        days: int = 7,
        limit: int = 10,
        metric: str = "velocity",
    ) -> Dict[str, Any]:
        """Rank entities by event velocity, sentiment shift, or raw event count."""
        limit = min(int(limit), 25)
        days = int(days)
        today = date.today()
        this_week_start = today - timedelta(days=days)
        last_week_start = today - timedelta(days=days * 2)

        this_period = (
            self.db.query(
                DailyTrend.entity_id,
                sa_func.sum(DailyTrend.event_count).label("this_count"),
                sa_func.avg(DailyTrend.avg_sentiment).label("this_sentiment"),
            )
            .filter(
                DailyTrend.observation_date >= this_week_start,
                DailyTrend.observation_date < today,
            )
            .group_by(DailyTrend.entity_id)
            .all()
        )
        last_period = (
            self.db.query(
                DailyTrend.entity_id,
                sa_func.sum(DailyTrend.event_count).label("last_count"),
                sa_func.avg(DailyTrend.avg_sentiment).label("last_sentiment"),
            )
            .filter(
                DailyTrend.observation_date >= last_week_start,
                DailyTrend.observation_date < this_week_start,
            )
            .group_by(DailyTrend.entity_id)
            .all()
        )

        last_map = {r.entity_id: r for r in last_period}
        entity_ids = [r.entity_id for r in this_period]
        entities = (
            self.db.query(Entity.id, Entity.label, Entity.sector)
            .filter(Entity.id.in_(entity_ids))
            .all()
        )
        entity_map = {e.id: (e.label, e.sector) for e in entities}

        rows = []
        for r in this_period:
            label, sector = entity_map.get(r.entity_id, ("Unknown", None))
            last = last_map.get(r.entity_id)
            this_count = int(r.this_count or 0)
            last_count = int(last.last_count or 0) if last else 0
            this_sent = float(r.this_sentiment or 0.0)
            last_sent = float(last.last_sentiment or 0.0) if last else 0.0
            rows.append({
                "entity": label,
                "sector": sector or "Unknown",
                "this_period_events": this_count,
                "last_period_events": last_count,
                "velocity": this_count - last_count,
                "current_sentiment": round(this_sent, 4),
                "sentiment_shift": round(this_sent - last_sent, 4),
            })

        metric_key = metric if metric in ("velocity", "sentiment_shift") else "this_period_events"
        rows.sort(key=lambda x: abs(x.get(metric_key, 0)), reverse=True)
        rows = rows[:limit]

        return {
            "viz": {
                "type": "chart:bar",
                "data": rows,
                "config": {
                    "title": f"Trending Entities — {metric.replace('_', ' ').title()} (Last {days}d)",
                    "xKey": "entity",
                    "bars": [{"key": metric_key, "color": "#00d0ff", "name": metric.replace("_", " ").title()}],
                },
            },
            "sources": ["Intelligence DB"],
            "entity_count": len(rows),
        }

    # ── Category C: Tracker & Pipeline Management ──────────────────────────

    def _tool_list_trackers(self, status_filter: str = "all") -> Dict[str, Any]:
        """List scrape targets the current user subscribes to, with status and recent event counts."""
        from intelligence_api.domain.models import UserTargetSubscription
        q = self.db.query(ScrapeTarget)
        if self.user_id is not None:
            q = q.join(
                UserTargetSubscription,
                UserTargetSubscription.scrape_target_id == ScrapeTarget.id,
            ).filter(UserTargetSubscription.user_id == self.user_id)
        if status_filter and status_filter.lower() not in ("all", ""):
            q = q.filter(ScrapeTarget.status.ilike(status_filter))
        targets = q.order_by(ScrapeTarget.status, ScrapeTarget.target_name).all()

        cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
        data = []
        for t in targets:
            event_count = (
                self.db.query(sa_func.count(ScrapedEvent.id))
                .join(Entity, ScrapedEvent.entity_id == Entity.id)
                .filter(
                    Entity.label.ilike(f"%{t.target_name}%"),
                    ScrapedEvent.created_at >= cutoff_7d,
                )
                .scalar()
                or 0
            )
            data.append({
                "entity": t.target_name,
                "source_type": t.source_type,
                "interval_minutes": int(t.scrape_interval_minutes or 60),
                "status": t.status,
                "last_scraped_at": t.last_scraped_at.isoformat() if t.last_scraped_at else "Never",
                "next_scrape_at": t.next_scrape_at.isoformat() if t.next_scrape_at else "Unknown",
                "events_last_7d": event_count,
                "campaign": t.campaign or "",
            })

        return {
            "viz": {
                "type": "table",
                "data": data,
                "config": {"title": f"Scrape Trackers ({len(data)} total)"},
            },
            "sources": ["Tracker DB"],
            "tracker_count": len(data),
        }

    def _tool_set_tracker_status(
        self,
        entity_name: str,
        action: str,
        source_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pause or resume scrape trackers for an entity."""
        new_status = "Paused" if action == "pause" else "Pending"
        q = self.db.query(ScrapeTarget).filter(
            ScrapeTarget.target_name.ilike(f"%{entity_name}%")
        )
        if source_type:
            q = q.filter(ScrapeTarget.source_type.ilike(source_type))
        targets = q.all()
        if not targets:
            return {"error": f"No trackers found for '{entity_name}'."}

        for t in targets:
            t.status = new_status
        self.db.commit()

        updated = [
            {"entity": t.target_name, "source_type": t.source_type, "new_status": new_status}
            for t in targets
        ]
        return {
            "viz": {
                "type": "tracker_status",
                "data": updated,
                "config": {"title": f"Trackers {action.title()}d for '{entity_name}'", "action": action},
            },
            "sources": [entity_name],
            "updated_count": len(updated),
        }

    def _tool_remove_entity_tracker(self, entity_name: str) -> Dict[str, Any]:
        """Deactivate all trackers for an entity. Historical events are preserved."""
        targets = (
            self.db.query(ScrapeTarget)
            .filter(ScrapeTarget.target_name.ilike(f"%{entity_name}%"))
            .all()
        )
        if not targets:
            return {"error": f"No trackers found for '{entity_name}'."}

        for t in targets:
            t.status = "Disabled"
        self.db.commit()

        return {
            "viz": {
                "type": "tracker_status",
                "data": [
                    {"entity": t.target_name, "source_type": t.source_type, "new_status": "Disabled"}
                    for t in targets
                ],
                "config": {"title": f"Trackers Disabled for '{entity_name}'"},
            },
            "sources": [entity_name],
            "disabled_count": len(targets),
            "note": "Historical events have been preserved.",
        }

    def _tool_get_scrape_health(self) -> Dict[str, Any]:
        """System health: overdue trackers, ingestion rates, source breakdown."""
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d = now - timedelta(days=7)

        events_24h = (
            self.db.query(sa_func.count(ScrapedEvent.id))
            .filter(ScrapedEvent.created_at >= cutoff_24h)
            .scalar()
            or 0
        )
        events_7d = (
            self.db.query(sa_func.count(ScrapedEvent.id))
            .filter(ScrapedEvent.created_at >= cutoff_7d)
            .scalar()
            or 0
        )
        overdue = (
            self.db.query(ScrapeTarget)
            .filter(
                ScrapeTarget.next_scrape_at < now,
                ScrapeTarget.status.notin_(["Disabled", "Completed", "Paused"]),
            )
            .order_by(ScrapeTarget.next_scrape_at.asc())
            .limit(20)
            .all()
        )
        source_breakdown = (
            self.db.query(
                ScrapedEvent.source_type,
                sa_func.count(ScrapedEvent.id).label("count"),
            )
            .filter(ScrapedEvent.created_at >= cutoff_7d)
            .group_by(ScrapedEvent.source_type)
            .all()
        )
        active_count = (
            self.db.query(sa_func.count(ScrapeTarget.id))
            .filter(ScrapeTarget.status.notin_(["Disabled", "Completed"]))
            .scalar()
            or 0
        )

        health_summary = {
            "active_trackers": active_count,
            "overdue_trackers": len(overdue),
            "events_last_24h": events_24h,
            "events_last_7d": events_7d,
            "source_breakdown": [
                {"source": r.source_type or "Unknown", "count": r.count}
                for r in source_breakdown
            ],
        }
        overdue_data = [
            {
                "entity": t.target_name,
                "source_type": t.source_type,
                "status": t.status,
                "overdue_since": t.next_scrape_at.isoformat() if t.next_scrape_at else "Unknown",
                "last_scraped": t.last_scraped_at.isoformat() if t.last_scraped_at else "Never",
            }
            for t in overdue
        ]
        return {
            "viz": {
                "type": "health_dashboard",
                "data": {"summary": health_summary, "overdue": overdue_data},
                "config": {"title": "Scraping Pipeline Health"},
            },
            "sources": ["System DB"],
            "health_summary": health_summary,
        }

    # ── Category D: Live / External Research ───────────────────────────────

    def _tool_web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Live DuckDuckGo web search — no API key required."""
        max_results = min(int(max_results), 10)
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw
            ]
            return {
                "viz": {
                    "type": "search_results",
                    "data": results,
                    "config": {"title": f"Web Search: {query}"},
                },
                "sources": ["DuckDuckGo"],
                "count": len(results),
            }
        except ImportError:
            return {"error": "duckduckgo-search package not installed. Run: pip install duckduckgo-search"}
        except Exception as e:
            return {"error": f"Web search failed: {e}"}

    def _tool_fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch and extract clean text from any URL using trafilatura."""
        if not url.startswith(("http://", "https://")):
            return {"error": "Invalid URL: only http/https URLs are supported."}
        try:
            import trafilatura

            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return {"error": f"Failed to download content from: {url}"}
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            if not text:
                return {"error": "Could not extract meaningful content from this URL."}
            truncated = len(text) > 6000
            text = text[:6000]
            if truncated:
                text += " ...[truncated]"
            return {
                "content": text,
                "url": url,
                "char_count": len(text),
                "truncated": truncated,
            }
        except ImportError:
            return {"error": "trafilatura package not installed. Run: pip install trafilatura"}
        except Exception as e:
            return {"error": f"Failed to fetch URL: {e}"}

    # ── Category E: Market & Financial Data ────────────────────────────────

    def _tool_get_stock_info(self, ticker_or_company: str) -> Dict[str, Any]:
        """Fetch live stock snapshot via yfinance."""
        raw = ticker_or_company.strip()
        ticker_symbol = raw.upper()
        try:
            import yfinance as yf
            from intelligence_api.infrastructure.market_data import MarketDataService, TickerResolutionError

            # Always attempt full resolution (cache → yfinance search → twelvedata)
            # so that company names like "Nvidia" or "Apple" resolve to "NVDA" / "AAPL".
            try:
                resolved = MarketDataService().resolve_ticker(raw, self.db)
                ticker_symbol = resolved.upper()
            except TickerResolutionError:
                # Input may already be a valid ticker — proceed with it as-is
                pass

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info or {}
            hist = ticker.history(period="1mo")
            price_30d_change = None
            if not hist.empty and len(hist) >= 2:
                price_30d_change = round(
                    ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100,
                    2,
                )

            card = {
                "ticker": ticker_symbol,
                "name": info.get("longName") or info.get("shortName", ticker_symbol),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "volume": info.get("volume") or info.get("regularMarketVolume"),
                "avg_volume": info.get("averageVolume"),
                "30d_change_pct": price_30d_change,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "exchange": info.get("exchange"),
            }
            return {
                "viz": {
                    "type": "stock_card",
                    "data": card,
                    "config": {"title": f"{card['name']} ({ticker_symbol}) — Market Snapshot"},
                },
                "sources": [ticker_symbol, "yfinance"],
            }
        except Exception as e:
            return {"error": f"Could not retrieve stock info for '{ticker_or_company}': {e}"}

    def _tool_compare_sentiment_vs_sector(
        self, entity_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """Entity sentiment vs its sector aggregate average over time."""
        entity = (
            self.db.query(Entity)
            .filter(Entity.label.ilike(f"%{entity_name}%"))
            .first()
        )
        if not entity:
            return {"error": f"Entity '{entity_name}' not found."}
        if not entity.sector:
            return {"error": f"Entity '{entity_name}' has no sector assigned — cannot compare vs sector."}

        cutoff = date.today() - timedelta(days=int(days))

        entity_rows = (
            self.db.query(DailyTrend)
            .filter(
                DailyTrend.entity_id == entity.id,
                DailyTrend.observation_date >= cutoff,
            )
            .order_by(DailyTrend.observation_date)
            .all()
        )
        sector_rows = (
            self.db.query(
                DailyTrend.observation_date,
                sa_func.avg(DailyTrend.avg_sentiment).label("sector_sentiment"),
            )
            .join(Entity, DailyTrend.entity_id == Entity.id)
            .filter(
                Entity.sector == entity.sector,
                Entity.id != entity.id,
                DailyTrend.observation_date >= cutoff,
            )
            .group_by(DailyTrend.observation_date)
            .order_by(DailyTrend.observation_date)
            .all()
        )
        sector_map = {
            r.observation_date: round(float(r.sector_sentiment), 4) if r.sector_sentiment else None
            for r in sector_rows
        }

        data = [
            {
                "date": t.observation_date.isoformat(),
                "entity_sentiment": float(t.avg_sentiment) if t.avg_sentiment else 0.0,
                "sector_sentiment": sector_map.get(t.observation_date),
            }
            for t in entity_rows
        ]
        return {
            "viz": {
                "type": "chart:line",
                "data": data,
                "config": {
                    "title": f"{entity.label} vs {entity.sector} Sector ({days}d)",
                    "xKey": "date",
                    "lines": [
                        {"key": "entity_sentiment", "color": "#00d0ff", "name": entity.label},
                        {"key": "sector_sentiment", "color": "#f59e0b", "name": f"{entity.sector} Sector Avg"},
                    ],
                },
            },
            "sources": [entity.label, f"{entity.sector} Sector"],
        }

    # ── Category F: Deep Intelligence ──────────────────────────────────────

    def _tool_find_related_entities(
        self, entity_name: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Top co-occurring entities ranked by co-occurrence count."""
        limit = min(int(limit), 25)

        rels = (
            self.db.query(EntityRelationship)
            .filter(
                or_(
                    EntityRelationship.entity_a_name.ilike(f"%{entity_name}%"),
                    EntityRelationship.entity_b_name.ilike(f"%{entity_name}%"),
                )
            )
            .order_by(EntityRelationship.co_occurrence_count.desc())
            .limit(limit)
            .all()
        )

        data = []
        for r in rels:
            if entity_name.lower() in r.entity_a_name.lower():
                other_name, other_type = r.entity_b_name, r.entity_b_type
            else:
                other_name, other_type = r.entity_a_name, r.entity_a_type
            source_keys = list(r.source_types.keys()) if isinstance(r.source_types, dict) else []
            data.append({
                "entity": other_name,
                "type": other_type or "UNKNOWN",
                "co_occurrences": r.co_occurrence_count,
                "avg_sentiment": round(float(r.avg_sentiment), 4) if r.avg_sentiment else 0.0,
                "sources": source_keys,
            })

        return {
            "viz": {
                "type": "entity_list",
                "data": data,
                "config": {"title": f"Entities Most Connected to {entity_name}"},
            },
            "sources": [entity_name, "Knowledge Graph DB"],
            "count": len(data),
        }

    def _tool_summarize_entity_brief(
        self, entity_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """AI-synthesized intelligence brief drawing on multiple tool handlers."""
        # Gather raw data internally
        profile = self._tool_get_entity_intelligence(entity_name)
        if "error" in profile:
            return profile

        recent_events = self._tool_get_recent_events(entity_name=entity_name, limit=10)
        related = self._tool_find_related_entities(entity_name=entity_name, limit=8)
        spike_data = self._tool_detect_sentiment_spike(entity_name=entity_name, days=days)

        entity_card = profile.get("viz", {}).get("data", {})
        events_list = recent_events.get("viz", {}).get("data", [])
        related_list = related.get("viz", {}).get("data", [])
        spike_events = spike_data.get("viz", {}).get("spike_events", [])
        spike_summary = spike_data.get("viz", {}).get("summary", {})

        context_parts = [
            f"ENTITY PROFILE:\n{json.dumps(entity_card, indent=2)}",
            f"\nRECENT EVENTS (last {days}d, sample of {len(events_list)}):\n"
            + "\n".join(
                f"- [{e.get('category', '')}] {e.get('summary', '')} (sentiment: {e.get('sentiment', 0):.2f})"
                for e in events_list[:8]
            ),
            f"\nKEY RELATIONSHIPS (top {len(related_list)} co-occurring entities):\n"
            + "\n".join(
                f"- {r.get('entity', '')} ({r.get('type', '')}) — "
                f"{r.get('co_occurrences', 0)} co-occurrences, avg sentiment {r.get('avg_sentiment', 0):.2f}"
                for r in related_list
            ),
        ]
        if spike_events:
            context_parts.append(
                f"\nSENTIMENT ANOMALIES ({spike_summary.get('spike_count', 0)} spikes detected):\n"
                + "\n".join(
                    f"- {s.get('date', '')} [{s.get('category', '')}]: {s.get('summary', '')} "
                    f"(sentiment: {s.get('sentiment', 0):.2f})"
                    for s in spike_events
                )
            )

        briefing_prompt = (
            f"You are an intelligence analyst. Write a comprehensive but concise intelligence brief "
            f"for '{entity_name}' covering the last {days} days based on the OSINT data below.\n\n"
            f"Structure your brief with these sections:\n"
            f"1. **Executive Summary** (2-3 sentences)\n"
            f"2. **Sentiment Narrative** (trend analysis and drivers)\n"
            f"3. **Key Themes** (top 3-4 themes from recent events)\n"
            f"4. **Risk Signals** (any negative, legal, or anomalous events)\n"
            f"5. **Key Relationships** (notable connections with other entities)\n"
            f"6. **Analyst Recommendation** (watch / monitor / high priority / de-prioritise)\n\n"
            f"OSINT DATA:\n{''.join(context_parts)}"
        )
        try:
            from openai import AzureOpenAI as _AzureOpenAI

            client = _AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
            resp = client.chat.completions.create(
                model=settings.AZURE_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a senior OSINT intelligence analyst."},
                    {"role": "user", "content": briefing_prompt},
                ],
                temperature=0.4,
                max_tokens=1200,
            )
            brief_text = resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"summarize_entity_brief LLM call failed: {e}")
            brief_text = f"[Brief synthesis failed: {e}]\n\nRaw data:\n{''.join(context_parts)}"

        return {
            "viz": {
                "type": "brief",
                "data": {"entity": entity_name, "days": days, "brief": brief_text},
                "config": {"title": f"Intelligence Brief: {entity_name} ({days}d)"},
            },
            "sources": [entity_name, "Intelligence DB", "LLM Synthesis"],
            "brief_text": brief_text,
        }

    # ── Tool dispatch ──────────────────────────────────────

    def _dispatch_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "search_intelligence": self._tool_search_intelligence,
            "get_entity_intelligence": self._tool_get_entity_intelligence,
            "get_sentiment_timeline": self._tool_get_sentiment_timeline,
            "get_knowledge_graph": self._tool_get_knowledge_graph,
            "get_market_correlation": self._tool_get_market_correlation,
            "get_sector_heatmap": self._tool_get_sector_heatmap,
            "search_entities": self._tool_search_entities,
            "get_recent_events": self._tool_get_recent_events,
            "read_article": self._tool_read_article,
            "add_entity_tracker": self._tool_add_entity_tracker,
            # Category A: Comparison
            "compare_entities": self._tool_compare_entities,
            "get_cross_entity_events": self._tool_get_cross_entity_events,
            # Category B: Anomaly & Risk
            "detect_sentiment_spike": self._tool_detect_sentiment_spike,
            "get_risk_signals": self._tool_get_risk_signals,
            "get_trending_entities": self._tool_get_trending_entities,
            # Category C: Tracker Management
            "list_trackers": self._tool_list_trackers,
            "set_tracker_status": self._tool_set_tracker_status,
            "remove_entity_tracker": self._tool_remove_entity_tracker,
            "get_scrape_health": self._tool_get_scrape_health,
            # Category D: Live Research
            "web_search": self._tool_web_search,
            "fetch_url": self._tool_fetch_url,
            # Category E: Market & Financial
            "get_stock_info": self._tool_get_stock_info,
            "compare_sentiment_vs_sector": self._tool_compare_sentiment_vs_sector,
            # Category F: Deep Intelligence
            "find_related_entities": self._tool_find_related_entities,
            "summarize_entity_brief": self._tool_summarize_entity_brief,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(**args)
        except Exception as e:
            logger.exception(f"Tool '{name}' raised an exception")
            return {"error": str(e)}

    # ── Session helpers ────────────────────────────────────

    def _load_history(self, session_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Load last 20 messages and convert to OpenAI message format.

        Tool messages stored in the DB have no preceding assistant message with
        tool_calls (that intermediary message was never persisted). We reconstruct
        the required sequence here so the OpenAI API does not reject the history.
        """
        messages_db = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(20)
            .all()
        )
        openai_messages: List[Dict[str, Any]] = []
        i = 0
        while i < len(messages_db):
            m = messages_db[i]
            if m.role == "user":
                openai_messages.append({"role": "user", "content": m.content or ""})
                i += 1
            elif m.role == "assistant":
                openai_messages.append({"role": "assistant", "content": m.content or ""})
                i += 1
            elif m.role == "tool":
                # Collect all consecutive tool messages into one group
                tool_group: List[ConversationMessage] = []
                while i < len(messages_db) and messages_db[i].role == "tool":
                    tool_group.append(messages_db[i])
                    i += 1
                # Synthesise the assistant message that requested these tools
                # (it was never explicitly persisted to the DB)
                synth_tool_calls = [
                    {
                        "id": t.tool_call_id or f"tc_{t.id}",
                        "type": "function",
                        "function": {
                            "name": t.tool_name or "",
                            "arguments": json.dumps(t.tool_args or {}),
                        },
                    }
                    for t in tool_group
                ]
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": synth_tool_calls,
                    }
                )
                # Add each tool result, stripping viz to keep token count low
                for t in tool_group:
                    result_for_history = {
                        k: v
                        for k, v in (t.tool_result or {}).items()
                        if k != "viz"
                    }
                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": t.tool_call_id or "",
                            "content": json.dumps(result_for_history),
                        }
                    )
            else:
                i += 1
        return openai_messages

    def _save_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        tool_args: Optional[Dict] = None,
        tool_result: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_result=tool_result,
            metadata_json=metadata or {},
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def _build_system_prompt(self) -> str:
        if self.user_id is not None:
            # Scope entity list to what the current user subscribes to
            from intelligence_api.application.subscription_service import get_user_entity_labels
            entity_labels = get_user_entity_labels(self.db, self.user_id)
        else:
            entity_labels = [
                e.label
                for e in self.db.query(Entity.label).limit(50).all()
            ]
        entity_list = ", ".join(entity_labels) if entity_labels else "none tracked yet"
        return _SYSTEM_PROMPT.format(
            today=date.today().isoformat(),
            entity_list=entity_list,
        )

    # ── Main streaming entry point ─────────────────────────

    async def stream_chat(
        self, session_id: uuid.UUID, user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted lines.
        Drives an LLM agent loop with tool calling.
        """

        def _sse(event: str, data: Dict[str, Any]) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        # 1. Persist user message
        self._save_message(session_id=session_id, role="user", content=user_message)

        # 2. Build message history
        system_content = self._build_system_prompt()
        history = self._load_history(session_id)
        # Remove last user message we just added — it's the current turn
        # (was already loaded from DB into history). We include it via history.
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_content}
        ] + history

        # 3. Agent loop (max 5 tool rounds to avoid runaway)
        all_sources: List[str] = []
        assistant_text = ""
        assistant_msg_id: Optional[str] = None

        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )

        for _round in range(6):
            # Non-streaming first pass to detect tool calls, then stream text
            # We use streaming throughout and accumulate tool call deltas.
            try:
                stream = client.chat.completions.create(
                    model=settings.AZURE_CHAT_DEPLOYMENT,
                    messages=messages,
                    tools=CHAT_TOOLS,
                    tool_choice="auto",
                    stream=True,
                    temperature=0.3,
                    max_tokens=1500,
                )
            except Exception as e:
                yield _sse("error", {"message": f"LLM error: {e}"})
                return

            # Accumulate streamed response
            accumulated_text = ""
            tool_calls_acc: Dict[str, Dict[str, Any]] = {}  # index → partial call
            finish_reason = None

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason or finish_reason

                # Text delta
                if delta.content:
                    accumulated_text += delta.content
                    yield _sse("text_delta", {"delta": delta.content})

                # Tool call deltas
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc.function.arguments

            assistant_text += accumulated_text

            # ── No tool calls → final answer ──────────────────
            if not tool_calls_acc:
                # Persist assistant message
                saved = self._save_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_text,
                    metadata={"sources": all_sources},
                )
                assistant_msg_id = str(saved.id)
                yield _sse(
                    "done",
                    {
                        "confidence": None,
                        "sources": all_sources,
                        "message_id": assistant_msg_id,
                    },
                )
                return

            # ── Execute tool calls (possibly parallel) ────────
            tool_results: List[Dict[str, Any]] = []
            tool_call_list = list(tool_calls_acc.values())

            # Notify frontend about each tool starting
            for tc in tool_call_list:
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                yield _sse(
                    "tool_start",
                    {
                        "name": tc["name"],
                        "label": _TOOL_LABELS.get(tc["name"], "Processing..."),
                        "args": args,
                    },
                )

            # Execute (run in executor to avoid blocking the event loop for sync DB calls)
            loop = asyncio.get_event_loop()

            async def _run_tool(tc: Dict) -> tuple:
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                result = await loop.run_in_executor(
                    None, lambda tc=tc, args=args: self._dispatch_tool(tc["name"], args)
                )
                return tc, args, result

            executed = await asyncio.gather(*[_run_tool(tc) for tc in tool_call_list])

            # Build assistant message for OpenAI (must include tool_calls block)
            openai_tool_calls = []
            for tc, args, result in executed:
                openai_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(args),
                        },
                    }
                )
                # Collect sources
                for src in result.get("sources", []):
                    if src not in all_sources:
                        all_sources.append(src)

                # Yield tool_result to frontend (with viz payload)
                yield _sse(
                    "tool_result",
                    {
                        "name": tc["name"],
                        "viz": result.get("viz"),
                        "sources": result.get("sources", []),
                        "error": result.get("error"),
                    },
                )
                tool_results.append((tc, args, result))

            # Append assistant message that requested the tools
            messages.append(
                {
                    "role": "assistant",
                    "content": accumulated_text or None,
                    "tool_calls": openai_tool_calls,
                }
            )

            # Append tool results to message list
            for tc, args, result in tool_results:
                # Strip viz payload from LLM context (keeps tokens low); send summary
                result_for_llm = {
                    k: v for k, v in result.items() if k not in ("viz",)
                }
                # Add a compact data summary so the LLM can reason about it
                viz = result.get("viz", {})
                if viz:
                    vtype = viz.get("type", "")
                    data = viz.get("data", [])
                    summary = viz.get("summary", {})
                    if isinstance(data, list):
                        result_for_llm["data_summary"] = f"{len(data)} records of type '{vtype}'"
                        # For table/list types pass ALL rows so the LLM can reference every item;
                        # for large chart datasets keep only the first record to save tokens.
                        if vtype in ("table", "entity_list", "tracker_status", "health_dashboard", "search_results"):
                            result_for_llm["all_records"] = data
                        elif data:
                            result_for_llm["first_record"] = data[0]
                    elif isinstance(data, dict):
                        # Card-style results (stock_card, entity_card, brief) — pass full data
                        result_for_llm["data_summary"] = f"card of type '{vtype}'"
                        result_for_llm["card_data"] = data
                    if summary:
                        result_for_llm["chart_summary"] = summary

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result_for_llm),
                    }
                )

                # Persist to DB
                self._save_message(
                    session_id=session_id,
                    role="tool",
                    tool_name=tc["name"],
                    tool_call_id=tc["id"],
                    tool_args=args,
                    tool_result=result,
                )

            # Continue loop for follow-up LLM response

        # Safety fallback if max rounds hit
        yield _sse("error", {"message": "Max tool call rounds reached. Please try a more specific question."})
