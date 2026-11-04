"""Testing catalogue (D-B-079): the tests of a consumer mechatronic product, macroscopic.

0.60.01: a generic base for a consumer mechatronic product (a household appliance or a small powered tool): electrical
safety (CSA C22.2 No. 60335-1 / UL 60335-1, or IEC 62368-1 for audio-video and ICT products), household EMC (ICES-003,
FCC Part 15, CISPR 32 / 35, IEC 61000-4-x), environmental (IEC 60068-2-x), ingress protection (IEC 60529), drop,
RoHS and life tests. Each team keeps what applies to its product and adds its custom tests. Standards are cited by title and section heading only -- never their text. Values not fixed yet are written [TBD],
like the requirements.

Test tuple: (test_id, subject, category, standard, section, level, method, title, objective, acceptance)
  category: standard (named standard), industry (usual practice of the consumer-product industry),
            custom (team test to define -- a function or a use case of the product).
  method:   the IADT letter the test gives as evidence (T test, A analysis, I inspection, D demonstration).
"""

SUBJECTS = {
    "func": "Functional Performance",
    "elec": "Electrical Safety",
    "emc": "EMC (Emissions & Immunity)",
    "therm": "Thermal",
    "env": "Environmental",
    "ingress": "Ingress Protection (IP)",
    "mech": "Mechanical, Drop & Structural",
    "life": "Durability & Life",
    "mat": "Materials & Compliance (RoHS)",
    "sw": "Electronics & Software",
    "usab": "Usability & Ergonomics",
    "prod": "Production & End-of-Line",
    "ver": "Verification without Test (Inspection, Analysis, Demonstration)",
}
CATEGORIES = {"standard": "Standard", "industry": "Industry Practice", "custom": "Custom Test (TBD)"}
STATUSES = ("Draft", "In Review", "Approved", "Obsolete")
LEVELS = ("Component", "Subsystem", "Product", "Product in Use")

TBD = "Criterion [TBD] set by the linked requirement."

S335 = "CSA C22.2 No. 60335-1 / UL 60335-1"
EMC_E = "ICES-003 ; FCC Part 15 Subpart B ; CISPR 32"
IND = "Industry practice"
TEAM = "Team custom test"

TESTS = [
    # ---------------------------------------------------------------- func
    ("TST-FUN-01", "func", "custom", TEAM, "Primary function", "Product", "T",
     "Primary function on the reference use case", "Run the reference use case of the product (storyline) end to end and "
     "measure the specification of its primary function (CdCF).", TBD),
    ("TST-FUN-02", "func", "custom", TEAM, "Response time", "Product", "T",
     "Start-up and response times", "Measure the time from power-on to ready, and the response time of every user command.",
     "Times ≤ the values of the CdCF [TBD]."),
    ("TST-FUN-03", "func", "custom", TEAM, "Secondary functions", "Subsystem", "T",
     "Secondary functions, one subsystem at a time", "Verify each secondary function of the functional tree on its subsystem, "
     "with the specification of the CdCF.", TBD),
    # ---------------------------------------------------------------- elec
    ("TST-ELE-01", "elec", "standard", S335, "Protection against access to live parts", "Product", "I",
     "Access to live parts", "With the test probes, check that no live part can be touched, enclosure open or closed as in use.",
     "No contact with a live part."),
    ("TST-ELE-02", "elec", "standard", S335, "Leakage current and electric strength", "Product", "T",
     "Leakage current and dielectric strength (hipot)", "Measure the leakage current, then apply the test voltage between "
     "live parts and accessible parts.", "Leakage current within the limit of the standard; no breakdown."),
    ("TST-ELE-03", "elec", "standard", S335, "Heating", "Product", "T",
     "Temperature rise in normal operation", "Operate at rated voltage until steady state; record the temperature of "
     "windings, accessible surfaces and handles.", "Every temperature rise within the limits of the standard."),
    ("TST-ELE-04", "elec", "standard", S335, "Abnormal operation", "Product", "T",
     "Abnormal operation and single fault", "Block, overload or short the parts named by the standard, one fault at a time.",
     "No fire, no dangerous part exposed, no ejection; protection devices act."),
    ("TST-ELE-05", "elec", "standard", S335, "Provision for earthing", "Product", "T",
     "Earth continuity (class I product)", "Measure the resistance between the earthing terminal and the accessible metal parts.",
     "Resistance within the limit of the standard."),
    ("TST-ELE-06", "elec", "standard", "IEC 60335-2-45", "Particular requirements", "Product", "A",
     "Part 2 of the product family", "Identify the part 2 of IEC 60335 of the product (e.g. 60335-2-45 for portable heating "
     "tools) and list its additional tests.", "Every additional test of the part 2 planned in the Test Base."),
    # ---------------------------------------------------------------- emc
    ("TST-EMC-01", "emc", "standard", EMC_E, "Conducted and radiated emissions", "Product", "T",
     "Conducted and radiated emissions", "Measure the emissions in the operating modes of the product (or CISPR 14-1 for a "
     "household appliance with a motor or a heater).", "Below the class B limits."),
    ("TST-EMC-02", "emc", "standard", "IEC 61000-4-2", "Electrostatic discharge", "Product", "T",
     "Electrostatic discharge (ESD)", "Contact and air discharges on the points the user touches.",
     "Performance criterion of the immunity standard (CISPR 35 or CISPR 14-2) met."),
    ("TST-EMC-03", "emc", "standard", "IEC 61000-4-4 ; IEC 61000-4-5", "Fast transients and surge", "Product", "T",
     "Electrical fast transients and surge on the mains", "Bursts and surges on the power cord.",
     "Performance criterion met; no damage."),
    ("TST-EMC-04", "emc", "standard", "IEC 61000-4-11", "Voltage dips and interruptions", "Product", "T",
     "Voltage dips and short interruptions", "Dips and interruptions of the mains voltage in operation.",
     "Performance criterion met; safe state on return."),
    # ---------------------------------------------------------------- therm / env
    ("TST-THR-01", "therm", "industry", IND, "Accessible surfaces", "Product", "T",
     "Temperature of surfaces touched in use", "Thermocouples and thermal camera on handles and surfaces, at the hottest use case.",
     "Surfaces held by the user ≤ the value of the CdCF [TBD]."),
    ("TST-ENV-01", "env", "standard", "IEC 60068-2-1 ; IEC 60068-2-2", "Test A — Cold ; Test B — Dry heat", "Product", "T",
     "Storage and operation at the temperature extremes", "Soak at the extremes of the CdCF, then operate.",
     "Function restored; no damage."),
    ("TST-ENV-02", "env", "standard", "IEC 60068-2-78", "Test Cab — Damp heat, steady state", "Product", "T",
     "Damp heat", "Soak in damp heat, then check function and insulation.", "Function restored; insulation within the limit."),
    ("TST-ENV-03", "env", "standard", "IEC 60068-2-6", "Test Fc — Vibration (sinusoidal)", "Product", "T",
     "Transport vibration", "Sine sweep on the three axes, packed product.", "No damage, no loose part, function restored."),
    # ---------------------------------------------------------------- ingress
    ("TST-IP-01", "ingress", "standard", "IEC 60529", "IPX4 — Splashing water", "Product", "T",
     "Splashing water (IPX4, if required)", "Oscillating tube or spray nozzle at the duration of the code.",
     "No harmful ingress; electric strength still met."),
    ("TST-IP-02", "ingress", "standard", "IEC 60529", "IP5X — Dust protected", "Product", "T",
     "Dust (IP5X, if required)", "Dust chamber at the duration of the code.", "No dust deposit that impairs function or safety."),
    # ---------------------------------------------------------------- mech
    ("TST-MEC-01", "mech", "standard", "IEC 60068-2-31", "Rough handling shocks — free fall", "Product", "T",
     "Drop", "Free fall of the product on its faces and edges from the height of the CdCF.",
     "No access to live parts, no sharp edge; function restored."),
    ("TST-MEC-02", "mech", "standard", S335, "Mechanical strength", "Product", "T",
     "Impact on the enclosure", "Impacts with the spring hammer on the weak points of the enclosure.",
     "No damage that impairs safety."),
    ("TST-MEC-03", "mech", "standard", S335, "Stability and mechanical hazards", "Product", "T",
     "Stability on its stand", "Tilt the product on its stand at the angle of the standard; check moving parts guards.",
     "The product does not tip over; no moving part accessible."),
    # ---------------------------------------------------------------- life
    ("TST-LIF-01", "life", "industry", IND, "Endurance", "Product", "T",
     "Endurance of the product", "Run use cycles until the life of the CdCF (accelerated when justified).",
     "Specifications still met at end of life [TBD]."),
    ("TST-LIF-02", "life", "industry", IND, "Mechanisms", "Subsystem", "T",
     "Endurance of buttons, triggers and hinges", "Cycling rig on every mechanism the user operates.",
     "No failure before the number of cycles of the CdCF [TBD]."),
    # ---------------------------------------------------------------- mat
    ("TST-MAT-01", "mat", "standard", "RoHS (2011/65/EU, 2015/863) ; IEC 62321", "Restricted substances", "Component", "I",
     "RoHS compliance of parts and materials", "Collect the declarations of the suppliers; XRF screening of doubtful parts.",
     "Every part declared or screened below the limits."),
    ("TST-MAT-02", "mat", "standard", "UL 94", "Flammability of plastic materials", "Component", "I",
     "Flammability rating of the plastics", "Check the rating of every plastic part near a hot or live part.",
     "Rating at least the one the safety standard requires."),
    # ---------------------------------------------------------------- sw / usab / prod / ver
    ("TST-SW-01", "sw", "custom", TEAM, "Firmware", "Subsystem", "T",
     "Firmware functions and faults", "Run every command and every fault case of the firmware on the bench.", TBD),
    ("TST-USA-01", "usab", "custom", TEAM, "Use", "Product in Use", "D",
     "Use test with users", "Five users follow the storyline of the product without help; note every hesitation.",
     "Each task done without help by at least 4 users out of 5 [TBD]."),
    ("TST-PRD-01", "prod", "industry", IND, "End of line", "Product", "T",
     "End-of-line test", "Hipot, earth continuity and a short function test on every unit.", "Every unit passes."),
    ("TST-VER-01", "ver", "industry", IND, "Inspection", "Product", "I",
     "Inspection of drawings, marking and documents", "Check drawings, marking, rating plate and instructions against the "
     "requirements.", "Every point conforms."),
    ("TST-VER-02", "ver", "industry", IND, "Analysis", "Subsystem", "A",
     "Design analysis (calculation, simulation, FMEA)", "Calculation note or simulation that shows the requirement is met.",
     "Margin ≥ the value of the requirement [TBD]."),
    ("TST-VER-03", "ver", "industry", IND, "Demonstration", "Product", "D",
     "Demonstration to the client", "Show the function in front of the client or the instructor, with a record.",
     "Function shown and accepted."),
    ("TST-VER-04", "ver", "standard", "IEC 60335-1 ; IEC 62368-1", "Scope", "Product", "A",
     "Applicable safety standard", "Decide which safety standard applies (household appliance: IEC 60335; audio-video or "
     "ICT: IEC 62368-1) and list its tests.", "Standard chosen and justified; tests planned."),
    ("TST-CUS-01", "func", "custom", TEAM, "To define", "Product", "T",
     "Custom test to define", "Placeholder for a need that no other test covers; to be defined with the test team.", TBD),
]
