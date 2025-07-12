#!/usr/bin/env python3
import logging
import sys
import httpx
from ollama import Client
from orchestrator import Orchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
OLLAMA_HOST = "http://localhost:11434"

# Health check

def is_ollama_running(host):
    try:
        return httpx.get(f"{host}/", timeout=2.0).status_code == 200
    except:
        return False

if __name__ == "__main__":
    if not is_ollama_running(OLLAMA_HOST):
        logger.critical("Ollama not running; start with 'ollama serve'.")
        sys.exit(1)
    logger.info("Ollama is up")

    client = Client(host=OLLAMA_HOST)
    orchestrator = Orchestrator(client, model="deepseek-r1:8b")

    # Example text
    text = (
        "Please be informed that Mr. Md. Mahadi Hasan holds two accounts with Modhumoti Bank PLC "
        "(Account No. 112013800000010 and Account No. 114412200000042). "
        "On 06.11.2024, he executed two transactions via the GO SMART app—an NPSB transaction of 50,000 "
        "and a BEFTN transaction of 50,000. Both were marked as failed in the GO SMART admin panel logs, "
        "but amounts were debited according to the Bank Ultimas report. Investigate and explain the discrepancy."
    )

    params = orchestrator.analyze(text)
    # print("Extracted parameters:\n", params)