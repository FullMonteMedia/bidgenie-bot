"""
BidGenie AI - Message & File Upload Handlers
Handles text messages, file uploads, and conversation state machine.
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.session_manager import session_manager
from ..utils.pricing import (
    build_line_items_from_scope, calculate_project_total,
    format_line_items_table, format_currency, get_preset
)
from ..processors.document_processor import parse_document, summarize_extraction
from ..processors.ai_analyzer import analyze_scope, generate_proposal_text, get_clarifying_questions
from ..generators.pdf_generator import generate_proposal_pdf, generate_csv_export

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
PROPOSALS_DIR = os.getenv("PROPOSALS_DIR", "proposals")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROPOSALS_DIR, exist_ok=True)


# ─── TEXT MESSAGE HANDLER ─────────────────────────────────────────────────────

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text messages based on current session state."""
    user = update.effective_user
    text = update.message.text.strip()
    session = session_manager.get_or_create(user.id)

    state = session.state

    if state == "intake_project_name":
        session.project_name = text
        session.state = "intake_client_name"
        session.touch()
        await update.message.reply_text(
            f"✅ Project: *{text}*\n\nNow, what is the *client's name*?",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif state == "intake_client_name":
        session.client_name = text
        session.state = "intake_trade_type"
        session.touch()

        keyboard = [
            [InlineKeyboardButton("🔧 Plumbing", callback_data="trade_Plumbing"),
             InlineKeyboardButton("⚡ Electrical", callback_data="trade_Electrical")],
            [InlineKeyboardButton("❄️ HVAC", callback_data="trade_HVAC"),
             InlineKeyboardButton("🏗 General Construction", callback_data="trade_General Construction")],
            [InlineKeyboardButton("🔨 Multi-Trade", callback_data="trade_Multi-Trade")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ Client: *{text}*\n\nWhat is the *trade type*?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    elif state == "intake_project_type":
        # Handled by callback, but accept text too
        session.state = "awaiting_upload"
        session.touch()
        await update.message.reply_text(
            f"✅ Setup complete!\n\n"
            f"📋 *Project:* {session.project_name}\n"
            f"👤 *Client:* {session.client_name}\n"
            f"🔧 *Trade:* {session.trade_type}\n\n"
            "Now upload your documents with /upload, or type /generate to describe the project manually.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif state == "rush_mode":
        await handle_rush_bid(update, context, text, session)

    elif state == "awaiting_upload":
        # User typed text instead of uploading — treat as manual description
        await update.message.reply_text(
            "💬 Got your description. Processing as manual scope...",
        )
        session.raw_text = text
        session.state = "processing"
        session.touch()
        await process_text_scope(update, context, text, session)

    elif state == "awaiting_clarification":
        # User answered a clarifying question
        session.raw_text += f"\n\nAdditional info: {text}"
        session.state = "awaiting_upload"
        session.touch()
        await update.message.reply_text(
            "✅ Got it! You can upload more documents or type /generate to create the proposal.",
        )

    elif state in ["reviewing", "done"]:
        # Handle revision requests
        if any(word in text.lower() for word in ["change", "update", "edit", "revise", "add", "remove"]):
            await handle_revision_request(update, context, text, session)
        else:
            await update.message.reply_text(
                "Your proposal is ready! Use /export to download it, or describe changes you'd like to make.",
            )

    else:
        # Default: show menu
        await update.message.reply_text(
            "I'm not sure what you'd like to do. Here are your options:\n\n"
            "/newbid — Start a new bid\n"
            "/upload — Upload a document\n"
            "/generate — Generate proposal\n"
            "/status — Check session status\n"
            "/help — Full command list",
        )


# ─── FILE UPLOAD HANDLER ──────────────────────────────────────────────────────

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded documents, photos, and files."""
    user = update.effective_user
    session = session_manager.get_or_create(user.id)
    message = update.message

    # Get file object
    file_obj = None
    file_name = None
    file_type = None

    if message.document:
        file_obj = message.document
        file_name = message.document.file_name or f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_type = "document"
    elif message.photo:
        file_obj = message.photo[-1]  # Highest resolution
        file_name = f"blueprint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_type = "photo"
    else:
        await message.reply_text("❌ Unsupported file type. Please send a PDF, image, or Word document.")
        return

    # Check file size (50MB limit)
    if hasattr(file_obj, 'file_size') and file_obj.file_size and file_obj.file_size > 50 * 1024 * 1024:
        await message.reply_text("❌ File too large. Maximum size is 50MB.")
        return

    # Check extension
    ext = Path(file_name).suffix.lower()
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".docx", ".doc", ".txt", ".webp"}
    if ext not in allowed_exts and file_type != "photo":
        await message.reply_text(
            f"❌ Unsupported file type: `{ext}`\n"
            "Supported: PDF, JPG, PNG, TIFF, DOCX, TXT",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Download file
    processing_msg = await message.reply_text("⏳ Downloading and processing your file...")

    try:
        user_upload_dir = os.path.join(UPLOAD_DIR, str(user.id))
        os.makedirs(user_upload_dir, exist_ok=True)

        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
        file_path = os.path.join(user_upload_dir, safe_name)

        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(file_path)

        # Tag file with metadata
        file_meta = {
            "path": file_path,
            "name": file_name,
            "type": file_type,
            "uploaded_at": datetime.now().isoformat(),
            "project": session.project_name,
            "client": session.client_name,
        }
        session.uploaded_files.append(file_meta)
        session.touch()

        await processing_msg.edit_text(f"✅ File received: `{file_name}`\n⏳ Extracting content...")

        # Process document
        result = parse_document(file_path)
        summary = summarize_extraction(result)

        if result.get("success") and result.get("raw_text"):
            session.raw_text += f"\n\n[File: {file_name}]\n{result['raw_text']}"
            if result.get("trade_type") and not session.trade_type:
                session.trade_type = result["trade_type"]
            session.extracted_materials.extend(result.get("materials", []))
            session.extracted_measurements.extend(result.get("measurements", []))
            if result.get("timeline"):
                session.timeline_notes = result["timeline"]
            session.touch()

        await processing_msg.edit_text(summary, parse_mode=ParseMode.MARKDOWN)

        # Offer next steps
        keyboard = [
            [InlineKeyboardButton("📎 Upload Another", callback_data="upload_more"),
             InlineKeyboardButton("🚀 Generate Proposal", callback_data="generate")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(
            f"File #{len(session.uploaded_files)} processed. What's next?",
            reply_markup=reply_markup,
        )

    except Exception as e:
        logger.error(f"File upload error: {e}")
        await processing_msg.edit_text(
            f"❌ Error processing file: {str(e)[:200]}\n\nPlease try again or describe the project manually.",
        )


# ─── GENERATE PROPOSAL ────────────────────────────────────────────────────────

async def handle_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main proposal generation flow."""
    user = update.effective_user
    session = session_manager.get_or_create(user.id)

    if not session.raw_text and not session.scope_items:
        await update.message.reply_text(
            "📋 No content to generate from yet.\n\n"
            "Please /upload a document or describe the project in a message first.",
        )
        return

    # Ensure basic project info
    if not session.project_name:
        session.project_name = "Plumbing Project"
    if not session.client_name:
        session.client_name = "Valued Client"

    session.state = "processing"
    session.touch()

    status_msg = await update.message.reply_text(
        "🧠 *AI Analysis in Progress...*\n\n"
        "⏳ Step 1/4: Analyzing document content...",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Step 1: AI scope analysis
        analysis = await analyze_scope(
            session.raw_text,
            session.trade_type,
            session.project_type,
        )

        await status_msg.edit_text(
            "🧠 *AI Analysis in Progress...*\n\n"
            "✅ Step 1/4: Document analyzed\n"
            "⏳ Step 2/4: Building cost estimate...",
            parse_mode=ParseMode.MARKDOWN,
        )

        if analysis.get("success") and analysis.get("data"):
            data = analysis["data"]
            session.scope_items = data.get("scope_items", [])
            session.project_summary = data.get("project_summary", "")
            if data.get("timeline_estimate"):
                session.timeline_notes = data["timeline_estimate"]
        else:
            # Use fallback scope items
            session.scope_items = _build_fallback_scope(session)

        # Step 2: Calculate pricing
        line_items = build_line_items_from_scope(
            session.scope_items,
            session.pricing_preset,
            session.custom_markup,
            session.custom_overhead,
            session.custom_profit,
        )
        totals = calculate_project_total(line_items)
        session.total_cost = totals["grand_total"]
        session.suggested_bid = totals["suggested_bid"]
        session.touch()

        await status_msg.edit_text(
            "🧠 *AI Analysis in Progress...*\n\n"
            "✅ Step 1/4: Document analyzed\n"
            "✅ Step 2/4: Pricing calculated\n"
            "⏳ Step 3/4: Writing proposal narrative...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Step 3: Generate proposal text
        session_dict = {
            "company_name": session.company_name,
            "client_name": session.client_name,
            "project_name": session.project_name,
            "project_type": session.project_type,
            "trade_type": session.trade_type,
            "timeline_notes": session.timeline_notes,
            "project_summary": getattr(session, "project_summary", ""),
            "line_items": [vars(li) for li in line_items],
            "total_cost": session.total_cost,
            "suggested_bid": session.suggested_bid,
        }
        proposal_text = await generate_proposal_text(session_dict)
        session.proposal_text = proposal_text
        session.touch()

        await status_msg.edit_text(
            "🧠 *AI Analysis in Progress...*\n\n"
            "✅ Step 1/4: Document analyzed\n"
            "✅ Step 2/4: Pricing calculated\n"
            "✅ Step 3/4: Proposal written\n"
            "⏳ Step 4/4: Generating PDF...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Step 4: Generate PDF
        user_proposals_dir = os.path.join(PROPOSALS_DIR, str(user.id))
        os.makedirs(user_proposals_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"BidProposal_{session.project_name.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(user_proposals_dir, pdf_filename)

        line_items_dicts = [vars(li) for li in line_items]
        session_dict["company_address"] = session.company_address
        session_dict["company_phone"] = session.company_phone
        session_dict["company_email"] = session.company_email
        session_dict["company_license"] = session.company_license

        generate_proposal_pdf(session_dict, line_items_dicts, proposal_text, pdf_path)
        session.proposal_pdf_path = pdf_path

        # Also generate Excel
        excel_filename = pdf_filename.replace(".pdf", ".xlsx")
        excel_path = os.path.join(user_proposals_dir, excel_filename)
        generate_csv_export(line_items_dicts, session_dict, excel_path)
        session.proposal_csv_path = excel_path

        session.state = "reviewing"
        session.revision_count += 1
        session.touch()

        await status_msg.delete()

        # Show summary
        table_text = format_line_items_table(line_items)
        summary = (
            f"✅ *Proposal Ready — {session.project_name}*\n\n"
            f"👤 Client: {session.client_name}\n"
            f"🔧 Trade: {session.trade_type} ({session.project_type.title()})\n"
            f"📋 Line Items: {len(line_items)}\n"
            f"⏱ Timeline: {session.timeline_notes}\n\n"
            f"{table_text}\n\n"
            f"💰 *Total: {format_currency(session.total_cost)}*\n"
            f"🎯 *Suggested Bid: {format_currency(session.suggested_bid)}*"
        )

        keyboard = [
            [InlineKeyboardButton("📄 Download PDF", callback_data="export_pdf"),
             InlineKeyboardButton("📊 Download Excel", callback_data="export_excel")],
            [InlineKeyboardButton("✏️ Revise Pricing", callback_data="revise_pricing"),
             InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send in chunks if too long
        if len(summary) > 4000:
            await update.message.reply_text(summary[:4000], parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text(
                summary[4000:] if len(summary) > 4000 else "",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                summary,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )

        # Ask about clarifying questions if any
        if analysis.get("data", {}).get("clarifying_questions"):
            questions = analysis["data"]["clarifying_questions"]
            if questions:
                q_text = "💡 *Suggestions to improve accuracy:*\n\n"
                for q in questions[:3]:
                    q_text += f"• {q}\n"
                q_text += "\n_Reply with answers to refine the estimate, or use /export to download now._"
                await update.message.reply_text(q_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Generate error: {e}")
        await status_msg.edit_text(
            f"❌ Error generating proposal: {str(e)[:300]}\n\n"
            "Please check your API keys in .env and try again.",
        )


# ─── EXPORT HANDLER ───────────────────────────────────────────────────────────

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE, export_type: str = "pdf"):
    """Send the generated proposal file to the user."""
    user = update.effective_user
    session = session_manager.get_session(user.id)

    if not session:
        await update.message.reply_text("No active session. Type /newbid to start.")
        return

    if export_type == "pdf":
        file_path = session.proposal_pdf_path
        if not file_path or not os.path.exists(file_path):
            await update.message.reply_text("No PDF generated yet. Use /generate first.")
            return
        await update.message.reply_text("📄 Sending your PDF proposal...")
        with open(file_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(file_path),
                caption=f"📋 *{session.project_name}* — Bid Proposal\nClient: {session.client_name}\nTotal: {format_currency(session.suggested_bid)}",
                parse_mode=ParseMode.MARKDOWN,
            )

    elif export_type in ["excel", "csv"]:
        file_path = session.proposal_csv_path
        if not file_path or not os.path.exists(file_path):
            await update.message.reply_text("No Excel file generated yet. Use /generate first.")
            return
        await update.message.reply_text("📊 Sending your Excel file...")
        with open(file_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(file_path),
                caption=f"📊 *{session.project_name}* — Cost Breakdown",
                parse_mode=ParseMode.MARKDOWN,
            )


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export command handler."""
    user = update.effective_user
    session = session_manager.get_session(user.id)

    if not session or (not session.proposal_pdf_path and not session.proposal_csv_path):
        await update.message.reply_text(
            "No proposal generated yet. Use /generate first.",
        )
        return

    keyboard = [
        [InlineKeyboardButton("📄 PDF Proposal", callback_data="export_pdf"),
         InlineKeyboardButton("📊 Excel/CSV", callback_data="export_excel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📥 *Export Your Proposal*\n\nChoose your format:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


# ─── CALLBACK QUERY HANDLER ───────────────────────────────────────────────────

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    session = session_manager.get_or_create(user.id)

    if data == "newbid":
        from .command_handlers import cmd_newbid
        await cmd_newbid(update, context)

    elif data == "settings":
        from .command_handlers import cmd_settings
        await cmd_settings(update, context)

    elif data == "help":
        from .command_handlers import cmd_help
        await cmd_help(update, context)

    elif data == "upload_more":
        session.state = "awaiting_upload"
        session.touch()
        await query.message.reply_text("📎 Send your next file.")

    elif data == "generate":
        # Create a fake update with message for generate handler
        await handle_generate(update, context)

    elif data == "export_pdf":
        await handle_export(update, context, "pdf")

    elif data == "export_excel":
        await handle_export(update, context, "excel")

    elif data.startswith("trade_"):
        trade = data.replace("trade_", "")
        session.trade_type = trade
        session.state = "intake_project_type"
        session.touch()

        keyboard = [
            [InlineKeyboardButton("🏠 Residential", callback_data="type_residential"),
             InlineKeyboardButton("🏢 Commercial", callback_data="type_commercial")],
            [InlineKeyboardButton("💎 Luxury", callback_data="type_luxury")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"✅ Trade: *{trade}*\n\nWhat is the *project type*?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    elif data.startswith("type_"):
        project_type = data.replace("type_", "")
        session.project_type = project_type
        session.pricing_preset = project_type
        preset = get_preset(project_type)
        session.custom_markup = preset["markup"]
        session.custom_overhead = preset["overhead"]
        session.custom_profit = preset["profit"]
        session.state = "awaiting_upload"
        session.touch()

        await query.message.reply_text(
            f"✅ Project type: *{project_type.title()}*\n\n"
            f"📋 *Project:* {session.project_name}\n"
            f"👤 *Client:* {session.client_name}\n"
            f"🔧 *Trade:* {session.trade_type}\n"
            f"💰 *Pricing:* {project_type.title()} preset\n\n"
            "Now upload your documents with /upload, or type /generate to describe the project manually.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data.startswith("preset_"):
        preset_name = data.replace("preset_", "")
        from .command_handlers import cmd_preset
        context.args = [preset_name]
        await cmd_preset(update, context)

    elif data == "view_scope":
        from .command_handlers import cmd_scope
        await cmd_scope(update, context)

    elif data == "revise_pricing":
        await query.message.reply_text(
            "✏️ *Revise Pricing*\n\n"
            "To adjust pricing, use:\n"
            "`/preset residential|commercial|luxury` — Change preset\n"
            "`/set markup 25` — Set custom markup %\n"
            "`/set overhead 12` — Set overhead %\n"
            "`/set profit 18` — Set profit %\n\n"
            "Then use /generate to recalculate.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "regenerate":
        session.revision_count += 1
        session.state = "awaiting_upload"
        await handle_generate(update, context)


# ─── RUSH BID MODE ────────────────────────────────────────────────────────────

async def handle_rush_bid(update, context, text: str, session):
    """Quick estimate from plain text description."""
    session.raw_text = text
    if not session.project_name:
        session.project_name = "Rush Estimate"
    if not session.client_name:
        session.client_name = "Client"

    await update.message.reply_text("⚡ Processing rush estimate...")
    await handle_generate(update, context)


# ─── REVISION HANDLER ────────────────────────────────────────────────────────

async def handle_revision_request(update, context, text: str, session):
    """Handle user's revision request in natural language."""
    session.raw_text += f"\n\nRevision request: {text}"
    session.state = "awaiting_upload"
    session.touch()
    await update.message.reply_text(
        "📝 Got your revision notes. Type /generate to regenerate the proposal with these changes.",
    )


# ─── FALLBACK SCOPE BUILDER ───────────────────────────────────────────────────

def _build_fallback_scope(session) -> list:
    """Build a basic plumbing scope when AI analysis fails."""
    items = []
    text_lower = session.raw_text.lower()

    from ..utils.pricing import PLUMBING_UNIT_COSTS

    # Check for common plumbing items
    checks = [
        ("toilet", "toilet_standard", 1),
        ("sink", "sink_bathroom", 1),
        ("kitchen sink", "sink_kitchen", 1),
        ("shower", "shower_stall", 1),
        ("bathtub", "bathtub_standard", 1),
        ("water heater", "water_heater_40gal", 1),
        ("tankless", "water_heater_tankless", 1),
        ("garbage disposal", "garbage_disposal", 1),
        ("sump pump", "sump_pump", 1),
        ("water softener", "water_softener", 1),
    ]

    for keyword, item_key, default_qty in checks:
        if keyword in text_lower:
            cost_data = PLUMBING_UNIT_COSTS[item_key]
            items.append({
                "description": cost_data["description"],
                "quantity": default_qty,
                "unit": cost_data["unit"],
                "material_cost": cost_data["material"],
                "labor_hours": cost_data["labor_hours"],
                "notes": "Detected from document",
                "is_estimated": True,
                "category": "Fixtures",
            })

    # Always add permit if not present
    if not items or "permit" not in text_lower:
        items.append({
            "description": "Permit & Inspection",
            "quantity": 1,
            "unit": "each",
            "material_cost": 250,
            "labor_hours": 2.0,
            "notes": "Required for all plumbing work",
            "is_estimated": True,
            "category": "General",
        })

    # Add misc materials
    items.append({
        "description": "Miscellaneous Materials & Fittings",
        "quantity": 1,
        "unit": "lot",
        "material_cost": 150,
        "labor_hours": 0,
        "notes": "Fittings, connectors, sealants, etc.",
        "is_estimated": True,
        "category": "General",
    })

    return items
