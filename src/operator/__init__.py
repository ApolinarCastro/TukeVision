"""Operator AI Foundation (AG-05 / OC-13, OC-14).

Explainable OperatorInsight generation and structured query experience.
No automatic accusation - only ACTIVITY_REQUIRES_REVIEW.
"""

from src.operator.engine import (
    OperatorInsightGenerator,
    OperatorQuery,
    OperatorQueryEngine,
    QueryResult,
)

__all__ = [
    "OperatorInsightGenerator",
    "OperatorQuery",
    "OperatorQueryEngine",
    "QueryResult",
]