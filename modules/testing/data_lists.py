"""Controlled lists of the Testing base (D-B-082): test equipment, test locations and the product functions (F-XX,
the function allocation of the functional analysis). One central list each, edited only by the managers of the
TESTING space ("Space Admin") or an administrator -- tests and requirements pick from them, never free text. Also
the default equipment / location / functions of the catalogue tests.
"""

LOCATIONS = [  # (code, label)
    ("LAB", "Laboratoire de l'école"), ("ATELIER", "Atelier de prototypage"),
    ("EXT", "Laboratoire externe accrédité (à choisir)"), ("CLIENT", "Chez le client"),
]

EQUIPMENT = [  # (code, label, category)
    ("EQ-DAQ", "Data acquisition (voltage, current, temperature)", "Measurement"),
    ("EQ-DMM", "Digital multimeter (calibrated)", "Measurement"),
    ("EQ-SCOPE", "Oscilloscope", "Measurement"),
    ("EQ-PSU", "Laboratory power supply", "Electrical"),
    ("EQ-WATT", "Power analyser (input power, standby consumption)", "Electrical"),
    ("EQ-MOHM", "Megohmmeter (insulation resistance)", "Electrical Safety"),
    ("EQ-HIPOT", "Dielectric tester (hipot)", "Electrical Safety"),
    ("EQ-LEAK", "Leakage / touch current tester", "Electrical Safety"),
    ("EQ-GND", "Ground bond tester", "Electrical Safety"),
    ("EQ-FINGER", "Test finger and test probes (IEC 61032)", "Electrical Safety"),
    ("EQ-CLIM", "Climatic chamber (temperature, humidity)", "Environmental"),
    ("EQ-TSHOCK", "Thermal shock chamber", "Environmental"),
    ("EQ-SALT", "Salt fog chamber", "Environmental"),
    ("EQ-DUST", "Dust chamber (IP5X / IP6X)", "Environmental"),
    ("EQ-WATER", "Water test equipment (drip, spray, jet, immersion — IPX1 to IPX8)", "Environmental"),
    ("EQ-VIB", "Vibration shaker and table (sine, random)", "Mechanical"),
    ("EQ-DROP", "Drop tester", "Mechanical"),
    ("EQ-IMPACT", "Impact hammer / ball impact", "Mechanical"),
    ("EQ-FORCE", "Force gauge (push, pull, torque)", "Mechanical"),
    ("EQ-CYCLE", "Endurance cycling rig (buttons, hinges, mechanisms)", "Mechanical"),
    ("EQ-IRCAM", "Thermal camera", "Thermal"),
    ("EQ-TC", "Thermocouples and logger", "Thermal"),
    ("EQ-EMC", "EMC laboratory (chamber, LISN, generators)", "EMC"),
    ("EQ-ESD", "ESD gun (IEC 61000-4-2)", "EMC"),
    ("EQ-XRF", "XRF analyser (RoHS screening)", "Materials"),
    ("EQ-EOL", "End-of-line test bench", "Production"),
]

FUNCTIONS = []  # (code, name, primary, supporting, notes) -- filled by each team from its functional analysis

# ------------------------------------------------------------------ defaults of the catalogue tests
EQUIPMENT_OF_SUBJECT = {
    "func": "EQ-DAQ", "elec": "EQ-MOHM, EQ-HIPOT, EQ-LEAK, EQ-GND", "emc": "EQ-EMC, EQ-ESD", "therm": "EQ-TC, EQ-IRCAM",
    "env": "EQ-CLIM", "ingress": "EQ-DUST, EQ-WATER", "mech": "EQ-DROP, EQ-IMPACT, EQ-VIB", "life": "EQ-CYCLE",
    "mat": "EQ-XRF", "sw": "EQ-SCOPE", "usab": "", "prod": "EQ-EOL", "ver": "",
}
EQUIPMENT_OF_TEST = {"TST-ENV-03": "EQ-VIB", "TST-MEC-01": "EQ-DROP", "TST-MEC-02": "EQ-IMPACT", "TST-MEC-03": "EQ-FORCE",
                     "TST-IP-01": "EQ-WATER", "TST-IP-02": "EQ-DUST", "TST-FUN-02": "EQ-DAQ, EQ-SCOPE",
                     "TST-ELE-01": "EQ-FINGER", "TST-ELE-03": "EQ-TC, EQ-DAQ", "TST-ELE-04": "EQ-TC, EQ-WATT",
                     "TST-EMC-02": "EQ-ESD", "TST-ENV-01": "EQ-CLIM", "TST-ENV-02": "EQ-CLIM"}
# where the test is planned by default: the school lab for what the team tests itself; empty = lab to choose
IN_HOUSE = {"func", "therm", "mech", "life", "sw", "usab", "prod", "ver"}
LOCATION_OF_TEST = {}
FUNCTIONS_OF_TEST = {}


def defaults(test_id, subject):
    """(location, equipment, functions) of a catalogue test."""
    equipment = EQUIPMENT_OF_TEST.get(test_id, EQUIPMENT_OF_SUBJECT.get(subject, ""))
    location = LOCATION_OF_TEST.get(test_id, "LAB" if subject in IN_HOUSE else "")
    return location, equipment, FUNCTIONS_OF_TEST.get(test_id, "")
