"""Backfill country_code for country names our mapper missed (GTD/Wikipedia
historical + alternate + territory names). Maps to ISO-3166-1 alpha-2 (successor
state for historical names) so flags resolve. Junk/ambiguous names are left null.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# name → ISO2 (successor state for historical entities)
EXTRA = {
    # standard countries missed by the mapper
    "Cambodia": "KH", "Pakistan": "PK", "Ukraine": "UA", "Israel": "IL", "Mali": "ML",
    "Lebanon": "LB", "Bulgaria": "BG", "Ethiopia": "ET", "Sudan": "SD", "Uruguay": "UY",
    "Suriname": "SR", "Madagascar": "MG", "Kazakhstan": "KZ", "Maldives": "MV", "Fiji": "FJ",
    "Luxembourg": "LU", "Nigeria": "NG", "Belarus": "BY", "Afghanistan": "AF", "Lithuania": "LT",
    "Slovenia": "SI", "Indonesia": "ID", "Syria": "SY", "Grenada": "GD", "Iceland": "IS",
    "Gabon": "GA", "Libya": "LY", "Iran": "IR", "Cameroon": "CM", "Vanuatu": "VU",
    "Turkmenistan": "TM", "Papua New Guinea": "PG", "Mauritius": "MU", "Haiti": "HT",
    "Equatorial Guinea": "GQ", "Niger": "NE", "Thailand": "TH", "Somalia": "SO",
    "Philippines": "PH", "South Sudan": "SS", "Chad": "TD", "Burundi": "BI", "Brunei": "BN",
    "Antigua and Barbuda": "AG", "Andorra": "AD", "Monaco": "MC", "Ghana": "GH",
    "Slovakia": "SK", "Montenegro": "ME", "Serbia": "RS", "Burkina Faso": "BF",
    "Vatican City": "VA",
    # alternate / formal names
    "Czech Republic": "CZ", "Slovak Republic": "SK", "People's Republic of China": "CN",
    "United States of America": "US", "U.S.": "US", "USA": "US", "United States.": "US",
    "The Netherlands": "NL", "Syrian Arab Republic": "SY", "East Timor": "TL",
    "Swaziland": "SZ", "Republic of the Congo": "CG", "Democratic Republic of Congo": "CD",
    "DRC": "CD", "DR Congo (Zaire)": "CD", "Myanmar (Burma)": "MM",
    "St. Kitts and Nevis": "KN", "St. Lucia": "LC", "England": "GB",
    # territories
    "West Bank and Gaza Strip": "PS", "Palestine": "PS", "West Bank": "PS",
    "Palestinian National Authority": "PS", "Kosovo": "XK", "Macau": "MO",
    "Guadeloupe": "GP", "Martinique": "MQ", "New Caledonia": "NC", "French Guiana": "GF",
    "French Polynesia": "PF", "Western Sahara": "EH", "Wallis and Futuna": "WF",
    "Falkland Islands": "FK",
    # historical → successor state
    "Yugoslavia": "RS", "Rhodesia": "ZW", "Czechoslovakia": "CZ", "Serbia-Montenegro": "RS",
    "Russia (Soviet Union)": "RU", "North Yemen": "YE", "South Yemen": "YE",
    "Yemen (North Yemen)": "YE", "South Vietnam": "VN", "New Hebrides": "VU",
    "People's Republic of the Congo": "CG", "Government of Islamic Emirate of Afghanistan": "AF",
    # sub-national → parent country
    "Jerusalem": "IL", "East Jerusalem": "PS", "Golan Heights": "IL", "Niger State": "NG",
    "Allenby Bridge": "JO", "Macedonia": "MK", "Transnistria": "MD",
}


def main():
    conn = sqlite3.connect("data/conflict.db", timeout=60)
    fixed = 0
    for name, code in EXTRA.items():
        n = conn.execute(
            "UPDATE events SET country_code=? WHERE country=? AND (country_code IS NULL OR country_code='')",
            (code, name)).rowcount
        fixed += n
    conn.commit()
    left = conn.execute(
        "SELECT country, COUNT(*) FROM events WHERE (country_code IS NULL OR country_code='') "
        "AND country!='' AND dup_of IS NULL GROUP BY country ORDER BY 2 DESC").fetchall()
    conn.close()
    print(f"country_code backfilled: {fixed:,} rows across {len(EXTRA)} names")
    print(f"still unmapped (junk/ambiguous, {len(left)}): {[c for c, _ in left]}")


if __name__ == "__main__":
    main()
