"""
Extract manufacturer, model, IP rating, and operating temperature range from the
datasheet PDFs in datasheets/, using the Blocky knowledge-bot API, and write the
results to output.csv.

Usage:
    python extract.py

Requires .env (copy .env.example) with BB_TOKEN, BB_URL, BB_BOT_ID.
"""

import csv
import json
import re
import sys
import time
import uuid
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BB_URL = os.environ.get("BB_URL", "https://api.theblockbrain.ai/blocky/v2").rstrip("/")
BB_TOKEN = os.environ.get("BB_TOKEN")
BB_BOT_ID = os.environ.get("BB_BOT_ID")

DATASHEETS_DIR = Path(__file__).parent / "datasheets"
OUTPUT_CSV = Path(__file__).parent / "output.csv"

POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 120

FIELDS = ["manufacturer", "model", "ip_rating", "operating_temperature_range"]

EXTRACTION_PROMPT = """\
Read the attached datasheet and extract exactly these four fields:

- **manufacturer**: the company name that publishes the datasheet.
- **model**: the product model code/name (generally mentioned in the the title
  or header of the attachment).
- **ip_rating**: the ingress protection / enclosure rating (e.g. "IP67"). This may
  appear under labels other than "IP rating", such as "Ingress protection",
  "Protection class", "IP code", "Enclosure rating", "Housing protection", or
  "Ingress Protection Rating" - treat all of these as the same field. It may
  also only be stated in a sentence rather than the specifications table.
  Be clever about finding it and keep in mind that this value in entered by a
  person, so it may be written in a variety of ways (e.g. "IP 67", "IP-67",
  "IP67", "IP6K7", etc.).
- **operating_temperature_range**: the operating/ambient/working temperature
  range, e.g. "-25 C to +70 C". This may appear under labels such as
  "Operating temperature", "Ambient temperature", "Working temperature range",
  or only mentioned in a descriptive sentence rather than the table - search
  the whole document, not just the specification table. Be as clever as are looking
  the **ip_rating** field, since this value is also entered by a person and may be written differently.

If the datasheet describes more than one model variant (e.g. two columns in
the specifications table for two part numbers) and ip_rating or
operating_temperature_range differ between variants, report all variants
(per manufacturer) in separate lines.

If a field truly cannot be found anywhere in the document, use "N/A".

Respond with ONLY a single JSON object, no other text, no markdown code
fences, in exactly this shape:
{"manufacturer": "...", "model": "...", "ip_rating": "...", "operating_temperature_range": "..."}
"""



def headers(extra=None):
  h = {"Authorization": f"Bearer {BB_TOKEN}"}
  if extra:
    h.update(extra)
  return h


def create_conversation(name: str) -> str:
  """Create a new conversation

  Args:
    name (str): Name of the conversation

  Returns:
    id (str): ID of the newly created conversation
  """
  resp = requests.post(
    f"{BB_URL}/cortex/active-bot/{BB_BOT_ID}/convo",
    headers=headers({"Content-Type": "application/json"}),
    json={"convoName": name},
    timeout=30,
  )
  resp.raise_for_status()
  convo_id = resp.json()["body"]["dataRoomId"]
  logger.info(f"Conversation with id {convo_id} and name {name} created.")
  return convo_id


def upload_file(convo_id: str, file_path: Path) -> str:
  """Upload a file to the conversation

  Args:
    convo_id (str): ID of the conversation
    file_path (Path): Path to the file to upload

  Returns:
    attachment id (str): ID of the uploaded attachment
  """
  with open(file_path, "rb") as f:
    logger.info(f"Uploading file {file_path.name} to conversation {convo_id}...")
    resp = requests.post(
      f"{BB_URL}/cortex/conversation/{convo_id}/attachment",
      headers=headers(),
      files={"attachment": (file_path.name, f, "application/pdf")},
      data={"session_id": str(uuid.uuid4())},
      timeout=60,
    )
  resp.raise_for_status()

  attachement_id = resp.json()["body"]["_id"]
  logger.info(f"File {file_path.name} successfully uploaded with attachment id {attachement_id}.")
  return attachement_id


def wait_for_processing(convo_id: str, attachment_id: str):
  """Check processing status of an attachement upload.

  Args:
    convo_id (str): conversation id
    attachment_id (str): file id
  """
  DEADLINE = time.time() + POLL_TIMEOUT_SECONDS
  DONE_OK = {"COMPLETED", "SUCCESS"}
  DONE_FAIL = {"ERROR", "FAILED"}

  while time.time() < DEADLINE:
    resp = requests.get(
      f"{BB_URL}/cortex/conversation/{convo_id}/attachment",
      headers=headers(),
      timeout=30,
    )
    resp.raise_for_status()
    attachments = resp.json()["body"]
    match = next((a for a in attachments if a["_id"] == attachment_id), None)

    if match is None:
      logger.error(f"Attachment {attachment_id} not found in status response")
      raise RuntimeError(f"Attachment {attachment_id} not found in status response")

    status = match["status"].upper()
    if status in DONE_OK:
      logger.info(f"Attachment {attachment_id} processing completed successfully.")
      return
    if status in DONE_FAIL:
      logger.error(f"Attachment {attachment_id} processing failed with status {status}.")
      raise RuntimeError(f"Attachment processing failed with status {status}")
    
    logger.info(f"Attachment {attachment_id} processing status: {status}. Waiting for {POLL_INTERVAL_SECONDS} seconds before next check...")
    time.sleep(POLL_INTERVAL_SECONDS)

  raise TimeoutError(f"Attachment {attachment_id} did not finish processing in time")


def ask(convo_id: str, content: str) -> str:
  """Send an user message to the knowledge bot. 

  Args:
      convo_id (str): convo id
      content (str): user msg

  Returns:
      str: assistant answer / bot's answer
  """
  resp = requests.post(
    f"{BB_URL}/cortex/completions/v2/user-input",
    headers=headers({"Content-Type": "application/json"}),
    json={
      "convoId": convo_id,
      "content": content,
      "sessionId": str(uuid.uuid4()),
      "messageType": "user-question",
      "enableStreaming": False,
    },
    timeout=90,
  )
  resp.raise_for_status()
  logger.info(f"User message sent to conversation {convo_id}. Received response.")
  return resp.json()["body"]["content"]


def delete_conversation(convo_id: str):
  try:
    requests.delete(f"{BB_URL}/cortex/conversation/{convo_id}", headers=headers(), timeout=30)
  except requests.RequestException as e:
    logger.warning(f"Failed to delete conversation {convo_id}: {e}")


def parse_json_answer(text: str) -> dict:
  """The bot may wrap its JSON in prose or code fences; pull out the object."""
  match = re.search(r"\{.*\}", text, re.DOTALL)
  if not match:
    raise ValueError(f"No JSON object found in response: {text!r}")
  return json.loads(match.group(0))


def process_file(pdf_path: Path):
  logger.info(f"[{pdf_path.name}] creating conversation")
  convo_id = create_conversation(f"extract-{pdf_path.stem}-{uuid.uuid4().hex[:8]}")
  try:
    logger.info(f"[{pdf_path.name}] uploading...")
    attachment_id = upload_file(convo_id, pdf_path)

    logger.info(f"[{pdf_path.name}] waiting for processing...")
    wait_for_processing(convo_id, attachment_id)

    logger.info(f"[{pdf_path.name}] asking for extraction...")
    answer = ask(convo_id, EXTRACTION_PROMPT)

    data = parse_json_answer(answer)
    row = {field: data.get(field, "N/A") for field in FIELDS}
    row["source_file"] = pdf_path.name
    return row
  finally:
    delete_conversation(convo_id)


def main():
  if not BB_TOKEN or not BB_BOT_ID:
    logger.error("Missing BB_TOKEN or BB_BOT_ID. Copy .env.example to .env and fill it in.")
    sys.exit(1)

  pdf_files = sorted(DATASHEETS_DIR.glob("*.pdf"))
  if not pdf_files:
    logger.error(f"No PDFs found in {DATASHEETS_DIR}")
    sys.exit(1)

  rows = []
  failures = []
  for pdf_path in pdf_files:
    try:
      rows.append(process_file(pdf_path))
    except Exception as e:
      logger.error(f"[{pdf_path.name}] FAILED: {e}")
      failures.append(pdf_path.name)
      rows.append({"source_file": pdf_path.name, **{f: "ERROR" for f in FIELDS}})
    logger.info("\n")

  with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["source_file"] + FIELDS)
    writer.writeheader()
    writer.writerows(rows)

  logger.info(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")
  if failures:
    logger.error(f"Failed to extract from: {', '.join(failures)}")
    sys.exit(1)


if __name__ == "__main__":
  main()
