from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import csv
import json
import re
import sqlite3
import time


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "productpulse.db"

CATEGORY_KEYWORDS = {
    "Bug": ["bug", "crash", "broken", "error", "issue", "fail", "freeze", "glitch", "incorrect"],
    "Feature Request": ["feature", "add", "need", "wish", "request", "support", "export", "integration"],
    "UI/UX": ["confusing", "layout", "design", "button", "screen", "navigation", "ux", "ui", "hard to find"],
    "Pricing": ["price", "pricing", "expensive", "cost", "plan", "billing", "subscription"],
    "Performance": ["slow", "lag", "loading", "delay", "performance", "speed", "timeout"],
}

POSITIVE_WORDS = {"love", "great", "excellent", "fast", "easy", "helpful", "smooth", "good", "amazing"}
NEGATIVE_WORDS = {"bad", "hate", "slow", "broken", "crash", "confusing", "expensive", "bug", "issue", "problem", "fail"}
URGENT_WORDS = {"urgent", "asap", "blocked", "blocker", "critical", "immediately", "cannot", "can't", "crash", "broken"}
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "you", "your", "our", "have",
    "has", "but", "not", "can", "cant", "cannot", "into", "when", "then", "than", "too", "very", "just",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                urgency TEXT NOT NULL,
                reach INTEGER NOT NULL,
                impact INTEGER NOT NULL,
                confidence INTEGER NOT NULL,
                effort INTEGER NOT NULL,
                rice_score REAL NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS total FROM feedback").fetchone()["total"]
        if count == 0:
            seed_rows = [
                ("Aarav", "The dashboard is useful, but CSV upload is confusing on the first try."),
                ("Maya", "The app is slow when I open analytics after uploading many feedback rows."),
                ("Priya", "Please add export to PDF for PRDs. That would help my team share plans."),
                ("Rohan", "Pricing feels expensive for a small startup team."),
                ("Neha", "The login page sometimes shows an error even when the password is correct."),
            ]
            for customer, content in seed_rows:
                row = analyze_feedback(customer, content)
                conn.execute(
                    """
                    INSERT INTO feedback
                    (customer, content, category, sentiment, urgency, reach, impact, confidence, effort, rice_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )


def normalize_words(text):
    return re.findall(r"[a-zA-Z']+", text.lower())


def detect_category(text):
    lowered = text.lower()
    scores = {
        category: sum(1 for word in keywords if word in lowered)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    return best_category if best_score > 0 else "General"


def detect_sentiment(text):
    words = set(normalize_words(text))
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)
    if positive > negative:
        return "Positive"
    if negative > positive:
        return "Negative"
    return "Neutral"


def detect_urgency(text):
    words = set(normalize_words(text))
    if words & URGENT_WORDS:
        return "High"
    if detect_sentiment(text) == "Negative":
        return "Medium"
    return "Low"


def estimate_rice(content, category, sentiment, urgency):
    words = normalize_words(content)
    reach = min(100, max(10, len(words) * 4))
    impact = {"High": 5, "Medium": 4, "Low": 2}[urgency]
    if category in {"Bug", "Performance"}:
        impact += 1
    if sentiment == "Negative":
        impact += 1
    impact = min(5, impact)
    confidence = 85 if category != "General" else 60
    effort = 2 if category in {"UI/UX", "General"} else 3
    score = round((reach * impact * confidence / 100) / effort, 2)
    return reach, impact, confidence, effort, score


def analyze_feedback(customer, content):
    category = detect_category(content)
    sentiment = detect_sentiment(content)
    urgency = detect_urgency(content)
    reach, impact, confidence, effort, score = estimate_rice(content, category, sentiment, urgency)
    return (
        customer.strip() or "Anonymous",
        content.strip(),
        category,
        sentiment,
        urgency,
        reach,
        impact,
        confidence,
        effort,
        score,
        int(time.time()),
    )


def row_to_dict(row):
    return {
        "id": row["id"],
        "customer": row["customer"],
        "content": row["content"],
        "category": row["category"],
        "sentiment": row["sentiment"],
        "urgency": row["urgency"],
        "reach": row["reach"],
        "impact": row["impact"],
        "confidence": row["confidence"],
        "effort": row["effort"],
        "rice_score": row["rice_score"],
        "created_at": row["created_at"],
    }


def get_feedback():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM feedback ORDER BY rice_score DESC, id DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def summarize_counts(rows, field):
    counts = {}
    for row in rows:
        counts[row[field]] = counts.get(row[field], 0) + 1
    return counts


def detect_pain_points(rows):
    phrases = {}
    for row in rows:
        words = [word for word in normalize_words(row["content"]) if len(word) > 3 and word not in STOPWORDS]
        for index in range(len(words) - 1):
            phrase = f"{words[index]} {words[index + 1]}"
            phrases.setdefault(phrase, {"count": 0, "examples": []})
            phrases[phrase]["count"] += 1
            if len(phrases[phrase]["examples"]) < 2:
                phrases[phrase]["examples"].append(row["content"])
    ranked = sorted(phrases.items(), key=lambda item: item[1]["count"], reverse=True)
    return [
        {"phrase": phrase.title(), "count": data["count"], "examples": data["examples"]}
        for phrase, data in ranked[:6]
        if data["count"] > 1
    ]


def build_prd(rows):
    if not rows:
        return "No feedback available yet. Add feedback first, then generate a PRD."
    top = sorted(rows, key=lambda row: row["rice_score"], reverse=True)[0]
    related = [row for row in rows if row["category"] == top["category"]][:4]
    examples = "\n".join(f"- {row['customer']}: {row['content']}" for row in related)
    return f"""# PRD: Improve {top['category']} Experience

## Problem
Customers are reporting {top['category'].lower()} feedback with a top RICE score of {top['rice_score']}.

## Goal
Reduce repeated customer friction and improve user satisfaction for the highest-priority feedback area.

## Evidence
{examples}

## User Stories
- As a product user, I want the product to handle this issue clearly so I can complete my work without delays.
- As a product manager, I want grouped feedback and priority scores so I can choose what to build next.

## Acceptance Criteria
- Feedback items in this category are visible in the dashboard.
- The team can see sentiment, urgency, and RICE score for each item.
- The proposed improvement can be validated with new feedback after release.

## Success Metrics
- Fewer negative feedback items in the {top['category']} category.
- Higher average sentiment score.
- Reduced number of repeated pain points.
"""


def make_dashboard():
    rows = get_feedback()
    return {
        "feedback": rows,
        "stats": {
            "total": len(rows),
            "avg_rice": round(sum(row["rice_score"] for row in rows) / len(rows), 2) if rows else 0,
            "high_urgency": sum(1 for row in rows if row["urgency"] == "High"),
            "negative": sum(1 for row in rows if row["sentiment"] == "Negative"),
        },
        "categories": summarize_counts(rows, "category"),
        "sentiments": summarize_counts(rows, "sentiment"),
        "pain_points": detect_pain_points(rows),
        "prd": build_prd(rows),
    }


class ProductPulseHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/dashboard":
            self.send_json(make_dashboard())
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/feedback":
            payload = self.read_json()
            customer = payload.get("customer", "Anonymous")
            content = payload.get("content", "")
            if not content.strip():
                self.send_json({"error": "Feedback content is required."}, status=400)
                return
            self.insert_feedback([analyze_feedback(customer, content)])
            self.send_json(make_dashboard(), status=201)
            return
        if parsed.path == "/api/upload":
            payload = self.read_json()
            rows = []
            for item in payload.get("rows", []):
                content = str(item.get("content", "")).strip()
                if content:
                    rows.append(analyze_feedback(str(item.get("customer", "Anonymous")), content))
            self.insert_feedback(rows)
            self.send_json(make_dashboard(), status=201)
            return
        if parsed.path == "/api/reset":
            with get_db() as conn:
                conn.execute("DELETE FROM feedback")
            init_db()
            self.send_json(make_dashboard())
            return
        self.send_json({"error": "Not found"}, status=404)

    def insert_feedback(self, rows):
        with get_db() as conn:
            conn.executemany(
                """
                INSERT INTO feedback
                (customer, content, category, sentiment, urgency, reach, impact, confidence, effort, rice_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path):
        routes = {
            "/": "index.html",
            "/index.html": "index.html",
            "/styles.css": "styles.css",
            "/app.js": "app.js",
            "/sample_feedback.csv": "sample_feedback.csv",
        }
        filename = routes.get(path)
        if not filename:
            self.send_error(404)
            return
        file_path = BASE_DIR / filename
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
        }
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_types[file_path.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), ProductPulseHandler)
    print("ProductPulse is running at http://127.0.0.1:8000")
    server.serve_forever()
