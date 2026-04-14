def validate_count(spider_name, count):
    if count <= 0:
        raise ValueError(f"{spider_name} returned invalid count: {count}")
    if count < 2:
        raise ValueError(f"{spider_name} suspiciously low count: {count}")


def validate_against_previous(spider_name, previous_count, current_count):

    if previous_count is None:
        return

    if previous_count == 0:
        return

    change_ratio = current_count / previous_count

    if change_ratio < 0.5:
        raise ValueError(
            f"{spider_name}: count dropped suspiciously "
            f"{previous_count} -> {current_count}"
        )

    if change_ratio > 3:
        raise ValueError(
            f"{spider_name}: count increased suspiciously "
            f"{previous_count} -> {current_count}"
        )
