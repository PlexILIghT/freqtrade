"""
IHyperStrategy interface, hyperoptable Parameter class.
This module defines a base class for auto-hyperoptable strategies.
"""
from contextlib import suppress
from typing import Iterator, Tuple, Any, Optional, Sequence, Union

with suppress(ImportError):
    from skopt.space import Integer, Real, Categorical

from freqtrade.exceptions import OperationalException


class BaseParameter(object):
    """
    Defines a parameter that can be optimized by hyperopt.
    """
    category: Optional[str]
    default: Any
    value: Any
    opt_range: Sequence[Any]

    def __init__(self, *, opt_range: Sequence[Any], default: Any, space: Optional[str] = None,
                 **kwargs):
        """
        Initialize hyperopt-optimizable parameter.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param kwargs: Extra parameters to skopt.space.(Integer|Real|Categorical).
        """
        if 'name' in kwargs:
            raise OperationalException(
                'Name is determined by parameter field name and can not be specified manually.')
        self.category = space
        self._space_params = kwargs
        self.value = default
        self.opt_range = opt_range

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value})'

    def get_space(self, name: str) -> Union['Integer', 'Real', 'Categorical']:
        raise NotImplementedError()


class IntParameter(BaseParameter):
    default: int
    value: int
    opt_range: Sequence[int]

    def __init__(self, low: Union[int, Sequence[int]], high: Optional[int] = None, *, default: int,
                 space: Optional[str] = None, **kwargs):
        """
        Initialize hyperopt-optimizable parameter.
        :param low: lower end of optimization space or [low, high].
        :param high: high end of optimization space. Must be none of entire range is passed first parameter.
        :param default: A default value.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param kwargs: Extra parameters to skopt.space.Integer.
        """
        if high is None:
            if len(low) != 2:
                raise OperationalException('IntParameter space must be [low, high]')
            opt_range = low
        else:
            opt_range = [low, high]
        super().__init__(opt_range=opt_range, default=default, space=space, **kwargs)

    def get_space(self, name: str) -> 'Integer':
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Integer(*self.opt_range, name=name, **self._space_params)


class FloatParameter(BaseParameter):
    default: float
    value: float
    opt_range: Sequence[float]

    def __init__(self, low: Union[float, Sequence[float]], high: Optional[int] = None, *,
                 default: float, space: Optional[str] = None, **kwargs):
        """
        Initialize hyperopt-optimizable parameter.
        :param low: lower end of optimization space or [low, high].
        :param high: high end of optimization space. Must be none of entire range is passed first parameter.
        :param default: A default value.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param kwargs: Extra parameters to skopt.space.Real.
        """
        if high is None:
            if len(low) != 2:
                raise OperationalException('IntParameter space must be [low, high]')
            opt_range = low
        else:
            opt_range = [low, high]
        super().__init__(opt_range=opt_range, default=default, space=space, **kwargs)

    def get_space(self, name: str) -> 'Real':
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Real(*self.opt_range, name=name, **self._space_params)


class CategoricalParameter(BaseParameter):
    default: Any
    value: Any
    opt_range: Sequence[Any]

    def __init__(self, categories: Sequence[Any], *, default: Optional[Any] = None,
                 space: Optional[str] = None, **kwargs):
        """
        Initialize hyperopt-optimizable parameter.
        :param categories: Optimization space, [a, b, ...].
        :param default: A default value. If not specified, first item from specified space will be
         used.
        :param space: A parameter category. Can be 'buy' or 'sell'. This parameter is optional if
         parameter field
         name is prefixed with 'buy_' or 'sell_'.
        :param kwargs: Extra parameters to skopt.space.Categorical.
        """
        if len(categories) < 2:
            raise OperationalException(
                'IntParameter space must be [a, b, ...] (at least two parameters)')
        super().__init__(opt_range=categories, default=default, space=space, **kwargs)

    def get_space(self, name: str) -> 'Categorical':
        """
        Create skopt optimization space.
        :param name: A name of parameter field.
        """
        return Categorical(self.opt_range, name=name, **self._space_params)


class HyperStrategyMixin(object):
    """
    A helper base class which allows HyperOptAuto class to reuse implementations of of buy/sell
     strategy logic.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize hyperoptable strategy mixin.
        """
        self._load_params(getattr(self, 'buy_params', None))
        self._load_params(getattr(self, 'sell_params', None))

    def enumerate_parameters(self, category: str = None) -> Iterator[Tuple[str, BaseParameter]]:
        """
        Find all optimizeable parameters and return (name, attr) iterator.
        :param category:
        :return:
        """
        if category not in ('buy', 'sell', None):
            raise OperationalException('Category must be one of: "buy", "sell", None.')
        for attr_name in dir(self):
            if not attr_name.startswith('__'):  # Ignore internals, not strictly necessary.
                attr = getattr(self, attr_name)
                if issubclass(attr.__class__, BaseParameter):
                    if category is None or category == attr.category or \
                       attr_name.startswith(category + '_'):
                        yield attr_name, attr

    def _load_params(self, params: dict) -> None:
        """
        Set optimizeable parameter values.
        :param params: Dictionary with new parameter values.
        """
        if not params:
            return
        for attr_name, attr in self.enumerate_parameters():
            if attr_name in params:
                attr.value = params[attr_name]
