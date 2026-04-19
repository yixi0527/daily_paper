from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.routes.helpers import serialize_source_state
from app.db.session import get_db
from app.models.journal import Journal
from app.schemas.journal import JournalDetailOut, JournalOut

router = APIRouter()


@router.get("", response_model=list[JournalDetailOut], summary="List journals")
def list_journals(db: Session = Depends(get_db)) -> list[JournalDetailOut]:
    journals = (
        db.scalars(
            select(Journal)
            .options(joinedload(Journal.source_states))
            .order_by(Journal.update_priority.desc(), Journal.journal_name.asc())
        )
        .unique()
        .all()
    )
    return [
        JournalDetailOut(
            **JournalOut.model_validate(journal).model_dump(),
            source_states=[serialize_source_state(state) for state in journal.source_states],
        )
        for journal in journals
    ]


@router.get("/{journal_slug}", response_model=JournalDetailOut, summary="Get journal detail")
def get_journal(journal_slug: str, db: Session = Depends(get_db)) -> JournalDetailOut:
    journal = db.scalar(
        select(Journal)
        .options(joinedload(Journal.source_states))
        .where(Journal.slug == journal_slug)
    )
    if journal is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Journal not found")
    return JournalDetailOut(
        **JournalOut.model_validate(journal).model_dump(),
        source_states=[serialize_source_state(state) for state in journal.source_states],
    )
