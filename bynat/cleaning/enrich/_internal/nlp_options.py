"""spaCy option normalization and cache-bucket naming for the NLP extraction."""

import hashlib
import json
from collections.abc import Iterable

__all__ = ["nlp_cache_bucket", "normalize_nlp_disable"]

_NLP_REQUIRED_PIPES = frozenset(
    {'tok2vec', 'tagger', 'attribute_ruler', 'lemmatizer', 'morphologizer'}
)


def normalize_nlp_disable(disable: Iterable[str] | str | None) -> tuple[str, ...]:
    """Normalize and validate spaCy components requested for disabling."""
    if disable is None:
        return ()

    if isinstance(disable, str):
        components: tuple = (disable,)
    else:
        try:
            components = tuple(disable)
        except TypeError as exc:
            raise TypeError(
                "disable must be None, a string, or an iterable of strings."
            ) from exc

    normalized: list[str] = []

    for component in components:
        if not isinstance(component, str):
            raise TypeError("disable must contain only strings.")

        component = component.strip()

        if not component:
            raise ValueError("disable cannot contain empty component names.")

        if component not in normalized:
            normalized.append(component)

    prohibited = sorted(set(normalized) & _NLP_REQUIRED_PIPES)

    if prohibited:
        raise ValueError(
            "disable cannot disable spaCy components required for NLP extraction: "
            f"{prohibited}."
        )

    return tuple(normalized)


def nlp_cache_bucket(target_col: str, model_identifier: str, disable: tuple[str, ...]) -> str:
    """Build a filesystem-safe cache bucket for one NLP configuration."""
    identity = json.dumps(
        [target_col, model_identifier, sorted(disable)],
        ensure_ascii = False,
        separators = (',', ':'),
    )
    digest = hashlib.sha1(identity.encode('utf-8')).hexdigest()[:16]
    return f"nlp_{digest}"