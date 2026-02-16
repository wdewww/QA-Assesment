from fastapi import FastAPI, HTTPException
from schemas.generate import GenerateRequest, GenerateResponse
from services.page_fetcher import PageFetcher
from services.qa_analyzer import QAAnalyzer
from services.report_generator import ReportGenerator
from dimensions.security import SecurityCalculator
from dimensions.ux import UxAccessibilityCalculator 
from dimensions.technical import TechnicalQualityCalculator
from dimensions.performance import PerformanceCalculator

app = FastAPI(
    title="Automated QA analysis",
    version = "0.1.0",
)

page_fetcher = PageFetcher()
qa_analyzer = QAAnalyzer(
    security_calculator= SecurityCalculator(),
    performance_calculator=PerformanceCalculator(),
    ux_calculator=UxAccessibilityCalculator(),
    technical_quality_calculator=TechnicalQualityCalculator(),


)
report_generator = ReportGenerator()


@app.post("/generate")
async def generate(payload: GenerateRequest):
    try:
        snapshot = await page_fetcher.fetch(str(payload.url), payload.setup_scripts)
        metrics_dict = await qa_analyzer.analyze(snapshot=snapshot, dimensions=payload.dimension)
        
        return metrics_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
