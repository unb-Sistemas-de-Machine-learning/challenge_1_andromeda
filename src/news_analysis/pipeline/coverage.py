def calculate_coverage(source_available: bool, writing_available: bool) -> int:
    if source_available and writing_available:
        return 100
    if source_available:
        return 60
    if writing_available:
        return 40
    return 0
