from request_hacker_news import Story, HackerNewsHandler

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

