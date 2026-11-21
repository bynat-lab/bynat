"""Binding and wrapper mechanics for the `df.bynat` accessor.

These factories adapt shared functional implementations to the accessor
surface: they replace the frame parameter with `self`, hide the internal
`cache_manager`, expose the accessor-facing signature, and implement the
`inplace` mutation contract. They contain no domain algorithms.
"""

import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bynat._accessors.dataframe import BynatAccessor

__all__: list[str] = []


def _method_signature(func: Callable) -> inspect.Signature:
    """
    The accessor-facing signature: `self` replaces the frame, no `cache_manager`.

    Args:
        func (Callable): Shared implementation function.

    Returns:
        inspect.Signature: The signature with the frame parameter replaced by
        `self` and any `cache_manager` parameter removed.
    """
    signature = inspect.signature(func)
    parameters = [
        parameter
        for parameter in list(signature.parameters.values())[1:]
        if parameter.name != 'cache_manager'
    ]
    self_parameter = inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return signature.replace(parameters = [self_parameter, *parameters])


def _with_inplace(
    signature: inspect.Signature, before: str | None = None
) -> tuple[inspect.Signature, bool, int]:
    """Insert `inplace` where the class API declares it.

    Returns:
        tuple[inspect.Signature, bool, int]: The new signature, whether
        `inplace` is keyword-only, and its index among the positional
        parameters. Without ``before``, `inplace` follows the last
        positional-or-keyword parameter; when the wrapped function takes
        variadic positional arguments there is no free positional slot, so it
        leads the keyword-only parameters instead. ``position`` is -1 when
        `inplace` is keyword-only.

    Raises:
        ValueError: If ``before`` is not a parameter of the signature, or if a
            positional `inplace` would have to be inserted before a required
            parameter.
    """
    parameters = list(signature.parameters.values())
    kind: inspect._ParameterKind
    if before is not None:
        index = next(
            position
            for position, parameter in enumerate(parameters)
            if parameter.name == before
        )
        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
    else:
        index = next(
            (
                position
                for position, parameter in enumerate(parameters)
                if parameter.kind
                in (
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ),
            len(parameters),
        )
        if index < len(parameters) and parameters[index].kind is inspect.Parameter.VAR_POSITIONAL:
            # No free positional slot: `inplace` becomes the first
            # keyword-only parameter, i.e. it goes AFTER the *args.
            kind = inspect.Parameter.KEYWORD_ONLY
            index += 1
        else:
            kind = inspect.Parameter.POSITIONAL_OR_KEYWORD

    position = sum(
        1
        for parameter in parameters[1:index]
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )
    parameters.insert(index, inspect.Parameter('inplace', kind, default = False))
    return signature.replace(parameters = parameters), kind is inspect.Parameter.KEYWORD_ONLY, position


def _frame_method(
    func: Callable, *, inplace: bool = False, stats: bool = False, inplace_before: str | None = None
) -> Callable:
    """Expose a shared implementation as an accessor method on the wrapped frame.

    The generated method's `__signature__` and `__doc__` come from the shared
    function, so `inspect.signature` and `help` show the accessor-facing
    signature. `tools/sync_docs.py` reads these factory calls to generate
    `accessor.pyi`.

    Args:
        func (Callable): Shared implementation whose first parameter is the
            frame.
        inplace (bool): Add an `inplace` parameter and implement the
            mutation/`None` contract. Defaults to False.
        stats (bool): The shared function can return a `(frame, statistics)`
            tuple, so `inplace=True` returns the statistics instead of None.
            Defaults to False.
        inplace_before (str | None): Name of the parameter `inplace` is
            inserted before, matching the `BaseData` method's positional slot.
            Defaults to None.

    Returns:
        Callable: The accessor method.

    Notes:
        When `inplace` is positional, a caller-supplied positional at that
        index is consumed as the flag and the remaining positionals are passed
        on to the shared function. When it is keyword-only, the flag is popped
        from `kwargs` before the call.
    """
    signature = _method_signature(func)
    keyword_only = True
    position = -1
    if inplace:
        signature, keyword_only, position = _with_inplace(signature, before = inplace_before)

    if inplace:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            if keyword_only:
                flag = kwargs.pop('inplace', False)
            elif position >= 0 and len(args) > position:
                # `inplace` sits at `position`, so any further positional
                # arguments belong to the parameters that follow it and must
                # be handed on rather than dropped.
                flag = args[position]
                args = args[:position] + args[position + 1 :]
            else:
                flag = kwargs.pop('inplace', False)

            with_stats = stats and bool(kwargs.get('get_hierarchical_stats', False))
            outcome = func(self._obj, *args, **kwargs)

            if not flag:
                return outcome

            result, statistics = outcome if with_stats else (outcome, None)
            self._obj._update_inplace(result)  # type: ignore[operator]
            return statistics
    else:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            return func(self._obj, *args, **kwargs)

    method.__signature__ = signature  # type: ignore[attr-defined]
    return method


def _cached_frame_method(
    func: Callable, *, inplace: bool = False, inplace_before: str | None = None
) -> Callable:
    """Like `_frame_method`, also passing the accessor's `CacheManager`.

    Args:
        func (Callable): Shared cached implementation whose first parameter is
            the frame and which takes a keyword-only `cache_manager`.
        inplace (bool): Add an `inplace` parameter and implement the
            mutation/`None` contract. Defaults to False.
        inplace_before (str | None): Name of the parameter `inplace` is
            inserted before, matching the `BaseData` method's positional slot.
            Defaults to None.

    Returns:
        Callable: The accessor method, which passes `self.cache_manager` to
        the shared function.

    Notes:
        The generated method's `__signature__` omits both the frame and
        `cache_manager`, and its `__doc__` comes from the shared function.
    """
    signature = _method_signature(func)
    keyword_only = True
    position = -1
    if inplace:
        signature, keyword_only, position = _with_inplace(signature, before = inplace_before)

    if inplace:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            if keyword_only:
                flag = kwargs.pop('inplace', False)
            elif position >= 0 and len(args) > position:
                # See `_frame_method`: keep the arguments that follow `inplace`.
                flag = args[position]
                args = args[:position] + args[position + 1 :]
            else:
                flag = kwargs.pop('inplace', False)

            result = func(self._obj, *args, cache_manager = self.cache_manager, **kwargs)

            if not flag:
                return result

            self._obj._update_inplace(result)  # type: ignore[operator]
            return None
    else:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            return func(self._obj, *args, cache_manager = self.cache_manager, **kwargs)

    method.__signature__ = signature  # type: ignore[attr-defined]
    return method
