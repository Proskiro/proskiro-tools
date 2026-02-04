"""Tests for profession data functions."""

import pytest

from proskiro_tools.data.profession import rows_to_profession, search_profession
from proskiro_tools.models.profession import Profession


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
