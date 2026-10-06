MAX_RETRY_EXPONENT = 10


def retry_delay(attempt: int, base_delay: float) -> float:
    exponent = min(max(attempt, 0), MAX_RETRY_EXPONENT)
    return base_delay * float(1 << exponent)


def retry_interval(retry_count: int, base_delay: float) -> float:
    return retry_delay(max(retry_count - 1, 0), base_delay)
