from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Interaction


def create_interaction(
    db: Session,
    request_type: str,
    input_summary: str | None,
    output: dict[str, Any],
    model: str | None,
    status_code: int = 200,
) -> Interaction:
    interaction = Interaction(
        request_type=request_type,
        input_summary=input_summary,
        output=output,
        model=model,
        status_code=status_code,
    )

    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return interaction


def list_interactions(
    db: Session,
    limit: int = 50,
    request_type: str | None = None,
) -> list[Interaction]:
    query = db.query(Interaction)

    if request_type:
        query = query.filter(Interaction.request_type == request_type)

    return query.order_by(desc(Interaction.created_at)).limit(limit).all()


def get_interaction(db: Session, interaction_id: int) -> Interaction | None:
    return db.query(Interaction).filter(Interaction.id == interaction_id).first()


def interaction_to_dict(interaction: Interaction) -> dict[str, Any]:
    return {
        "id": interaction.id,
        "request_type": interaction.request_type,
        "input_summary": interaction.input_summary,
        "model": interaction.model,
        "status_code": interaction.status_code,
        "output": interaction.output,
        "created_at": interaction.created_at,
    }
