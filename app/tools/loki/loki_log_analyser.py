#!/usr/bin/env python3
"""
log_compiler.py: Library for compiling Loki and application logs into human-readable timeline reports.
"""

import json
import os
import re
from xml.etree import ElementTree as ET
from datetime import datetime

from app.tools.loki.loki_query_builder import download_logs
from app.tools.loki.loki_trace_id_extractor import extract_trace_ids, gather_logs_for_trace_ids

def parse_loki_json(json_files):
    """
    Parse one or more Loki JSON files into timestamped entries per trace_id.
    """
    entries = []
    for path in json_files:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        for stream in data.get('data', {}).get('result', []):
            tid = stream['stream'].get('trace_id')
            for ts_ns, msg in stream.get('values', []):
                ts = int(ts_ns) / 1e9
                timestamp = datetime.fromtimestamp(ts)
                entries.append({
                    'timestamp': timestamp,
                    'trace_id': tid,
                    'message': msg.strip(),
                    'source': os.path.basename(path)
                })
    return entries

def parse_xml_trace(file_path):
    """
    Parse XML-format trace.log entries into structured entries.
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
            'message': msg.strip(),
            'source': os.path.basename(file_path)
        })
    return entries

def parse_plain_log(file_path, trace_id):
    """
    Parse plain-text logs, filtering lines containing the given trace_id.
    """
    entries = []
    ts_re = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,\.]\d+)")
    with open(file_path, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if trace_id not in line:
                continue
            m = ts_re.match(line)
            timestamp = None
            if m:
                dt_str = m.group(1)
                for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%dT%H:%M:%S.%f"):
                    try:
                        timestamp = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
            entries.append({
                'timestamp': timestamp,
                'trace_id': trace_id,
                'message': line.strip(),
                'source': os.path.basename(file_path)
            })
    return entries

def compile_report(entries, trace_id, output_path):
    """
    Sort entries by timestamp and write a timeline report file.
    """
    filtered = [e for e in entries if e.get('trace_id') == trace_id]
    filtered.sort(key=lambda e: e['timestamp'] or datetime.min)
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write(f"TRACE REPORT: {trace_id}\n")
        out.write(f"TOTAL EVENTS: {len(filtered)}\n\n")
        for e in filtered:
            ts = e['timestamp'].isoformat() if e['timestamp'] else 'N/A'
            out.write(f"[{ts}] ({e['source']}) {e['message']}\n")
    return output_path

def compile_from_file_paths(
    trace_id,
    loki_json_paths=None,
    xml_trace_paths=None,
    plain_log_paths=None,
    output_path=None
):
    """
    Convenience wrapper: parse given file lists and generate a report.
    Returns the output file path.
    """
    loki_json_paths = loki_json_paths or []
    xml_trace_paths = xml_trace_paths or []
    plain_log_paths = plain_log_paths or []
    output_path = output_path or f"report_{trace_id}.txt"

    entries = []
    if loki_json_paths:
        entries += parse_loki_json(loki_json_paths)
    for x in xml_trace_paths:
        entries += parse_xml_trace(x)
    for p in plain_log_paths:
        entries += parse_plain_log(p, trace_id)

    return compile_report(entries, trace_id, output_path)

def download_and_compile(
    service_namespace,
    search,
    start_date,
    end_date,
    output_dir='.'
):
    """
    Full pipeline: downloads Loki logs, extracts trace IDs,
    gathers per-trace logs, and writes reports to output_dir.
    Returns a list of generated report file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    raw_json = os.path.join(output_dir, 'loki_output.json')

    # 1) Download raw Loki JSON
    download_logs(
        filters={'service_namespace': service_namespace},
        search=search,
        date_str=start_date,
        end_date_str=end_date,
        output=raw_json
    )

    # 2) Extract trace IDs
    trace_ids = extract_trace_ids(raw_json)
    if not trace_ids:
        return []

    # 3) Gather per-trace Loki JSON files
    loki_files = gather_logs_for_trace_ids(
        filters={'service_namespace': service_namespace},
        trace_ids=trace_ids,
        date_str=start_date,
        end_date_str=end_date
    )

    # 4) Compile a report for each trace
    reports = []
    for file_path in loki_files:
        # derive trace_id from filename: trace_<id>.json
        fname = os.path.basename(file_path)
        tid = fname.replace('trace_','').replace('.json','')
        report_path = os.path.join(output_dir, f"report_{tid}.txt")
        compile_from_file_paths(
            trace_id=tid,
            loki_json_paths=[file_path],
            xml_trace_paths=[],
            plain_log_paths=[],
            output_path=report_path
        )
        reports.append(report_path)

    return reports

# === Test script (download & compile) ===
if __name__ == '__main__':
    # Full pipeline: download Loki logs, extract trace IDs, gather logs, and compile reports
    reports = download_and_compile(
        service_namespace='ncc',
        search='merchant',
        start_date='2025-07-15',
        end_date='2025-07-16',
        output_dir='test_reports'
    )
    print("Test pipeline generated reports:", reports)
