"""
Scoring logic for the screentime challenge.

Two ranking paths per day:
  - Total screentime:  rank -> points, linear (rank == points)
  - Social screentime: rank -> points, punishing (accelerates for
    worse ranks) -- generalized so the group size can shrink if
    someone is removed mid-challenge, while still reproducing the
    original tuned curve (1, 2, 3, 5, 7) at exactly 5 people.

Ties share the lowest rank of the tied group, and the next rank skips
ahead (standard competition ranking, e.g. 1, 1, 3, 4, 5).

A missing upload is scored as the worst possible rank on both paths
for whatever the CURRENT group size is -- as bad as genuinely
finishing last on both metrics, never worse and never a free pass.
"""

from dataclasses import dataclass


def _social_points_for_rank(rank: int, group_size: int) -> int:
    """
    Generalized punishing curve. At group_size=5 this reproduces the
    original hand-tuned curve exactly: 1, 2, 3, 5, 7.
    """
    threshold = max(group_size - 2, 1)
    extra = max(0, rank - threshold)
    return rank + extra


@dataclass
class DailyEntry:
    user_id: str
    total_minutes: int | None   # None = did not upload
    social_minutes: int | None  # None = did not upload


@dataclass
class DailyResult:
    user_id: str
    total_minutes: int | None
    social_minutes: int | None
    total_rank: int
    social_rank: int
    total_points: int
    social_points: int
    combined_score: int
    uploaded: bool


def _rank_with_ties(values: list[tuple[str, int]]) -> dict[str, int]:
    """
    Standard competition ranking (1, 1, 3, 4, 5) for a list of
    (user_id, value) pairs, sorted ascending (lower value = better rank).
    """
    sorted_vals = sorted(values, key=lambda pair: pair[1])
    ranks: dict[str, int] = {}

    i = 0
    while i < len(sorted_vals):
        current_value = sorted_vals[i][1]
        tied_group = [pair for pair in sorted_vals if pair[1] == current_value]
        shared_rank = i + 1
        for user_id, _ in tied_group:
            ranks[user_id] = shared_rank
        i += len(tied_group)

    return ranks


def calculate_daily_scores(entries: list[DailyEntry]) -> list[DailyResult]:
    """
    Takes one DailyEntry per current group member (however many are
    currently active -- the group size is whatever len(entries) is for
    this call, not a fixed constant) and returns each person's rank,
    points, and combined score for the day.
    """
    group_size = len(entries)
    if group_size == 0:
        return []

    max_total_points = group_size
    max_social_points = _social_points_for_rank(group_size, group_size)

    uploaded = [e for e in entries if e.total_minutes is not None and e.social_minutes is not None]
    missing = [e for e in entries if e not in uploaded]

    total_ranks = _rank_with_ties([(e.user_id, e.total_minutes) for e in uploaded])
    social_ranks = _rank_with_ties([(e.user_id, e.social_minutes) for e in uploaded])

    results: list[DailyResult] = []

    for e in uploaded:
        t_rank = total_ranks[e.user_id]
        s_rank = social_ranks[e.user_id]
        t_points = t_rank  # linear
        s_points = _social_points_for_rank(s_rank, group_size)
        results.append(DailyResult(
            user_id=e.user_id,
            total_minutes=e.total_minutes,
            social_minutes=e.social_minutes,
            total_rank=t_rank,
            social_rank=s_rank,
            total_points=t_points,
            social_points=s_points,
            combined_score=t_points + s_points,
            uploaded=True,
        ))

    for e in missing:
        results.append(DailyResult(
            user_id=e.user_id,
            total_minutes=e.total_minutes,
            social_minutes=e.social_minutes,
            total_rank=group_size,
            social_rank=group_size,
            total_points=max_total_points,
            social_points=max_social_points,
            combined_score=max_total_points + max_social_points,
            uploaded=False,
        ))

    return results


def weekly_loser(daily_results_by_day: list[list[DailyResult]]) -> str:
    totals: dict[str, int] = {}
    for day in daily_results_by_day:
        for result in day:
            totals[result.user_id] = totals.get(result.user_id, 0) + result.combined_score
    return max(totals, key=totals.get)


def challenge_loser(daily_results_by_day: list[list[DailyResult]]) -> tuple[str, int]:
    totals: dict[str, int] = {}
    for day in daily_results_by_day:
        for result in day:
            totals[result.user_id] = totals.get(result.user_id, 0) + result.combined_score
    loser_id = max(totals, key=totals.get)
    return loser_id, totals[loser_id]