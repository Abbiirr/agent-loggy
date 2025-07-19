import re
from datetime import datetime, timedelta
from urllib.parse import urlencode


class LokiQueryBuilder:
    def __init__(self, base_url="https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range"):
        self.base_url = base_url

    def build_query(self, filters=None, search_text=None, date_str=None, time_str=None, end_date_str=None,
                    end_time_str=None):
        """
        Build Loki query URL

        Args:
            filters: dict of label filters {'service_namespace': 'abbl', 'trace_id': '61fa...'}
            search_text: raw text to search for in logs (string or list of strings)
            date_str: start date in format 'YYYY-MM-DD' or 'YYYY/MM/DD'
            time_str: optional start time in format 'HH:MM' or 'HH:MM:SS'
            end_date_str: optional end date (if not provided, uses date_str logic)
            end_time_str: optional end time in format 'HH:MM' or 'HH:MM:SS'
        """
        # Build LogQL query
        logql_query = self._build_logql(filters or {}, search_text)

        # Build time parameters
        start_time, end_time = self._parse_datetime_range(date_str, time_str, end_date_str, end_time_str)

        # Build query parameters
        params = {
            'query': logql_query,
            'start': start_time,
            'end': end_time
        }

        return f"{self.base_url}?{urlencode(params)}"

    def _build_logql(self, filters, search_text=None):
        """Build LogQL query from filters and search text"""
        # Build label selectors
        if filters:
            selectors = []
            for key, value in filters.items():
                selectors.append(f'{key}="{value}"')
            query = "{" + ", ".join(selectors) + "}"
        else:
            query = "{}"

        # Add text search filters
        if search_text:
            if isinstance(search_text, str):
                search_text = [search_text]

            for text in search_text:
                # Escape double quotes and use LogQL contains operator with double quotes
                escaped_text = text.replace('"', '\\"')
                query += f' |= "{escaped_text}"'

        return query

    def _parse_datetime_range(self, date_str, time_str=None, end_date_str=None, end_time_str=None):
        """Parse date/time range and return start/end timestamps in ISO format"""
        if not date_str:
            # Default to last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
        else:
            # Parse start date/time
            start_time = self._parse_single_datetime(date_str, time_str)

            if end_date_str:
                # Parse end date/time
                end_time = self._parse_single_datetime(end_date_str, end_time_str)
            else:
                # No end date specified, use original logic
                if time_str:
                    # End time is 1 hour later by default
                    end_time = start_time + timedelta(hours=1)
                else:
                    # Whole day: end at 23:59:59 of the same day
                    end_time = start_time.replace(hour=23, minute=59, second=59)

        # Convert to ISO 8601 format (RFC 3339)
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        return start_iso, end_iso

    def _parse_single_datetime(self, date_str, time_str=None):
        """Parse a single date/time combination"""
        # Parse date
        date_formats = ['%Y-%m-%d', '%Y/%m/%d']
        parsed_date = None

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if not parsed_date:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY/MM/DD")

        if time_str:
            # Parse time and combine with date
            time_match = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
            if not time_match:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM or HH:MM:SS")

            hour, minute, second = time_match.groups()
            second = second or "00"

            return parsed_date.replace(
                hour=int(hour),
                minute=int(minute),
                second=int(second)
            )
        else:
            # No time specified, default to start of day
            return parsed_date.replace(hour=0, minute=0, second=0)

    def build_curl_command(self, filters=None, search_text=None, date_str=None, time_str=None,
                           end_date_str=None, end_time_str=None, output_file=None):
        """
        Build a curl command for the Loki query
        """
        # Build LogQL query
        logql_query = self._build_logql(filters or {}, search_text)

        # Build time parameters
        start_time, end_time = self._parse_datetime_range(date_str, time_str, end_date_str, end_time_str)

        # Build curl command
        curl_cmd = f'curl -G "{self.base_url}"'
        curl_cmd += f" \\\n  --data-urlencode 'query={logql_query}'"
        curl_cmd += f" \\\n  --data-urlencode 'start={start_time}'"
        curl_cmd += f" \\\n  --data-urlencode 'end={end_time}'"

        if output_file:
            curl_cmd += f" \\\n  -o {output_file}"

        return curl_cmd


# Simple CLI tool
def main():
    import argparse

    parser = argparse.ArgumentParser(description='Build Loki queries')
    parser.add_argument('--service-namespace', help='Service namespace filter')
    parser.add_argument('--trace-id', help='Trace ID filter')
    parser.add_argument('--level', help='Log level filter')
    parser.add_argument('--search', action='append', help='Text to search for (can use multiple times)')
    parser.add_argument('--date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--time', help='Start time (HH:MM)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--end-time', help='End time (HH:MM)')
    parser.add_argument('--url-only', action='store_true', help='Print only the URL')
    parser.add_argument('--curl', action='store_true', help='Generate curl command instead of URL')
    parser.add_argument('--output-file', help='Output file for curl command')

    args = parser.parse_args()

    # Build filters
    filters = {}
    if args.service_namespace:
        filters['service_namespace'] = args.service_namespace
    if args.trace_id:
        filters['trace_id'] = args.trace_id
    if args.level:
        filters['level'] = args.level

    # Build query
    builder = LokiQueryBuilder()

    if args.curl:
        result = builder.build_curl_command(
            filters=filters,
            search_text=args.search,
            date_str=args.date,
            time_str=args.time,
            end_date_str=args.end_date,
            end_time_str=args.end_time,
            output_file=args.output_file
        )
        print(result)
    else:
        url = builder.build_query(
            filters=filters,
            search_text=args.search,
            date_str=args.date,
            time_str=args.time,
            end_date_str=args.end_date,
            end_time_str=args.end_time
        )

        if args.url_only:
            print(url)
        else:
            print(f"Loki Query URL:\n{url}")


# Usage examples
if __name__ == "__main__":
    # Check if running as CLI
    import sys

    if len(sys.argv) > 1:
        main()
    else:
        # Show examples
        builder = LokiQueryBuilder()

        print("=== LOKI QUERY BUILDER EXAMPLES ===\n")

        # Example 1: Service namespace + text search for whole day
        url1 = builder.build_query(
            filters={'service_namespace': 'ncc'},
            search_text='merchant',
            date_str='2024-01-15'
        )
        print("1. Service + text search (whole day):")
        print(url1)
        print()

        # Example 2: Multiple search terms
        url2 = builder.build_query(
            filters={'service_namespace': 'abbl'},
            search_text=['error', 'timeout'],
            date_str='2024-01-15',
            time_str='14:30'
        )
        print("2. Multiple search terms:")
        print(url2)
        print()

        # Example 3: Date range with trace ID
        url3 = builder.build_query(
            filters={'trace_id': '61fa1ef4cd67e7eb71bea49683bdbc33'},
            date_str='2024-01-15',
            end_date_str='2024-01-17'
        )
        print("3. Date range + trace ID:")
        print(url3)
        print()

        # Example 4: Time range + text search
        url4 = builder.build_query(
            filters={'service_namespace': 'ncc', 'level': 'error'},
            search_text='connection failed',
            date_str='2024-01-15',
            time_str='09:00',
            end_date_str='2024-01-15',
            end_time_str='17:00'
        )
        print("4. Time range + filters + text:")
        print(url4)
        print()

        # Example 5: Generate curl command
        curl_cmd = builder.build_curl_command(
            filters={'service_namespace': 'ncc'},
            search_text='merchant',
            date_str='2025-07-14',
            end_date_str='2025-07-15',
            output_file='loki-ncc-merchant-14-15.json'
        )
        print("5. Curl command:")
        print(curl_cmd)
        print()

        print("=== CLI USAGE ===")
        print("python loki_tool.py --service-namespace ncc --search merchant --date 2025-07-14")
        print("python loki_tool.py --trace-id 61fa... --search error --search timeout --date 2025-07-14 --time 14:30")
        print("python loki_tool.py --service-namespace abbl --date 2025-07-14 --end-date 2025-07-17 --url-only")
        print(
            "python loki_tool.py --service-namespace ncc --search merchant --date 2025-07-14 --end-date 2025-07-15 --curl --output-file loki-ncc-merchant-14-15.json")