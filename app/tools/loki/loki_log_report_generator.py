#!/usr/bin/env python3
"""
log_compiler.py: Library for compiling Loki and application logs into human-readable comprehensive timeline reports.
"""

import json
import os
import re
from typing import List, Dict, Any
from xml.etree import ElementTree as ET
from datetime import datetime


def parse_loki_json(json_files):
    """
    Parse one or more Loki JSON files into timestamped entries per trace_id,
    capturing metadata like scope, service, severity, and span.
    """
    entries = []
    for path in json_files:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        for stream in data.get('data', {}).get('result', []):
            meta = stream.get('stream', {})
            tid = meta.get('trace_id')
            entry_meta = {
                'scope_name': meta.get('scope_name'),
                'service_instance_id': meta.get('service_instance_id'),
                'service_name': meta.get('service_name'),
                'service_namespace': meta.get('service_namespace'),
                'severity_number': meta.get('severity_number'),
                'severity_text': meta.get('severity_text'),
                'span_id': meta.get('span_id')
            }
            for ts_ns, msg in stream.get('values', []):
                ts = int(ts_ns) / 1e9
                timestamp = datetime.fromtimestamp(ts)
                detected_level = entry_meta['severity_text'].lower() if entry_meta.get('severity_text') else None
                entries.append({
                    'timestamp': timestamp,
                    'trace_id': tid,
                    'level': entry_meta['severity_text'],
                    'message': msg.strip(),
                    'source': os.path.basename(path),
                    'detected_level': detected_level,
                    **entry_meta
                })
    return entries

def parse_xml_trace(file_path):
    """
    Parse XML-format trace.log entries into structured entries (assumed TRACE level).
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    entries = []
    for row in root.findall('.//log-row'):
        dt = row.findtext('dateTime')
        rid = row.findtext('request-id')
        msg = row.findtext('log-message') or ''
        timestamp = datetime.strptime(dt, "%Y-%m-%d/%H:%M:%S.%f/BDT")
        entries.append({
            'timestamp': timestamp,
            'trace_id': rid,
            'scope_name': None,
            'service_instance_id': None,
            'service_name': None,
            'service_namespace': None,
            'severity_number': None,
            'severity_text': 'TRACE',
            'span_id': None,
            'level': 'TRACE',
            'detected_level': 'trace',
            'message': msg.strip(),
            'source': os.path.basename(file_path)
        })
    return entries

def parse_plain_log(file_path, trace_id):
    """
    Parse plain-text logs, filtering lines containing the given trace_id.
    Attempts to detect level from common patterns; metadata fields not available.
    """
    entries = []
    ts_re = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,\.]\d+)")
    level_re = re.compile(r"\b(INFO|WARN|ERROR|TRACE|DEBUG)\b")
    with open(file_path, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if trace_id not in line:
                continue
            m = ts_re.match(line)
            timestamp = None
            if m:
                dt_str = m.group('ts')
                for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%dT%H:%M:%S.%f"):
                    try:
                        timestamp = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
            lev = level_re.search(line)
            level = lev.group(1) if lev else 'LOG'
            detected_level = level.lower()
            entries.append({
                'timestamp': timestamp,
                'trace_id': trace_id,
                'scope_name': None,
                'service_instance_id': None,
                'service_name': None,
                'service_namespace': None,
                'severity_number': None,
                'severity_text': None,
                'span_id': None,
                'level': level,
                'detected_level': detected_level,
                'message': line.strip(),
                'source': os.path.basename(file_path)
            })
    return entries

def generate_comprehensive_report(
    trace_ids: List[str],
    entries: List[Dict[str, Any]],
    dispute_text: str,
    search_params: Dict[str, Any],
    summary_metrics: Dict[str, Any],
    analysis_model: str,
    output_path: str
) -> str:
    """
    Write a comprehensive banking log analysis report to output_path.
    - trace_ids: all IDs we investigated
    - entries   : flat list of log-entry dicts (can mix multiple trace_ids)
    - dispute_text: original user text
    - search_params: whatever params dict you used to drive the searches
    - summary_metrics: a dict you build (e.g. relevance_score, confidence_level, etc.)
    - analysis_model : name/version of the LLM or analyzer used
    """
    # 1) Sort entries by timestamp (None => earliest)
    entries_sorted = sorted(entries, key=lambda e: e.get('timestamp') or datetime.min)

    # 2) Prepare header info
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ids_line = ", ".join(trace_ids)

    # 3) Write out the report
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write("COMPREHENSIVE BANKING LOG ANALYSIS\n")
        out.write("="*60 + "\n")
        out.write(f"Generated:    {gen_time}\n")
        out.write(f"Trace IDs:    {ids_line}\n")
        out.write(f"Analysis LLM: {analysis_model}\n")
        out.write("="*60 + "\n\n")

        out.write("EXECUTIVE SUMMARY\n")
        out.write("-"*20 + "\n")
        # No hard‑coded metrics here—just loop over what was passed in
        for key, val in summary_metrics.items():
            out.write(f"{key.replace('_',' ').title():18}: {val}\n")
        out.write(f"{'Total Entries':18}: {len(entries_sorted)}\n\n")

        out.write("ORIGINAL DISPUTE\n")
        out.write("-"*20 + "\n")
        out.write(dispute_text.strip() + "\n\n")

        out.write("SEARCH PARAMETERS\n")
        out.write("-"*20 + "\n")
        for k, v in search_params.items():
            out.write(f"{k:18}: {v}\n")
        out.write("\n")

        out.write("TRANSACTION TIMELINE\n")
        out.write("-"*20 + "\n")
        for i, e in enumerate(entries_sorted, 1):
            ts = e['timestamp'].strftime('%Y-%m-%d/%H:%M:%S') if e.get('timestamp') else 'N/A'
            svc = e.get('service_name') or 'N/A'
            lvl = e.get('level') or 'N/A'
            msg = (e.get('message') or '').replace('\n',' ')[:80]
            out.write(f"{i:3}. {ts} | {lvl:5} | {svc:20} | {msg}...\n")
        out.write("\n")

        out.write("COMPLETE LOG ENTRIES\n")
        out.write("="*40 + "\n\n")
        for i, e in enumerate(entries_sorted, 1):
            out.write(f"ENTRY {i}\n")
            out.write("-"*15 + "\n")
            out.write(f"Source    : {e.get('source')}\n")
            ts = e['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if e.get('timestamp') else 'N/A'
            out.write(f"Timestamp : {ts}\n")
            out.write(f"Level     : {e.get('level')}\n")
            out.write(f"Span ID   : {e.get('span_id')}\n")
            out.write(f"Namespace : {e.get('service_namespace')}\n")
            out.write(f"Message   : {e.get('message')}\n\n")

    return output_path




# Example usage (to be called from other module)
if __name__ == '__main__':
    # assume test_reports/loki_output.json exists from previous steps
    json_files = ['test_reports/loki_output.json']
    entries = parse_loki_json(json_files)
    report = generate_comprehensive_report(
        trace_id='68184aaf-819a-466b-8450-b64dda7301cc',
        entries=entries,
        dispute_text=(
            "Please be informed that Mr. Md. Mahadi Hasan holds two accounts ..."
        ),
        search_params={
            'Time Frame': '06.11.2024',
            'Domain': 'NPSB, BEFTN',
            'Account Numbers': '112013800000010, 114412200000042'
        },
        summary_metrics={
            'relevance_score': '70/100',
            'confidence_level': 'MEDIUM',
            'primary_issue': 'processing_delay|network_issue',
            'recommendation': 'Investigate fund transfer processing logs and account balance checks.'
        },
        analysis_model='deepseek-r1:8b',
        output_path='comprehensive_report.txt'
    )
    print(f"Generated report: {report}")
