from request_hacker_news import Story, HackerNewsHandler

from fastapi import FastAPI

app = FastAPI()
news_handler = HackerNewsHandler()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/fetch_news/")
async def get_news(page:int = 1 ):
    news_handler.fetch_page(page)
    return news_handler.page(page)

@app.get("/refresh_news/")
async def refresh_page(page:int | None = None):
    if page: 
        news_handler.refresh_page(page)
        return news_handler.page(page)
    else:
        news_handler.refresh_all()
        return {"message" : "All pages refreshed"}
    
