"""
Subscription service — manages the relationship between Users and ScrapeTargets.

Key rules:
- A ScrapeTarget is shared infrastructure (entity + source combo).
- Multiple users can subscribe to the same target, each getting the same
  historical data immediately upon subscription.
- A ScrapeTarget is only deleted when its last subscriber unsubscribes.
- Subscribing to a target does NOT re-trigger a scrape if one already exists,
  but returns the count of existing events so the UI can inform the user.
"""

from __future__ import annotations

import uuid
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func as sqlfunc

from intelligence_api.domain.models import (
    Entity,
    ScrapedEvent,
    ScrapeTarget,
    User,
    UserTargetSubscription,
)

logger = logging.getLogger(__name__)


def subscribe_user_to_entity(
    db: Session,
    user: User,
    entity_label: str,
    entity_type: str,
    sources: List[str],
    interval_minutes: int,
    campaign: Optional[str] = None,
) -> dict:
    """Ensure the user is subscribed to all requested source types for an entity.

    Steps:
    1. Upsert Entity by label.
    2. For each source: check if ScrapeTarget exists; create if not.
    3. Check if UserTargetSubscription exists; create if not.
    4. Return total existing event count (so UI can show "X articles available").
    """
    entity_label = entity_label.strip()
    entity_type = entity_type.upper()
    interval_minutes = max(15, int(interval_minutes))

    # 1. Upsert Entity
    entity = db.query(Entity).filter(Entity.label.ilike(entity_label)).first()
    if not entity:
        entity = Entity(
            label=entity_label,
            type=entity_type,
            is_pii=False,
        )
        db.add(entity)
        db.flush()

    created_targets: List[str] = []
    subscribed_targets: List[str] = []
    already_subscribed: List[str] = []

    for source in sources:
        # 2. Upsert ScrapeTarget for this entity+source combo
        existing_target = (
            db.query(ScrapeTarget)
            .filter(
                ScrapeTarget.target_name.ilike(entity_label),
                ScrapeTarget.source_type.ilike(source),
            )
            .first()
        )

        if not existing_target:
            existing_target = ScrapeTarget(
                target_name=entity_label,
                source_type=source,  # preserve original casing for scheduler matching
                scrape_interval_minutes=interval_minutes,
                campaign=campaign or "User-Added",
                status="Pending",
                metadata_json={"entity_type": entity_type},
                next_scrape_at=sqlfunc.now(),
                created_by_user_id=user.id,
            )
            db.add(existing_target)
            db.flush()
            created_targets.append(source)

        # 3. Upsert UserTargetSubscription
        existing_sub = (
            db.query(UserTargetSubscription)
            .filter(
                UserTargetSubscription.user_id == user.id,
                UserTargetSubscription.scrape_target_id == existing_target.id,
            )
            .first()
        )

        if not existing_sub:
            sub = UserTargetSubscription(
                user_id=user.id,
                scrape_target_id=existing_target.id,
            )
            db.add(sub)
            subscribed_targets.append(source)
        else:
            already_subscribed.append(source)

    # 4. Count existing events for this entity
    existing_event_count = (
        db.query(sqlfunc.count(ScrapedEvent.id))
        .filter(ScrapedEvent.entity_id == entity.id)
        .scalar()
        or 0
    )

    db.commit()

    return {
        "entity_label": entity.label,
        "entity_type": entity.type,
        "entity_id": str(entity.id),
        "created_targets": created_targets,
        "subscribed_targets": subscribed_targets,
        "already_subscribed": already_subscribed,
        "existing_events": int(existing_event_count),
    }


def unsubscribe_user_from_target(
    db: Session,
    user: User,
    target_id: uuid.UUID,
) -> dict:
    """Remove the user's subscription to a scrape target.

    If this was the last subscription, the target and all its associated data
    are fully deleted (preserving the historical cleanup behaviour).
    Returns a dict with 'deleted' (bool) indicating whether the target was removed.
    """
    sub = (
        db.query(UserTargetSubscription)
        .filter(
            UserTargetSubscription.user_id == user.id,
            UserTargetSubscription.scrape_target_id == target_id,
        )
        .first()
    )

    if not sub:
        return {"deleted": False, "message": "No subscription found for this target"}

    db.delete(sub)
    db.flush()

    # Check remaining subscriptions for this target
    remaining = (
        db.query(UserTargetSubscription)
        .filter(UserTargetSubscription.scrape_target_id == target_id)
        .count()
    )

    if remaining > 0:
        db.commit()
        return {
            "deleted": False,
            "message": "Unsubscribed. Other users still tracking this entity — data preserved.",
        }

    # Last subscriber removed — fully delete the target and associated data
    return {"deleted": True, "message": "Last subscriber removed. Target and data will be cleaned up."}


def get_user_entity_labels(db: Session, user_id: uuid.UUID) -> List[str]:
    """Return the distinct entity labels for all targets the user subscribes to."""
    rows = (
        db.query(ScrapeTarget.target_name)
        .join(
            UserTargetSubscription,
            UserTargetSubscription.scrape_target_id == ScrapeTarget.id,
        )
        .filter(UserTargetSubscription.user_id == user_id)
        .distinct()
        .all()
    )
    return [r.target_name for r in rows]
