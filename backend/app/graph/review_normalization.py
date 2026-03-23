"""Convert ReviewMemo (agent output) to InteractiveReviewMemo (HITL UI format).

This module provides utilities for normalizing reviewer agent outputs into
interactive format for HITL approval workflows. Assigns deterministic item keys
and simplifies structure for frontend display.
"""

from app.schemas.review import ReviewMemo, InteractiveReviewMemo, InteractiveReviewItem


def normalize_review_memo(memo: ReviewMemo, reviewer_role: str) -> InteractiveReviewMemo:
    """Convert ReviewMemo (agent output) to InteractiveReviewMemo (HITL UI format).
    
    Assigns deterministic item_key to each recommendation for user interaction.
    Simplifies structure for frontend display and decision tracking.
    
    The normalization process:
    1. Iterates through memo.priority_changes (top 3 recommendations)
    2. For each change at index i:
       - Creates item_key = "{reviewer_role}:{i}"
       - Finds matching ReviewItem where priority_change is substring of item.recommendation
       - Extracts rationale from item.finding and severity from item.severity
       - Falls back to generic rationale and "suggestion" severity if no match
    3. Builds overall_rationale from first 2 strengths and first 2 weaknesses
    4. Returns InteractiveReviewMemo with all fields populated
    
    Args:
        memo: ReviewMemo from reviewer agent (hr, technical, ats)
        reviewer_role: Role identifier ('hr', 'technical', 'ats')
    
    Returns:
        InteractiveReviewMemo with items keyed as "{reviewer_role}:{index}"
    """
    interactive_items: list[InteractiveReviewItem] = []
    
    for index, priority_change in enumerate(memo.priority_changes):
        item_key = f"{reviewer_role}:{index}"
        
        # Find matching ReviewItem where priority_change is substring of recommendation
        matching_item = None
        for review_item in memo.items:
            if priority_change.lower() in review_item.recommendation.lower():
                matching_item = review_item
                break
        
        # Extract rationale and severity from matching item, or use defaults
        if matching_item:
            rationale = matching_item.finding
            severity = matching_item.severity
        else:
            rationale = f"Recommended by {reviewer_role} reviewer"
            severity = "suggestion"
        
        interactive_item = InteractiveReviewItem(
            item_key=item_key,
            recommendation=priority_change,
            rationale=rationale,
            severity=severity,
        )
        interactive_items.append(interactive_item)
    
    # Build overall_rationale from first 2 strengths and first 2 weaknesses
    strengths_summary = ", ".join(memo.strengths[:2])
    weaknesses_summary = ", ".join(memo.weaknesses[:2])
    overall_rationale = f"Strengths: {strengths_summary}. Weaknesses: {weaknesses_summary}."
    
    return InteractiveReviewMemo(
        reviewer_role=reviewer_role,
        items=interactive_items,
        overall_score=memo.overall_score,
        overall_rationale=overall_rationale,
    )
