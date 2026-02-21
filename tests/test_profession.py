"""Tests for profession data functions."""

import pytest

from proskiro_tools.data.profession import rows_to_profession, search_profession
from proskiro_tools.models.profession import Books, Profession, Skills


class TestRowsToProfession:
    """Tests for the rows_to_profession function."""

    def test_returns_profession_with_correct_metadata(self, mock_profession_rows):
        """Should extract profession metadata from first row."""
        result = rows_to_profession(mock_profession_rows)

        assert isinstance(result, Profession)
        assert result.preferred_title == "Nurse"
        assert result.isco_code == "2221"
        assert result.uri == "http://example.com/occupation/nurse"
        assert result.description == "A healthcare professional"

    def test_separates_essential_and_optional_skills(self, mock_profession_rows):
        """Should group skills into essential and optional lists."""
        result = rows_to_profession(mock_profession_rows)

        essential_titles = [s.preferred_title for s in result.essential_skills]
        optional_titles = [s.preferred_title for s in result.optional_skills]

        assert "Anatomy" in essential_titles
        assert "Patient Care" in essential_titles
        assert "Pharmacology" in essential_titles
        assert "Psychology" in optional_titles
        assert "Teamwork" in optional_titles

    def test_deduplicates_skills_from_multiple_book_rows(self, mock_profession_rows):
        """Should not duplicate skills when multiple book rows exist."""
        result = rows_to_profession(mock_profession_rows)

        # Anatomy has 2 book rows but should appear once
        anatomy_skills = [
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        ]
        assert len(anatomy_skills) == 1

    def test_attaches_books_to_knowledge_skills(self, mock_profession_rows):
        """Should attach books to knowledge-type skills."""
        result = rows_to_profession(mock_profession_rows)

        anatomy_skill = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        assert len(anatomy_skill.books) == 2
        assert anatomy_skill.books[0].title == "Gray's Anatomy"

    def test_no_books_for_competence_skills(self, mock_profession_rows):
        """Should not attach books to skill/competence type skills."""
        result = rows_to_profession(mock_profession_rows)

        patient_care = next(
            s for s in result.essential_skills if s.preferred_title == "Patient Care"
        )
        assert len(patient_care.books) == 0

    def test_tracks_book_count_per_skill(self, mock_profession_rows):
        """Should store the total book count for each skill."""
        result = rows_to_profession(mock_profession_rows)

        anatomy = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        psychology = next(
            s for s in result.optional_skills if s.preferred_title == "Psychology"
        )

        assert anatomy.book_count == 2
        assert psychology.book_count == 3

    def test_raises_on_empty_rows(self):
        """Should raise ValueError when given empty rows."""
        with pytest.raises(ValueError, match="No rows to convert"):
            rows_to_profession([])


class TestRowsToProfessionLimits:
    """Tests for skill count limits in rows_to_profession."""

    def test_limits_essential_knowledge(self, mock_profession_rows):
        """Should respect max_essential_knowledge limit."""
        result = rows_to_profession(mock_profession_rows, max_essential_knowledge=1)

        essential_knowledge = [
            s for s in result.essential_skills if s.skill_type == "knowledge"
        ]
        assert len(essential_knowledge) == 1

    def test_limits_essential_skills(self, mock_profession_rows):
        """Should respect max_essential_skills limit."""
        result = rows_to_profession(mock_profession_rows, max_essential_skills=0)

        essential_competence = [
            s for s in result.essential_skills if s.skill_type == "skill/competence"
        ]
        assert len(essential_competence) == 0

    def test_limits_optional_knowledge(self, mock_profession_rows):
        """Should respect max_optional_knowledge limit."""
        result = rows_to_profession(mock_profession_rows, max_optional_knowledge=0)

        optional_knowledge = [
            s for s in result.optional_skills if s.skill_type == "knowledge"
        ]
        assert len(optional_knowledge) == 0

    def test_limits_optional_skills(self, mock_profession_rows):
        """Should respect max_optional_skills limit."""
        result = rows_to_profession(mock_profession_rows, max_optional_skills=0)

        optional_competence = [
            s for s in result.optional_skills if s.skill_type == "skill/competence"
        ]
        assert len(optional_competence) == 0

    def test_none_limit_means_no_limit(self, mock_profession_rows):
        """Should include all skills when limit is None."""
        result = rows_to_profession(mock_profession_rows)

        # Should have all 3 essential skills (2 knowledge + 1 competence)
        assert len(result.essential_skills) == 3
        # Should have all 2 optional skills (1 knowledge + 1 competence)
        assert len(result.optional_skills) == 2

    def test_limits_are_independent(self, mock_profession_rows):
        """Each limit category should be independent."""
        result = rows_to_profession(
            mock_profession_rows,
            max_essential_knowledge=1,
            max_essential_skills=1,
            max_optional_knowledge=0,
            max_optional_skills=1,
        )

        essential_knowledge = [
            s for s in result.essential_skills if s.skill_type == "knowledge"
        ]
        essential_competence = [
            s for s in result.essential_skills if s.skill_type == "skill/competence"
        ]
        optional_knowledge = [
            s for s in result.optional_skills if s.skill_type == "knowledge"
        ]
        optional_competence = [
            s for s in result.optional_skills if s.skill_type == "skill/competence"
        ]

        assert len(essential_knowledge) == 1
        assert len(essential_competence) == 1
        assert len(optional_knowledge) == 0
        assert len(optional_competence) == 1


class TestStarRating:
    """Tests for the star_rating computed field on Skills."""

    def _make_skill(self, **overrides) -> Skills:
        defaults = {
            "skill_uri": "http://example.com/skill/test",
            "preferred_title": "Test Skill",
            "importance": "essential",
            "skill_type": "knowledge",
            "book_count": 0,
            "occupation_count": 0,
            "google_books_total": None,
        }
        defaults.update(overrides)
        return Skills(**defaults)

    def test_essential_base_is_2(self):
        skill = self._make_skill(importance="essential")
        assert skill.star_rating == 2

    def test_optional_base_is_1(self):
        skill = self._make_skill(importance="optional")
        assert skill.star_rating == 1

    def test_popular_topic_adds_2(self):
        skill = self._make_skill(google_books_total=60)
        assert skill.star_rating == 4  # 2 base + 2 popularity

    def test_established_topic_adds_1(self):
        skill = self._make_skill(google_books_total=20)
        assert skill.star_rating == 3  # 2 base + 1 popularity

    def test_below_threshold_no_popularity_bonus(self):
        skill = self._make_skill(google_books_total=19)
        assert skill.star_rating == 2  # 2 base only

    def test_fallback_to_book_count_when_no_search_data(self):
        skill = self._make_skill(google_books_total=None, book_count=1)
        assert skill.star_rating == 3  # 2 base + 1 fallback

    def test_no_fallback_when_zero_books(self):
        skill = self._make_skill(google_books_total=None, book_count=0)
        assert skill.star_rating == 2  # 2 base only

    def test_book_count_5_adds_recommendation_bonus(self):
        skill = self._make_skill(google_books_total=10, book_count=5)
        assert skill.star_rating == 3  # 2 base + 0 popularity (10<20) + 1 recommendations

    def test_book_count_below_5_no_recommendation_bonus(self):
        skill = self._make_skill(google_books_total=10, book_count=4)
        assert skill.star_rating == 2  # 2 base + 0 popularity (10<20) + 0 recommendations

    def test_occupation_breadth_adds_1(self):
        skill = self._make_skill(occupation_count=20)
        assert skill.star_rating == 3  # 2 base + 1 breadth

    def test_max_is_5_stars(self):
        skill = self._make_skill(
            importance="essential",
            google_books_total=100,
            book_count=10,
            occupation_count=50,
        )
        # 2 base + 2 popularity + 1 recommendations + 1 breadth = 6 → capped at 5
        assert skill.star_rating == 5

    def test_optional_max_scenario(self):
        skill = self._make_skill(
            importance="optional",
            google_books_total=60,
            book_count=5,
            occupation_count=20,
        )
        # 1 base + 2 popularity + 1 recommendations + 1 breadth = 5
        assert skill.star_rating == 5

    def test_optional_minimum(self):
        skill = self._make_skill(importance="optional")
        assert skill.star_rating == 1

    def test_popularity_and_book_count_independent(self):
        """google_books_total and book_count are independent signals."""
        skill = self._make_skill(google_books_total=60, book_count=5)
        # 2 base + 2 popularity + 1 recommendations = 5
        assert skill.star_rating == 5

    def test_no_fallback_when_search_data_exists(self):
        """book_count fallback should NOT apply when google_books_total is set."""
        skill = self._make_skill(google_books_total=5, book_count=3)
        # 2 base + 0 popularity (5 < 20) + 0 recommendations (3 < 5) = 2
        assert skill.star_rating == 2


class TestBookScoreAndLimiting:
    """Tests for book score persistence and top-5 limiting in rows_to_profession."""

    def test_books_have_score(self, mock_profession_rows):
        """Books should carry the score from the database row."""
        result = rows_to_profession(mock_profession_rows)

        anatomy = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        assert anatomy.books[0].score == 85.5
        assert anatomy.books[1].score == 72.3

    def test_limits_books_to_5(self):
        """Skills with >5 books should be trimmed to top 5 by score."""
        from tests.conftest import ProfessionRow

        base = {
            "uri": "http://example.com/occupation/dev",
            "isco_code": "2512",
            "preferred_title": "Developer",
            "description": "A software developer",
            "slug": "developer",
            "status": "released",
            "is_featured": True,
        }

        rows = []
        for i in range(8):
            rows.append(
                ProfessionRow(
                    **base,
                    skill_uri="http://example.com/skill/python",
                    skill_code="SK1",
                    skill_title="Python",
                    importance="essential",
                    skill_type="knowledge",
                    skill_description="Python programming",
                    book_id=100 + i,
                    isbn_10=f"ISBN{i:06d}",
                    book_title=f"Python Book {i}",
                    book_authors=[f"Author {i}"],
                    book_published_year=2020 + i,
                    book_rank=i + 1,
                    book_score=float(80 - i * 5),
                    skill_book_count=8,
                    skill_occupation_count=10,
                    skill_google_books_total=50,
                )
            )

        result = rows_to_profession(rows)
        python_skill = result.essential_skills[0]
        assert len(python_skill.books) == 5

    def test_top_5_are_highest_scored(self):
        """The 5 retained books should be the ones with highest scores."""
        from tests.conftest import ProfessionRow

        base = {
            "uri": "http://example.com/occupation/dev",
            "isco_code": "2512",
            "preferred_title": "Developer",
            "description": "A software developer",
            "slug": "developer",
            "status": "released",
            "is_featured": True,
        }

        scores = [10.0, 90.0, 30.0, 70.0, 50.0, 80.0, 20.0]
        rows = []
        for i, score in enumerate(scores):
            rows.append(
                ProfessionRow(
                    **base,
                    skill_uri="http://example.com/skill/python",
                    skill_code="SK1",
                    skill_title="Python",
                    importance="essential",
                    skill_type="knowledge",
                    skill_description="Python programming",
                    book_id=200 + i,
                    isbn_10=f"ISBNX{i:05d}",
                    book_title=f"Book {i}",
                    book_authors=[f"Author {i}"],
                    book_published_year=2020,
                    book_rank=i + 1,
                    book_score=score,
                    skill_book_count=7,
                    skill_occupation_count=10,
                    skill_google_books_total=50,
                )
            )

        result = rows_to_profession(rows)
        python_skill = result.essential_skills[0]
        retained_scores = [b.score for b in python_skill.books]
        # Top 5 scores from [10, 90, 30, 70, 50, 80, 20] = [90, 80, 70, 50, 30]
        assert retained_scores == [90.0, 80.0, 70.0, 50.0, 30.0]

    def test_5_or_fewer_books_not_trimmed(self, mock_profession_rows):
        """Skills with 5 or fewer books should keep all of them."""
        result = rows_to_profession(mock_profession_rows)

        anatomy = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        assert len(anatomy.books) == 2  # Only 2 books, no trimming

    def test_skills_have_occupation_count(self, mock_profession_rows):
        """Skills should carry occupation_count from rows."""
        result = rows_to_profession(mock_profession_rows)

        anatomy = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        assert anatomy.occupation_count == 15

    def test_skills_have_google_books_total(self, mock_profession_rows):
        """Skills should carry google_books_total from rows."""
        result = rows_to_profession(mock_profession_rows)

        anatomy = next(
            s for s in result.essential_skills if s.preferred_title == "Anatomy"
        )
        assert anatomy.google_books_total == 45


class TestSearchProfessionIntegration:
    """Integration tests for search_profession against real database.

    These tests require a running PostgreSQL database with test data.
    Mark with @pytest.mark.integration if you want to skip in CI.
    """

    @pytest.mark.integration
    def test_finds_nurse_profession(self, db_session):
        """Should find the nurse profession by name."""
        result = search_profession(db_session, "nurse")

        assert result is not None
        assert "nurse" in result.preferred_title.lower()

    @pytest.mark.integration
    def test_returns_none_for_nonexistent_profession(self, db_session):
        """Should return None for a profession that doesn't exist."""
        result = search_profession(db_session, "xyznonexistent123")

        assert result is None

    @pytest.mark.integration
    def test_applies_limits_in_search(self, db_session):
        """Should apply skill limits when searching."""
        result = search_profession(
            db_session,
            "nurse",
            max_essential_knowledge=2,
            max_essential_skills=2,
        )

        if result:
            essential_knowledge = [
                s for s in result.essential_skills if s.skill_type == "knowledge"
            ]
            essential_competence = [
                s for s in result.essential_skills if s.skill_type == "skill/competence"
            ]

            assert len(essential_knowledge) <= 2
            assert len(essential_competence) <= 2

    @pytest.mark.integration
    def test_skills_have_book_counts(self, db_session):
        """Skills should have book_count populated."""
        result = search_profession(db_session, "nurse", max_essential_knowledge=5)

        if result and result.essential_skills:
            # At least some skills should have book counts
            knowledge_skills = [
                s for s in result.essential_skills if s.skill_type == "knowledge"
            ]
            if knowledge_skills:
                # Check that book_count is an integer (could be 0)
                assert isinstance(knowledge_skills[0].book_count, int)

    @pytest.mark.integration
    def test_partial_name_match(self, db_session):
        """Should match professions with partial name."""
        result = search_profession(db_session, "nurs")

        assert result is not None
        assert "nurs" in result.preferred_title.lower()
