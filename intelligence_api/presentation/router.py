from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from intelligence_api.core.database import get_db
from intelligence_api.core.security import get_current_user
from intelligence_api.application.processor import IntelligenceProcessor
import httpx
from fastapi.responses import Response
import urllib.parse

router = APIRouter()

class EventIn(BaseModel):
    entity_label: str
    content: str
    source_type: str
    is_user: bool = False
    raw_url: Optional[str] = None
    discovery_depth: int = 0

@router.post("/process-event")
async def process_event(event: EventIn, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        processor = IntelligenceProcessor(db)
        result = await processor.process_event(event.dict())
        return {"status": "success", "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TargetIn(BaseModel):
    target_name: str
    source_type: str
    scrape_interval_minutes: int
    campaign: Optional[str] = None
    entity_type: Optional[str] = "COMPANY" # COMPANY, PERSON, TOPIC
    scraper_params: Optional[Dict[str, Any]] = None # New field

class TargetUpdateIn(BaseModel):
    scrape_interval_minutes: Optional[int] = None
    scraper_params: Optional[Dict[str, Any]] = None
    entity_type: Optional[str] = None
    
@router.post("/targets")
def create_target(
    target: TargetIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe the current user to track an entity+source.

    If another user already tracks the same entity+source, the existing
    ScrapeTarget is reused and the user is subscribed to it, gaining immediate
    access to all historical events already collected.
    """
    from intelligence_api.application.subscription_service import subscribe_user_to_entity
    try:
        result = subscribe_user_to_entity(
            db=db,
            user=current_user,
            entity_label=target.target_name,
            entity_type=target.entity_type or "COMPANY",
            sources=[target.source_type],
            interval_minutes=target.scrape_interval_minutes,
            campaign=target.campaign,
        )
        return {
            "status": "success",
            "target_id": result["entity_id"],  # entity id as a stable reference
            "existing_events": result["existing_events"],
            "shared": len(result["subscribed_targets"]) == 0 and len(result["already_subscribed"]) > 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/targets")
def get_targets(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    from intelligence_api.domain.models import ScrapeTarget, Entity, ScrapedEvent, UserTargetSubscription
    from sqlalchemy import func
    from urllib.parse import urlparse

    # Return only the targets this user is subscribed to
    targets = (
        db.query(ScrapeTarget)
        .join(UserTargetSubscription, UserTargetSubscription.scrape_target_id == ScrapeTarget.id)
        .filter(UserTargetSubscription.user_id == current_user.id)
        .order_by(ScrapeTarget.created_at.desc())
        .all()
    )
    
    results = []
    for t in targets:
        # Get event count and recent sources by matching target name to entity label
        # Note: In a larger system, we'd use a direct FK, but here we match on the string label
        entity = db.query(Entity).filter(func.upper(Entity.label) == func.upper(t.target_name)).first()
        
        event_count = 0
        recent_sources = []
        
        if entity:
            event_count = db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity.id).count()
            
            # Get top 3 unique domains from recent events
            recent_events = db.query(ScrapedEvent.raw_url).filter(
                ScrapedEvent.entity_id == entity.id,
                ScrapedEvent.raw_url.isnot(None)
            ).order_by(ScrapedEvent.created_at.desc()).limit(20).all()
            
            domains = []
            for (url,) in recent_events:
                try:
                    domain = urlparse(url).netloc
                    if domain and domain not in domains:
                        domains.append(domain)
                    if len(domains) >= 3:
                        break
                except:
                    continue
            recent_sources = domains

        results.append({
            "id": str(t.id), 
            "target_name": t.target_name, 
            "source_type": t.source_type, 
            "interval": t.scrape_interval_minutes, 
            "campaign": t.campaign, 
            "status": t.status, 
            "metadata_json": t.metadata_json,
            "next_scrape": t.next_scrape_at, 
            "last_scraped": t.last_scraped_at, 
            "error": t.error_message,
            "event_count": event_count,
            "recent_sources": recent_sources
        })
    return results

@router.post("/targets/{target_id}/run")
def run_target_now(target_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    from intelligence_api.domain.models import ScrapeTarget
    from sqlalchemy.sql import func
    target = db.query(ScrapeTarget).filter(ScrapeTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    target.next_scrape_at = func.now()
    target.status = "Pending"
    db.commit()
    return {"status": "success", "message": "Triggered target scrape"}

@router.put("/targets/{target_id}")
def update_target(target_id: str, payload: TargetUpdateIn, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a target's configuration (e.g., scrape interval)."""
    from intelligence_api.domain.models import ScrapeTarget
    import uuid
    
    try:
        try:
            target_uuid = uuid.UUID(target_id)
        except ValueError:
             raise HTTPException(status_code=400, detail="Invalid target ID format")

        target = db.query(ScrapeTarget).filter(ScrapeTarget.id == target_uuid).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        
        if payload.scrape_interval_minutes is not None:
            target.scrape_interval_minutes = payload.scrape_interval_minutes
        
        # Optionally update metadata json
        if payload.scraper_params or payload.entity_type:
             old_meta = target.metadata_json or {}
             new_meta = {**old_meta, **(payload.scraper_params or {})}
             if payload.entity_type:
                 new_meta["entity_type"] = payload.entity_type
             target.metadata_json = new_meta
             
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.delete("/targets/{target_id}")
def delete_target(target_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Unsubscribe the current user from a scrape target.

    If this was the last subscription, the target and ALL associated intelligence
    data are permanently deleted (same behaviour as before multi-user support).
    If other users still subscribe, only the subscription row is removed and
    the shared data is preserved.
    """
    from intelligence_api.domain.models import (
        ScrapeTarget, Entity, ScrapedEvent, DailyTrend,
        TickerMapping, StockPrice, EntityMention, EntityRelationship,
        UserTargetSubscription,
    )
    from intelligence_api.application.subscription_service import unsubscribe_user_from_target
    from sqlalchemy import or_, func
    import uuid

    try:
        try:
            target_uuid = uuid.UUID(target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target ID format")

        target = db.query(ScrapeTarget).filter(ScrapeTarget.id == target_uuid).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        result = unsubscribe_user_from_target(db, current_user, target_uuid)

        if not result["deleted"]:
            # Other users still subscribed — data is preserved.
            return {"status": "success", "message": result["message"]}

        # Last subscriber removed — perform full cleanup (original behaviour)
        normalized_name = target.target_name.strip().upper()
        entities = db.query(Entity).filter(func.upper(Entity.label) == normalized_name).all()

        for entity in entities:
            db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity.id).delete()
            db.query(DailyTrend).filter(DailyTrend.entity_id == entity.id).delete()
            db.query(EntityMention).filter(EntityMention.resolved_entity_id == entity.id).delete()
            db.query(EntityRelationship).filter(or_(
                func.upper(EntityRelationship.entity_a_name) == normalized_name,
                func.upper(EntityRelationship.entity_b_name) == normalized_name,
            )).delete()

            mapping = db.query(TickerMapping).filter(
                func.upper(TickerMapping.company_name) == normalized_name
            ).first()
            if mapping:
                if mapping.ticker_symbol:
                    db.query(StockPrice).filter(
                        StockPrice.ticker_symbol == mapping.ticker_symbol
                    ).delete()
                db.delete(mapping)

            try:
                from intelligence_api.infrastructure.ai_service import SemanticCache
                SemanticCache().delete_by_filter(filter_dict={"entity_label": entity.label})
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    f"Could not delete Pinecone vectors for {entity.label}: {exc}"
                )

            db.delete(entity)

        db.delete(target)
        db.commit()
        return {
            "status": "success",
            "message": f"Deleted '{target.target_name}' and all associated intelligence data.",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# ──────────────── Market Correlation Endpoints ────────────────

@router.get("/targets/by-entity/{name}")
def get_target_by_entity(name: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch the active scrape target for a specific entity name."""
    from intelligence_api.domain.models import ScrapeTarget
    from sqlalchemy import func
    target = db.query(ScrapeTarget).filter(func.lower(ScrapeTarget.target_name) == name.lower()).first()
    if not target:
        return {"target": None}
    return {
        "target": {
            "id": str(target.id),
            "name": target.target_name,
            "source": target.source_type,
            "interval": int(target.scrape_interval_minutes),
            "status": target.status,
            "campaign": target.campaign,
            "allow_discovery": target.metadata_json.get("allow_discovery", False) if target.metadata_json else False
        }
    }

@router.get("/entities/by-name/{name}")
def get_entity_by_name(name: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch entity details by name."""
    from intelligence_api.domain.models import Entity
    from sqlalchemy import func
    entity = db.query(Entity).filter(func.lower(Entity.label) == name.lower()).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {
        "id": str(entity.id),
        "label": entity.label,
        "type": entity.type
    }

@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Deep delete an entity and all its data."""
    from intelligence_api.domain.models import Entity, ScrapedEvent, DailyTrend, EntityMention, EntityRelationship, ScrapeTarget
    import uuid
    from sqlalchemy import or_
    
    try:
        entity_uuid = uuid.UUID(entity_id)
        entity = db.query(Entity).filter(Entity.id == entity_uuid).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        name = entity.label
        
        # 1. Delete Targets
        db.query(ScrapeTarget).filter(ScrapeTarget.target_name.ilike(name)).delete(synchronize_session=False)
        
        # 2. Delete Events & Trends
        db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity_uuid).delete(synchronize_session=False)
        db.query(DailyTrend).filter(DailyTrend.entity_id == entity_uuid).delete(synchronize_session=False)
        
        # 3. Delete Mentions
        db.query(EntityMention).filter(or_(
            EntityMention.mentioned_name.ilike(name),
            EntityMention.resolved_entity_id == entity_uuid
        )).delete(synchronize_session=False)
        
        # 4. Delete Relationships mapping to this name
        db.query(EntityRelationship).filter(or_(
            EntityRelationship.entity_a_name.ilike(name),
            EntityRelationship.entity_b_name.ilike(name)
        )).delete(synchronize_session=False)
        
        # 5. Delete Entity
        db.query(Entity).filter(Entity.id == entity_uuid).delete(synchronize_session=False)
        
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/ticker/{entity_label}")
def get_ticker(entity_label: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Resolve and cache a ticker symbol for a company entity."""
    from intelligence_api.infrastructure.market_data import MarketDataService, TickerResolutionError
    try:
        service = MarketDataService()
        ticker = service.resolve_ticker(entity_label, db)
        
        # Get cached mapping details
        from intelligence_api.domain.models import TickerMapping
        mapping = db.query(TickerMapping).filter(
            TickerMapping.company_name == entity_label.lower()
        ).first()
        
        return {
            "entity_label": entity_label,
            "ticker_symbol": ticker,
            "exchange": mapping.exchange if mapping else None,
            "resolved_via": mapping.resolved_via if mapping else None
        }
    except TickerResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/correlation/{entity_label}")
def get_correlation(entity_label: str, days: int = 90, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Return aligned sentiment + stock price data with signal strength score.
    Query params: ?days=90
    """
    from intelligence_api.application.correlation import CorrelationEngine
    from intelligence_api.infrastructure.market_data import TickerResolutionError
    try:
        engine = CorrelationEngine(db)
        result = engine.compute_correlation(entity_label, days=days)
        return result.to_dict()
    except TickerResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/market/refresh/{entity_label}")
def refresh_stock_data(entity_label: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Force-refresh stock price data for an entity's ticker."""
    from intelligence_api.infrastructure.market_data import MarketDataService, TickerResolutionError
    from intelligence_api.domain.models import StockPrice
    try:
        service = MarketDataService()
        ticker = service.resolve_ticker(entity_label, db)
        
        # Delete existing prices to force full refetch
        db.query(StockPrice).filter(StockPrice.ticker_symbol == ticker).delete()
        db.commit()
        
        prices = service.fetch_stock_prices(ticker, db, days=90)
        return {
            "status": "success",
            "ticker": ticker,
            "days_fetched": len(prices)
        }
    except TickerResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/sector-heatmap")
def get_sector_heatmap(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get sector-grouped sentiment data for heatmap visualization."""
    from intelligence_api.application.correlation import get_sector_heatmap_data
    try:
        data = get_sector_heatmap_data(db)
        return {"sectors": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import Response

@router.get("/market/export/{entity_label}")
def export_analysis_pdf(entity_label: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Export the correlation and intelligence data for an entity as a PDF."""
    from intelligence_api.application.correlation import CorrelationEngine
    from reporting.pdf_generator import generate_pdf
    from intelligence_api.domain.models import Entity, ScrapedEvent
    from sqlalchemy import func, desc
    
    try:
        normalized_name = entity_label.strip().upper()
        
        # Gather market data
        engine = CorrelationEngine(db)
        corr_data = None
        try:
            corr_data = engine.compute_correlation(entity_label, days=30).to_dict()
        except Exception as e:
            # Fallback if no market data is available
            corr_data = {"error": "Market data unavailable for this entity"}

        # Gather OSINT events
        recent_events = []
        entity = db.query(Entity).filter(func.upper(Entity.label) == normalized_name).first()
        if entity:
            events = db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity.id).order_by(desc(ScrapedEvent.created_at)).limit(5).all()
            for ev in events:
                recent_events.append({
                    "source": ev.source_type,
                    "sentiment": round(ev.sentiment_score, 2) if ev.sentiment_score else 0.0,
                    "summary": ev.summary,
                    "category": ev.category,
                    "date": ev.published_at.strftime('%Y-%m-%d') if ev.published_at else ev.created_at.strftime('%Y-%m-%d')
                })
        
        # Structure the payload for the PDF generator
        report_data = []
        
        # Add Market Stats Block
        if "error" not in corr_data:
             report_data.append({
                 "Signal Strength": str(corr_data.get("signal_strength", 0)),
                 "Insight": str(corr_data.get("insight", "")),
                 "Alpha Correlation": str(round(corr_data.get("pearson_r", 0), 2))
             })
        
        # Add Event Blocks
        for ev in recent_events:
            report_data.append(ev)

        if not report_data:
             report_data.append({"info": "No significant intelligence gathered yet."})
             
        # Generate the PDF
        title = f"Intelligence Export: {entity_label}"
        pdf_bytes = generate_pdf(title, report_data)

        # Return as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={entity_label.replace(' ', '_')}_intelligence.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────── Knowledge Graph Endpoints ────────────────

@router.get("/knowledge-graph")
def get_knowledge_graph(
    entity: Optional[str] = None,
    min_co_occurrences: int = 2,
    days: int = 30,
    entity_types: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns nodes and edges for the Knowledge Graph visualization.
    Filters by optional central entity, minimum co-occurrences, time window, and entity types.
    """
    from intelligence_api.domain.models import EntityRelationship, Entity, EntityMention
    from sqlalchemy import or_, and_, desc
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    types_filter = entity_types.split(",") if entity_types and entity_types != "All" else None

    # Base query for edges
    query = db.query(EntityRelationship).filter(
        EntityRelationship.last_seen >= cutoff,
        EntityRelationship.co_occurrence_count >= min_co_occurrences
    )

    if entity:
        normalized = entity.strip()
        query = query.filter(or_(
            EntityRelationship.entity_a_name == normalized,
            EntityRelationship.entity_b_name == normalized
        ))
        
    if types_filter:
        # Include edges where AT LEAST ONE entity matches the type filter
        query = query.filter(or_(
            EntityRelationship.entity_a_type.in_(types_filter),
            EntityRelationship.entity_b_type.in_(types_filter)
        ))

    # Limit to top 200 edges to prevent massive graphs
    edges_raw = query.order_by(desc(EntityRelationship.co_occurrence_count)).limit(200).all()

    nodes_dict = {}
    edges_dict = {} # Key: frozenset([source, target]) for undirected normalization

    # Get set of all currently tracked entities
    tracked_labels = {e.label.lower() for e in db.query(Entity.label).all()}

    for e in edges_raw:
        # Normalize names to handle capitalization duplicates (NVIDIA vs Nvidia)
        # We'll use the original database name as the key, but case-insensitively
        u_norm = e.entity_a_name.strip().upper()
        v_norm = e.entity_b_name.strip().upper()
        
        # Prefer the original DB casing if it matches the normalized one
        def get_canonical_name(raw_name):
            return raw_name.strip() # In a more complex setup, we could vote on the 'best' casing

        u_canonical = get_canonical_name(e.entity_a_name)
        v_canonical = get_canonical_name(e.entity_b_name)

        def add_node(norm_name, canonical_name, etype):
            if norm_name not in nodes_dict:
                nodes_dict[norm_name] = {
                    "id": canonical_name, # Map internally to the first encountered name
                    "name": canonical_name,
                    "type": etype,
                    "mention_count": 0,
                    "is_tracked": norm_name.lower() in tracked_labels
                }
            nodes_dict[norm_name]["mention_count"] += e.co_occurrence_count

        # Filtering logic
        keep = True
        if types_filter and entity:
            other_type = e.entity_b_type if e.entity_a_name == entity.strip() else e.entity_a_type
            if other_type not in types_filter:
                keep = False

        if keep:
            add_node(u_norm, u_canonical, e.entity_a_type)
            add_node(v_norm, v_canonical, e.entity_b_type)

            # Aggregate edges by canonical pair
            edge_key = tuple(sorted([u_norm, v_norm]))
            if edge_key not in edges_dict:
                edges_dict[edge_key] = {
                    "source": nodes_dict[u_norm]["id"],
                    "target": nodes_dict[v_norm]["id"],
                    "weight": 0,
                    "sentiment_sum": 0.0,
                    "sentiment_count": 0,
                    "last_seen": e.last_seen
                }
            
            ed = edges_dict[edge_key]
            ed["weight"] += e.co_occurrence_count
            if e.avg_sentiment:
                ed["sentiment_sum"] += float(e.avg_sentiment)
                ed["sentiment_count"] += 1
            if e.last_seen and (not ed["last_seen"] or e.last_seen > ed["last_seen"]):
                ed["last_seen"] = e.last_seen

    # Format edges for output
    edges_out = []
    for ed in edges_dict.values():
        edges_out.append({
            "source": ed["source"],
            "target": ed["target"],
            "weight": ed["weight"],
            "avg_sentiment": ed["sentiment_sum"] / ed["sentiment_count"] if ed["sentiment_count"] > 0 else 0.0,
            "last_seen": ed["last_seen"].isoformat() if ed["last_seen"] else None
        })

    nodes_list = list(nodes_dict.values())
    
    # Calculate most connected for stats
    most_connected = max(nodes_list, key=lambda x: x["mention_count"], default={"name": "None"})["name"]

    return {
        "nodes": nodes_list,
        "edges": edges_out,
        "stats": {
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_out),
            "most_connected": most_connected
        }
    }

@router.get("/knowledge-graph/entity/{name}/details")
def get_entity_graph_details(name: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch recent co-mentions and details for a specific entity."""
    from intelligence_api.domain.models import EntityRelationship, EntityMention, ScrapedEvent, Entity
    from sqlalchemy import or_, desc, func
    
    normalized = name.strip().upper()
    
    # Top connections - Case insensitive matching to aggregate all casing variants (NVIDIA, Nvidia, etc)
    connections = db.query(EntityRelationship).filter(or_(
        func.upper(EntityRelationship.entity_a_name) == normalized,
        func.upper(EntityRelationship.entity_b_name) == normalized
    )).order_by(desc(EntityRelationship.co_occurrence_count)).limit(30).all()
    
    related = []
    seen_related = {} # Case-insensitive deduplication for the side-panel list
    
    for rel in connections:
        # Determine the 'other' entity
        other_name = rel.entity_b_name if rel.entity_a_name.strip().upper() == normalized else rel.entity_a_name
        other_type = rel.entity_b_type if rel.entity_a_name.strip().upper() == normalized else rel.entity_a_type
        other_norm = other_name.strip().upper()
        
        if other_norm not in seen_related:
            seen_related[other_norm] = {
                "name": other_name,
                "type": other_type,
                "co_mentions": 0,
                "sentiment_sum": 0.0,
                "sentiment_count": 0
            }
        seen_related[other_norm]["co_mentions"] += rel.co_occurrence_count
        if rel.avg_sentiment:
            seen_related[other_norm]["sentiment_sum"] += float(rel.avg_sentiment)
            seen_related[other_norm]["sentiment_count"] += 1
    
    # Calculate average sentiment and format for output
    for other_norm, data in seen_related.items():
        avg_sentiment = data["sentiment_sum"] / data["sentiment_count"] if data["sentiment_count"] > 0 else 0.0
        related.append({
            "name": data["name"],
            "type": data["type"],
            "co_mentions": data["co_mentions"],
            "avg_sentiment": avg_sentiment
        })

    related = sorted(related, key=lambda x: x["co_mentions"], reverse=True)[:10]
        
    # Get recent news summary
    entity = db.query(Entity).filter(func.upper(Entity.label) == normalized).first()
    osint_summary = None
    if entity:
        recent_events = db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity.id).order_by(desc(ScrapedEvent.created_at)).limit(3).all()
        if recent_events:
            summaries = [e.summary for e in recent_events if e.summary]
            if summaries:
                osint_summary = " ".join(summaries)
            else:
                osint_summary = f"Recent monitoring recorded {len(recent_events)} signals without verbose summarization."
        else:
             osint_summary = "No recent signals recorded for this entity."
    else:
        osint_summary = "Entity not actively tracked in primary intelligence tables."

    return {
        "entity": normalized,
        "top_connections": related,
        "osint_summary": osint_summary
    }

@router.get("/knowledge-graph/edge/details")
def get_edge_details(source: str, target: str, limit: int = 5, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch recent articles (events) that mention both 'source' and 'target' entities."""
    from intelligence_api.domain.models import EntityMention, ScrapedEvent, Entity
    from sqlalchemy import text, desc
    
    source_normalized = source.strip()
    target_normalized = target.strip()

    # Find events where BOTH entities are mentioned
    # We do an intersection of event_ids
    
    query = text("""
        SELECT e.id, e.source_type, e.cleaned_content, e.summary, e.sentiment_score, e.raw_url, e.created_at
        FROM events e
        JOIN entity_mentions em1 ON e.id = em1.event_id
        JOIN entity_mentions em2 ON e.id = em2.event_id
        WHERE UPPER(em1.mentioned_name) = UPPER(:source) AND UPPER(em2.mentioned_name) = UPPER(:target)
        ORDER BY e.created_at DESC
        LIMIT :limit
    """)
    
    result = db.execute(query, {"source": source_normalized, "target": target_normalized, "limit": limit}).fetchall()
    
    # Fallback to just the main node (source) if ghost relationship exists due to deletions
    if not result:
        fallback_query = text("""
            SELECT e.id, e.source_type, e.cleaned_content, e.summary, e.sentiment_score, e.raw_url, e.created_at
            FROM events e
            JOIN entity_mentions em1 ON e.id = em1.event_id
            WHERE UPPER(em1.mentioned_name) = UPPER(:source)
            ORDER BY e.created_at DESC
            LIMIT :limit
        """)
        result = db.execute(fallback_query, {"source": source_normalized, "limit": limit}).fetchall()
        
    # Final fallback to target node
    if not result:
        fallback_query = text("""
            SELECT e.id, e.source_type, e.cleaned_content, e.summary, e.sentiment_score, e.raw_url, e.created_at
            FROM events e
            JOIN entity_mentions em1 ON e.id = em1.event_id
            WHERE UPPER(em1.mentioned_name) = UPPER(:target)
            ORDER BY e.created_at DESC
            LIMIT :limit
        """)
        result = db.execute(fallback_query, {"target": target_normalized, "limit": limit}).fetchall()
    
    articles = []
    for row in result:
        articles.append({
            "id": str(row.id),
            "source_type": row.source_type,
            "content": row.cleaned_content or row.summary,
            "sentiment_score": float(row.sentiment_score) if row.sentiment_score else None,
            "raw_url": row.raw_url,
            "created_at": row.created_at.isoformat() if row.created_at else None
        })

    return {
        "source": source_normalized,
        "target": target_normalized,
        "articles": articles
    }

# ──────────────── Dashboard Data Endpoints ────────────────

@router.get("/dashboard/data")
def get_dashboard_data(
    filter_entity: Optional[str] = "All",
    filter_source: Optional[str] = "All",
    filter_cat: Optional[str] = "All",
    filter_type: Optional[str] = "All",
    filter_campaign: Optional[str] = "All",
    min_sentiment: float = -1.0,
    max_sentiment: float = 1.0,
    limit: int = 20,
    page: int = 1,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified endpoint to fetch dashboard event data securely without raw SQL.
    Returns the latest events matching the advanced filters, paginated.
    """
    from intelligence_api.domain.models import ScrapedEvent, Entity, ScrapeTarget
    from sqlalchemy.orm import aliased
    from sqlalchemy import and_, or_
    import math

    query = db.query(
        Entity.label.label("entity"),
        Entity.type.label("entity_type"),
        ScrapedEvent.source_type,
        ScrapedEvent.sentiment_score,
        ScrapedEvent.summary,
        ScrapedEvent.category,
        ScrapedEvent.content,
        ScrapedEvent.raw_url,
        ScrapedEvent.published_at,
        ScrapedEvent.created_at,
        ScrapeTarget.campaign
    ).select_from(ScrapedEvent).join(
        Entity, ScrapedEvent.entity_id == Entity.id
    ).outerjoin(
        ScrapeTarget, Entity.label == ScrapeTarget.target_name
    )

    if filter_entity and filter_entity != "All":
        query = query.filter(Entity.label.ilike(f"%{filter_entity}%"))
    
    if filter_source and filter_source != "All":
        query = query.filter(ScrapedEvent.source_type == filter_source)
        
    if filter_cat and filter_cat != "All":
        query = query.filter(ScrapedEvent.category == filter_cat)

    if filter_type and filter_type != "All":
        query = query.filter(Entity.type == filter_type)

    if filter_campaign and filter_campaign != "All":
        query = query.filter(ScrapeTarget.campaign == filter_campaign)

    query = query.filter(ScrapedEvent.sentiment_score.between(min_sentiment, max_sentiment))
    
    total = query.count()
    offset = (page - 1) * limit
    
    # Execute query
    results = query.order_by(ScrapedEvent.created_at.desc()).offset(offset).limit(limit).all()

    # Convert to dict
    data = [
        {
            "entity": r.entity,
            "entity_type": r.entity_type,
            "source_type": r.source_type,
            "sentiment_score": r.sentiment_score,
            "summary": r.summary,
            "category": r.category,
            "content": r.content,
            "raw_url": r.raw_url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "campaign": r.campaign
        }
        for r in results
    ]
    
    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if limit > 0 else 1
    }

@router.get("/system/status")
def get_system_status():
    """Returns real-time system metrics (CPU, RAM)."""
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        return {
            "cpu_load": f"{cpu_pct}%",
            "memory_usage": f"{memory.percent}%",
            "latency": "42ms", # Simulated for now as it depends on network
            "status": "Healthy"
        }
    except Exception as e:
        return {"error": str(e), "status": "Degraded"}


@router.get("/dashboard/filters/entities")
def get_filter_entities(entity_type: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch distinct entity names for dropdowns, optionally filtered by type."""
    from intelligence_api.domain.models import Entity
    query = db.query(Entity.label).filter(Entity.label != None)
    if entity_type and entity_type != "All":
        query = query.filter(Entity.type == entity_type)
    entities = query.distinct().all()
    return ["All"] + [e[0] for e in entities if e[0]]

@router.get("/dashboard/filters/categories")
def get_filter_categories(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch distinct event categories for dropdowns."""
    from intelligence_api.domain.models import ScrapedEvent
    cats = db.query(ScrapedEvent.category).filter(ScrapedEvent.category != None).distinct().all()
    return ["All"] + [c[0] for c in cats if c[0]]

@router.get("/dashboard/filters/campaigns")
def get_filter_campaigns(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch distinct existing campaigns for dropdowns."""
    from intelligence_api.domain.models import ScrapeTarget
    camps = db.query(ScrapeTarget.campaign).filter(ScrapeTarget.campaign != None).distinct().all()
    return ["All"] + [c[0] for c in camps if c[0]]

@router.get("/entity/logo/{name}")
async def proxy_logo(name: str):
    """Proxy company logos through the backend to bypass adblockers."""
    mapping = {
        "apple": "apple.com",
        "nvidia": "nvidia.com",
        "tesla": "tesla.com",
        "microsoft": "microsoft.com",
        "google": "google.com",
        "amazon": "amazon.com",
        "meta": "meta.com",
        "netflix": "netflix.com",
        "amd": "amd.com",
        "intel": "intel.com"
    }
    
    clean_name = name.lower().strip()
    domain = mapping.get(clean_name, f"{clean_name.replace(' ', '')}.com")
    
    # Try multiple providers in order of quality
    providers = [
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    ]
    
    async with httpx.AsyncClient() as client:
        for url in providers:
            try:
                resp = await client.get(url, timeout=3.0, follow_redirects=True)
                if resp.status_code == 200 and len(resp.content) > 500: # Ensure it's not a tiny/empty pixel
                    return Response(
                        content=resp.content, 
                        media_type=resp.headers.get("content-type", "image/png"),
                        headers={"Cache-Control": "public, max-age=86400"}
                    )
            except Exception:
                continue
            
    # Ultimate Fallback to ui-avatars
    fallback_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(name)}&background=random&color=fff&size=200"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(fallback_url)
            return Response(content=resp.content, media_type="image/png")
        except Exception:
            return Response(status_code=404)

