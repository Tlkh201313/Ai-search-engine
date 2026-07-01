"""Pydantic schemas — the API contract shared with the web client."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ResearchMode(str, Enum):
    """User-selectable research strategies."""

    quick = "quick"
    deep = "deep"
    compare = "compare"
    news = "news"
    academic = "academic"
    code = "code"


class ProgressStage(str, Enum):
    """Ordered pipeline stages surfaced to the UI as live progress."""

    understanding = "understanding"
    searching = "searching"
    finding_sources = "finding_sources"
    reading = "reading"
    deduping = "deduping"
    ranking = "ranking"
    writing = "writing"
    verifying = "verifying"
    done = "done"
    error = "error"


# --------------------------------------------------------------------------- #
#  Search + sources
# --------------------------------------------------------------------------- #
class SearchResult(BaseModel):
    title: str = ""
    url: str
    snippet: str = ""
    provider: str = ""
    published_at: str | None = None


class SourceScores(BaseModel):
    relevance: float = 0.0
    freshness: float = 0.0
    quality: float = 0.0
    depth: float = 0.0
    overall: float = 0.0


class Source(BaseModel):
    """A fetched, read, and scored web source ready for citation."""

    id: int  # 1-based citation number
    url: str
    title: str = ""
    domain: str = ""
    snippet: str = ""
    excerpt: str = ""  # cleaned evidence text sent to the LLM
    author: str | None = None
    description: str | None = None
    published_at: str | None = None
    fetched_at: str | None = None
    favicon: str | None = None
    provider: str = ""
    word_count: int = 0
    scores: SourceScores = Field(default_factory=SourceScores)
    used: bool = False  # cited in the final answer


class Answer(BaseModel):
    """Structured, source-grounded answer."""

    summary: str = ""  # short direct answer
    detail: str = ""  # full markdown explanation with inline [n] citations
    key_takeaways: list[str] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    citations: list[int] = Field(default_factory=list)  # source ids actually used
    confidence: float = 0.0  # 0..1


class ModelInfo(BaseModel):
    model: str = ""
    available: bool = False  # True if the hosted LLM is configured/reachable
    grounded: bool = False  # True if an LLM synthesized the answer


class ResearchTimings(BaseModel):
    search_ms: int = 0
    fetch_ms: int = 0
    answer_ms: int = 0
    total_ms: int = 0


# --------------------------------------------------------------------------- #
#  Requests / responses
# --------------------------------------------------------------------------- #
class ConversationTurn(BaseModel):
    """A prior question and its short answer, used to ground follow-ups."""

    query: str = Field(max_length=2000)
    answer: str = Field(default="", max_length=4000)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    mode: ResearchMode = ResearchMode.quick
    max_sources: int | None = Field(default=None, ge=1, le=20)
    # Prior turns in the same conversation (most recent last), for follow-ups.
    context: list[ConversationTurn] = Field(default_factory=list, max_length=8)

    @field_validator("query")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned


class ResearchCreated(BaseModel):
    id: str
    query: str
    mode: ResearchMode


class ResearchResult(BaseModel):
    id: str
    query: str
    mode: ResearchMode
    status: str = "complete"  # running | complete | error
    answer: Answer = Field(default_factory=Answer)
    sources: list[Source] = Field(default_factory=list)
    confidence: float = 0.0
    model: ModelInfo = Field(default_factory=ModelInfo)
    timings: ResearchTimings = Field(default_factory=ResearchTimings)
    error: str | None = None
    created_at: str = ""


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    mode: ResearchMode = ResearchMode.quick
    limit: int = Field(default=10, ge=1, le=30)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    providers: list[str]
    total: int
    cached: bool = False


class FetchRequest(BaseModel):
    url: HttpUrl
    max_chars: int = Field(default=12000, ge=200, le=100000)


class FetchResponse(BaseModel):
    url: str
    title: str = ""
    domain: str = ""
    text: str = ""
    author: str | None = None
    description: str | None = None
    published_at: str | None = None
    word_count: int = 0
    cached: bool = False


class ProgressEvent(BaseModel):
    """A single Server-Sent-Event payload during a research run."""

    stage: ProgressStage
    status: str = "active"  # active | done | error
    message: str = ""
    progress: float = 0.0  # 0..1 overall
    data: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    llm: ModelInfo
    search_providers: list[str]


class SettingsPublic(BaseModel):
    """Non-secret runtime settings the UI may read. No keys are ever exposed."""

    llm_available: bool
    model: str
    grounded: bool  # whether answers are LLM-synthesized (vs extractive fallback)
    search_providers: list[str]
    modes: list[str]


class SettingsUpdate(BaseModel):
    """Only non-secret, operator-safe toggles. Keys are never accepted here."""

    search_providers: list[str] | None = None
