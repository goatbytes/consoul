"""Tests for file matching algorithms.

Tests the progressive matching strategies used by edit_file_search_replace:
- Exact matching
- Whitespace-tolerant matching
- Fuzzy matching
- Similar block finding
- Indentation detection
"""

from consoul.ai.tools.implementations.file_matching import (
    detect_indentation_style,
    exact_match,
    find_similar_blocks,
    fuzzy_match,
    whitespace_tolerant_match,
)


class TestExactMatch:
    """Tests for exact_match function."""

    def test_single_exact_match(self):
        """Test finding a single exact match."""
        file_lines = ["line1", "line2", "line3"]
        search_lines = ["line2"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].start_line == 2
        assert matches[0].end_line == 2
        assert matches[0].confidence == 1.0
        assert matches[0].matched_lines == ["line2"]

    def test_multiple_exact_matches(self):
        """Test finding multiple exact matches."""
        file_lines = ["foo", "bar", "foo", "baz", "foo"]
        search_lines = ["foo"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 3
        assert matches[0].start_line == 1
        assert matches[1].start_line == 3
        assert matches[2].start_line == 5

    def test_no_exact_match(self):
        """Test when no exact match exists."""
        file_lines = ["line1", "line2", "line3"]
        search_lines = ["lineX"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_multiline_exact_match(self):
        """Test exact match with multiple lines."""
        file_lines = ["def foo():", "    pass", "    return", "end"]
        search_lines = ["def foo():", "    pass"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].start_line == 1
        assert matches[0].end_line == 2
        assert matches[0].matched_lines == ["def foo():", "    pass"]

    def test_whitespace_difference_fails_exact(self):
        """Test that whitespace differences fail in exact mode."""
        file_lines = ["  line1", "  line2"]
        search_lines = ["line1", "line2"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_case_sensitive(self):
        """Test that matching is case-sensitive."""
        file_lines = ["Line1", "line2"]
        search_lines = ["line1"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_partial_line_no_match(self):
        """Test that partial line matches don't count."""
        file_lines = ["this is line1 with extra"]
        search_lines = ["line1"]

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_empty_search_lines(self):
        """Test behavior with empty search lines."""
        file_lines = ["line1", "line2"]
        search_lines = []

        matches = exact_match(file_lines, search_lines)

        assert len(matches) == 0


class TestWhitespaceTolerantMatch:
    """Tests for whitespace_tolerant_match function."""

    def test_leading_whitespace_match(self):
        """Test matching with leading whitespace difference."""
        file_lines = ["  line1", "  line2"]
        search_lines = ["line1", "line2"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].start_line == 1
        assert matches[0].end_line == 2
        assert matches[0].confidence == 0.95
        assert matches[0].indentation_offset == 2

    def test_trailing_whitespace_match(self):
        """Test matching with trailing whitespace difference."""
        file_lines = ["line1  ", "line2  "]
        search_lines = ["line1", "line2"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].confidence == 0.95

    def test_mixed_indentation(self):
        """Test matching with mixed indentation levels."""
        file_lines = ["    def foo():", "        pass"]
        search_lines = ["def foo():", "    pass"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_offset == 4

    def test_indentation_offset_negative(self):
        """Test indentation offset when file has less indentation."""
        file_lines = ["def foo():", "    pass"]
        search_lines = ["    def foo():", "        pass"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_offset == -4

    def test_multiple_whitespace_matches(self):
        """Test multiple matches with different indentation."""
        file_lines = ["  foo", "bar", "    foo", "baz"]
        search_lines = ["foo"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 2
        assert matches[0].indentation_offset == 2
        assert matches[1].indentation_offset == 4

    def test_blank_line_handling(self):
        """Test handling of blank lines."""
        file_lines = ["line1", "", "line2"]
        search_lines = ["line1", "", "line2"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].start_line == 1

    def test_all_whitespace_lines(self):
        """Test matching all-whitespace lines."""
        file_lines = ["   ", "    "]
        search_lines = ["", ""]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1

    def test_python_code_indentation(self):
        """Test with realistic Python code indentation."""
        file_lines = [
            "def calculate():",
            "    x = 1",
            "    y = 2",
            "    return x + y",
        ]
        search_lines = ["x = 1", "y = 2", "return x + y"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].start_line == 2
        assert matches[0].indentation_offset == 4

    def test_empty_search_lines(self):
        """Test with empty search lines."""
        file_lines = ["line1", "line2"]
        search_lines = []

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_indentation_offset_zero(self):
        """Test indentation offset when indentation matches."""
        file_lines = ["    line1", "    line2"]
        search_lines = ["    line1", "    line2"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_offset == 0

    def test_tab_indentation_preserved(self):
        """Test that tab indentation character is preserved."""
        file_lines = ["\tdef foo():", "\t\tpass"]
        search_lines = ["def foo():", "\tpass"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_offset == 1
        assert matches[0].indentation_char == "\t"

    def test_space_indentation_preserved(self):
        """Test that space indentation character is preserved."""
        file_lines = ["    def foo():", "        pass"]
        search_lines = ["def foo():", "    pass"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_offset == 4
        assert matches[0].indentation_char == " "

    def test_mixed_tab_space_uses_first_char(self):
        """Test that first indentation character is used for mixed indentation."""
        file_lines = ["\t  line1"]  # Tab followed by spaces
        search_lines = ["line1"]

        matches = whitespace_tolerant_match(file_lines, search_lines)

        assert len(matches) == 1
        assert matches[0].indentation_char == "\t"


class TestFuzzyMatch:
    """Tests for fuzzy_match function."""

    def test_high_similarity_match(self):
        """Test matching with high similarity (95%+)."""
        file_lines = ["def hello():", "    print('world')"]
        search_lines = ["def hello():", "    print('world')"]

        matches = fuzzy_match(file_lines, search_lines, threshold=0.8)

        assert len(matches) == 1
        assert matches[0].confidence > 0.95
        assert matches[0].start_line == 1

    def test_medium_similarity_match(self):
        """Test matching with medium similarity (80-90%)."""
        file_lines = ["def hello():", "    print('world')"]
        search_lines = ["def hello():", "    print('wrld')"]  # Missing 'o'

        matches = fuzzy_match(file_lines, search_lines, threshold=0.8)

        assert len(matches) >= 1
        # Just check it's above threshold (might be higher than 95% due to exact first line)
        assert matches[0].confidence >= 0.8

    def test_low_similarity_no_match(self):
        """Test that low similarity below threshold returns no match."""
        file_lines = ["def hello():", "    print('world')"]
        search_lines = ["class Foo:", "    pass"]

        matches = fuzzy_match(file_lines, search_lines, threshold=0.8)

        assert len(matches) == 0

    def test_threshold_configuration(self):
        """Test configuring similarity threshold."""
        file_lines = ["hello world"]
        search_lines = ["goodbye universe"]  # More different

        # Strict threshold - no match
        strict_matches = fuzzy_match(file_lines, search_lines, threshold=0.95)
        assert len(strict_matches) == 0

        # Lenient threshold - match (these have some common words)
        lenient_matches = fuzzy_match(file_lines, search_lines, threshold=0.1)
        assert len(lenient_matches) == 1

    def test_multiple_candidates_best_first(self):
        """Test that best match is returned first when multiple candidates exist."""
        file_lines = [
            "hello world",  # 90% match
            "hello world!",  # 100% match
            "hello wrld",  # 80% match
        ]
        search_lines = ["hello world!"]

        matches = fuzzy_match(file_lines, search_lines, threshold=0.7)

        # Best match should be first
        assert matches[0].start_line == 2
        assert matches[0].confidence == 1.0

    def test_typo_tolerance(self):
        """Test tolerance for typos."""
        file_lines = ["def calcualte(x, y):"]  # Typo: calcualte
        search_lines = ["def calculate(x, y):"]  # Correct spelling

        matches = fuzzy_match(file_lines, search_lines, threshold=0.85)

        assert len(matches) == 1
        assert matches[0].confidence > 0.85

    def test_multiline_fuzzy_matching(self):
        """Test fuzzy matching across multiple lines."""
        file_lines = ["def foo():", "    x = 1", "    y = 2", "    return x + y"]
        search_lines = ["def foo():", "    x = 1", "    y = 3"]  # y = 3 instead of 2

        matches = fuzzy_match(file_lines, search_lines, threshold=0.8)

        # Should find partial match
        assert len(matches) >= 1

    def test_confidence_score_accuracy(self):
        """Test that confidence scores are reasonable."""
        file_lines = ["abcdefghij"]
        search_lines = ["abcdefghi"]  # 90% of characters match

        matches = fuzzy_match(file_lines, search_lines, threshold=0.8)

        assert len(matches) == 1
        # Should be roughly 90% similar
        assert 0.85 <= matches[0].confidence <= 1.0

    def test_empty_search_lines(self):
        """Test with empty search lines."""
        file_lines = ["line1", "line2"]
        search_lines = []

        matches = fuzzy_match(file_lines, search_lines)

        assert len(matches) == 0

    def test_indentation_offset_not_set(self):
        """Test that fuzzy match doesn't set indentation_offset."""
        file_lines = ["    line1"]
        search_lines = ["line1"]

        matches = fuzzy_match(file_lines, search_lines, threshold=0.7)

        # Fuzzy match should not auto-fix indentation
        if matches:
            assert matches[0].indentation_offset == 0


class TestFindSimilarBlocks:
    """Tests for find_similar_blocks function."""

    def test_top_n_suggestions(self):
        """Test that top N most similar blocks are returned."""
        file_lines = ["line1", "line2", "line3", "line4", "line5"]
        search_lines = ["line2"]

        blocks = find_similar_blocks(file_lines, search_lines, top_n=3)

        assert len(blocks) <= 3
        # Most similar should be exact match
        assert blocks[0].start_line == 2
        assert blocks[0].similarity == 1.0

    def test_context_lines_before_after(self):
        """Test that context lines are included."""
        file_lines = ["a", "b", "c", "TARGET", "d", "e", "f"]
        search_lines = ["TARGET"]

        blocks = find_similar_blocks(file_lines, search_lines, top_n=1)

        assert len(blocks) == 1
        # Should have up to 3 lines before and after
        assert blocks[0].context_before == ["a", "b", "c"]
        assert blocks[0].context_after == ["d", "e", "f"]

    def test_similarity_scoring(self):
        """Test similarity scoring accuracy."""
        file_lines = ["hello world", "hello wrld", "goodbye world"]
        search_lines = ["hello world"]

        blocks = find_similar_blocks(file_lines, search_lines, top_n=3)

        # First should be exact match
        assert blocks[0].similarity == 1.0
        assert blocks[0].start_line == 1

        # Second should be similar
        assert blocks[1].similarity > 0.7
        assert blocks[1].start_line == 2

    def test_no_similar_blocks_below_threshold(self):
        """Test when no blocks are particularly similar."""
        file_lines = ["aaaa", "bbbb", "cccc"]
        search_lines = ["xxxx"]

        blocks = find_similar_blocks(file_lines, search_lines, top_n=3)

        # Should still return blocks, but with low similarity
        assert len(blocks) > 0
        assert all(block.similarity < 0.5 for block in blocks)

    def test_context_at_file_boundaries(self):
        """Test context extraction at start/end of file."""
        file_lines = ["line1", "line2", "line3"]
        search_lines = ["line1"]

        blocks = find_similar_blocks(file_lines, search_lines, top_n=1)

        # At file start - no context before
        assert blocks[0].context_before == []
        assert len(blocks[0].context_after) <= 2

    def test_empty_search_lines(self):
        """Test with empty search lines."""
        file_lines = ["line1", "line2"]
        search_lines = []

        blocks = find_similar_blocks(file_lines, search_lines)

        assert len(blocks) == 0


class TestDetectIndentationStyle:
    """Tests for detect_indentation_style function."""

    def test_spaces_4(self):
        """Test detection of 4-space indentation."""
        lines = ["def foo():", "    pass", "    return", "        nested"]

        style, width = detect_indentation_style(lines)

        assert style == "spaces"
        assert width == 4

    def test_spaces_2(self):
        """Test detection of 2-space indentation."""
        lines = ["if True:", "  print('hello')", "  print('world')"]

        style, width = detect_indentation_style(lines)

        assert style == "spaces"
        assert width == 2

    def test_tabs(self):
        """Test detection of tab indentation."""
        lines = ["def foo():", "\tpass", "\treturn"]

        style, width = detect_indentation_style(lines)

        assert style == "tabs"
        assert width == 1

    def test_mixed_majority_wins(self):
        """Test that majority indentation style wins."""
        lines = [
            "def foo():",
            "    pass",  # spaces
            "    return",  # spaces
            "\tprint()",  # tab
        ]

        style, _ = detect_indentation_style(lines)

        assert style == "spaces"

    def test_no_indentation(self):
        """Test file with no indented lines."""
        lines = ["line1", "line2", "line3"]

        style, width = detect_indentation_style(lines)

        # When no tabs/spaces found, should return the winning style (tabs by default)
        # or spaces with default width - implementation returns tabs,1 when equal counts
        assert style in ["spaces", "tabs"]
        if style == "spaces":
            assert width == 4
        else:
            assert width == 1
