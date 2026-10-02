"""Deterministic category filtering before any model reading."""
import re

DEFAULT_CATEGORIES = ("astro-ph.GA", "astro-ph.CO")


def select_papers(papers, categories=DEFAULT_CATEGORIES):
    categories = tuple(sorted(set(categories)))
    if not categories or any(not re.fullmatch(r"[A-Za-z][A-Za-z.-]+", c) for c in categories):
        raise ValueError("Provide valid arXiv category codes")
    selected, excluded, unclassified = [], [], []
    for paper in papers:
        subjects = paper.get("subjects")
        if not isinstance(subjects, str) or not subjects.strip():
            unclassified.append(paper["arxiv_id"])
            continue
        matches = [c for c in categories if re.search(r"(?<![\w.-])" + re.escape(c) + r"(?![\w.-])", subjects)]
        if matches:
            selected.append(paper)
        else:
            excluded.append(paper["arxiv_id"])
    if unclassified:
        raise ValueError(f"Missing source categories for {len(unclassified)} papers; cannot verify complete filtering")
    return selected, {"categories": list(categories), "match": "any primary or cross-listed category",
                      "source_count": len(papers), "selected_count": len(selected),
                      "excluded_count": len(excluded)}
