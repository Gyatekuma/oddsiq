"""Market prediction strategies."""
from .base_market_strategy import BaseMarketStrategy
from .over_under_strategy import OverUnderStrategy
from .btts_strategy import BTTSStrategy
from .double_chance_strategy import DoubleChanceStrategy
from .corners_strategy import CornersStrategy
from .ht_ft_strategy import HTFTStrategy

__all__ = [
    'BaseMarketStrategy',
    'OverUnderStrategy',
    'BTTSStrategy',
    'DoubleChanceStrategy',
    'CornersStrategy',
    'HTFTStrategy',
]
