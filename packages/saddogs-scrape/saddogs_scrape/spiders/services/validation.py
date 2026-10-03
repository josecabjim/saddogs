import warnings


def validate_count(spider_name, count):
    if count <= 0:
        raise ValueError(f"{spider_name} returned invalid count: {count}")
    if count < 2:
        warnings.warn(f"{spider_name} suspiciously low count: {count}")


def validate_against_previous(spider_name, previous_count, current_count) -> bool:
    """Return True if current_count looks anomalous vs. previous_count (caller
    should save the row with needs_review=True instead of dropping it)."""

    if previous_count is None:
        return False

    if previous_count == 0:
        return False

    change_ratio = current_count / previous_count

    if change_ratio < 0.5:
        warnings.warn(
            f"{spider_name}: count dropped suspiciously "
            f"{previous_count} -> {current_count}"
        )
        return True

    if change_ratio > 3:
        warnings.warn(
            f"{spider_name}: count increased suspiciously "
            f"{previous_count} -> {current_count}"
        )
        return True

    return False
