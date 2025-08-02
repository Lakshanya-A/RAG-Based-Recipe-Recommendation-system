# create base route

from typing import List
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from embedding_pipeline.vector_db import VectorDB, CookingAssistant
from fastapi.staticfiles import StaticFiles
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()
api_router = APIRouter()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize VectorDB and CookingAssistant
vector_db = VectorDB()
cooking_assistant = CookingAssistant(vector_db)

class ChatMessage(BaseModel):
    message: str

# @app.get("/", tags=["root"])
# async def read_root() -> dict:
#     return {"message": "Welcome to your recipe recommender."}

@api_router.post("/chat")
async def chat(message: ChatMessage):
    """
    Process a chat message and return a response.
    """
    try:
        response = cooking_assistant.process_message(message.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return {"error": "Sorry, I encountered an error while processing your message. Please try again."}

@app.post("/getem/{keywords}")
async def get_em(keywords: str):
    """
    Legacy endpoint for recipe search. Suggests using the chat endpoint instead.
    """
    return {
        "message": "This endpoint is deprecated. Please use the /chat endpoint instead.",
        "example": "Try sending a message like 'What can I make with chicken?' to the /chat endpoint"
    }

app.include_router(api_router, prefix="/api")

# Serve static files from the 'dist' directory
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../dist"))
app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
