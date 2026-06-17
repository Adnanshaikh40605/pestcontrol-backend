"""Mumbai / default region pricing — unchanged from legacy CRM Create Booking."""

COMMERCIAL_AREA_KEY = 'Commercial'

MUMBAI_PRICING: dict[str, dict[str, dict[str, int]]] = {
    'Cockroach / Ants': {
        'AMC 3 Services': {
            '1 RK': 1800,
            '1 BHK': 2200,
            '2 BHK': 2500,
            '3 BHK': 3000,
            '4 BHK': 3500,
            COMMERCIAL_AREA_KEY: 0,
        },
        'One Time Service': {
            '1 RK': 1000,
            '1 BHK': 1200,
            '2 BHK': 1500,
            '3 BHK': 1800,
            '4 BHK': 2000,
            COMMERCIAL_AREA_KEY: 0,
        },
    },
    'Bed Bugs': {
        'One Time Service': {
            '1 RK': 2000,
            '1 BHK': 2500,
            '2 BHK': 3000,
            '3 BHK': 3500,
            '4 BHK': 4000,
            COMMERCIAL_AREA_KEY: 0,
        },
    },
    'Termite': {
        'One Time Service': {
            '1 RK': 2000,
            '1 BHK': 2500,
            '2 BHK': 3000,
            '3 BHK': 3500,
            '4 BHK': 4000,
            COMMERCIAL_AREA_KEY: 0,
        },
    },
    'Rodent': {
        'One Time Service': {
            'Windows': 1000,
            'Society Area': 0,
            COMMERCIAL_AREA_KEY: 0,
        },
    },
    'Mosquito': {
        'One Time Service': {
            '1 RK': 800,
            '1 BHK': 1000,
            '2 BHK': 1500,
            '3 BHK': 1800,
            '4 BHK': 2000,
            COMMERCIAL_AREA_KEY: 0,
        },
    },
    'Hotel / Commercial': {
        'One Time Service': {
            'Commercial Space': 0,
        },
    },
}

MUMBAI_PROPERTY_LOCATIONS = ['1 RK', '1 BHK', '2 BHK', '3 BHK', '4 BHK']

MUMBAI_SERVICE_TYPES: dict[str, list[str]] = {
    'Cockroach / Ants': ['One Time Service', 'AMC 3 Services'],
    'Bed Bugs': ['One Time Service'],
    'Termite': ['One Time Service'],
    'Rodent': ['One Time Service'],
    'Mosquito': ['One Time Service'],
    'Hotel / Commercial': ['One Time Service'],
}
