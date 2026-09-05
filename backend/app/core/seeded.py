import hashlib


def digest(*parts) -> bytes:
    seed = ":".join(str(part) for part in parts)
    return hashlib.sha256(seed.encode()).digest()


def token(*parts) -> str:
    return digest(*parts).hex()[:14]


def unit(*parts) -> float:
    return int.from_bytes(digest(*parts)[:8], "big") / float(1 << 64)


def pick(options: list, *parts):
    if not options:
        return None
    return options[int(unit(*parts) * len(options))]


def spread(low: float, high: float, *parts) -> float:
    return low + (high - low) * unit(*parts)
