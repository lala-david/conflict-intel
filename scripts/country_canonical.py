"""Single source of truth for collapsing historical / variant country names onto
one modern canonical name.

UCDP (and older backfills) label events with Gleditsch & Ward historical country
names — "Russia (Soviet Union)", "DR Congo (Zaire)", "Myanmar (Burma)" — while
GTD/ACLED/news use the modern name. Left un-normalized the two forms:

  * split into separate country_stats rows (double-counting, wrong threat),
  * show up as an odd "Russia (Soviet Union)" entry in country lists, and
  * fail to color the map — the choropleth matches Natural Earth feature names
    ("Russia", "Myanmar", …), which never equal the parenthetical form.

Every variant of a country is folded onto the modern name Natural Earth uses, so
the same key drives events, country_stats, routing and the map. `DR Congo` is the
one modern name that still differs from the NE label ("Dem. Rep. Congo"); the map
component bridges that via a display→feature alias.
"""

# alias (as seen in the data) → modern canonical name
CANONICAL_COUNTRY: dict[str, str] = {
    # Russia
    "Russia (Soviet Union)": "Russia",
    "Soviet Union": "Russia",
    # Myanmar
    "Myanmar (Burma)": "Myanmar",
    # Yemen
    "Yemen (North Yemen)": "Yemen",
    "North Yemen": "Yemen",
    "South Yemen": "Yemen",
    # DR Congo
    "DR Congo (Zaire)": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Zaire": "DR Congo",
    "DRC": "DR Congo",
    # Cambodia
    "Cambodia (Kampuchea)": "Cambodia",
    # eSwatini
    "Kingdom of eSwatini (Swaziland)": "eSwatini",
    "Swaziland": "eSwatini",
    # Madagascar
    "Madagascar (Malagasy)": "Madagascar",
    # Serbia
    "Serbia (Yugoslavia)": "Serbia",
    "Yugoslavia": "Serbia",
    "Serbia-Montenegro": "Serbia",
    # Zimbabwe
    "Zimbabwe (Rhodesia)": "Zimbabwe",
    "Rhodesia": "Zimbabwe",
    # Germany (historical FRG/GDR events fold into the modern state)
    "West Germany (FRG)": "Germany",
    "East Germany (GDR)": "Germany",
}


def canonical_country(name: str | None) -> str | None:
    """Fold a historical/variant country name onto its modern canonical form.

    Idempotent: canonical names map to themselves. Unknown names pass through
    unchanged (trimmed), so this is safe to run over the whole events table.
    """
    if not name:
        return name
    return CANONICAL_COUNTRY.get(name.strip(), name.strip())
