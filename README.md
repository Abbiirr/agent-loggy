# agent-loggy

## Overview

**agent-loggy** is a Python tool for automated log analysis and verification, designed to process banking or financial logs. It extracts parameters, searches log files, identifies unique trace IDs, compiles comprehensive trace data, and generates detailed analysis reports.

## Features

- Parameter extraction from user input using an LLM agent
- Log file searching and verification
- Trace ID extraction across multiple log files
- Compilation of comprehensive trace data per trace ID
- Automated creation of analysis and summary files
- Confidence scoring and summary reporting

## Project Structure

- `orchestrator.py`: Main pipeline for analysis and file generation
- `agents/parameter_agent.py`: Extracts parameters from input text
- `agents/file_searcher.py`: Finds and verifies relevant log files
- `tools/log_searcher.py`: Searches logs for patterns and trace IDs
- `tools/trace_id_extractor.py`: Extracts trace IDs from log entries
- `tools/full_log_finder.py`: Compiles all log entries for a given trace ID
- `agents/verify_agent.py`: Performs verification and creates analysis files

## Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt