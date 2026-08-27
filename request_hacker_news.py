import requests
import os
from bs4 import BeautifulSoup, SoupStrainer, Tag
from dataclasses import dataclass, asdict
import json

@dataclass
class Story:
    rank: int | None
    title: str
    url: str
    site: str | None
    score: int | None
    time: str | None
    author: str | None

    def __str__(self):
        site = f' ({self.site})' if self.site else ''
        return f'{self.rank}. {self.title}{site} — {self.score or 0} pts by {self.author or "?"} {self.time or ""}'


def fetch_news(page_no: int) -> list[Story]:
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
    print(fetch_news(1))