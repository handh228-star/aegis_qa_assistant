from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import init_db
from app.api import projects, documents, testcases, manuals, defects, crawler, rulesets

app = FastAPI(
    title="Aegis QA Assistant",
    description="AI 기반 테스트케이스 자동 생성 시스템",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(testcases.router, prefix="/api")
app.include_router(manuals.router, prefix="/api")
app.include_router(defects.router, prefix="/api")
app.include_router(crawler.router, prefix="/api")
app.include_router(rulesets.router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Aegis QA Assistant API", "docs": "/docs"}
