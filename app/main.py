from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, events, questions, answers, photos, faqs, admin

app = FastAPI(
    title="Mautoulouse API",
    description="Backend REST pour la plateforme communautaire Mautoulouse",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────
# Allow the Next.js frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Explicitly allow your Next.js frontend
    allow_credentials=True,                  # Must be True if sending cookies/auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTERS ───────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(photos.router)
app.include_router(faqs.router)
app.include_router(admin.router)


# ── HEALTH CHECK ─────────────────────────────────────────────
@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "Mautoulouse API v1.0"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
