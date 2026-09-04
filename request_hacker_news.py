import requests
import os
from bs4 import BeautifulSoup, SoupStrainer, Tag
from dataclasses import dataclass, asdict
import json
import time
from functools import wraps
from pydantic import BaseModel, Field, field_validator
from typing import Annotated

def retry(attempts: int = 5, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            last_exc = None
            for attempt in range(attempts):
                try:
                    output = func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    output = None
                if output:
                    return output
                if attempt < attempts - 1:
                    time.sleep(wait)
                    wait *= backoff
            if last_exc is not None:
                raise last_exc
            return output
        return wrapper
    return decorator

class Story(BaseModel):
    rank: int | None = None
    title: str
    url: str
    site: str | None = None
    score: int | None = None
    time: str | None = None
    author: str | None = None

    def __str__(self) -> str:
        site = f' ({self.site})' if self.site else ''
        return f'{self.rank}. {self.title}{site} — {self.score or 0} pts by {self.author or "?"} {self.time or ""}'

    def to_dict(self) -> dict:
        return self.model_dump()


class PageNumberError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class HackerNewsPage(BaseModel):

    page_no: int = Field(ge=1)
    tuple_of_stories: tuple[Story, ...]
    
    @field_validator("page_no")
    @classmethod
    def check_page_no(cls, v: int) -> int:
        if v < 1:
            raise PageNumberError("Page number must be an int of 1 or greater.")
        return v
    
    @property
    def stories(self) -> list[Story]:
        return list(self.tuple_of_stories)
    
    @property
    def page_number(self) -> int:
        return self.page_no
    
    def to_dict(self) -> dict:
        return {
            "page_no": self.page_no,
            "stories": [s.to_dict() for s in self.tuple_of_stories],
        }

class HackerNewsHandler:
    class PageNumberNotFound(Exception):
        def __init__(self, *args):
            super().__init__(*args)

    def __init__(self):
        self.news_pages: dict[int, HackerNewsPage] = {}

    def refresh_page(self, page_no:int) -> None:
        if self.news_pages.get(page_no):
            self.news_pages[page_no] = HackerNewsPage(
                page_no=page_no, tuple_of_stories=tuple(self._fetch_news(page_no)))
        else:
            raise self.PageNumberNotFound("Page not found in stored pages")
        
    def refresh_all(self) -> None:
        for page_id in list(self.news_pages):
            self.refresh_page(page_id)
            
    def fetch_page(self, page_no:int) -> None:
        if not self.news_pages.get(page_no):
            self.news_pages[page_no] = HackerNewsPage(
                page_no=page_no, tuple_of_stories=tuple(self._fetch_news(page_no)))
            
    def page(self, page_id: int) -> HackerNewsPage | None:
        self.fetch_page(page_id)
        return self.news_pages[page_id]

    @retry()
    def _fetch_news(self, page_no: int) -> list[Story]:
        req = requests.get(f'https://news.ycombinator.com/?p={page_no}')
        soup = BeautifulSoup(req.content, 'html.parser', parse_only=SoupStrainer('td'))

        td_title = soup.find_all('td', attrs={'class': 'title'})
        td_metrics = soup.find_all('td', attrs={'class': 'subtext'})
        td_rank = [t for t in td_title if t.get('align') == 'right']
        td_title_only = [t for t in td_title if t.get('align') != 'right']

        list_of_stories:list[Story] = []

        for idx in range(min(len(td_rank), len(td_title_only))):
            rank = td_rank[idx].find('span', attrs={'class': 'rank'})  
            titleline = td_title_only[idx].find('span', attrs={'class': 'titleline'})
            title = titleline.find('a') if isinstance(titleline, Tag) else None

            if not isinstance(title, Tag):
                continue

            href = title.get('href', '')
            if not isinstance(href, str):
                continue
            url = href if href.startswith('http') else f'https://news.ycombinator.com/{href}'
            site = td_title_only[idx].find('span', attrs={'class': 'sitestr'})
            score = td_metrics[idx].find('span', attrs={'class': 'score'}) if idx < len(td_metrics) else None
            time = td_metrics[idx].find('span', attrs={'class': 'age'}) if idx < len(td_metrics) else None
            author = td_metrics[idx].find('a', attrs={'class': 'hnuser'}) if idx < len(td_metrics) else None

            list_of_stories.append(Story(
                rank=int(rank.text.rstrip('.')) if rank else None,
                title=title.text,
                url=url,
                site=site.text if site else None,
                score=int(score.text.split()[0]) if score else None,
                time=time.text if time else None,
                author=author.text if author else None,
            ))

        return list_of_stories

if __name__ == "__main__":

    news_handler = HackerNewsHandler()
    
    print(HackerNewsHandler._fetch_news(1))