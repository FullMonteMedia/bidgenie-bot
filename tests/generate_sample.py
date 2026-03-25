"""Generate a sample PDF and Excel proposal for demonstration purposes."""
import sys
sys.path.insert(0, '/home/ubuntu/bidgenie')

from src.generators.pdf_generator import generate_proposal_pdf, generate_csv_export

session_data = {
    'company_name': 'Ace Plumbing',
    'company_address': '1234 Main Street, Suite 100, Your City, CA 90210',
    'company_phone': '(555) 123-4567',
    'company_email': 'info@aceplumbing.com',
    'company_license': 'LIC# C-36 123456',
    'client_name': 'Mr. & Mrs. Johnson',
    'project_name': 'Johnson Residence Master Bath Remodel',
    'project_type': 'residential',
    'trade_type': 'Plumbing',
    'timeline_notes': '2 weeks',
    'project_summary': (
        'Complete master bathroom plumbing renovation including demo of existing fixtures, '
        'installation of new double vanity sinks, walk-in shower system, comfort-height toilet, '
        'and replacement of 40-gallon water heater with a new Navien tankless unit.'
    ),
    'total_cost': 8516.00,
    'suggested_bid': 8941.80,
}

line_items = [
    {
        'description': 'Demo & Remove Existing Fixtures',
        'quantity': 1, 'unit': 'lot',
        'material_cost': 0, 'labor_cost': 340, 'markup_amount': 170, 'total': 510,
        'is_estimated': False, 'notes': 'Toilet, vanity sink, shower insert',
    },
    {
        'description': 'Bathroom Sink & Faucet (Kohler/Moen)',
        'quantity': 2, 'unit': 'each',
        'material_cost': 480, 'labor_cost': 340, 'markup_amount': 164, 'total': 984,
        'is_estimated': False, 'notes': 'Double vanity',
    },
    {
        'description': 'Rough-In Plumbing (Double Vanity)',
        'quantity': 1, 'unit': 'each',
        'material_cost': 350, 'labor_cost': 680, 'markup_amount': 205, 'total': 1235,
        'is_estimated': True, 'notes': 'Supply and drain lines',
    },
    {
        'description': 'Walk-In Shower System Installation',
        'quantity': 1, 'unit': 'each',
        'material_cost': 600, 'labor_cost': 510, 'markup_amount': 222, 'total': 1332,
        'is_estimated': False, 'notes': 'Rain head + handheld wand',
    },
    {
        'description': 'Premium Toilet (Toto Elongated)',
        'quantity': 1, 'unit': 'each',
        'material_cost': 450, 'labor_cost': 255, 'markup_amount': 141, 'total': 846,
        'is_estimated': False, 'notes': 'Comfort height',
    },
    {
        'description': 'Navien Tankless Water Heater',
        'quantity': 1, 'unit': 'each',
        'material_cost': 1200, 'labor_cost': 510, 'markup_amount': 340, 'total': 2050,
        'is_estimated': False, 'notes': 'Installed in garage',
    },
    {
        'description': '3/4" Copper Supply Lines',
        'quantity': 45, 'unit': 'linear ft',
        'material_cost': 270, 'labor_cost': 459, 'markup_amount': 146, 'total': 875,
        'is_estimated': True, 'notes': 'New runs to master bath',
    },
    {
        'description': 'Permit & Inspection',
        'quantity': 1, 'unit': 'each',
        'material_cost': 250, 'labor_cost': 170, 'markup_amount': 84, 'total': 504,
        'is_estimated': True, 'notes': 'Required for all plumbing work',
    },
    {
        'description': 'Miscellaneous Materials & Fittings',
        'quantity': 1, 'unit': 'lot',
        'material_cost': 150, 'labor_cost': 0, 'markup_amount': 30, 'total': 180,
        'is_estimated': True, 'notes': 'Fittings, sealants, hardware',
    },
]

proposal_text = (
    "Dear Mr. & Mrs. Johnson,\n\n"
    "Thank you for the opportunity to submit this proposal for your Master Bathroom Remodel. "
    "Ace Plumbing is pleased to provide the following bid for all plumbing work described herein.\n\n"
    "Our team of licensed, experienced plumbers will complete all work in strict accordance with "
    "local building codes, manufacturer specifications, and industry best practices. We take pride "
    "in delivering quality craftsmanship and professional service on every project.\n\n"
    "SCOPE OF WORK:\n"
    "We will begin by carefully demolishing and removing all existing plumbing fixtures, including "
    "the toilet, vanity sink, and fiberglass shower insert, ensuring proper disposal and minimal "
    "disruption to surrounding finishes. All rough-in plumbing will be updated to accommodate the "
    "new double vanity configuration, with new supply and drain lines run to code.\n\n"
    "The new double vanity will feature two Kohler undermount sinks paired with Moen widespread "
    "faucets, providing both elegance and durability. The walk-in shower will be equipped with a "
    "rain shower head and handheld wand system for a spa-like experience. A new Toto elongated "
    "comfort-height toilet will be installed to complete the bathroom fixture package.\n\n"
    "The existing 40-gallon water heater will be replaced with a new Navien tankless water heater "
    "installed in the garage, providing on-demand hot water and significant energy savings. All new "
    "3/4\" copper supply lines will be run to the master bath to ensure optimal water pressure and "
    "longevity.\n\n"
    "INCLUSIONS:\n"
    "All labor, materials, and equipment necessary to complete the described scope of work. Permit "
    "application and scheduling of all required inspections. Final cleanup of all work areas upon "
    "project completion.\n\n"
    "EXCLUSIONS:\n"
    "Tile work, drywall patching, or painting after rough-in. Any work not specifically listed in "
    "the scope above. Unforeseen conditions discovered during demolition will be addressed via "
    "written change order prior to proceeding.\n\n"
    "We look forward to transforming your master bathroom into the space you envision. Please do "
    "not hesitate to contact us with any questions.\n\n"
    "Sincerely,\n"
    "Ace Plumbing\n"
    "Licensed & Insured | LIC# C-36 123456"
)

pdf_path = '/home/ubuntu/bidgenie/tests/Sample_BidProposal_AcePlumbing.pdf'
generate_proposal_pdf(session_data, line_items, proposal_text, pdf_path)
print(f'PDF generated: {pdf_path}')

excel_path = '/home/ubuntu/bidgenie/tests/Sample_BidProposal_AcePlumbing.xlsx'
generate_csv_export(line_items, session_data, excel_path)
print(f'Excel generated: {excel_path}')
