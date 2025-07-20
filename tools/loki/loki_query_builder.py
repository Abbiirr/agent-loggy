import re
import subprocess
from datetime import datetime, timedelta
from typing import Union, List, Dict

# Default Loki endpoint
BASE_URL = "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range"


def _parse_single_datetime(date_str: str, time_str: Union[str, None] = None) -> datetime:
    """
    Parse date (YYYY-MM-DD or YYYY/MM/DD) with optional time (HH:MM or HH:MM:SS).
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Invalid date: {date_str}")

    if time_str:
        m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", time_str)
        if not m:
            raise ValueError(f"Invalid time: {time_str}")
        h, mi, s = m.groups()
        return dt.replace(hour=int(h), minute=int(mi), second=int(s or '0'))

    return dt.replace(hour=0, minute=0, second=0)


def build_curl_args(
        filters: Union[Dict[str, str], None] = None,
        pipeline: Union[Dict[str, str], List[str], None] = None,
        search: Union[str, List[str], None] = None,
        date_str: Union[str, None] = None,
        time_str: Union[str, None] = None,
        end_date_str: Union[str, None] = None,
        end_time_str: Union[str, None] = None,
        output: Union[str, None] = None,
        base_url: str = BASE_URL,
) -> List[str]:
    """
    Return a list of curl args for Loki query, ready for subprocess.
    """
    # Build LogQL selector
    sel = "{" + ",".join(f'{k}="{v}"' for k, v in (filters or {}).items()) + "}"
    if pipeline:
        items = (pipeline.items() if isinstance(pipeline, dict) else pipeline)
        for entry in items:
            if isinstance(entry, tuple):
                k, v = entry
                sel += f' | {k}="{v}"'
            else:
                sel += f' | {entry}'
    if search:
        terms = [search] if isinstance(search, str) else search
        for term in terms:
            esc = term.replace('"', '\\"')
            sel += f' |= "{esc}"'

    # Time range
    if date_str:
        start_dt = _parse_single_datetime(date_str, time_str)
        if end_date_str:
            end_dt = _parse_single_datetime(end_date_str, end_time_str)
        else:
            delta = timedelta(hours=1) if time_str else timedelta(days=1)
            end_dt = start_dt + delta
    else:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=1)

    start = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    end = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Build arg list
    args = ["curl", "-G", base_url,
            "--data-urlencode", f"query={sel}",
            "--data-urlencode", f"start={start}",
            "--data-urlencode", f"end={end}"]
    if output:
        args += ["-o", output]
    return args


def build_curl_command(
        *args,
        **kwargs
) -> str:
    """
    Return a properly formatted curl command string with each parameter on a new line.
    Format: curl -G "url" \
              --param 'value' \
              --param 'value' \
              -o output
    """
    arg_list = build_curl_args(*args, **kwargs)

    # Start with curl command and URL
    formatted_parts = [f'curl -G "{arg_list[2]}" \\']

    # Process remaining arguments in pairs (flag, value)
    i = 3
    while i < len(arg_list):
        if arg_list[i].startswith('--'):
            # Long option with value
            if i + 1 < len(arg_list) and not arg_list[i + 1].startswith('-'):
                flag = arg_list[i]
                value = arg_list[i + 1]
                formatted_parts.append(f"  {flag} '{value}' \\")
                i += 2
            else:
                # Flag without value
                formatted_parts.append(f"  {arg_list[i]} \\")
                i += 1
        elif arg_list[i].startswith('-'):
            # Short option with value
            if i + 1 < len(arg_list) and not arg_list[i + 1].startswith('-'):
                flag = arg_list[i]
                value = arg_list[i + 1]
                formatted_parts.append(f"  {flag} {value}")
                i += 2
            else:
                # Flag without value
                formatted_parts.append(f"  {arg_list[i]}")
                i += 1
        else:
            # Standalone argument
            formatted_parts.append(f"  {arg_list[i]}")
            i += 1

    # Remove trailing backslash from last line
    if formatted_parts[-1].endswith(' \\'):
        formatted_parts[-1] = formatted_parts[-1][:-2]

    return '\n'.join(formatted_parts)


def download_logs(
        *args,
        **kwargs,
) -> None:
    """
    Execute the curl via subprocess, avoiding shell parsing issues.
    """
    arg_list = build_curl_args(*args, **kwargs)
    # Use build_curl_command to get the nice formatted string
    curl_str = build_curl_command(*args, **kwargs)
    print("Running:")
    print(curl_str)
    subprocess.run(arg_list, check=True)


# Example usage
if __name__ == '__main__':
    cmd_str = build_curl_command(
        filters={'service_namespace': 'ncc'},
        pipeline={'trace_id': '6dcac4a5b100123ae1793cb296f11ddf'},
        search='merchant',
        date_str='2025-07-14',
        end_date_str='2025-07-15',
        output='loki-ncc-merchant-14-15.json'
    )
    print(cmd_str)
    print()

    download_logs(
        filters={'service_namespace': 'ncc'},
        pipeline={'trace_id': '6dcac4a5b100123ae1793cb296f11ddf'},
        search='merchant',
        date_str='2025-07-15',
        end_date_str='2025-07-16',
        output='loki-ncc-merchant-15-16.json'
    )