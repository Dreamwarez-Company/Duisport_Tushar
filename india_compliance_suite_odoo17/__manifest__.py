
{
    "name": "India Compliance Suite (GST ITC, TDS, DPT-3)",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "summary": "GST ITC Reversal (Rule 42/43), TDS Returns, MCA DPT-3",
    "depends": ["account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/itc_views.xml",
        "views/tds_views.xml",
        "views/dpt3_views.xml"
    ],
    "installable": True,
    "application": True
}
