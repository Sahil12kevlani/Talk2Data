from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from app.api.routes import router as api_router
from app.api.multidb_routes import router as multidb_router

app = FastAPI(title="Talk2Data Backend")

# ✅ Enable CORS so frontend can access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] for stricter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include routers
app.include_router(multidb_router, prefix="/api")
#app.include_router(api_router, prefix="/api")
