def calculate_coverage(available: dict[str, bool], weights: dict[str, float]) -> int:
    """Share of intended scoring weight backed by available criteria."""
    return round(100 * sum(weights[name] for name, active in available.items() if active))
