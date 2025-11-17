{
    "name": "HR Employee Ledger (A/B simple)",
    "version": "18.0.1.1",
    "summary": "Anticipos de sueldo A/B ligados a empleados, con recibo imprimible y resumen por empleado.",
    "category": "Human Resources",
    "depends": ["base", "web", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "report/report.xml",
        "report/report_receipt.xml",
        "views/employee_ledger_views.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False
}