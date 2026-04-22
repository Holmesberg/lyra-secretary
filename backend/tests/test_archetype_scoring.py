"""Unit tests for instrument scoring + archetype assignment.

Covers the 2026-04-22 clustering service (see app/services/archetype_service.py).
Fixtures include boundary values, reverse-keying correctness, classification
thresholds, and all 5 archetype cells.
"""
import pytest

from app.services.archetype_service import (
    DIFFUSE_AVERAGE_ID,
    assign_archetype,
    classify_discipline,
    compute_discipline_z,
    score_bfi_c,
    score_bscs,
    score_gp,
    score_meq,
)


# ---------------------------------------------------------------------------
# MEQ-5 — chronotype classification
# ---------------------------------------------------------------------------

class TestMeq5:
    def test_min_evening(self):
        # Items 1,5 in 1-5, items 2,3,4 in 1-4 → min sum = 5 (5×1).
        assert score_meq([1, 1, 1, 1, 1]) == (5, "evening")

    def test_max_morning(self):
        # Max = 5+4+4+4+5 = 22 → morning.
        assert score_meq([5, 4, 4, 4, 5]) == (22, "morning")

    def test_boundary_evening_intermediate(self):
        # Sum 11 → evening. Sum 12 → intermediate.
        assert score_meq([3, 2, 2, 2, 2])[1] == "evening"  # 11
        assert score_meq([3, 2, 2, 2, 3])[1] == "intermediate"  # 12

    def test_sum_18_is_morning(self):
        assert score_meq([5, 3, 3, 3, 4])[1] == "morning"

    def test_sum_17_is_intermediate(self):
        assert score_meq([5, 3, 3, 3, 3])[1] == "intermediate"

    def test_rejects_wrong_count(self):
        with pytest.raises(ValueError):
            score_meq([3, 3, 3])

    def test_rejects_out_of_range_item_1(self):
        # Item 1 allows 1-5; 6 is out of range.
        with pytest.raises(ValueError):
            score_meq([6, 3, 3, 3, 3])

    def test_rejects_out_of_range_middle_item(self):
        # Items 2,3,4 allow 1-4; 5 is out of range.
        with pytest.raises(ValueError):
            score_meq([3, 5, 3, 3, 3])


# ---------------------------------------------------------------------------
# BFI-10 C — conscientiousness, with reverse-keying on item 2
# ---------------------------------------------------------------------------

class TestBfi10C:
    def test_min_low_all_disagree_with_forward(self):
        # Item 1 = 1 (forward: strongly disagree with "thorough job").
        # Item 2 = 5 (reverse-keyed: strongly agree with "lazy" → reversed to 1).
        # Total = 1 + 1 = 2.
        assert score_bfi_c([1, 5]) == (2, "low")

    def test_max_high(self):
        # Item 1 = 5 (thorough). Item 2 = 1 (strongly disagree with lazy → reversed to 5).
        # Total = 5 + 5 = 10.
        assert score_bfi_c([5, 1]) == (10, "high")

    def test_mid_balanced(self):
        # Item 1 = 3. Item 2 = 3 → reversed to 3. Total = 6 → mid.
        assert score_bfi_c([3, 3]) == (6, "mid")

    def test_boundary_low_mid(self):
        # Total 4 → low. Total 5 → mid.
        assert score_bfi_c([2, 4])[1] == "low"  # 2 + (6-4)=2 → 4
        assert score_bfi_c([2, 3])[1] == "mid"  # 2 + (6-3)=3 → 5

    def test_boundary_mid_high(self):
        # Total 7 → mid. Total 8 → high.
        assert score_bfi_c([4, 3])[1] == "mid"  # 4 + 3 = 7
        assert score_bfi_c([4, 2])[1] == "high"  # 4 + 4 = 8

    def test_rejects_wrong_count(self):
        with pytest.raises(ValueError):
            score_bfi_c([3])

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            score_bfi_c([0, 3])


# ---------------------------------------------------------------------------
# BSCS-Brief — 13 items with 9 reverse-keyed (2,3,4,5,7,9,10,12,13)
# ---------------------------------------------------------------------------

class TestBscs:
    def test_all_threes_midpoint(self):
        # All 3s: forward items score 3, reverse items score (6-3)=3.
        # Total = 13 × 3 = 39 → mid (tertile 34-45).
        assert score_bscs([3] * 13) == (39, "mid")

    def test_all_ones_produces_high_after_reverse(self):
        # All 1s: forward items (4 of them: 1,6,8,11) score 1 each → 4.
        # Reverse items (9 of them) score (6-1)=5 each → 45.
        # Total = 4 + 45 = 49 → high.
        assert score_bscs([1] * 13) == (49, "high")

    def test_all_fives_produces_low_after_reverse(self):
        # All 5s: forward items score 5 × 4 = 20.
        # Reverse items score (6-5)=1 × 9 = 9.
        # Total = 20 + 9 = 29 → low (≤33).
        assert score_bscs([5] * 13) == (29, "low")

    def test_forward_keyed_items_score_as_given(self):
        # Forward items are at positions 0, 5, 7, 10 (1-indexed: 1, 6, 8, 11).
        # Put 5 on only those and 1 on the reverse-keyed items.
        items = [0] * 13
        for idx_1 in (1, 6, 8, 11):
            items[idx_1 - 1] = 5
        for idx_1 in (2, 3, 4, 5, 7, 9, 10, 12, 13):
            items[idx_1 - 1] = 1
        # Forward sum: 4 × 5 = 20. Reverse sum: 9 × (6-1) = 45. Total = 65 (max).
        total, level = score_bscs(items)
        assert total == 65
        assert level == "high"

    def test_boundary_low_mid(self):
        # 33 → low. 34 → mid.
        # All 3s gives 39 → mid. Need to construct 33 + 34.
        # 39 - 6 = 33. Subtract from forward items (3→1 on 3 forward items = -6)
        items = [3] * 13
        items[0] = 1  # -2
        items[5] = 1  # -2
        items[7] = 1  # -2
        # Total: forward = 1+3+1+3 = 8 (items 1,6,8,11 with 1,3,1,3 via positions 0,5,7,10). Wait let me recount.
        # items[0] forward (item 1): was 3, now 1 → -2
        # items[5] forward (item 6): was 3, now 1 → -2
        # items[7] forward (item 8): was 3, now 1 → -2
        # items[10] forward (item 11): unchanged at 3
        # Reverse items: all still 3 → each contributes (6-3)=3.
        # Forward sum: 1+1+1+3 = 6. Reverse sum: 9 × 3 = 27. Total = 33.
        total, level = score_bscs(items)
        assert total == 33
        assert level == "low"

    def test_boundary_mid_high(self):
        # 45 → mid. 46 → high.
        # All 3s = 39. Need 45 = add 6.
        # Increase forward items by 2 each on 3 forward items.
        items = [3] * 13
        items[0] = 5  # +2
        items[5] = 5  # +2
        items[7] = 5  # +2
        # Forward sum: 5+5+5+3 = 18. Reverse sum: 27. Total = 45.
        total, level = score_bscs(items)
        assert total == 45
        assert level == "mid"

    def test_rejects_wrong_count(self):
        with pytest.raises(ValueError):
            score_bscs([3] * 12)


# ---------------------------------------------------------------------------
# GP-Short — 9 items all forward-keyed
# ---------------------------------------------------------------------------

class TestGpShort:
    def test_min_low_procrastination(self):
        assert score_gp([1] * 9) == (9, "low")

    def test_max_high_procrastination(self):
        assert score_gp([5] * 9) == (45, "high")

    def test_boundary_low_mid(self):
        # Sum 20 → low. Sum 21 → mid.
        assert score_gp([2, 2, 2, 2, 2, 2, 2, 2, 4]) == (20, "low")   # 20
        assert score_gp([2, 2, 2, 2, 2, 2, 2, 2, 5]) == (21, "mid")   # 21

    def test_boundary_mid_high(self):
        # Sum 32 → mid. Sum 33 → high.
        # 32 = 8×3 + 1×8 — nope, 8+24=32 with 1 item =8 ... items are 1-5.
        # 3+3+3+3+3+3+3+3+8 invalid. Let's: 4+4+4+4+4+4+4+3+1 = 32.
        items_32 = [4, 4, 4, 4, 4, 4, 4, 3, 1]
        assert sum(items_32) == 32
        assert score_gp(items_32) == (32, "mid")
        items_33 = [4, 4, 4, 4, 4, 4, 4, 3, 2]
        assert sum(items_33) == 33
        assert score_gp(items_33) == (33, "high")

    def test_rejects_wrong_count(self):
        with pytest.raises(ValueError):
            score_gp([3] * 10)


# ---------------------------------------------------------------------------
# discipline_z composite
# ---------------------------------------------------------------------------

class TestDisciplineZ:
    def test_all_at_mean_returns_zero(self):
        # bfi_c mean 6, bscs mean 39, gp mean 28.
        assert abs(compute_discipline_z(6, 39, 28)) < 1e-6

    def test_high_discipline_positive(self):
        # High BFI-C (8), high BSCS (50), low GP (15).
        z = compute_discipline_z(8, 50, 15)
        # z(bfi_c) = (8-6)/1.8 ≈ 1.11
        # z(bscs) = (50-39)/8 = 1.375
        # z(gp)   = (15-28)/7.5 ≈ -1.733
        # composite = 0.30*1.11 + 0.40*1.375 + 0.30*1.733 ≈ 0.333 + 0.550 + 0.520 = 1.403
        assert z > 1.0

    def test_low_discipline_negative(self):
        z = compute_discipline_z(3, 25, 40)
        assert z < -1.0


class TestClassifyDiscipline:
    def test_low_at_minus_half(self):
        assert classify_discipline(-0.5) == "low"

    def test_high_at_plus_half(self):
        assert classify_discipline(0.5) == "high"

    def test_mid_at_zero(self):
        assert classify_discipline(0.0) == "mid"

    def test_boundary_low_tertile(self):
        assert classify_discipline(-0.43) == "low"
        assert classify_discipline(-0.42) == "mid"

    def test_boundary_high_tertile(self):
        assert classify_discipline(0.43) == "high"
        assert classify_discipline(0.42) == "mid"


# ---------------------------------------------------------------------------
# Archetype assignment — all 5 cells + ambiguity-clarification cases
# ---------------------------------------------------------------------------

class TestAssignArchetype:
    def test_morning_high_is_disciplined_lark(self):
        assert assign_archetype("morning", "high") == "disciplined_lark"

    def test_evening_high_is_disciplined_owl(self):
        assert assign_archetype("evening", "high") == "disciplined_owl"

    def test_morning_low_is_lark_low_discipline(self):
        # Specific-first: morning+low → Lark Low-Discipline, NOT Procrastinator.
        assert assign_archetype("morning", "low") == "lark_low_discipline"

    def test_evening_low_is_procrastinator(self):
        assert assign_archetype("evening", "low") == "procrastinator"

    def test_intermediate_low_is_procrastinator(self):
        assert assign_archetype("intermediate", "low") == "procrastinator"

    def test_morning_mid_is_diffuse_average(self):
        assert assign_archetype("morning", "mid") == "diffuse_average"

    def test_evening_mid_is_diffuse_average(self):
        assert assign_archetype("evening", "mid") == "diffuse_average"

    def test_intermediate_mid_is_diffuse_average(self):
        assert assign_archetype("intermediate", "mid") == "diffuse_average"

    def test_intermediate_high_is_diffuse_average(self):
        # Methodology table: only morning+high and evening+high are Disciplined;
        # intermediate+high falls through to the default bucket.
        assert assign_archetype("intermediate", "high") == "diffuse_average"

    def test_diffuse_average_id_constant(self):
        assert DIFFUSE_AVERAGE_ID == "diffuse_average"
