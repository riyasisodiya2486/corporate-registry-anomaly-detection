from normalize import (
    normalize_address,
    normalize_company_name,
    extract_pincode,
    parse_capital
)


tests_address = [
    "Plot 14, MIDC Rd, Pune - 411019",
    "Plot-14 M.I.D.C. Road, Pune 411019",
    "PLOT NO. 14, MIDC ROAD, PUNE-411019",
    None,
    "",
]


print("=== Address normalization ===")
for a in tests_address:
    print(repr(a), "->", repr(normalize_address(a)))


tests_name = [
    "Sharma Traders Private Limited",
    "SHARMA TRADERS PVT LTD",
    "Sharma Traders Ltd.",
    "Verma & Sons LLP",
]


print("\n=== Name normalization ===")
for n in tests_name:
    print(repr(n), "->", repr(normalize_company_name(n)))


print("\n=== Pincode extraction ===")
for a in tests_address:
    print(repr(a), "->", extract_pincode(a))


print("\n=== Capital parsing ===")
for c in ["1,00,000", "100000.00", "Rs. 5,00,000", None, "abc"]:
    print(repr(c), "->", parse_capital(c))