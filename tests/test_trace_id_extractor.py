import pytest
from tools.trace_id_extractor import TraceIDExtractor

SAMPLE_LOG_ROW = """<log-row>
  <dateTime>2024-11-06/12:00:00.900/BDT</dateTime>
  <request-id>1143072e-d9bd-4a3c-8ce5-a13733650513</request-id>
  <processId>82284</processId>
  <threadName>https-jsse-nio-8443-exec-15</threadName>
  <threadId>1456</threadId>
  <threadPriority>5</threadPriority>
  <logger>traceLogger</logger>
  <log-level>TRACE</log-level>
  <log-message>
    Invoking Service
    Class: com.brainstation.ib.serviceapp.authentication.service.AccessService
    Method: getToken
    Arguments: "930336e4-6acb-4222-aaf2-dd5bb5defbdb"
  </log-message>
</log-row>"""

MULTI_ROW_LOG = f"""{SAMPLE_LOG_ROW}
<log-row>
  <dateTime>2024-11-06/12:05:00.123/BDT</dateTime>
  <request-id>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</request-id>
  <processId>82285</processId>
  <threadName>https-jsse-nio-8443-exec-16</threadName>
  <threadId>1457</threadId>
  <threadPriority>5</threadPriority>
  <logger>traceLogger</logger>
  <log-level>TRACE</log-level>
  <log-message>Some other message</log-message>
</log-row>"""

MULTI_REQUEST_ID_ROW = """<log-row>
  <request-id>first-id-0001</request-id>
  <request-id>second-id-0002</request-id>
</log-row>"""

OVERLAPPED_LOG = """<log-row><request-id>id-A</request-id></log-row><log-row><request-id>id-B</request-id></log-row>"""

def test_extract_first_trace_id_without_position():
    """Should return the first request-id when no position is provided."""
    trace_id = TraceIDExtractor.extract(SAMPLE_LOG_ROW)
    assert trace_id == "1143072e-d9bd-4a3c-8ce5-a13733650513"

def test_extract_first_trace_id_in_multi_row():
    """Should return the first request-id by default when multiple <log-row> exist."""
    trace_id = TraceIDExtractor.extract(MULTI_ROW_LOG)
    assert trace_id == "1143072e-d9bd-4a3c-8ce5-a13733650513"

def test_extract_by_position_second_row():
    """Should return the correct request-id from second row."""
    pos = MULTI_ROW_LOG.find("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    trace_id = TraceIDExtractor.extract(MULTI_ROW_LOG, position=pos)
    assert trace_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

def test_return_none_when_no_log_row():
    """Should return None if there are no <log-row> tags."""
    log = "<some-other-tag>no rows here</some-other-tag>"
    assert TraceIDExtractor.extract(log) is None

def test_return_none_when_no_request_id_inside_row():
    """Should return None if the log-row has no <request-id> tag."""
    bad_row = "<log-row><foo>bar</foo></log-row>"
    assert TraceIDExtractor.extract(bad_row) is None

def test_handles_empty_input():
    """Should return None for empty string input."""
    assert TraceIDExtractor.extract("") is None

def test_multi_request_id_returns_first():
    """Should return first request-id when multiple exist in same row."""
    trace_id = TraceIDExtractor.extract(MULTI_REQUEST_ID_ROW)
    assert trace_id == "first-id-0001"

def test_overlapped_default():
    """Should return first request-id from overlapped log rows."""
    trace_id = TraceIDExtractor.extract(OVERLAPPED_LOG)
    assert trace_id == "id-A"

def test_overlapped_position_second():
    """Should return second request-id when position is in second row."""
    pos = OVERLAPPED_LOG.find("id-B")
    trace_id = TraceIDExtractor.extract(OVERLAPPED_LOG, position=pos)
    assert trace_id == "id-B"

def test_malformed_xml_tags():
    """Rows with missing closing tags should be ignored."""
    bad = "<log-row><request-id>bad-id"
    assert TraceIDExtractor.extract(bad) is None

def test_non_string_input():
    """Passing non-str input raises TypeError."""
    with pytest.raises(TypeError):
        TraceIDExtractor.extract(None)

def test_negative_position():
    """Negative position values should treat as no-position (first row)."""
    trace_id = TraceIDExtractor.extract(MULTI_ROW_LOG, position=-10)
    assert trace_id == "1143072e-d9bd-4a3c-8ce5-a13733650513"