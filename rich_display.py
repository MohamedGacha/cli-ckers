import webbrowser

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Static
from textual.binding import Binding

from request_hacker_news import Story, HackerNewsHandler


class StoryCard(Static, can_focus=True):
    def __init__(self, story: Story) -> None:
        super().__init__()
        self.story = story

    def render(self) -> Table:
        s = self.story
        title = Text(s.title, style=f"bold link {s.url}")
        title.append(" ↗", style="dim")

        site = Text(s.site or "news.ycombinator.com", style="dim")

        parts = []
        if s.score is not None:
            parts.append(f"▲ {s.score} points")
        if s.author:
            parts.append(f"@ {s.author}")
        if s.time:
            parts.append(f"○ {s.time}")
        metrics = Text("  ·  ".join(parts) or "job posting", style="grey62")

        body = Table.grid(padding=(0, 1))
        body.add_column(justify="right", width=3)
        body.add_column(ratio=1)
        rank = Text(str(s.rank) if s.rank is not None else "•", style="bold cyan")
        body.add_row(rank, Group(title, site, metrics))
        return body


class HackerNewsApp(App):
    CSS = """
    StoryCard {
        border: round $foreground 30%;
        padding: 0 1;
        margin: 0 1 1 1;
    }
    StoryCard:hover {
        border: round $accent 50%;
    }
    StoryCard:focus {
        border: round $accent;
        background: $boost;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        ("enter", "app.open_story", "Open"),
        ("right", "next_page", "Next page"),
        ("left", "previous_page", "Previous page"),
        ("ctrl+r", "refresh_current_page", "Refresh"),
        ("ctrl+shift+r", "refresh_all", "Refresh all"),
    ]

    page_no = 1

    def __init__(self) -> None:
        super().__init__()
        self.hacker_news_handler = HackerNewsHandler()

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="feed")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Hacker News CLI"
        self.load_page()

    def load_page(self) -> None:
        self.sub_title = f"page {self.page_no}"
        self.query_one("#feed").loading = True
        self.run_worker(self.fetch_and_fill, thread=True, exclusive=True)

    def fetch_and_fill(self) -> None:
        page = self.page_no
        self.hacker_news_handler.fetch_page(page)
        self.call_from_thread(self.show_stories, page)

    def show_stories(self, page: int) -> None:
        if page != self.page_no:
            return
        feed = self.query_one("#feed", VerticalScroll)
        feed.loading = False
        stories = self.hacker_news_handler.page(page).stories
        if not stories:
            self.sub_title = f"page {page} · nothing loaded, ctrl+r to retry"
            return
        feed.remove_children()
        feed.mount_all(StoryCard(s) for s in stories)
        self.call_after_refresh(self._focus_first_card)

    def _focus_first_card(self) -> None:
        cards = self.query(StoryCard)
        if cards:
            cards.first().focus()

    def action_cursor_down(self) -> None:
        cards = list(self.query(StoryCard))
        if not cards:
            return
        if self.focused is cards[-1]:
            self.bell()
            return
        self.screen.focus_next(StoryCard)
        if isinstance(self.focused, StoryCard):
            self.focused.scroll_visible()

    def action_cursor_up(self) -> None:
        cards = list(self.query(StoryCard))
        if not cards:
            return
        if self.focused is cards[0]:
            self.bell()
            return
        self.screen.focus_previous(StoryCard)
        if isinstance(self.focused, StoryCard):
            self.focused.scroll_visible()

    def action_open_story(self) -> None:
        focused = self.focused
        if isinstance(focused, StoryCard):
            webbrowser.open(focused.story.url)

    def action_refresh_current_page(self) -> None:
        self.hacker_news_handler.refresh_page(self.page_no)
        self.load_page()

    def action_refresh_all(self) -> None:
        self.query_one("#feed").loading = True
        self.run_worker(self._refresh_all_worker, thread=True, exclusive=True)

    def _refresh_all_worker(self) -> None:
        self.hacker_news_handler.refresh_all()
        self.call_from_thread(self.show_stories, self.page_no)

    def action_next_page(self) -> None:
        self.page_no += 1
        self.load_page()

    def action_previous_page(self) -> None:
        if self.page_no <= 1:
            self.bell()
            return
        self.page_no -= 1
        self.load_page()


if __name__ == "__main__":
    HackerNewsApp().run()