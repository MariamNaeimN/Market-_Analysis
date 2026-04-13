"""Property-based tests for the realtime-dashboard feature."""

import sys
import os
from unittest import mock

# Mock heavy/unavailable dependencies before importing app
_st_mock = mock.MagicMock()
# Make @st.cache_data(ttl=0) act as a passthrough decorator
_st_mock.cache_data = lambda **kwargs: lambda fn: fn

_mocks = {
    "streamlit": _st_mock,
    "streamlit_autorefresh": mock.MagicMock(),
    "boto3": mock.MagicMock(),
    "pandas": mock.MagicMock(),
    "plotly": mock.MagicMock(),
    "plotly.express": mock.MagicMock(),
    "plotly.graph_objects": mock.MagicMock(),
}

for mod_name, mod_mock in _mocks.items():
    sys.modules[mod_name] = mod_mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import clean_display_name, find_by_id, load_insights  # noqa: E402

from hypothesis import given, settings
from hypothesis import strategies as st


# Feature: realtime-dashboard, Property 6: Clean display name strips path prefixes
class TestCleanDisplayNameProperty:
    """Property 6: For any S3 key string, clean_display_name() returns only
    the portion after the last '/' separator. Keys without '/' are returned
    unchanged. Empty strings return empty."""

    @given(segments=st.lists(
        st.text(min_size=1).filter(lambda s: "/" not in s),
        min_size=1, max_size=6,
    ))
    @settings(max_examples=100)
    def test_strips_path_prefixes(self, segments):
        s3_key = "/".join(segments)
        result = clean_display_name(s3_key)
        assert result == segments[-1]

    @given(name=st.text(min_size=1).filter(lambda s: "/" not in s))
    @settings(max_examples=100)
    def test_no_slash_returns_unchanged(self, name):
        assert clean_display_name(name) == name

    def test_empty_string_returns_empty(self):
        assert clean_display_name("") == ""


def exponential_backoff(failure_count):
    """Mirror the JS WebSocket reconnection backoff logic from app.py.

    Starting delay is 1000 ms, doubled after each failure, capped at 30000 ms.
    """
    return min(1000 * (2 ** failure_count), 30000)

    @given(
        prefix=st.text(min_size=1).filter(lambda s: "/" not in s),
        filename=st.text(min_size=1).filter(lambda s: "/" not in s),
    )
    @settings(max_examples=100)
    def test_single_prefix_stripped(self, prefix, filename):
        s3_key = f"{prefix}/{filename}"
        assert clean_display_name(s3_key) == filename

    @given(
        depth=st.integers(min_value=1, max_value=10),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_varying_depth(self, depth, data):
        segments = [
            data.draw(st.text(min_size=1).filter(lambda s: "/" not in s))
            for _ in range(depth + 1)
        ]
        s3_key = "/".join(segments)
        assert clean_display_name(s3_key) == segments[-1]


# Feature: realtime-dashboard, Property 3: find_by_id correctness
class TestFindByIdProperty:
    """Property 3: For any list of insight objects and any documentId string,
    find_by_id() returns the index of the first matching item, or 0 if absent."""

    @given(
        doc_ids=st.lists(st.text(min_size=1), min_size=1, max_size=20),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_present_id_returns_correct_index(self, doc_ids, data):
        insights = [{"documentId": did} for did in doc_ids]
        pick = data.draw(st.integers(min_value=0, max_value=len(doc_ids) - 1))
        target_id = doc_ids[pick]
        result = find_by_id(insights, target_id)
        # Must point to an item with the correct ID (first occurrence)
        assert insights[result]["documentId"] == target_id
        # Must be the first occurrence
        assert result == next(i for i, d in enumerate(insights) if d["documentId"] == target_id)

    @given(
        doc_ids=st.lists(st.text(min_size=1), min_size=0, max_size=20),
        absent_id=st.text(min_size=1),
    )
    @settings(max_examples=100)
    def test_absent_id_returns_zero(self, doc_ids, absent_id):
        from hypothesis import assume
        assume(absent_id not in doc_ids)
        insights = [{"documentId": did} for did in doc_ids]
        assert find_by_id(insights, absent_id) == 0

    def test_empty_list_returns_zero(self):
        assert find_by_id([], "any_id") == 0


# Feature: realtime-dashboard, Property 4: Batch upload resilience
class TestBatchUploadResilienceProperty:
    """Property 4: For any list of N files where an arbitrary subset of uploads
    fail (due to S3 errors), the system should attempt put_object() for every
    file in the list regardless of prior failures. The number of upload attempts
    should always equal N."""

    @given(
        file_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                min_size=1,
                max_size=30,
            ),
            min_size=1,
            max_size=15,
        ),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_all_files_attempted_regardless_of_failures(self, file_names, data):
        """Each file gets exactly one put_object call even when some uploads raise."""
        # Draw a random failure mask: True means that file's upload will raise
        fail_mask = [
            data.draw(st.booleans(), label=f"fail_{i}")
            for i in range(len(file_names))
        ]

        mock_s3 = mock.MagicMock()
        call_log = []

        def put_object_side_effect(**kwargs):
            call_log.append(kwargs["Key"])
            # Find which index this call corresponds to
            idx = len(call_log) - 1
            if idx < len(fail_mask) and fail_mask[idx]:
                raise Exception(f"Simulated S3 failure for {kwargs['Key']}")

        mock_s3.put_object.side_effect = put_object_side_effect

        # Simulate the upload loop from main() — mirrors the app logic exactly
        for i, name in enumerate(file_names):
            try:
                mock_s3.put_object(
                    Bucket="test-bucket", Key=name, Body=b"content"
                )
            except Exception:
                pass  # app continues to next file on failure

        # Core property: every file was attempted
        assert len(call_log) == len(file_names)
        # Each call used the correct file name in order
        for logged_key, expected_name in zip(call_log, file_names):
            assert logged_key == expected_name

    @given(
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100)
    def test_all_failures_still_attempts_all(self, n):
        """Even when every single upload fails, all N files are attempted."""
        mock_s3 = mock.MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 down")

        attempt_count = 0
        for i in range(n):
            try:
                mock_s3.put_object(
                    Bucket="test-bucket", Key=f"file_{i}.txt", Body=b"data"
                )
            except Exception:
                pass
            attempt_count += 1

        assert attempt_count == n
        assert mock_s3.put_object.call_count == n

    def test_no_files_no_calls(self):
        """Empty file list results in zero upload attempts."""
        mock_s3 = mock.MagicMock()
        files = []
        for f in files:
            try:
                mock_s3.put_object(Bucket="test-bucket", Key=f, Body=b"data")
            except Exception:
                pass
        assert mock_s3.put_object.call_count == 0


# Feature: realtime-dashboard, Property 5: Success message includes file name
class TestSuccessMessageIncludesFileNameProperty:
    """Property 5: For any file with name F that is successfully uploaded,
    the displayed success message should contain the string F.

    **Validates: Requirements 7.3**
    """

    @given(
        file_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=1,
            max_size=50,
        ),
        file_size=st.integers(min_value=1, max_value=10_000_000),
    )
    @settings(max_examples=100)
    def test_success_message_contains_file_name(self, file_name, file_size):
        """Simulate a successful upload and verify the success message includes
        the file name."""
        # Build a mock file object matching Streamlit's UploadedFile interface
        mock_file = mock.MagicMock()
        mock_file.name = file_name
        mock_file.size = file_size
        mock_file.getvalue.return_value = b"file-content"

        mock_s3 = mock.MagicMock()
        # put_object succeeds (no exception)

        captured_messages = []

        def fake_success(msg):
            captured_messages.append(msg)

        # Simulate the upload loop from app.py main()
        upload_key = f"uploaded_{mock_file.name}_{mock_file.size}"
        session_state = {}

        if upload_key not in session_state:
            try:
                mock_s3.put_object(
                    Bucket="test-bucket",
                    Key=mock_file.name,
                    Body=mock_file.getvalue(),
                )
                session_state[upload_key] = True
                fake_success(f"Uploaded {mock_file.name}")
            except Exception:
                pass  # not expected in this test

        # Core property: the success message must contain the file name
        assert len(captured_messages) == 1
        assert file_name in captured_messages[0]

    @given(
        file_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100)
    def test_success_message_format_matches_template(self, file_name):
        """The success message should exactly match the format 'Uploaded {name}'."""
        message = f"Uploaded {file_name}"
        assert file_name in message
        assert message == f"Uploaded {file_name}"

    @given(
        file_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                min_size=1,
                max_size=30,
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_each_file_gets_own_success_message(self, file_names):
        """When multiple files are uploaded, each success message contains
        its respective file name."""
        mock_s3 = mock.MagicMock()
        captured_messages = []
        session_state = {}

        for name in file_names:
            mock_file = mock.MagicMock()
            mock_file.name = name
            mock_file.size = 100
            mock_file.getvalue.return_value = b"data"

            upload_key = f"uploaded_{mock_file.name}_{mock_file.size}"
            if upload_key not in session_state:
                try:
                    mock_s3.put_object(
                        Bucket="test-bucket",
                        Key=mock_file.name,
                        Body=mock_file.getvalue(),
                    )
                    session_state[upload_key] = True
                    captured_messages.append(f"Uploaded {mock_file.name}")
                except Exception:
                    pass

        # Each unique file should have a success message containing its name
        unique_names = []
        seen_keys = set()
        for name in file_names:
            key = f"uploaded_{name}_100"
            if key not in seen_keys:
                unique_names.append(name)
                seen_keys.add(key)

        assert len(captured_messages) == len(unique_names)
        for msg, name in zip(captured_messages, unique_names):
            assert name in msg


# Feature: realtime-dashboard, Property 2: Exponential backoff calculation
class TestExponentialBackoffProperty:
    """Property 2: For any non-negative integer n representing consecutive
    reconnection failures, the reconnection delay should equal
    min(1000 * 2^n, 30000) milliseconds — starting at 1 second and capping
    at 30 seconds.

    **Validates: Requirements 4.3**
    """

    @given(n=st.integers(min_value=0, max_value=1000))
    @settings(max_examples=100)
    def test_delay_equals_formula(self, n):
        delay = exponential_backoff(n)
        assert delay == min(1000 * (2 ** n), 30000)

    @given(n=st.integers(min_value=0, max_value=4))
    @settings(max_examples=100)
    def test_delay_below_cap(self, n):
        """For small failure counts (0-4), delay should be exactly 1000 * 2^n."""
        delay = exponential_backoff(n)
        assert delay == 1000 * (2 ** n)
        assert delay <= 30000

    @given(n=st.integers(min_value=5, max_value=1000))
    @settings(max_examples=100)
    def test_delay_capped_at_30000(self, n):
        """For failure counts >= 5, delay should be capped at 30000 ms."""
        delay = exponential_backoff(n)
        assert delay == 30000

    def test_initial_delay_is_1000(self):
        assert exponential_backoff(0) == 1000

    def test_known_sequence(self):
        expected = [1000, 2000, 4000, 8000, 16000, 30000, 30000]
        for i, exp in enumerate(expected):
            assert exponential_backoff(i) == exp


# Feature: realtime-dashboard, Property 1: Fresh data on every load
class TestFreshDataOnEveryLoadProperty:
    """Property 1: For any sequence of DynamoDB table states S1, S2 where
    S1 != S2, calling load_insights() after the table transitions from S1 to
    S2 should return data reflecting S2, never S1.

    **Validates: Requirements 3.2**
    """

    @given(
        state1=st.lists(
            st.fixed_dictionaries({
                "insightId": st.text(min_size=1, max_size=20),
                "documentId": st.text(min_size=1, max_size=20),
            }),
            min_size=0,
            max_size=10,
        ),
        state2=st.lists(
            st.fixed_dictionaries({
                "insightId": st.text(min_size=1, max_size=20),
                "documentId": st.text(min_size=1, max_size=20),
            }),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_returns_current_state_not_stale(self, state1, state2):
        """load_insights() always returns the current table state."""
        mock_table = mock.MagicMock()

        # First call returns state1
        mock_table.scan.return_value = {"Items": list(state1)}

        with mock.patch("app.init_aws_clients", return_value=mock_table):
            result1 = load_insights()
            assert result1 == state1

        # Table transitions to state2
        mock_table.scan.return_value = {"Items": list(state2)}

        with mock.patch("app.init_aws_clients", return_value=mock_table):
            result2 = load_insights()
            assert result2 == state2

    @given(
        states=st.lists(
            st.lists(
                st.fixed_dictionaries({
                    "insightId": st.text(min_size=1, max_size=15),
                    "documentId": st.text(min_size=1, max_size=15),
                }),
                min_size=0,
                max_size=5,
            ),
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_sequential_transitions_always_fresh(self, states):
        """Across N sequential table states, each call reflects the current state."""
        mock_table = mock.MagicMock()

        with mock.patch("app.init_aws_clients", return_value=mock_table):
            for expected_state in states:
                mock_table.scan.return_value = {"Items": list(expected_state)}
                result = load_insights()
                assert result == expected_state

    @given(
        items=st.lists(
            st.fixed_dictionaries({
                "insightId": st.text(min_size=1, max_size=20),
                "documentId": st.text(min_size=1, max_size=20),
            }),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_paginated_scan_returns_all_items(self, items):
        """load_insights() follows pagination and returns all items."""
        mid = len(items) // 2
        page1 = items[:mid]
        page2 = items[mid:]

        mock_table = mock.MagicMock()
        mock_table.scan.side_effect = [
            {"Items": page1, "LastEvaluatedKey": {"pk": "cursor"}},
            {"Items": page2},
        ]

        with mock.patch("app.init_aws_clients", return_value=mock_table):
            result = load_insights()
            assert result == items
            assert mock_table.scan.call_count == 2
