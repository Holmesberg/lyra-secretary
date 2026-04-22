"""Pydantic schemas for archetype survey submission.

Shape matches what `archetype_service.score_*` functions expect:
- meq: 5 items, items 1,5 on 1-5 scale; items 2,3,4 on 1-4 scale
- bfi_c: 2 items, each 1-5 (item 2 reverse-keyed server-side)
- bscs: 13 items, each 1-5 (items 2,3,4,5,7,9,10,12,13 reverse-keyed server-side)
- gp: 9 items, each 1-5 (all forward-keyed)

Frontend sends raw 1-5 responses. Server handles reverse-keying + range
validation. Out-of-range values fail loud via ValueError in the service,
surfaced here as 400 by FastAPI.
"""
from pydantic import BaseModel, Field


class ArchetypeSurveyIn(BaseModel):
    """Full 29-item instrument battery response.

    Frontend constructs this from the UI form state; server scores and
    writes an ArchetypeAssignment row with completed=True.
    """

    meq: list[int] = Field(..., min_length=5, max_length=5)
    bfi_c: list[int] = Field(..., min_length=2, max_length=2)
    bscs: list[int] = Field(..., min_length=13, max_length=13)
    gp: list[int] = Field(..., min_length=9, max_length=9)


class ArchetypeAssignmentOut(BaseModel):
    """Response shape for both submit and skip endpoints.

    archetype_id tells the frontend which archetype prior is now active
    for this user's bias_factor blend. completed=True when user answered
    the full battery; False on skip (Diffuse Average defaulted).
    """

    archetype_id: str
    completed: bool
    chronotype: str | None = None
    discipline_z: float | None = None
    meq_score: int | None = None
    bfi_c_score: int | None = None
    bscs_score: int | None = None
    gp_score: int | None = None
