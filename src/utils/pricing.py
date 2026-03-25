"""
BidGenie AI - Pricing Engine
Handles cost estimation, markup calculations, and pricing presets.
Tailored for Ace Plumbing with plumbing-specific line items.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


# ─── PRICING PRESETS ─────────────────────────────────────────────────────────

PRICING_PRESETS: Dict[str, Dict[str, float]] = {
    "residential": {
        "markup": 20.0,
        "overhead": 10.0,
        "profit": 15.0,
        "labor_rate_per_hour": 85.0,
        "description": "Standard residential projects",
    },
    "commercial": {
        "markup": 25.0,
        "overhead": 12.0,
        "profit": 18.0,
        "labor_rate_per_hour": 105.0,
        "description": "Commercial & light industrial projects",
    },
    "luxury": {
        "markup": 35.0,
        "overhead": 15.0,
        "profit": 22.0,
        "labor_rate_per_hour": 130.0,
        "description": "High-end / luxury residential projects",
    },
}

# ─── PLUMBING UNIT COSTS (Material + Labor per unit) ─────────────────────────

PLUMBING_UNIT_COSTS: Dict[str, Dict[str, Any]] = {
    # Fixtures
    "toilet_standard": {"material": 180, "labor_hours": 2.5, "unit": "each", "description": "Standard toilet installation"},
    "toilet_premium": {"material": 450, "labor_hours": 3.0, "unit": "each", "description": "Premium toilet installation"},
    "sink_bathroom": {"material": 120, "labor_hours": 2.0, "unit": "each", "description": "Bathroom sink & faucet"},
    "sink_kitchen": {"material": 250, "labor_hours": 3.0, "unit": "each", "description": "Kitchen sink & faucet"},
    "bathtub_standard": {"material": 400, "labor_hours": 5.0, "unit": "each", "description": "Standard bathtub installation"},
    "shower_stall": {"material": 600, "labor_hours": 6.0, "unit": "each", "description": "Shower stall installation"},
    "water_heater_40gal": {"material": 650, "labor_hours": 4.0, "unit": "each", "description": "40-gallon water heater"},
    "water_heater_50gal": {"material": 800, "labor_hours": 4.5, "unit": "each", "description": "50-gallon water heater"},
    "water_heater_tankless": {"material": 1200, "labor_hours": 6.0, "unit": "each", "description": "Tankless water heater"},

    # Pipes & Rough-In
    "pipe_copper_half": {"material": 4.50, "labor_hours": 0.1, "unit": "linear ft", "description": '1/2" copper supply pipe'},
    "pipe_copper_three_quarter": {"material": 6.00, "labor_hours": 0.12, "unit": "linear ft", "description": '3/4" copper supply pipe'},
    "pipe_pex_half": {"material": 1.50, "labor_hours": 0.07, "unit": "linear ft", "description": '1/2" PEX supply pipe'},
    "pipe_pvc_3inch": {"material": 3.50, "labor_hours": 0.1, "unit": "linear ft", "description": '3" PVC drain pipe'},
    "pipe_pvc_4inch": {"material": 5.00, "labor_hours": 0.12, "unit": "linear ft", "description": '4" PVC drain pipe'},
    "rough_in_bathroom": {"material": 350, "labor_hours": 8.0, "unit": "each", "description": "Full bathroom rough-in"},
    "rough_in_kitchen": {"material": 250, "labor_hours": 6.0, "unit": "each", "description": "Kitchen rough-in"},
    "rough_in_laundry": {"material": 150, "labor_hours": 4.0, "unit": "each", "description": "Laundry room rough-in"},

    # Drain & Sewer
    "drain_cleaning": {"material": 25, "labor_hours": 1.5, "unit": "each", "description": "Drain cleaning service"},
    "sewer_line_repair": {"material": 200, "labor_hours": 4.0, "unit": "each", "description": "Sewer line repair (per section)"},
    "clean_out_install": {"material": 75, "labor_hours": 2.0, "unit": "each", "description": "Cleanout installation"},

    # Valves & Fittings
    "shutoff_valve": {"material": 35, "labor_hours": 0.75, "unit": "each", "description": "Shutoff valve installation"},
    "pressure_regulator": {"material": 120, "labor_hours": 1.5, "unit": "each", "description": "Pressure regulating valve"},
    "backflow_preventer": {"material": 180, "labor_hours": 2.0, "unit": "each", "description": "Backflow preventer"},

    # Specialty
    "water_softener": {"material": 900, "labor_hours": 5.0, "unit": "each", "description": "Water softener system"},
    "filtration_system": {"material": 450, "labor_hours": 3.0, "unit": "each", "description": "Whole-house filtration"},
    "sump_pump": {"material": 350, "labor_hours": 3.5, "unit": "each", "description": "Sump pump installation"},
    "garbage_disposal": {"material": 180, "labor_hours": 1.5, "unit": "each", "description": "Garbage disposal installation"},

    # General
    "general_labor": {"material": 0, "labor_hours": 1.0, "unit": "hour", "description": "General plumbing labor"},
    "permit": {"material": 250, "labor_hours": 2.0, "unit": "each", "description": "Permit & inspection"},
    "misc_materials": {"material": 1, "labor_hours": 0, "unit": "dollar", "description": "Miscellaneous materials"},
}

# ─── GENERAL CONSTRUCTION UNIT COSTS ─────────────────────────────────────────

GENERAL_UNIT_COSTS: Dict[str, Dict[str, Any]] = {
    "flooring_install": {"material": 3.50, "labor_hours": 0.05, "unit": "sq ft", "description": "Flooring installation"},
    "drywall": {"material": 1.80, "labor_hours": 0.04, "unit": "sq ft", "description": "Drywall installation"},
    "painting": {"material": 0.80, "labor_hours": 0.03, "unit": "sq ft", "description": "Interior painting"},
    "tile_install": {"material": 6.00, "labor_hours": 0.12, "unit": "sq ft", "description": "Tile installation"},
    "electrical_outlet": {"material": 45, "labor_hours": 1.0, "unit": "each", "description": "Electrical outlet rough-in"},
    "door_install": {"material": 250, "labor_hours": 3.0, "unit": "each", "description": "Door installation"},
    "window_install": {"material": 350, "labor_hours": 4.0, "unit": "each", "description": "Window installation"},
    "insulation": {"material": 1.20, "labor_hours": 0.02, "unit": "sq ft", "description": "Insulation installation"},
    "concrete_pour": {"material": 8.00, "labor_hours": 0.10, "unit": "sq ft", "description": "Concrete slab pour"},
}

ALL_UNIT_COSTS = {**PLUMBING_UNIT_COSTS, **GENERAL_UNIT_COSTS}


@dataclass
class LineItem:
    description: str
    quantity: float
    unit: str
    material_cost: float
    labor_cost: float
    subtotal: float
    markup_amount: float
    total: float
    notes: str = ""
    is_estimated: bool = True


def calculate_line_item(
    description: str,
    quantity: float,
    unit: str,
    material_unit_cost: float,
    labor_hours: float,
    labor_rate: float,
    markup_pct: float,
    overhead_pct: float,
    profit_pct: float,
    notes: str = "",
    is_estimated: bool = True,
) -> LineItem:
    """Calculate full cost for a single line item."""
    material_cost = material_unit_cost * quantity
    labor_cost = labor_hours * quantity * labor_rate
    subtotal = material_cost + labor_cost
    overhead_amount = subtotal * (overhead_pct / 100)
    markup_amount = (subtotal + overhead_amount) * (markup_pct / 100)
    profit_amount = (subtotal + overhead_amount + markup_amount) * (profit_pct / 100)
    total = subtotal + overhead_amount + markup_amount + profit_amount

    return LineItem(
        description=description,
        quantity=quantity,
        unit=unit,
        material_cost=round(material_cost, 2),
        labor_cost=round(labor_cost, 2),
        subtotal=round(subtotal, 2),
        markup_amount=round(markup_amount + overhead_amount + profit_amount, 2),
        total=round(total, 2),
        notes=notes,
        is_estimated=is_estimated,
    )


def calculate_project_total(line_items: List[LineItem]) -> Dict[str, float]:
    """Sum all line items and return project totals."""
    total_material = sum(item.material_cost for item in line_items)
    total_labor = sum(item.labor_cost for item in line_items)
    total_markup = sum(item.markup_amount for item in line_items)
    grand_total = sum(item.total for item in line_items)

    return {
        "total_material": round(total_material, 2),
        "total_labor": round(total_labor, 2),
        "total_markup": round(total_markup, 2),
        "grand_total": round(grand_total, 2),
        "suggested_bid": round(grand_total * 1.05, 2),  # 5% contingency buffer
    }


def get_preset(preset_name: str) -> Dict[str, float]:
    """Get pricing preset by name, defaulting to residential."""
    return PRICING_PRESETS.get(preset_name.lower(), PRICING_PRESETS["residential"])


def build_line_items_from_scope(
    scope_items: List[Dict[str, Any]],
    preset_name: str = "residential",
    custom_markup: Optional[float] = None,
    custom_overhead: Optional[float] = None,
    custom_profit: Optional[float] = None,
) -> List[LineItem]:
    """Convert scope items into priced line items."""
    preset = get_preset(preset_name)
    markup = custom_markup if custom_markup is not None else preset["markup"]
    overhead = custom_overhead if custom_overhead is not None else preset["overhead"]
    profit = custom_profit if custom_profit is not None else preset["profit"]
    labor_rate = preset["labor_rate_per_hour"]

    line_items = []
    for item in scope_items:
        description = item.get("description", "Unlabeled Item")
        quantity = float(item.get("quantity", 1))
        unit = item.get("unit", "each")
        material_cost = float(item.get("material_cost", 0))
        labor_hours = float(item.get("labor_hours", 1))
        notes = item.get("notes", "")
        is_estimated = item.get("is_estimated", True)

        li = calculate_line_item(
            description=description,
            quantity=quantity,
            unit=unit,
            material_unit_cost=material_cost,
            labor_hours=labor_hours,
            labor_rate=labor_rate,
            markup_pct=markup,
            overhead_pct=overhead,
            profit_pct=profit,
            notes=notes,
            is_estimated=is_estimated,
        )
        line_items.append(li)

    return line_items


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def format_line_items_table(line_items: List[LineItem]) -> str:
    """Format line items as a Telegram-friendly text table."""
    lines = ["📋 *Line Item Breakdown*\n"]
    lines.append("```")
    lines.append(f"{'#':<3} {'Description':<30} {'Qty':<6} {'Unit':<10} {'Total':>10}")
    lines.append("-" * 62)

    for i, item in enumerate(line_items, 1):
        desc = item.description[:29]
        est_marker = "~" if item.is_estimated else " "
        lines.append(
            f"{i:<3} {est_marker}{desc:<29} {item.quantity:<6.1f} {item.unit:<10} {format_currency(item.total):>10}"
        )

    totals = calculate_project_total(line_items)
    lines.append("-" * 62)
    lines.append(f"{'Material Cost:':<50} {format_currency(totals['total_material']):>10}")
    lines.append(f"{'Labor Cost:':<50} {format_currency(totals['total_labor']):>10}")
    lines.append(f"{'Markup/Overhead/Profit:':<50} {format_currency(totals['total_markup']):>10}")
    lines.append(f"{'TOTAL PROJECT COST:':<50} {format_currency(totals['grand_total']):>10}")
    lines.append(f"{'SUGGESTED BID PRICE:':<50} {format_currency(totals['suggested_bid']):>10}")
    lines.append("```")
    lines.append("\n_~ = Estimated value based on extracted data_")

    return "\n".join(lines)
