from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from intelligence_api.core.database import get_db
from intelligence_api.application.processor import IntelligenceProcessor

router = APIRouter()

class EventIn(BaseModel):
    entity_label: str
    content: str
    source_type: str
    is_user: bool = False
    raw_url: Optional[str] = None

@router.post("/process-event")
async def process_event(event: EventIn, db: Session = Depends(get_db)):
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
    scraper_params: Optional[Dict[str, Any]] = None # New field
    
@router.post("/targets")
def create_target(target: TargetIn, db: Session = Depends(get_db)):
    try:
        from intelligence_api.domain.models import ScrapeTarget
        from sqlalchemy.sql import func
        new_target = ScrapeTarget(
            target_name=target.target_name,
            source_type=target.source_type,
            scrape_interval_minutes=target.scrape_interval_minutes,
            campaign=target.campaign,
            metadata_json=target.scraper_params or {},
            status="Pending",
            next_scrape_at=func.now()
        )
        db.add(new_target)
        db.commit()
        db.refresh(new_target)
        return {"status": "success", "target_id": new_target.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/targets")
def get_targets(db: Session = Depends(get_db)):
    from intelligence_api.domain.models import ScrapeTarget
    targets = db.query(ScrapeTarget).order_by(ScrapeTarget.created_at.desc()).all()
    # Pydantic dicts
    return [{
        "id": str(t.id), 
        "target_name": t.target_name, 
        "source_type": t.source_type, 
        "interval": t.scrape_interval_minutes, 
        "campaign": t.campaign, 
        "status": t.status, 
        "metadata_json": t.metadata_json, # Added
        "next_scrape": t.next_scrape_at, 
        "last_scraped": t.last_scraped_at, 
        "error": t.error_message
    } for t in targets]

@router.post("/targets/{target_id}/run")
def run_target_now(target_id: str, db: Session = Depends(get_db)):
    from intelligence_api.domain.models import ScrapeTarget
    from sqlalchemy.sql import func
    target = db.query(ScrapeTarget).filter(ScrapeTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    target.next_scrape_at = func.now()
    target.status = "Pending"
    db.commit()
    return {"status": "success", "message": "Triggered target scrape"}

@router.delete("/targets/{target_id}")
def delete_target(target_id: str, db: Session = Depends(get_db)):
    """Delete a target and ALL related intelligence/market/graph data."""
    from intelligence_api.domain.models import ScrapeTarget, Entity, ScrapedEvent, DailyTrend, TickerMapping, StockPrice, EntityMention, EntityRelationship
    from sqlalchemy import or_
    import uuid
    
    try:
        target_uuid = uuid.UUID(target_id)
        target = db.query(ScrapeTarget).filter(ScrapeTarget.id == target_uuid).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        
        # 1. Find the corresponding Entity
        # We match by label/name
        entity = db.query(Entity).filter(Entity.label == target.target_name).first()
        
        if entity:
            # 2. Delete Events and DailyTrends, Mentions
            db.query(ScrapedEvent).filter(ScrapedEvent.entity_id == entity.id).delete()
            db.query(DailyTrend).filter(DailyTrend.entity_id == entity.id).delete()
            db.query(EntityMention).filter(EntityMention.resolved_entity_id == entity.id).delete()
            
            # 3. Handle Relationships
            normalized_name = entity.label.strip()
            db.query(EntityRelationship).filter(or_(
                EntityRelationship.entity_a_name == normalized_name,
                EntityRelationship.entity_b_name == normalized_name
            )).delete()

            # 4. Handle Market Data
            mapping = db.query(TickerMapping).filter(TickerMapping.company_name == entity.label.lower()).first()
            if mapping:
                if mapping.ticker_symbol:
                    db.query(StockPrice).filter(StockPrice.ticker_symbol == mapping.ticker_symbol).delete()
                db.delete(mapping)
            
            # 5. Semantic Cache Wipe (Pinecone)
            try:
                from intelligence_api.infrastructure.ai_service import SemanticCache
                cache = SemanticCache()
                cache.delete_by_filter(filter_dict={"entity_label": entity.label})
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not delete from Pinecone: {e}")
            
            # 6. Delete Entity
            db.delete(entity)

        
        # 7. Finally delete the target itself
        db.delete(target)
        db.commit()
        
        return {"status": "success", "message": f"Deleted '{target.target_name}' and all associated data."}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target ID format")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



# ──────────────── Market Correlation Endpoints ────────────────

@router.get("/market/ticker/{entity_label}")
def get_ticker(entity_label: str, db: Session = Depends(get_db)):
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
def get_correlation(entity_label: str, days: int = 90, db: Session = Depends(get_db)):
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
def refresh_stock_data(entity_label: str, db: Session = Depends(get_db)):
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
def get_sector_heatmap(db: Session = Depends(get_db)):
    """Get sector-grouped sentiment data for heatmap visualization."""
    from intelligence_api.application.correlation import get_sector_heatmap_data
    try:
        data = get_sector_heatmap_data(db)
        return {"sectors": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────── Knowledge Graph Endpoints ────────────────

@router.get("/knowledge-graph")
def get_knowledge_graph(
    entity: Optional[str] = None,
    min_co_occurrences: int = 2,
    days: int = 30,
    entity_types: Optional[str] = None, # comma separated
    db: Session = Depends(get_db)
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
    edges_out = []

    # Get set of all currently tracked entities
    tracked_labels = {e.label.lower() for e in db.query(Entity.label).all()}

    for e in edges_raw:
        def add_node(name, etype):
            if name not in nodes_dict:
                nodes_dict[name] = {
                    "name": name,
                    "type": etype,
                    "mention_count": 0, # Can be enriched if needed, but we'll use co_occurrence for size
                    "is_tracked": name.lower() in tracked_labels
                }
            nodes_dict[name]["mention_count"] += e.co_occurrence_count
        
        # Only add nodes/edges if they meet the type filter logic after extracting
        keep = True
        if types_filter and entity:
            # If a specific entity is queried, maybe the OTHER entity doesn't match the type filter.
            # E.g. query=Tesla, type=PERSON. We only want edges where the non-Tesla node is a PERSON.
            other_type = e.entity_b_type if e.entity_a_name == entity.strip() else e.entity_a_type
            if other_type not in types_filter:
                keep = False

        if keep:
            add_node(e.entity_a_name, e.entity_a_type)
            add_node(e.entity_b_name, e.entity_b_type)

            edges_out.append({
                "source": e.entity_a_name,
                "target": e.entity_b_name,
                "weight": e.co_occurrence_count,
                "avg_sentiment": float(e.avg_sentiment) if e.avg_sentiment else 0.0,
                "last_seen": e.last_seen.isoformat() if e.last_seen else None
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
def get_entity_graph_details(name: str, db: Session = Depends(get_db)):
    """Fetch recent co-mentions and details for a specific entity."""
    from intelligence_api.domain.models import EntityRelationship, EntityMention, ScrapedEvent
    from sqlalchemy import or_, desc
    
    normalized = name.strip()
    
    # Top connections
    connections = db.query(EntityRelationship).filter(or_(
        EntityRelationship.entity_a_name == normalized,
        EntityRelationship.entity_b_name == normalized
    )).order_by(desc(EntityRelationship.co_occurrence_count)).limit(10).all()
    
    related = []
    for c in connections:
        other_name = c.entity_b_name if c.entity_a_name == normalized else c.entity_a_name
        other_type = c.entity_b_type if c.entity_a_name == normalized else c.entity_a_type
        related.append({
            "name": other_name,
            "type": other_type,
            "co_mentions": c.co_occurrence_count,
            "avg_sentiment": float(c.avg_sentiment or 0)
        })
        
    return {
        "entity": normalized,
        "top_connections": related
    }
