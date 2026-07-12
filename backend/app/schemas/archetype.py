"""Pydantic schemas for archetype survey submission.

Shape matches what `archetype_service.score_*` functions expect:
- meq: 5 items, items 1,5 on 1-5 scale; items 2,3,4 on 1-4 scale
- bfi_c: 2 items, each 1-5 (item 2 reverse-keyed server-side)
- bscs: 13 items, each 1-5 (items 2,3,4,5,7,9,10,12,13 reverse-keyed server-side)
- gp: 9 items, each 1-5 (all forward-keyed)

Frontend sends raw responses. The request boundary enforces each instrument's
item scale as a 422 before the scoring service or assignment writer runs;
server scoring still repeats the bounds defensively before reverse-keying.
"""
from pydantic import BaseModel, Field, field_validator


def _validate_item_bounds(
    values: list[int],
    bounds: list[tuple[int, int]],
    label: str,
) -> list[int]:
    for index, (value, (low, high)) in enumerate(zip(values, bounds)):
        if value < low or value > high:
            raise ValueError(
                f"{label}: item {index} value {value!r} out of range "
                f"[{low}, {high}]"
            )
    return values


class ArchetypeSurveyIn(BaseModel):
    """Full 29-item instrument battery response.

    Frontend constructs this from the UI form state; server scores and
    writes an ArchetypeAssignment row with completed=True.
    """

    meq: list[int] = Field(..., min_length=5, max_length=5)
    bfi_c: list[int] = Field(..., min_length=2, max_length=2)
    bscs: list[int] = Field(..., min_length=13, max_length=13)
    gp: list[int] = Field(..., min_length=9, max_length=9)

    @field_validator("meq")
    @classmethod
    def validate_meq_bounds(cls, values: list[int]) -> list[int]:
        return _validate_item_bounds(
            values,
            [(1, 5), (1, 4), (1, 4), (1, 4), (1, 5)],
            "meq",
        )

    @field_validator("bfi_c")
    @classmethod
    def validate_bfi_c_bounds(cls, values: list[int]) -> list[int]:
        return _validate_item_bounds(values, [(1, 5)] * 2, "bfi_c")

    @field_validator("bscs")
    @classmethod
    def validate_bscs_bounds(cls, values: list[int]) -> list[int]:
        return _validate_item_bounds(values, [(1, 5)] * 13, "bscs")

    @field_validator("gp")
    @classmethod
    def validate_gp_bounds(cls, values: list[int]) -> list[int]:
        return _validate_item_bounds(values, [(1, 5)] * 9, "gp")


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
