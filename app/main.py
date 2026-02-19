from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas.generate import GenerateRequest, GenerateResponse
from services.page_fetcher import PageFetcher
from services.qa_analyzer import QAAnalyzer
from services.report_generator import ReportGenerator
from dimensions.security import SecurityCalculator
from dimensions.ux import UxAccessibilityCalculator 
from dimensions.technical import TechnicalQualityCalculator
from dimensions.performance import PerformanceCalculator
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os




app = FastAPI(
    title="Automated QA analysis",
    version = "0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

page_fetcher = PageFetcher()
qa_analyzer = QAAnalyzer(
    security_calculator= SecurityCalculator(),
    performance_calculator=PerformanceCalculator(),
    ux_calculator=UxAccessibilityCalculator(),
    technical_quality_calculator=TechnicalQualityCalculator(),


)
report_generator = ReportGenerator()




BASE_DIR = Path(__file__).resolve().parent
FRONT_DIR = BASE_DIR / "front"

app.mount("/static", StaticFiles(directory=FRONT_DIR), name="static")
@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONT_DIR, "index.html"))

@app.post("/api/1/generate")
async def generate(payload: GenerateRequest):
    try:
        snapshot = await page_fetcher.fetch(str(payload.url), payload.setup_scripts)
        metrics_dict = await qa_analyzer.analyze(snapshot=snapshot, dimensions=payload.dimension)
        pdf_path = await report_generator.generate(url=str(payload.url), metrics=metrics_dict)
        return FileResponse(
            path=pdf_path,
            filename="report.pdf",  # name that will appear to the user
            media_type="application/pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/2/generate")
async def generate(payload: GenerateRequest):
    try:
        snapshot = await page_fetcher.fetch(str(payload.url), payload.setup_scripts)
        metrics_dict = await qa_analyzer.analyze(snapshot=snapshot, dimensions=payload.dimension)
        pdf_path = await report_generator.generate(url=str(payload.url), metrics=metrics_dict)
        
        return {
            "metrics": metrics_dict,
            "report_path": pdf_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
