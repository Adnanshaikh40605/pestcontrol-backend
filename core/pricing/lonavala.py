"""
Lonavala launch rate card 2026 — PestControl99_Lonavala_Final_Round_Figure_Rates.
Residential BHK + Villa/Bungalow sq.ft slabs. Mumbai pricing is unaffected.
"""

# General Pest Control (maps to CRM package "Cockroach / Ants")
_COMMERCIAL_AREA = 'Commercial'

_GENERAL_PEST_RESIDENTIAL_ONE_TIME = {
    '1 RK': 1000,
    '1 BHK': 1200,
    '2 BHK': 1500,
    '3 BHK': 1800,
    '4 BHK': 2200,
    '5 BHK': 2500,
    '6 BHK': 3000,
    '7 BHK': 3300,
    '8 BHK': 3600,
    '9 BHK': 3900,
    '10 BHK': 4200,
    _COMMERCIAL_AREA: 0,
}
_GENERAL_PEST_RESIDENTIAL_AMC = {
    '1 RK': 2500,
    '1 BHK': 3000,
    '2 BHK': 4000,
    '3 BHK': 5000,
    '4 BHK': 6000,
    '5 BHK': 7000,
    '6 BHK': 8000,
    '7 BHK': 9000,
    '8 BHK': 10000,
    '9 BHK': 11000,
    '10 BHK': 12000,
    _COMMERCIAL_AREA: 0,
}

# Villa / Bungalow / Farm House — General Pest
_GENERAL_PEST_VILLA_ONE_TIME = {
    'Up to 1,000 Sq.Ft.': 2000,
    '1,001-2,000 Sq.Ft.': 3500,
    '2,001-4,000 Sq.Ft.': 5500,
    '4,001-6,000 Sq.Ft.': 7500,
    '6,001-10,000 Sq.Ft.': 10000,
}
_GENERAL_PEST_VILLA_AMC = {
    'Up to 1,000 Sq.Ft.': 5000,
    '1,001-2,000 Sq.Ft.': 7000,
    '2,001-4,000 Sq.Ft.': 10000,
    '4,001-6,000 Sq.Ft.': 15000,
    '6,001-10,000 Sq.Ft.': 20000,
}

LONAVALA_PRICING: dict[str, dict[str, dict[str, int]]] = {
    'Cockroach / Ants': {
        'One Time Service': {**_GENERAL_PEST_RESIDENTIAL_ONE_TIME, **_GENERAL_PEST_VILLA_ONE_TIME},
        'AMC 3 Services': {**_GENERAL_PEST_RESIDENTIAL_AMC, **_GENERAL_PEST_VILLA_AMC},
    },
    'Bed Bugs': {
        'One Time Service': {
            '1 BHK': 3000,
            '2 BHK': 4000,
            '3 BHK': 5000,
            '4 BHK': 6000,
            '5 BHK': 7000,
            _COMMERCIAL_AREA: 0,
        },
    },
    'Termite': {
        'One Time Service': {
            '1 BHK': 3500,
            '2 BHK': 4500,
            '3 BHK': 5500,
            '4 BHK': 6500,
            '5 BHK': 7500,
            _COMMERCIAL_AREA: 0,
        },
        'One Time Treatment': {
            '1 BHK': 3500,
            '2 BHK': 4500,
            '3 BHK': 5500,
            '4 BHK': 6500,
            '5 BHK': 7500,
            _COMMERCIAL_AREA: 0,
        },
    },
    'Mosquito': {
        'One Time Service': {
            '1 RK': 1000,
            '1 BHK': 1200,
            '2 BHK': 1500,
            '3 BHK': 2000,
            '4 BHK': 2500,
            '5 BHK': 3000,
            _COMMERCIAL_AREA: 0,
            # Mosquito Fogging (villa / large area)
            'Up to 1,000 Sq.Ft.': 1000,
            '1,001-2,000 Sq.Ft.': 1500,
            '2,001-5,000 Sq.Ft.': 2500,
            '5,001-10,000 Sq.Ft.': 4000,
        },
    },
    'Rodent': {
        'One Time Service': {
            'Up to 1,000 Sq.Ft.': 1000,
            '1,001-2,000 Sq.Ft.': 1500,
            '2,001-4,000 Sq.Ft.': 2500,
            '4,001-6,000 Sq.Ft.': 4000,
            '6,001-10,000 Sq.Ft.': 6000,
            '10,001-15,000 Sq.Ft.': 9000,
            '15,001-20,000 Sq.Ft.': 12000,
        },
    },
    'Hotel / Commercial': {
        'One Time Service': {
            'Commercial Space': 0,
        },
    },
}

LONAVALA_RESIDENTIAL_LOCATIONS = [
    '1 RK', '1 BHK', '2 BHK', '3 BHK', '4 BHK', '5 BHK',
    '6 BHK', '7 BHK', '8 BHK', '9 BHK', '10 BHK',
]

LONAVALA_VILLA_LOCATIONS = [
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-4,000 Sq.Ft.',
    '4,001-6,000 Sq.Ft.',
    '6,001-10,000 Sq.Ft.',
]

LONAVALA_MOSQUITO_FOGGING_LOCATIONS = [
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-5,000 Sq.Ft.',
    '5,001-10,000 Sq.Ft.',
]

LONAVALA_RODENT_LOCATIONS = [
    'Up to 1,000 Sq.Ft.',
    '1,001-2,000 Sq.Ft.',
    '2,001-4,000 Sq.Ft.',
    '4,001-6,000 Sq.Ft.',
    '6,001-10,000 Sq.Ft.',
    '10,001-15,000 Sq.Ft.',
    '15,001-20,000 Sq.Ft.',
]

LONAVALA_SERVICE_TYPES: dict[str, list[str]] = {
    'Cockroach / Ants': ['One Time Service', 'AMC 3 Services'],
    'Bed Bugs': ['One Time Service'],
    'Termite': ['One Time Service'],
    'Rodent': ['One Time Service'],
    'Mosquito': ['One Time Service'],
    'Hotel / Commercial': ['One Time Service'],
}
