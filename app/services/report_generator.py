class ReportGenerator:

    async def generate(self, url: str, metrics: dict):
        return {
            "summary_score": 0.85,
            "dimensions": metrics
        }
