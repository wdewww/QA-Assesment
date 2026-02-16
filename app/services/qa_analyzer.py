from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import asyncio
from services.page_fetcher import PageSnapshot
from interfaces.interfaces import DimensionCalculator
from dimensions.security import SecurityCalculator



class QAAnalyzer:

    def __init__(
        self,
        security_calculator: SecurityCalculator,
        performance_calculator: DimensionCalculator,
        ux_calculator: DimensionCalculator,
        technical_quality_calculator: DimensionCalculator,
        max_workers: int  = 8,
    ):
        self._calculators = {
            security_calculator.name: security_calculator,
            performance_calculator.name: performance_calculator,
            ux_calculator.name: ux_calculator,
            technical_quality_calculator.name: technical_quality_calculator,
        }

        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def analyze(
        self,
        snapshot: PageSnapshot,
        dimensions: List[str],
    ) -> Dict[str, Dict[str, Any]]:

        loop = asyncio.get_running_loop()
        tasks = []

        for dimension_name in dimensions:

            if dimension_name not in self._calculators:
                raise ValueError(f"Unsupported dimension: {dimension_name}")

            calculator = self._calculators[dimension_name]

            task = loop.run_in_executor(
                self._executor,
                calculator.calculate,
                snapshot,
            )

            tasks.append((dimension_name, task))

        results = {}

        for dimension_name, task in tasks:
            metrics = await task
            results[dimension_name] = metrics

        return results
