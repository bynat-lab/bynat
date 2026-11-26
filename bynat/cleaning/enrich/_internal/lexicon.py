"""Lexicon traversal helper for the NLP entity extraction."""

from typing import Any

__all__ = ["lexicon_terms"]


def lexicon_terms(lexicon_data: Any, keys_to_match: list) -> set[str]:
    """Collect lowercase terms found under any of the requested lexicon keys.

    Args:
        lexicon_data (Any): Nested dict/list lexicon payload.
        keys_to_match (list): Keys whose values are collected as terms.

    Returns:
        set[str]: Lowercase terms found under the requested keys.
    """
    extracted_terms = set()

    stack = [(lexicon_data, False)]

    while stack:
        current_node, is_inside = stack.pop()

        if isinstance(current_node, dict):
            for k, v in current_node.items():
                current_is_target = is_inside or (str(k) in keys_to_match)

                if current_is_target and isinstance(v, bool) and v is True:
                    term = str(k).strip().lower()

                    if term:
                        extracted_terms.add(term)

                elif current_is_target and isinstance(v, str):
                    term = str(v).strip().lower()

                    if term:
                        extracted_terms.add(term)

                elif isinstance(v, (dict, list)):
                    stack.append((v, current_is_target))

        elif isinstance(current_node, list):
            for item in current_node:
                if is_inside and isinstance(item, str):
                    term = str(item).strip().lower()

                    if term:
                        extracted_terms.add(term)

                elif isinstance(item, (dict, list)):
                    stack.append((item, is_inside))

    return extracted_terms
