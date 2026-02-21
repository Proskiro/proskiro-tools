from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, computed_field

# ISCO-08 Major Groups with styling (international standard)
# Each group has: label, icon (SVG path), color (for icon), bg_color (light background)
ISCO_GROUPS = {
    "0": {
        "label": "Armed Forces",
        "icon": "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z",
        "color": "#1d4ed8",
        "bg_color": "#dbeafe",
    },
    "1": {
        "label": "Managers",
        "icon": "M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z",
        "color": "#7c3aed",
        "bg_color": "#ede9fe",
    },
    "2": {
        "label": "Professionals",
        "icon": "M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5",
        "color": "#0d9488",
        "bg_color": "#ccfbf1",
    },
    "3": {
        "label": "Technicians",
        "icon": "M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z",
        "color": "#ea580c",
        "bg_color": "#ffedd5",
    },
    "4": {
        "label": "Clerical Support",
        "icon": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z",
        "color": "#6366f1",
        "bg_color": "#e0e7ff",
    },
    "5": {
        "label": "Service & Sales",
        "icon": "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z",
        "color": "#e11d48",
        "bg_color": "#ffe4e6",
    },
    "6": {
        "label": "Agriculture & Forestry",
        "icon": "M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z",
        "color": "#65a30d",
        "bg_color": "#ecfccb",
    },
    "7": {
        "label": "Craft & Trades",
        "icon": "M21.75 6.75a4.5 4.5 0 01-4.884 4.484c-1.076-.091-2.264.071-2.95.904l-7.152 8.684a2.548 2.548 0 11-3.586-3.586l8.684-7.152c.833-.686.995-1.874.904-2.95a4.5 4.5 0 016.336-4.486l-3.276 3.276a3.004 3.004 0 002.25 2.25l3.276-3.276c.256.565.398 1.192.398 1.852z",
        "color": "#b45309",
        "bg_color": "#fef3c7",
    },
    "8": {
        "label": "Machine Operators",
        "icon": "M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m-6.063 16.658l.26-1.477m2.605-14.772l.26-1.477m0 17.726l-.26-1.477M10.698 4.614l-.26-1.477M16.5 19.794l-.75-1.299M7.5 4.205L12 12m6.894 5.785l-1.149-.964M6.256 7.178l-1.15-.964m15.352 8.864l-1.41-.513M4.954 9.435l-1.41-.514M12.002 12l-3.75 6.495",
        "color": "#0891b2",
        "bg_color": "#cffafe",
    },
    "9": {
        "label": "Elementary Occupations",
        "icon": "M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.834.166l-1.591 1.591M20.25 10.5H18M7.757 14.743l-1.59 1.59M6 10.5H3.75m4.007-4.243l-1.59-1.59",
        "color": "#db2777",
        "bg_color": "#fce7f3",
    },
}


def get_isco_group_label(isco_code: Optional[str]) -> Optional[str]:
    """Return the ISCO major group label for a given code."""
    if not isco_code:
        return None
    code = isco_code.lstrip("C")
    if code and code[0] in ISCO_GROUPS:
        return ISCO_GROUPS[code[0]]["label"]
    return None


def get_isco_group_style(isco_code: Optional[str]) -> Optional[dict]:
    """Return the full ISCO group style dict (label, icon, color, bg_color)."""
    if not isco_code:
        return None
    code = isco_code.lstrip("C")
    if code and code[0] in ISCO_GROUPS:
        return ISCO_GROUPS[code[0]]
    return None


class Books(BaseModel):
    book_id: int
    isbn_10: str
    title: str
    authors: Optional[list[str]] = None
    published_year: Optional[int] = None
    rank: Optional[int] = None
    score: Optional[float] = None  # Composite ranking score from BookRanker
    cover_url: Optional[str] = None
    free_access_url: Optional[str] = None
    free_access_type: Optional[str] = None  # 'full', 'preview', 'pdf', 'epub', or 'none'
    amazon_affiliate_url: Optional[str] = None


class Courses(BaseModel):
    title: str
    provider: str


class Skills(BaseModel):
    skill_uri: str
    skill_code: Optional[str] = None
    preferred_title: str
    description: Optional[str] = None
    importance: str
    skill_type: str
    book_count: int = 0  # Total books matched to this skill
    occupation_count: int = 0  # How many occupations use this skill
    google_books_total: int | None = (
        None  # Pre-filter book count from search (popularity signal)
    )
    books: list[Books] = Field(default_factory=list)
    courses: list[Courses] = Field(default_factory=list)

    @computed_field
    @property
    def star_rating(self) -> int:
        """Compute importance rating (1-5 stars) based on available data.

        Two complementary book signals:
        - google_books_total: Popularity signal. Count of unique books from
          tier 0 (primary search only) across Google Books + Open Library,
          deduped by ISBN, before hard filters. Answers: "is this a
          well-documented topic?" Fallback results (broader skill, older
          years) are excluded to preserve the niche vs popular distinction.
        - book_count: Recommendation quality. Count of final curated books
          persisted for this skill-occupation pair across ALL tiers (0-4)
          and both sources. Answers: "did we find good recommendations?"
          Includes fallback results, so niche skills that needed broader
          searches still get credit.

        Formula:
        - Base: 2 for essential, 1 for optional
        - Topic popularity (google_books_total, tier 0 pre-filter only):
          - 40+ books: +2 (highly popular topic)
          - 20+ books: +1 (established topic)
        - Matched recommendations (book_count, all tiers):
          - 5+ books: +1 (enough to fill top 5 display)
        - Occupation breadth:
          - 10+ occupations: +1 (transferable skill)
        - Max: 5 stars
        """
        rating = 2 if self.importance == "essential" else 1

        # Bonus for topic popularity (pre-filter book count from both sources)
        if self.google_books_total is not None:
            if self.google_books_total >= 40:
                rating += 2
            elif self.google_books_total >= 20:
                rating += 1
        elif self.book_count >= 1:
            # Fallback to local book count if no search data yet
            rating += 1

        # Bonus for having actual book recommendations matched
        if self.book_count >= 5:
            rating += 1

        # Bonus for broad applicability
        if self.occupation_count >= 10:
            rating += 1

        return min(rating, 5)


class Profession(BaseModel):
    uri: Optional[str] = None
    isco_code: Optional[str] = None
    preferred_title: str
    description: Optional[str] = None
    slug: str
    essential_skills: list[Skills] = Field(default_factory=list)
    optional_skills: list[Skills] = Field(default_factory=list)
    is_featured: Optional[bool] = None

    @computed_field
    @property
    def isco_group_label(self) -> Optional[str]:
        """ISCO major group label (e.g., 'Professionals')."""
        return get_isco_group_label(self.isco_code)

    @computed_field
    @property
    def isco_group_style(self) -> Optional[dict]:
        """Full ISCO group style (label, icon, color, bg_color)."""
        return get_isco_group_style(self.isco_code)


class ProfessionSummary(BaseModel):
    """Lightweight profession model for listing/search results."""

    uri: Optional[str] = None
    isco_code: Optional[str] = None
    preferred_title: str
    description: Optional[str] = None
    slug: str

    @computed_field
    @property
    def isco_group_label(self) -> Optional[str]:
        """ISCO major group label (e.g., 'Professionals')."""
        return get_isco_group_label(self.isco_code)

    @computed_field
    @property
    def isco_group_style(self) -> Optional[dict]:
        """Full ISCO group style (label, icon, color, bg_color)."""
        return get_isco_group_style(self.isco_code)
