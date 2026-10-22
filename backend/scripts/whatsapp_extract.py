"""Optional: turn a WhatsApp "Export chat (without media)" .txt into draft voice examples. Runs fully local.

    uv run python scripts/whatsapp_extract.py chat.txt --me "Chandru" > data/voice/whatsapp_draft.jsonl
Keeps only your messages (grouped into bursts) plus the other person's previous message as context,
then strips phone numbers, emails, URLs and names. REVIEW the output by hand; entries start as reviewed: false.
"""

import argparse
import json
import re

LINE = re.compile(r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),? (\d{1,2}:\d{2}(?::\d{2})?\s?[APMapm]{0,2})\]?\s?-?\s?([^:]+): (.*)$")
SCRUB = [
    (re.compile(r"https?://\S+"), "<link>"), (re.compile(r"\S+@\S+\.\S+"), "<email>"),
    (re.compile(r"\+?\d[\d\s-]{8,}\d"), "<phone>"),
]
SKIP = ("<Media omitted>", "This message was deleted", "Messages and calls are end-to-end encrypted")


def scrub(text: str, names: list[str]) -> str:
    for pat, rep in SCRUB:
        text = pat.sub(rep, text)
    for n in names:
        text = re.sub(rf"\b{re.escape(n)}\b", "<name>", text, flags=re.I)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--me", required=True, help="your display name in the export")
    args = ap.parse_args()
    msgs = []
    for raw in open(args.file, encoding="utf-8"):
        m = LINE.match(raw.strip())
        if m:
            msgs.append([m.group(3).strip(), m.group(4)])
        elif msgs:
            msgs[-1][1] += " " + raw.strip()
    others = sorted({s for s, _ in msgs if s != args.me})
    i, n = 0, 0
    while i < len(msgs):
        if msgs[i][0] == args.me or any(t in msgs[i][1] for t in SKIP):
            i += 1
            continue
        context = msgs[i][1]
        j = i + 1
        bursts = []
        while j < len(msgs) and msgs[j][0] == args.me:
            if not any(t in msgs[j][1] for t in SKIP):
                bursts.append(scrub(msgs[j][1], others))
            j += 1
        if bursts:
            n += 1
            print(json.dumps({"id": f"wa-{n:04d}", "category": "whatsapp", "persona": "casual",
                              "context": scrub(context, others), "bursts": bursts[:4], "source": "whatsapp",
                              "reviewed": False}, ensure_ascii=False))
        i = j


if __name__ == "__main__":
    main()
