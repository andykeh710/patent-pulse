"""Industry → CPC prefix mapping constants.

Used by the onboarding wizard to suggest relevant companies and
themes based on the user's selected industry.
"""

INDUSTRY_CPC_MAP: dict[str, list[str]] = {
    "AI/ML": ["G06N", "G06V", "G06F"],
    "Biotech/Pharma": ["A61K", "C12N", "A61P"],
    "Semiconductors": ["H01L", "H03K"],
    "Robotics": ["B25J", "G05B"],
    "Energy/Climate": ["H02J", "H02S", "F03D", "H01M"],
    "Fintech/Web3": ["G06Q", "H04L9"],
    "Consumer/Retail": ["G06Q30"],
    "Aerospace/Defense": ["B64C", "B64G", "F41"],
    "Materials/Manufacturing": ["C08", "B22", "B23", "B29"],
    "Medical Devices": ["A61B", "A61M", "G16H"],
    "Automotive/Mobility": ["B60", "B62D"],
    "Telecom": ["H04W", "H04L", "H04B"],
}

ONBOARDING_PERSONAS = ("Founder", "VC", "Engineer", "Researcher", "Operator", "Other")
ONBOARDING_INDUSTRIES = list(INDUSTRY_CPC_MAP.keys())
