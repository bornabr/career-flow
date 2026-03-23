"""Convert ReviewMemo dict (agent output) to InteractiveReviewMemo dict (HITL UI format).

This module provides utilities for normalizing reviewer agent outputs into
interactive format for HITL approval workflows. Assigns deterministic item keys
and simplifies structure for frontend display.
"""

from typing import Any


def normalize_review_memo(memo: dict[str, Any], reviewer_role: str) -> dict[str, Any]:
    """Convert ReviewMemo dict to InteractiveReviewMemo dict for HITL UI.
    
    Assigns deterministic item_key to each recommendation for user interaction.
    Simplifies structure for frontend display and decision tracking.
    
    Args:
        memo: ReviewMemo dict from reviewer agent (hr, technical, ats)
        reviewer_role: Role identifier ('hr', 'technical', 'ats')
    
    Returns:
        dict matching InteractiveReviewMemo shape with items keyed as "{reviewer_role}:{index}"
    """
    interactive_items: list[dict[str, Any]] = []
    
    for index, priority_change in enumerate(memo["priority_changes"]):
        item_key = f"{reviewer_role}:{index}"
        
        # Find matching ReviewItem where priority_change is substring of recommendation
        matching_item = None
        for review_item in memo["items"]:
            if priority_change.lower() in review_item["recommendation"].lower():
                matching_item = review_item
                break
        
        # Extract rationale and severity from matching item, or use defaults
        if matching_item:
            rationale = matching_item["finding"]
            severity = matching_item["severity"]
        else:
            rationale = f"Recommended by {reviewer_role} reviewer"
            severity = "suggestion"
        
        interactive_items.append({
            "item_key": item_key,
            "recommendation": priority_change,
            "rationale": rationale,
            "severity": severity,
        })
    
    # Build overall_rationale from first 2 strengths and first 2 weaknesses
    strengths_summary = ", ".join(memo["strengths"][:2])
    weaknesses_summary = ", ".join(memo["weaknesses"][:2])
    overall_rationale = f"Strengths: {strengths_summary}. Weaknesses: {weaknesses_summary}."
    
    return {
        "reviewer_role": reviewer_role,
        "items": interactive_items,
        "overall_score": memo["overall_score"],
        "overall_rationale": overall_rationale,
    }
