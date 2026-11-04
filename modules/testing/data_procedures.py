"""Draft test procedures (D-B-079): one Dynamite page per subject in the TESTING space.

Each page is a draft the test team completes like a wiki; the table of tests on the page is generated from the
Testing database and links every test to its record (#/testing/test/<ID>), and every test record links back to
its procedure page. Procedure tuple:
  (code, subject, purpose, means, conditions, steps) -- the records are COMMON_RECORDS
"""

COMMON_RECORDS = ["Signed test plan (article, configuration, instrumentation, criteria) before the first test.",
                  "Article conformity record (serial number, software and hardware revision).",
                  "Time-stamped and archived raw data; test report with deviations and decision.",
                  "Key of the verified Goldmine requirement and report reference in \"Verification Ref.\"."]

PROCEDURES = [
    ("PRC-FUN", "func", "Verify the functions of the product, from the functional tree and the CdCF.",
     ["Prototype in the configuration to test", "Measurement means of the CdCF", "Storyline of the product"],
     ["Configuration recorded (hardware, firmware)", "Ambient conditions recorded"],
     ["Prepare the prototype and the means.", "Run the use case or the function.", "Measure each specification.",
      "Compare with the level and the flexibility of the CdCF.", "Report."]),
    ("PRC-ELE", "elec", "Verify the electrical safety of the product against its safety standard.",
     ["Megohmmeter", "Dielectric tester (hipot)", "Leakage current tester", "Ground bond tester", "Test probes"],
     ["Product at rated voltage", "Accredited lab for the compliance tests; school lab for the pre-tests"],
     ["Inspect: marking, cord, enclosure.", "Access to live parts.", "Heating.", "Leakage current and electric strength.",
      "Abnormal operation, one fault at a time.", "Report with photos."]),
    ("PRC-EMC", "emc", "Verify the emissions and the immunity of the product.",
     ["EMC laboratory (chamber, LISN, generators)", "ESD gun"], ["Operating modes chosen and written down beforehand"],
     ["Pre-scan of the emissions.", "Conducted and radiated emissions.", "ESD, fast transients, surge, dips.",
      "Note the behaviour against the performance criterion.", "Report."]),
    ("PRC-ENV", "env", "Verify that the product withstands its environment (temperature, humidity, transport).",
     ["Climatic chamber", "Vibration shaker"], ["Profiles taken from the CdCF"],
     ["Initial function check.", "Exposure.", "Recovery.", "Final function and insulation check.", "Report."]),
    ("PRC-MEC", "mech", "Verify drop, impact and stability.", ["Drop tester", "Spring hammer", "Tilt table"],
     ["Heights and energies from the CdCF and the standard"],
     ["Initial check.", "Drops, impacts, tilt.", "Inspect after each one.", "Final function check.", "Report."]),
    ("PRC-LIF", "life", "Verify the life of the product and of its mechanisms.", ["Endurance cycling rig", "Counter"],
     ["Number of cycles from the CdCF; acceleration justified"],
     ["Set the rig.", "Run the cycles with periodic checks.", "Record every failure.", "Report."]),
    ("PRC-VER", "ver", "Verification without physical test: inspection, analysis, demonstration. Each requirement "
     "verified this way points to one of these records.", ["Design reviews", "Calculation notes", "Compliance matrix"],
     ["Method (I, A, D) consistent with the requirement record", "Referenced report or minutes"],
     ["Choose the method.", "Execute (review, calculation, demonstration).", "Record the evidence.",
      "Fill in the verification reference of the requirement."]),
]

# 0.60.01: the subjects without a procedure of their own are covered by a neighbouring one (subject -> subject)
COVERS = {"therm": "elec", "ingress": "env", "mat": "ver", "sw": "func", "usab": "func", "prod": "ver"}
