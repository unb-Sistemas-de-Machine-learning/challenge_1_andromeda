def calculate_coverage(available: dict[str, bool], intended_weights: dict[str, float]) -> int:
    return round(
        sum(
            intended_weights[key] * 100
            for key, is_available in available.items()
            if is_available
        )
    )
