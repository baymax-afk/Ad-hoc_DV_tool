from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.exceptions import SessionNotFoundError
from src.core.session_store import session_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionResponse(BaseModel):
    session_id: str


@router.post("", response_model=SessionResponse, status_code=201)
def create_session():
    session_id = session_store.create()
    return SessionResponse(session_id=session_id)


@router.get("/{session_id}/schema")
def get_schema(session_id: str):
    try:
        data = session_store.get(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    understanding = data.get("understanding")
    if not understanding:
        raise HTTPException(status_code=400, detail="No file uploaded for this session yet.")

    return {
        "columns": [
            {
                "name": c.name,
                "role": c.role.value,
                "null_pct": c.null_pct,
                "cardinality": c.cardinality,
                "sample_values": c.sample_values[:5],
                "mean": c.mean,
                "distribution": c.distribution,
            }
            for c in understanding.columns
        ],
        "row_count": understanding.profile.row_count,
        "col_count": understanding.profile.col_count,
        "has_time_series": understanding.has_time_series,
        "parse_warnings": understanding.profile.parse_warnings,
    }


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    session_store.delete(session_id)
