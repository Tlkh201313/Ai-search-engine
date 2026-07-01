"""Per-mode research strategy configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import ResearchMode


@dataclass(frozen=True)
class ModeConfig:
    key: ResearchMode
    label: str
    description: str
    search_limit: int  # results requested per provider per query
    max_fetch: int  # pages actually fetched/read
    max_sources: int  # sources kept + citable
    expansions: int  # number of extra sub-queries to generate
    weights: dict[str, float]
    prefer_domains: tuple[str, ...] = ()
    style: str = ""
    providers: tuple[str, ...] = ()  # override enabled providers (empty = default)
    # Evidence-gathering LLM tool rounds before synthesis. 0 = synthesize straight
    # from the fetched sources (fastest); None = settings.llm_max_tool_rounds.
    tool_rounds: int | None = None


_MODES: dict[ResearchMode, ModeConfig] = {
    ResearchMode.quick: ModeConfig(
        key=ResearchMode.quick,
        label="Quick Answer",
        description="Fast, direct answer from a few strong sources.",
        search_limit=6,
        max_fetch=4,
        max_sources=4,
        expansions=0,
        weights={"relevance": 0.55, "freshness": 0.10, "quality": 0.20, "depth": 0.15},
        style="Be concise and direct. Lead with the answer.",
        tool_rounds=0,  # one streamed synthesis call — speed is the point of Quick
    ),
    ResearchMode.deep: ModeConfig(
        key=ResearchMode.deep,
        label="Deep Research",
        description="Broad search, more sources, thorough synthesis.",
        search_limit=10,
        max_fetch=10,
        max_sources=10,
        expansions=3,
        weights={"relevance": 0.40, "freshness": 0.10, "quality": 0.25, "depth": 0.25},
        style="Be thorough and well-structured. Synthesize across many sources.",
    ),
    ResearchMode.compare: ModeConfig(
        key=ResearchMode.compare,
        label="Compare Sources",
        description="Highlight where sources agree and disagree.",
        search_limit=10,
        max_fetch=9,
        max_sources=8,
        expansions=2,
        weights={"relevance": 0.45, "freshness": 0.10, "quality": 0.25, "depth": 0.20},
        style=(
            "Explicitly contrast sources. Populate agreements and disagreements. "
            "Attribute contested claims to specific sources."
        ),
    ),
    ResearchMode.news: ModeConfig(
        key=ResearchMode.news,
        label="Latest News",
        description="Prioritize the most recent, timely reporting.",
        search_limit=10,
        max_fetch=8,
        max_sources=8,
        expansions=1,
        weights={"relevance": 0.35, "freshness": 0.45, "quality": 0.15, "depth": 0.05},
        prefer_domains=(
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "theguardian.com",
            "nytimes.com", "bloomberg.com", "ft.com", "cnbc.com", "aljazeera.com",
        ),
        style="Prioritize the latest developments. Note dates. Flag fast-moving stories.",
        tool_rounds=1,  # freshness beats depth — one gap-filling round is enough
    ),
    ResearchMode.academic: ModeConfig(
        key=ResearchMode.academic,
        label="Academic",
        description="Favor papers, references, and authoritative sources.",
        search_limit=10,
        max_fetch=9,
        max_sources=9,
        expansions=2,
        weights={"relevance": 0.30, "freshness": 0.05, "quality": 0.35, "depth": 0.30},
        prefer_domains=(
            "arxiv.org", "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "nature.com",
            "science.org", "sciencedirect.com", "springer.com", "wiley.com",
            "acm.org", "ieee.org", "jstor.org", "doi.org", "semanticscholar.org",
        ),
        style="Use precise, careful language. Prefer primary sources and cite them.",
    ),
    ResearchMode.code: ModeConfig(
        key=ResearchMode.code,
        label="Code / Technical",
        description="Favor docs, GitHub, and technical Q&A.",
        search_limit=10,
        max_fetch=8,
        max_sources=8,
        expansions=2,
        weights={"relevance": 0.45, "freshness": 0.10, "quality": 0.25, "depth": 0.20},
        prefer_domains=(
            "github.com", "stackoverflow.com", "developer.mozilla.org", "docs.python.org",
            "readthedocs.io", "docs.rs", "pkg.go.dev", "kubernetes.io", "docs.docker.com",
            "learn.microsoft.com", "developer.apple.com", "developer.android.com",
        ),
        style=(
            "Be technically precise. Include short code examples when helpful and cite "
            "official documentation."
        ),
    ),
}


def get_mode(mode: ResearchMode) -> ModeConfig:
    return _MODES[mode]


def all_modes() -> list[ModeConfig]:
    return list(_MODES.values())
