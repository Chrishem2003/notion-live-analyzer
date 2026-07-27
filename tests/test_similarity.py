"""Unit tests for modules.similarity."""
import pytest

from modules import similarity as sim

SOURCE_TEXT = (
    "Rainfall variability in the Lake Victoria basin has increased markedly "
    "over the past three decades, driven by shifts in sea surface temperature."
)
UNRELATED = (
    "Quantum error correction requires redundant physical qubits arranged in "
    "a surface code lattice with repeated syndrome extraction rounds."
)


def source(id_="s1", title="Source one", text=SOURCE_TEXT):
    return sim.Source(id=id_, title=title, text=text)


class TestTokenisation:
    def test_words_are_lowercased(self):
        assert sim.words("The Lake Victoria") == ["the", "lake", "victoria"]

    def test_hyphens_and_apostrophes_stay_in_a_token(self):
        assert sim.words("sea-surface don't") == ["sea-surface", "don't"]

    def test_empty_text(self):
        assert sim.words("") == []
        assert sim.shingles("") == []

    def test_shingle_count(self):
        text = "one two three four five six"
        assert len(sim.shingles(text, 5)) == 2

    def test_shingles_carry_their_word_offset(self):
        first, second = sim.shingles("one two three four five six", 5)
        assert first == ("one two three four five", 0)
        assert second[1] == 1

    def test_text_shorter_than_the_shingle_yields_nothing(self):
        assert sim.shingles("one two", 5) == []


class TestCompare:
    def test_identical_text_is_fully_matched(self):
        report = sim.compare(SOURCE_TEXT, [source()])
        assert report.overall_similarity == 100.0

    def test_unrelated_text_has_no_overlap(self):
        report = sim.compare(UNRELATED, [source()])
        assert report.overall_similarity == 0.0
        assert report.matches == []

    def test_partial_overlap_is_between(self):
        mixed = SOURCE_TEXT + " " + UNRELATED
        report = sim.compare(mixed, [source()])
        assert 0 < report.overall_similarity < 100

    def test_no_sources_reports_zero_rather_than_failing(self):
        report = sim.compare(SOURCE_TEXT, [])
        assert report.overall_similarity == 0.0
        assert report.top_source is None

    def test_empty_document(self):
        assert sim.compare("", [source()]).overall_similarity == 0.0

    def test_matches_are_attributed_per_source(self):
        report = sim.compare(SOURCE_TEXT, [source(), source("s2", "Other", UNRELATED)])
        assert [m.source_id for m in report.matches] == ["s1"]

    def test_matches_are_sorted_by_similarity(self):
        half = " ".join(SOURCE_TEXT.split()[:12])
        report = sim.compare(
            SOURCE_TEXT, [source("s2", "Partial", half), source("s1", "Full")]
        )
        assert [m.source_title for m in report.matches] == ["Full", "Partial"]

    def test_overall_is_not_the_sum_of_overlapping_sources(self):
        """Two sources containing the same passage must not add up past 100."""
        report = sim.compare(SOURCE_TEXT, [source("a", "A"), source("b", "B")])
        assert report.overall_similarity == 100.0

    def test_empty_source_is_skipped(self):
        report = sim.compare(SOURCE_TEXT, [sim.Source("empty", "Empty", "")])
        assert report.matches == []

    def test_scope_note_travels_with_the_report(self):
        assert "not against the web" in sim.compare(SOURCE_TEXT, []).scope_note


class TestPassages:
    def test_a_copied_run_is_reported_as_one_passage(self):
        document = "Intro sentence here. " + SOURCE_TEXT + " Closing thoughts."
        passages = sim.compare(document, [source()]).passages()
        assert len(passages) == 1
        assert "lake victoria basin" in passages[0].text

    def test_passage_knows_its_source(self):
        passage = sim.compare(SOURCE_TEXT, [source()]).passages()[0]
        assert passage.source_title == "Source one"
        assert passage.word_count > 5

    def test_isolated_single_hits_are_not_passages(self):
        report = sim.compare(UNRELATED, [source()])
        assert report.passages() == []

    def test_passages_are_longest_first(self):
        document = SOURCE_TEXT + " " + " ".join(UNRELATED.split()[:6])
        passages = sim.compare(
            document, [source(), source("s2", "Short", UNRELATED)]
        ).passages()
        assert passages == sorted(passages, key=lambda p: p.word_count, reverse=True)

    def test_passage_offsets_point_into_the_document(self):
        document = "Padding words that come first. " + SOURCE_TEXT
        passage = sim.compare(document, [source()]).passages()[0]
        assert passage.start_word >= 5


class TestHeatmap:
    def test_shape_matches_labels(self):
        text = (SOURCE_TEXT + " ") * 4
        labels, sources, matrix = sim.heatmap(text, [source(), source("s2", "B", UNRELATED)])
        assert len(matrix) == len(sources) == 2
        assert all(len(row) == len(labels) for row in matrix)

    def test_values_are_percentages(self):
        text = (SOURCE_TEXT + " ") * 4
        _, _, matrix = sim.heatmap(text, [source()])
        assert all(0 <= value <= 100 for row in matrix for value in row)

    def test_matching_region_scores_higher_than_unrelated_region(self):
        text = (UNRELATED + " ") * 3 + (SOURCE_TEXT + " ") * 3
        _, _, matrix = sim.heatmap(text, [source()], segments=2)
        assert matrix[0][-1] > matrix[0][0]

    def test_no_sources_returns_empty(self):
        assert sim.heatmap(SOURCE_TEXT, []) == ([], [], [])

    def test_empty_document_returns_empty(self):
        assert sim.heatmap("", [source()]) == ([], [], [])


class TestCitationCoverage:
    def test_cited_claim_counts_as_covered(self):
        report = sim.citation_coverage(
            "Rainfall increased by 30% over the decade (Mwangi, 2019)."
        )
        assert report.coverage == 100.0
        assert report.uncited == []

    def test_uncited_claim_is_flagged(self):
        report = sim.citation_coverage("Studies show that rainfall increased sharply.")
        assert report.coverage == 0.0
        assert len(report.uncited) == 1

    def test_numeric_sentences_need_a_source(self):
        assert sim.needs_citation("Yields fell by 42% last season.")

    def test_opinion_sentences_do_not(self):
        assert not sim.needs_citation("This chapter is organised in three parts.")

    def test_numeric_citation_style_is_recognised(self):
        report = sim.citation_coverage("Studies show a sharp increase [12].")
        assert report.coverage == 100.0

    def test_et_al_year_style_is_recognised(self):
        report = sim.citation_coverage(
            "Research demonstrates a link (Okello et al., 2021)."
        )
        assert report.coverage == 100.0

    def test_mixed_document(self):
        report = sim.citation_coverage(
            "Studies show A (Ali, 2020). Research reports B. "
            "The chapter proceeds as follows."
        )
        assert report.claims == 2
        assert report.cited_claims == 1
        assert report.coverage == 50.0

    def test_text_without_claims_is_full_coverage(self):
        report = sim.citation_coverage("This chapter is organised in three parts.")
        assert report.coverage == 100.0
        assert "No citation-worthy claims" in report.verdict

    def test_empty_text(self):
        assert sim.citation_coverage("").coverage == 100.0

    @pytest.mark.parametrize(
        "coverage_text,expected",
        [
            ("Studies show A (Ali, 2020).", "Claims are well supported."),
            (
                "Studies show A (Ali, 2020). Research reports B (Bee, 2021). Data reveal C.",
                "Some claims still need a source.",
            ),
            ("Studies show A. Research reports B.", "Most claims are unsupported."),
        ],
    )
    def test_verdict_wording(self, coverage_text, expected):
        assert sim.citation_coverage(coverage_text).verdict == expected

    def test_markers_are_counted(self):
        report = sim.citation_coverage("A (Ali, 2020). B (Bee, 2021). C.")
        assert report.markers == 2


class TestRepeatedPhrases:
    def test_finds_a_repeated_phrase(self):
        text = ("the same eight word phrase repeated verbatim here " * 3)
        repeats = sim.repeated_phrases(text, size=8)
        assert repeats and repeats[0][1] >= 2

    def test_unique_text_has_no_repeats(self):
        assert sim.repeated_phrases(SOURCE_TEXT, size=8) == []


class TestSummarise:
    def test_bundles_both_analyses(self):
        result = sim.summarise(
            SOURCE_TEXT + " Studies show more rain.", [source()]
        )
        assert result["similarity"] > 0
        assert result["top_source"] == "Source one"
        assert result["uncited_claims"] == 1
        assert result["scope_note"] == sim.SCOPE_NOTE

    def test_works_without_sources(self):
        result = sim.summarise(SOURCE_TEXT, [])
        assert result["similarity"] == 0
        assert result["top_source"] is None
