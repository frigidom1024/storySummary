from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import auth, users, books

app = FastAPI(
    title="Story Summary API",
    description="API for story summarization and narrative analysis",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)


@app.get("/")
def root():
    return {"message": "Story Summary API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
