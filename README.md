# ProductPulse

ProductPulse is a small AI-style product feedback dashboard. It collects feedback, classifies category and sentiment, estimates urgency, calculates RICE priority scores, detects repeated pain points, and generates a simple PRD.

This MVP is intentionally lightweight:

- Python standard library backend
- SQLite database
- Vanilla HTML, CSS, and JavaScript frontend
- No Node setup required
- No paid AI API key required

## Run Locally

Open PowerShell in this folder and run:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Features

- Add feedback manually
- Upload CSV feedback with `customer` and `content` columns
- Auto-detect category, sentiment, urgency, and RICE score
- View dashboard metrics and simple charts
- Detect repeated pain-point phrases
- Generate a PRD from the highest-priority feedback

## Project Files

- `app.py` - Python web server, API, SQLite database, scoring logic
- `index.html` - App layout
- `styles.css` - Responsive dashboard styling
- `app.js` - Frontend interactions and rendering
- `sample_feedback.csv` - Example CSV upload file
- `productpulse.db` - Created automatically when the app runs

## Push To GitHub

Install Git first if the `git` command is not available:

```text
https://git-scm.com/downloads
```

Then run these commands from this folder:

```powershell
git init
git add .
git commit -m "Initial ProductPulse MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/productpulse.git
git push -u origin main
```

Before pushing, create an empty GitHub repository named `productpulse`. Do not add a README on GitHub because this project already has one.
