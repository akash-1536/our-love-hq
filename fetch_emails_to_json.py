import imaplib
import email
import json
from email.header import decode_header
from email.utils import parsedate_to_datetime

# ====== CONFIGURE THESE ======
GMAIL_ADDRESS = "akashjain1536@gmail.com"   # the Gmail you log into
APP_PASSWORD  = "ytxp xcpb caix bnyx"       # 16-char app password
AKASH_EMAIL   = "akashjain1536@gmail.com"
PAYAL_EMAIL   = "payaltelisara999@gmail.com"
OUTPUT_FILE   = "emails.json"
MAILBOX       = '"[Gmail]/All Mail"'   # or "INBOX" if All Mail doesn't exist
# ==============================


def decode_str(value):
  if not value:
    return ""
  parts = decode_header(value)
  decoded = ""
  for text, enc in parts:
    if isinstance(text, bytes):
      try:
        decoded += text.decode(enc or "utf-8", errors="ignore")
      except LookupError:
        decoded += text.decode("utf-8", errors="ignore")
    else:
      decoded += text
  return decoded


def get_body(msg):
  """Prefer text/plain body. Fallback to text/html stripped crudely."""
  if msg.is_multipart():
    for part in msg.walk():
      content_type = part.get_content_type()
      disp = str(part.get("Content-Disposition") or "").lower()
      if "attachment" in disp:
        continue
      if content_type == "text/plain":
        try:
          return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
        except Exception:
          continue

    # fallback: try first text/html
    for part in msg.walk():
      content_type = part.get_content_type()
      if content_type == "text/html":
        try:
          html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
          import re
          text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
          text = re.sub(r"<.*?>", "", text)
          return text
        except Exception:
          continue
    return ""
  else:
    try:
      return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
    except Exception:
      return ""


def search_pair(imap, from_addr, to_addr):
  """Search messages from from_addr to to_addr."""
  status, data = imap.search(None, 'FROM', f'"{from_addr}"', 'TO', f'"{to_addr}"')
  if status != "OK":
    return []
  ids = data[0].split()
  return ids


def main():
  print("Connecting to Gmail...")
  imap = imaplib.IMAP4_SSL("imap.gmail.com")
  imap.login(GMAIL_ADDRESS, APP_PASSWORD)

  # Select mailbox
  status, _ = imap.select(MAILBOX)
  if status != "OK":
    print("Could not select mailbox", MAILBOX)
    imap.logout()
    return

  all_ids = set()

  # Akash -> Payal
  ids1 = search_pair(imap, AKASH_EMAIL, PAYAL_EMAIL)
  # Payal -> Akash
  ids2 = search_pair(imap, PAYAL_EMAIL, AKASH_EMAIL)

  all_ids.update(ids1)
  all_ids.update(ids2)

  print(f"Found {len(all_ids)} messages between {AKASH_EMAIL} and {PAYAL_EMAIL}")

  emails = []

  for num in all_ids:
    status, data = imap.fetch(num, "(RFC822)")
    if status != "OK":
      continue

    raw = data[0][1]
    msg = email.message_from_bytes(raw)

    raw_from = decode_str(msg.get("From"))
    raw_to = decode_str(msg.get("To"))
    subject = decode_str(msg.get("Subject") or "")

    # 🚫 Skip link-only subjects (Link, link, LINK)
    if subject.strip().lower() == "link":
      continue

    # Extract actual emails
    from_email = email.utils.parseaddr(raw_from)[1] or raw_from
    to_email = email.utils.parseaddr(raw_to)[1] or raw_to

    # Friendly names based on address
    if from_email.lower().startswith(AKASH_EMAIL.lower()):
      from_name = "Akash"
      to_name = "Payal"
    elif from_email.lower().startswith(PAYAL_EMAIL.lower()):
      from_name = "Payal"
      to_name = "Akash"
    else:
      from_name = from_email
      to_name = to_email

    # Date
    date_header = msg.get("Date")
    try:
      dt = parsedate_to_datetime(date_header) if date_header else None
      date_iso = dt.isoformat() if dt else ""
    except Exception:
      date_iso = ""

    body = get_body(msg)

    emails.append({
      "from": from_name,
      "to": to_name,
      "from_email": from_email,
      "to_email": to_email,
      "date": date_iso,
      "subject": subject,
      "body": body.strip()
    })

  imap.close()
  imap.logout()

  # Sort newest to oldest
  def sort_key(e):
    from datetime import datetime
    try:
      return datetime.fromisoformat(e["date"])
    except Exception:
      return datetime.min

  emails.sort(key=sort_key, reverse=True)

  with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(emails, f, ensure_ascii=False, indent=2)

  print(f"Wrote {len(emails)} messages to {OUTPUT_FILE}")


if __name__ == "__main__":
  main()
