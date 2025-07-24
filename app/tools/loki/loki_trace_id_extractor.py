import json
import os
from typing import List, Set, Union, Dict
from app.tools.loki.loki_query_builder import download_logs

def extract_trace_ids(json_file: str) -> List[str]:
    """
    Read a Loki JSON result file and return sorted list of unique trace IDs.

    Args:
        json_file: path to Loki JSON output (query_range)
    Returns:
        List of unique trace_id strings
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ids: Set[str] = set()
    for stream_obj in data.get('data', {}).get('result', []):
        trace_id = stream_obj.get('stream', {}).get('trace_id')
        if trace_id:
            ids.add(trace_id)
    return sorted(ids)

def gather_logs_for_trace_ids(
    filters: Union[Dict[str, str], None],
    trace_ids: List[str],
    date_str: str,
    end_date_str: str,
    time_str: Union[str, None] = None,
    end_time_str: Union[str, None] = None,
    output_dir: str = 'trace_logs'
) -> List[str]:
    """
    For each trace_id, download its logs into a separate JSON file under output_dir.
    Returns list of output file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    files: List[str] = []
    for tid in trace_ids:
        filename = os.path.join(output_dir, f"trace_{tid}.json")
        download_logs(filters=filters,  # ensure service_namespace forward for each call
                      date_str=date_str,
                      time_str=time_str,
                      end_date_str=end_date_str,
                      end_time_str=end_time_str,
                      trace_id=tid,
                      output=filename)
        files.append(filename)
    return files

if __name__ == '__main__':
    # Download logs to file
    download_logs(
        filters={'service_namespace': 'ncc'},
        search='merchant',
        date_str='2025-07-15',
        end_date_str='2025-07-16',
        output='loki-ncc-merchant-15-16.json'
    )

    # Extract unique trace IDs
    trace_ids = extract_trace_ids('loki-ncc-merchant-15-16.json')
    print("Found trace IDs:", trace_ids)

    # Step 2: gather logs for each trace_id
    files = gather_logs_for_trace_ids(
        filters={'service_namespace': 'ncc'},
        trace_ids=trace_ids,
        date_str='2025-07-15',
        end_date_str='2025-07-16'
    )
    print("Downloaded trace logs:", files)

