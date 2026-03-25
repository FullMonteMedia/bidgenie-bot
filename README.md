# BidGenie AI 🧞‍♂️

**BidGenie AI** is a production-ready Telegram bot designed for **Ace Plumbing** (and adaptable for any construction trade). It allows contractors to upload construction plans, scope documents, and bid specs, and returns professional, client-ready bid proposals in PDF and Excel formats.

## 🎯 Core Features

- **Document Processing Engine:** Extracts text from PDFs, Word documents, and images (blueprints) using OCR.
- **AI Scope Analyzer:** Uses Claude (Anthropic) or GPT to intelligently parse scope, identify materials, and estimate labor.
- **Cost Estimation Engine:** Built-in pricing logic with customizable presets (Residential, Commercial, Luxury).
- **Proposal Generator:** Automatically writes professional proposal narratives and generates branded PDF documents.
- **Session Memory:** Tracks project state, uploaded files, and revisions across the conversation.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+
- Tesseract OCR (for image/blueprint processing)
- Poppler (for PDF processing)

**Ubuntu/Debian Installation:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

**Mac Installation:**
```bash
brew install tesseract poppler
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your API keys:
   - `TELEGRAM_BOT_TOKEN`: Get this from [@BotFather](https://t.me/BotFather) on Telegram.
   - `ANTHROPIC_API_KEY`: Get this from [Anthropic Console](https://console.anthropic.com/).
   - Update the `COMPANY_*` variables with your business details.

### 4. Run the Bot
```bash
python bot.py
```

---

## 📱 Telegram Commands

- `/start` — Welcome + instructions
- `/newbid` — Begin new project intake
- `/upload` — Prompt for file upload
- `/settings` — Adjust pricing presets and company info
- `/generate` — Produce proposal from uploaded docs
- `/export` — Download PDF/CSV
- `/scope` — View current scope breakdown
- `/rush` — Quick estimate mode from text

---

## 🏗️ Architecture & Modules

The codebase is structured for scalability and easy maintenance:

- `bot.py` — Main entry point and Telegram application setup.
- `src/handlers/` — Telegram command and message routing.
- `src/processors/` — Document parsing (OCR, PDF extraction) and AI analysis.
- `src/generators/` — PDF and Excel file generation.
- `src/utils/` — Pricing logic, presets, and session management.

---

## ☁️ Deployment Guide

### Option 1: Render / Railway (Recommended)
1. Push this repository to GitHub.
2. Connect your repository to Render or Railway.
3. Set the Build Command: `pip install -r requirements.txt && apt-get install -y tesseract-ocr poppler-utils` (Note: Render requires a custom Dockerfile for apt packages).
4. Set the Start Command: `python bot.py`
5. Add your `.env` variables in the platform's Environment Variables section.

### Option 2: VPS (DigitalOcean, AWS, Linode)
1. Clone the repository to your server.
2. Install system dependencies (Tesseract, Poppler).
3. Set up a Python virtual environment and install `requirements.txt`.
4. Use `systemd` or `pm2` to keep the bot running in the background:
   ```bash
   npm install -g pm2
   pm2 start bot.py --name "bidgenie" --interpreter python3
   pm2 save
   ```

---

## 🛠️ Customizing Pricing

You can adjust the default plumbing unit costs and labor rates in `src/utils/pricing.py`. The bot comes pre-loaded with standard industry rates for fixtures, rough-ins, and general construction tasks.

*Built with ❤️ for Ace Plumbing.*
