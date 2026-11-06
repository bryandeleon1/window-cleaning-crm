"""Static demo copy for the dummy/portfolio marketing site.

Swap without a migration. Not seed_demo data.
"""

BRAND_NAME = "Lakeside Pane Co."
OWNER_NAME = "Jordan Hale"
PHONE_DISPLAY = "(555) 010-2040"
PHONE_TEL = "+15550102040"
TIME_ZONE_LABEL = "Central Time"

SERVICE_AREA_CITIES = [
    "Cedar Falls",
    "Waterloo",
]

# Nearby ZIPs used for the public page and a basic inbound sanity check.
SERVICE_AREA_ZIPS = [
    "50613",  # Cedar Falls
    "50614",  # Cedar Falls PO boxes / nearby
    "50701",  # Waterloo
    "50702",  # Waterloo
    "50703",  # Waterloo
    "50707",  # Evansdale
    "50647",  # Janesville
    "50622",  # Denver
    "50667",  # Shell Rock
    "50626",  # Dunkerton
    "50648",  # Jesup
]

CORE_SERVICES = [
    {"slug": "exterior", "title": "Exterior window cleaning", "blurb": "Glass, frames, and sills from the outside — weather permitting."},
    {"slug": "interior", "title": "Interior window cleaning", "blurb": "Inside glass when access and furniture allow a careful visit."},
    {"slug": "both", "title": "Interior + exterior", "blurb": "Full-house glass on both sides in one coordinated visit."},
]

ADDON_SERVICES = [
    {"slug": "screens", "title": "Screens", "blurb": "Remove, wash, and reinstall screens."},
    {"slug": "tracks-sills", "title": "Tracks & sills", "blurb": "Brush and wipe tracks and interior sills."},
    {"slug": "hard-water", "title": "Hard-water treatment", "blurb": "Mineral-spot restoration — quoted separately from routine cleaning."},
    {"slug": "skylights", "title": "Skylights", "blurb": "Reachable residential skylights as an add-on."},
    {"slug": "storm-windows", "title": "Storm windows", "blurb": "Storm panels cleaned and handled with care."},
    {"slug": "post-construction", "title": "Post-construction", "blurb": "Construction dust and sticker residue after remodel or new build."},
]

NOT_OFFERED = [
    "Solar panel cleaning",
    "High-rise / rope-access work",
]

FAQ_ITEMS = [
    {
        "q": "Do you clean interiors?",
        "a": "Yes — interior, exterior, or both. Interior visits need access and a clear path to the glass.",
    },
    {
        "q": "How do quotes work?",
        "a": "Send a photo quote request or call. We confirm scope (window/pane count, stories, add-ons) before any date is locked.",
    },
    {
        "q": "What area do you cover?",
        "a": "Cedar Falls, Waterloo, and nearby ZIPs in Central Time. Outside that list we may decline or quote travel.",
    },
    {
        "q": "Do you book instantly online?",
        "a": "No. Weather and drive time matter for a solo operator, so every job is request + confirm — not an open calendar hold.",
    },
    {
        "q": "Are you insured?",
        "a": "This is a fictional portfolio demo brand. A live owner site should state insurance/bonded status accurately for their business.",
    },
]
