# import requests
# import json
# import os
# import time
# from datetime import datetime
# from urllib.parse import urlparse
# import argparse
# import sys
#
# # Import the query builder (assumes it's in the same directory)
# try:
#     from loki_query_builder import LokiQueryBuilder
# except ImportError:
#     logger.error("loki_query_builder.py not found in the same directory")
#     sys.exit(1)
#
#
# class LokiLogDownloader:
#     def __init__(self, headers=None, cookies=None, timeout=30):
#         self.headers = headers or {}
#         self.cookies = cookies or {}
#         self.timeout = timeout
#         self.session = requests.Session()
#         self.session.headers.update(self.headers)
#         self.session.cookies.update(self.cookies)
#
#     def download_logs(self, query_url, output_file=None, format_logs=False, print_curl=False):
#         """
#         Download logs from Loki
#
#         Args:
#             query_url: Full Loki query URL
#             output_file: Output file path (auto-generated if None)
#             format_logs: Whether to format/pretty print the logs
#             print_curl: Whether to print equivalent curl command
#
#         Returns:
#             dict: Response data or None if failed
#         """
#         print(f"Downloading logs from: {query_url}")
#
#         # Print curl command if requested
#         if print_curl:
#             self._print_curl_command(query_url, output_file)
#
#         try:
#             response = self.session.get(query_url, timeout=self.timeout)
#             response.raise_for_status()
#
#             data = response.json()
#
#             # Generate output filename if not provided
#             if not output_file:
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 output_file = f"loki_logs_{timestamp}.json"
#
#             # Save raw response
#             with open(output_file, 'w') as f:
#                 json.dump(data, f, indent=2 if format_logs else None)
#
#             # Print summary
#             self._print_summary(data, output_file)
#
#             # Save formatted logs if requested
#             if format_logs:
#                 formatted_file = output_file.replace('.json', '_formatted.txt')
#                 self._save_formatted_logs(data, formatted_file)
#
#             return data
#
#         except requests.exceptions.RequestException as e:
#             print(f"Error downloading logs: {e}")
#             return None
#         except json.JSONDecodeError as e:
#             print(f"Error parsing JSON response: {e}")
#             return None
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             return None
#
#     def _print_curl_command(self, query_url, output_file=None):
#         """Print equivalent curl command"""
#         print("\n" + "=" * 80)
#         print("📋 EQUIVALENT CURL COMMAND:")
#         print("=" * 80)
#
#         # Generate output filename if not provided
#         if not output_file:
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             output_file = f"loki_logs_{timestamp}.json"
#
#         curl_cmd = f"curl -G '{query_url}'"
#
#         # Add headers
#         for key, value in self.headers.items():
#             curl_cmd += f" \\\n  -H '{key}: {value}'"
#
#         # Add cookies
#         if self.cookies:
#             cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
#             curl_cmd += f" \\\n  -b '{cookie_str}'"
#
#         # Add output
#         curl_cmd += f" \\\n  -o {output_file}"
#
#         print(curl_cmd)
#         print("=" * 80 + "\n")
#
#     def _print_summary(self, data, output_file):
#         """Print download summary"""
#         print(f"\n✅ Logs downloaded successfully!")
#         print(f"📁 Saved to: {output_file}")
#         print(f"📊 File size: {self._get_file_size(output_file)}")
#
#         if 'data' in data and 'result' in data['data']:
#             results = data['data']['result']
#             total_entries = sum(len(stream.get('values', [])) for stream in results)
#             print(f"📝 Total log entries: {total_entries}")
#             print(f"🔢 Log streams: {len(results)}")
#
#         print()
#
#     def _get_file_size(self, filepath):
#         """Get human readable file size"""
#         size = os.path.getsize(filepath)
#         for unit in ['B', 'KB', 'MB', 'GB']:
#             if size < 1024:
#                 return f"{size:.1f} {unit}"
#             size /= 1024
#         return f"{size:.1f} TB"
#
#     def _save_formatted_logs(self, data, output_file):
#         """Save logs in readable text format"""
#         try:
#             with open(output_file, 'w') as f:
#                 f.write("=" * 80 + "\n")
#                 f.write("LOKI LOGS - FORMATTED OUTPUT\n")
#                 f.write("=" * 80 + "\n\n")
#
#                 if 'data' in data and 'result' in data['data']:
#                     for i, stream in enumerate(data['data']['result']):
#                         # Write stream labels
#                         labels = stream.get('stream', {})
#                         f.write(f"🔖 STREAM {i + 1}: {json.dumps(labels, indent=2)}\n")
#                         f.write("-" * 80 + "\n")
#
#                         # Write log entries
#                         for timestamp, log_line in stream.get('values', []):
#                             # Convert nanosecond timestamp to readable format
#                             dt = datetime.fromtimestamp(int(timestamp) / 1_000_000_000)
#                             f.write(f"⏰ {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
#                             f.write(f"📄 {log_line}\n")
#                             f.write("\n")
#
#                         f.write("\n" + "=" * 80 + "\n\n")
#
#             logger.info(f"📖 Formatted logs saved to: {output_file}")
#         except Exception as e:
#             logger.warning(f"Could not save formatted logs: {e}")
#
#     def download_with_params(self, filters=None, search_text=None, date_str=None,
#                              time_str=None, end_date_str=None, end_time_str=None,
#                              output_file=None, format_logs=False, print_curl=False, base_url=None):
#         """
#         Build query and download logs in one step
#
#         Args:
#             Same as LokiQueryBuilder.build_query() plus:
#             output_file: Output file path
#             format_logs: Whether to format logs
#             print_curl: Whether to print equivalent curl command
#             base_url: Custom Loki base URL
#         """
#         builder = LokiQueryBuilder(base_url) if base_url else LokiQueryBuilder()
#
#         query_url = builder.build_query(
#             filters=filters,
#             search_text=search_text,
#             date_str=date_str,
#             time_str=time_str,
#             end_date_str=end_date_str,
#             end_time_str=end_time_str
#         )
#
#         return self.download_logs(query_url, output_file, format_logs, print_curl)
#
#
# def main():
#     parser = argparse.ArgumentParser(description='Download logs from Loki')
#
#     # Query parameters
#     parser.add_argument('--service-namespace', help='Service namespace filter')
#     parser.add_argument('--trace-id', help='Trace ID filter')
#     parser.add_argument('--level', help='Log level filter')
#     parser.add_argument('--search', action='append', help='Text to search for (can use multiple times)')
#     parser.add_argument('--date', help='Start date (YYYY-MM-DD)')
#     parser.add_argument('--time', help='Start time (HH:MM)')
#     parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
#     parser.add_argument('--end-time', help='End time (HH:MM)')
#
#     # Download options
#     parser.add_argument('--output', '-o', help='Output file path')
#     parser.add_argument('--format', action='store_true', help='Save formatted/readable logs')
#     parser.add_argument('--print-curl', action='store_true', help='Print equivalent curl command')
#     parser.add_argument('--url', help='Direct Loki query URL to download')
#     parser.add_argument('--base-url', help='Custom Loki base URL')
#
#     # Authentication
#     parser.add_argument('--header', action='append', help='HTTP header (format: "Key: Value")')
#     parser.add_argument('--cookie', help='Cookie string')
#     parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
#     parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
#                         default='INFO', help='Set logging level')
#
#     args = parser.parse_args()
#
#     # Parse headers
#     headers = {}
#     if args.header:
#         for header in args.header:
#             if ':' in header:
#                 key, value = header.split(':', 1)
#                 headers[key.strip()] = value.strip()
#
#     # Parse cookies
#     cookies = {}
#     if args.cookie:
#         for cookie in args.cookie.split(';'):
#             if '=' in cookie:
#                 key, value = cookie.split('=', 1)
#                 cookies[key.strip()] = value.strip()
#
#     # Create downloader
#     downloader = LokiLogDownloader(headers=headers, cookies=cookies, timeout=args.timeout)
#
#     if args.url:
#         # Direct URL download
#         downloader.download_logs(args.url, args.output, args.format, args.print_curl)
#     else:
#         # Build query and download
#         filters = {}
#         if args.service_namespace:
#             filters['service_namespace'] = args.service_namespace
#         if args.trace_id:
#             filters['trace_id'] = args.trace_id
#         if args.level:
#             filters['level'] = args.level
#
#         result = downloader.download_with_params(
#             filters=filters,
#             search_text=args.search,
#             date_str=args.date,
#             time_str=args.time,
#             end_date_str=args.end_date,
#             end_time_str=args.end_time,
#             output_file=args.output,
#             format_logs=args.format,
#             print_curl=args.print_curl,
#             base_url=args.base_url
#         )
#
#         if not result:
#             sys.exit(1)
#
#
# # Usage examples
# # Usage examples
# if __name__ == "__main__":
#     # Download logs with your parameters
#     downloader = LokiLogDownloader(
#         headers={'User-Agent': 'LokiDownloader/1.0'},
#         cookies={'session': 'your-session-token'}
#     )
#     result = downloader.download_with_params(
#         filters={'service_namespace': 'ncc'},
#         search_text='merchant',
#         date_str='2025-01-14',  # Start date
#         end_date_str='2025-07-15',  # End date
#         format_logs=True,  # Get readable format too
#         print_curl=True,  # Show curl command
#         output_file='ncc_merchant_logs.json'
#     )
#
#     if result:
#         print("✅ Download completed successfully!")
#     else:
#         print("❌ Download failed")
#     if len(sys.argv) > 1:
#         main()
#     else:
#         print("=== LOKI LOG DOWNLOADER EXAMPLES ===\n")
#
#         # Example programmatic usage
#
#
#         print("Programmatic usage:")
#         print("""
# downloader = LokiLogDownloader()
#
# # Download logs for a date range
# result = downloader.download_with_params(
#     filters={'service_namespace': 'ncc'},
#     search_text='merchant',
#     date_str='2024-01-15',
#     end_date_str='2024-01-17',
#     format_logs=True
# )
#         """)
#
#         print("\n=== CLI EXAMPLES ===")
#         print("# Basic download")
#         print("python loki_downloader.py --service-namespace ncc --search merchant --date 2024-01-15")
#         print()
#         print("# With authentication and curl command")
#         print(
#             'python loki_downloader.py --service-namespace ncc --date 2024-01-15 --header "Authorization: Bearer token" --cookie "session=abc123" --print-curl')
#         print()
#         print("# Download and format logs")
#         print(
#             "python loki_downloader.py --trace-id 61fa1ef4cd67e7eb --date 2024-01-15 --format --output my_logs.json --print-curl")
#         print()
#         print("# Direct URL download with curl")
#         print("python loki_downloader.py --url 'https://loki-gateway.../query_range?...' --format --print-curl")
#         print()
#         print("# Multiple search terms with time range")
#         print(
#             "python loki_downloader.py --service-namespace abbl --search error --search timeout --date 2024-01-15 --time 09:00 --end-time 17:00 --print-curl")
