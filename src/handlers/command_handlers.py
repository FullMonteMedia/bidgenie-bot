"""
BidGenie AI - Telegram Command Handlers
Implements /start, /newbid, /upload, /settings, /generate, /export commands.
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.session_manager import session_manager
from ..utils.pricing import PRICING_PRESETS, format_currency

logger = logging.getLogger(__name__)

COMPANY_NAME = os.getenv("COMPANY_NAME", "Ace Plumbing")


# ─── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and instructions."""
    user = update.effective_user
    session_manager.clear_session(user.id)

    welcome_text = f"""🔧 *Welcome to BidGenie AI* — Powered by {COMPANY_NAME}

I'm your AI-powered bid proposal assistant. Upload construction plans, scope documents, or describe your project — and I'll generate a professional, client-ready bid proposal in minutes.

*What I can do:*
• 📄 Process PDFs, blueprints, and Word documents
• 🔍 Extract scope of work, materials & measurements
• 💰 Calculate labor, material & markup costs
• 📋 Generate professional PDF proposals
• 📊 Export to Excel/CSV for your records

*Quick Start Commands:*
/newbid — Start a new bid project
/upload — Upload a document or blueprint
/settings — Configure your company & pricing
/generate — Generate the bid proposal
/export — Download PDF or Excel file
/help — Show all commands

---
_Ready to build your first bid? Type /newbid to begin._"""

    keyboard = [
        [InlineKeyboardButton("🚀 Start New Bid", callback_data="newbid")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


# ─── /help ───────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all commands and usage."""
    help_text = """📖 *BidGenie AI — Command Reference*

*Project Commands:*
/newbid — Start a new bid project (clears current session)
/upload — Upload a PDF, image, or Word document
/generate — Analyze documents and generate proposal
/export — Download PDF proposal or Excel file

*Configuration:*
/settings — View/update company info and pricing
/preset — Set pricing preset (residential/commercial/luxury)
/company — Update company name and contact info

*Review & Edit:*
/scope — View current scope breakdown
/pricing — View/edit line item pricing
/revise — Make changes before final export
/status — Show current session status

*Utilities:*
/rush — Quick estimate mode (faster, less detail)
/clear — Clear current session and start fresh
/start — Return to main menu
/help — Show this help message

---
*Workflow:*
1️⃣ /newbid → Enter project & client name
2️⃣ /upload → Upload your documents
3️⃣ /generate → AI analyzes and builds proposal
4️⃣ Review pricing and make edits
5️⃣ /export → Download your PDF proposal

_~ = Estimated value | [C] = Confirmed value_"""

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


# ─── /newbid ─────────────────────────────────────────────────────────────────

async def cmd_newbid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new bid project."""
    user = update.effective_user
    session = session_manager.create_session(user.id)
    session_manager.apply_settings_to_session(session, user.id)
    session.state = "intake_project_name"

    await update.message.reply_text(
        "🆕 *New Bid Project*\n\nLet's get started! First, what is the *project name*?\n\n"
        "_Example: Johnson Residence Bathroom Remodel, Main St Commercial Buildout_",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /upload ─────────────────────────────────────────────────────────────────

async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to upload a file."""
    user = update.effective_user
    session = session_manager.get_or_create(user.id)
    session.state = "awaiting_upload"
    session.touch()

    await update.message.reply_text(
        "📎 *Upload Document*\n\n"
        "Please send me your file. I accept:\n"
        "• 📄 PDF (plans, specs, scope documents)\n"
        "• 🖼 Images (blueprints, photos, drawings)\n"
        "• 📝 Word documents (.docx)\n"
        "• 📋 Text files (.txt)\n\n"
        "_You can upload multiple files. Send /generate when done._",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /settings ───────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and manage settings."""
    user = update.effective_user
    settings = session_manager.get_settings(user.id)

    settings_text = f"""⚙️ *Settings — {settings.get('company_name', COMPANY_NAME)}*

*Company Information:*
• Name: `{settings.get('company_name', 'Not set')}`
• Address: `{settings.get('company_address', 'Not set')}`
• Phone: `{settings.get('company_phone', 'Not set')}`
• Email: `{settings.get('company_email', 'Not set')}`
• License #: `{settings.get('company_license', 'Not set')}`

*Default Pricing:*
• Preset: `{settings.get('default_preset', 'residential').title()}`
• Markup: `{settings.get('default_markup', 20)}%`
• Overhead: `{settings.get('default_overhead', 10)}%`
• Profit Margin: `{settings.get('default_profit', 15)}%`

*To update, send:*
`/set company_name Your Company Name`
`/set company_phone (555) 000-0000`
`/set markup 25`
`/preset residential|commercial|luxury`"""

    keyboard = [
        [InlineKeyboardButton("🏠 Residential Preset", callback_data="preset_residential"),
         InlineKeyboardButton("🏢 Commercial Preset", callback_data="preset_commercial")],
        [InlineKeyboardButton("💎 Luxury Preset", callback_data="preset_luxury")],
        [InlineKeyboardButton("✏️ Edit Company Info", callback_data="edit_company")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        settings_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


# ─── /set (settings update) ──────────────────────────────────────────────────

async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update a specific setting: /set key value"""
    user = update.effective_user
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: `/set <key> <value>`\n\nKeys: `company_name`, `company_phone`, `company_email`, `company_address`, `company_license`, `markup`, `overhead`, `profit`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = args[0].lower()
    value = " ".join(args[1:])

    valid_keys = {
        "company_name": "company_name",
        "company_phone": "company_phone",
        "company_email": "company_email",
        "company_address": "company_address",
        "company_license": "company_license",
        "markup": "default_markup",
        "overhead": "default_overhead",
        "profit": "default_profit",
    }

    if key not in valid_keys:
        await update.message.reply_text(
            f"❌ Unknown setting: `{key}`\nValid keys: {', '.join(valid_keys.keys())}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    setting_key = valid_keys[key]
    if key in ["markup", "overhead", "profit"]:
        try:
            value = float(value.replace("%", ""))
        except ValueError:
            await update.message.reply_text("❌ Please provide a numeric value for percentages.")
            return

    session_manager.save_settings(user.id, {setting_key: value})
    await update.message.reply_text(
        f"✅ Updated `{key}` → `{value}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /preset ─────────────────────────────────────────────────────────────────

async def cmd_preset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set pricing preset."""
    user = update.effective_user
    args = context.args

    if not args:
        presets_text = "📊 *Available Pricing Presets:*\n\n"
        for name, data in PRICING_PRESETS.items():
            presets_text += f"*{name.title()}* — {data['description']}\n"
            presets_text += f"  Markup: {data['markup']}% | Overhead: {data['overhead']}% | Profit: {data['profit']}% | Labor: ${data['labor_rate_per_hour']}/hr\n\n"
        presets_text += "Usage: `/preset residential|commercial|luxury`"
        await update.message.reply_text(presets_text, parse_mode=ParseMode.MARKDOWN)
        return

    preset_name = args[0].lower()
    if preset_name not in PRICING_PRESETS:
        await update.message.reply_text(
            f"❌ Invalid preset. Choose: `residential`, `commercial`, or `luxury`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    preset = PRICING_PRESETS[preset_name]
    session_manager.save_settings(user.id, {
        "default_preset": preset_name,
        "default_markup": preset["markup"],
        "default_overhead": preset["overhead"],
        "default_profit": preset["profit"],
    })

    session = session_manager.get_or_create(user.id)
    session.pricing_preset = preset_name
    session.custom_markup = preset["markup"]
    session.custom_overhead = preset["overhead"]
    session.custom_profit = preset["profit"]

    await update.message.reply_text(
        f"✅ Pricing preset set to *{preset_name.title()}*\n"
        f"Markup: {preset['markup']}% | Overhead: {preset['overhead']}% | Profit: {preset['profit']}% | Labor: ${preset['labor_rate_per_hour']}/hr",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /scope ──────────────────────────────────────────────────────────────────

async def cmd_scope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current scope breakdown."""
    user = update.effective_user
    session = session_manager.get_session(user.id)

    if not session or not session.scope_items:
        await update.message.reply_text(
            "📋 No scope items yet. Upload a document with /upload or start a new bid with /newbid.",
        )
        return

    from ..utils.pricing import format_line_items_table, build_line_items_from_scope
    line_items = build_line_items_from_scope(
        session.scope_items,
        session.pricing_preset,
        session.custom_markup,
        session.custom_overhead,
        session.custom_profit,
    )
    table_text = format_line_items_table(line_items)

    await update.message.reply_text(
        f"📋 *Current Scope — {session.project_name or 'Unnamed Project'}*\n\n{table_text}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /status ─────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current session status."""
    user = update.effective_user
    session = session_manager.get_session(user.id)

    if not session:
        await update.message.reply_text(
            "No active session. Type /newbid to start.",
        )
        return

    status_text = f"""📊 *Session Status*

*Project:* {session.project_name or '_(not set)_'}
*Client:* {session.client_name or '_(not set)_'}
*Trade:* {session.trade_type}
*Type:* {session.project_type.title()}
*State:* `{session.state}`

*Files Uploaded:* {len(session.uploaded_files)}
*Scope Items:* {len(session.scope_items)}
*Revisions:* {session.revision_count}

*Pricing Preset:* {session.pricing_preset.title()}
*Markup:* {session.custom_markup}% | *Overhead:* {session.custom_overhead}% | *Profit:* {session.custom_profit}%

*Total Cost:* {format_currency(session.total_cost) if session.total_cost else '_(not calculated)_'}
*Suggested Bid:* {format_currency(session.suggested_bid) if session.suggested_bid else '_(not calculated)_'}"""

    keyboard = [
        [InlineKeyboardButton("📄 View Scope", callback_data="view_scope"),
         InlineKeyboardButton("🚀 Generate Proposal", callback_data="generate")],
        [InlineKeyboardButton("📥 Export PDF", callback_data="export_pdf"),
         InlineKeyboardButton("📊 Export Excel", callback_data="export_excel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        status_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


# ─── /clear ──────────────────────────────────────────────────────────────────

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear current session."""
    user = update.effective_user
    session_manager.clear_session(user.id)
    await update.message.reply_text(
        "🗑 Session cleared. Type /newbid to start a fresh bid.",
    )


# ─── /rush ───────────────────────────────────────────────────────────────────

async def cmd_rush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rush bid mode — quick estimate from text description."""
    user = update.effective_user
    session = session_manager.get_or_create(user.id)
    session.state = "rush_mode"
    session.touch()

    await update.message.reply_text(
        "⚡ *Rush Bid Mode*\n\n"
        "Describe the project in plain text and I'll generate a quick estimate.\n\n"
        "_Example: 'Replace 2 toilets, 1 bathroom sink, and water heater in a 3-bed residential home. Standard grade fixtures.'_\n\n"
        "Just type your description below:",
        parse_mode=ParseMode.MARKDOWN,
    )
