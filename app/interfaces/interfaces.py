from abc import ABC, abstractmethod
from typing import Dict, Any
from services.page_fetcher import PageSnapshot


class DimensionCalculator(ABC):

    @abstractmethod
    def calculate(self, snapshot: PageSnapshot) -> Dict[str, Any]:
        """
        Executes all metrics for this dimension.
        Returns a dictionary of metric_name -> metric_value.
        """
        pass

    @property
    @abstractmethod
    def name(self) ->str:
        """
        Returns the dimension name.
        """
        pass