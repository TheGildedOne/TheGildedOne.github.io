#!/usr/bin/env python3
"""Search Wikimedia Commons for candidate images, report licence and size.

Search only — downloads nothing. Run:  python tools/find_images.py
"""

import json
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "VeiledAntiquity-ImageResearch/1.0 (https://veiledantiquity.com; blog illustration sourcing)"

# One or more search phrases per post. Deliberately ancient material only.
QUERIES = {
    "ancient-necromancy":                 ["Nekyia", "underworld Hades vase painting Charon lekythos"],
    "greek-magical-gems":                 ["Abraxas gem", "magic gem amulet antique intaglio"],
    "mithraism-seven-grades":             ["Felicissimus mithraeum mosaic Ostia", "mitreo di Felicissimo"],
    "ancient-binding-spells-law":         ["katadesmos lead curse tablet Greek", "defixio lead tablet museum Greek"],
    "evil-eye-ancient-world":             ["tintinnabulum bronze Pompeii", "fascinum amulet Roman bronze"],
    "ancient-mystery-cults-guide":        ["Great Eleusinian Relief", "Ninnion Tablet"],
    "eleusinian-mysteries-telesterion":   ["Ninnion Tablet", "Telesterion Eleusis"],
    "eleusinian-kykeon-psychedelic":      ["Demeter Persephone Triptolemos relief", "Eleusis museum Demeter"],
    "orphic-gold-tablets":                ["Orphic gold tablet", "Petelia tablet British Museum"],
    "mithras-tauroctony-decoded":         ["tauroctony relief Mithras", "Mithras British Museum relief"],
    "villa-of-the-mysteries-frescoes":    ["Villa dei Misteri fresco", "Villa of the Mysteries Pompeii megalography"],
    "greek-magical-papyri":               ["Greek magical papyrus", "magical gem Roman abraxas"],
    "ancient-curse-tablets":              ["curse tablet defixio", "Bath curse tablet Roman"],
    "sibylline-books-rome":               ["Cave of the Sibyl Cumae", "Cumae antro della Sibilla"],
    "damnatio-memoriae":                  ["Severan Tondo", "Arch of the Argentarii Geta"],
    "library-of-alexandria-what-was-lost": ["Serapeum Alexandria ruins", "Oxyrhynchus papyrus fragment"],
    "oracle-of-the-dead-ephyra":          ["Necromanteion Acheron", "Nekromanteion Ephyra ruins"],
    "piacenza-liver-etruscan":            ["Liver of Piacenza", "Fegato di Piacenza bronze"],
    "books-augustus-burned":              ["Augustus Via Labicana pontifex maximus", "Augustus capite velato statue"],
    "liber-linteus":                      ["Liber Linteus Zagrabiensis", "Zagreb mummy linen book Etruscan"],
    "etruscan-language-lost":             ["Pyrgi Tablets", "Cippus Perusinus", "Tabula Cortonensis"],
    "claudius-etruscan-history":          ["Table claudienne Lyon", "Lyon Tablet Claudius bronze inscription"],
    "delphi-pythia":                      ["Themis Aegeus kylix Berlin", "Temple of Apollo Delphi ruins"],
    "delphi-gases-hypothesis":            ["Delphi temple of Apollo adyton", "Castalian spring Delphi"],
    "dream-incubation-asclepius":         ["Amphiaraos relief Oropos incubation", "Asklepios votive relief healing Piraeus"],
    "etruscan-lightning-doctrine":        ["Tinia Etruscan bronze thunderbolt", "Etruscan Jupiter statuette thunderbolt"],
}

FREE = ("public domain", "cc0", "cc-by-sa", "cc by-sa", "cc-by", "cc by")


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search(term, limit=6):
    d = api({"action": "query", "list": "search", "srsearch": term,
             "srnamespace": "6", "srlimit": str(limit)})
    return [h["title"] for h in d.get("query", {}).get("search", [])]


def info(titles):
    if not titles:
        return {}
    d = api({"action": "query", "titles": "|".join(titles), "prop": "imageinfo",
             "iiprop": "url|size|extmetadata", "iiurlwidth": "1600"})
    out = {}
    for page in d.get("query", {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii:
            continue
        meta = ii.get("extmetadata", {})
        out[page["title"]] = {
            "licence": meta.get("LicenseShortName", {}).get("value", "?"),
            "artist": meta.get("Artist", {}).get("value", "")[:90],
            "w": ii.get("width"), "h": ii.get("height"),
            "thumb": ii.get("thumburl"),
            "descurl": ii.get("descriptionurl"),
        }
    return out


def main():
    for slug, terms in QUERIES.items():
        print(f"\n{'='*78}\n{slug}\n{'='*78}")
        seen = set()
        for term in terms:
            titles = [t for t in search(term) if t not in seen]
            seen.update(titles)
            for title, d in info(titles).items():
                lic = d["licence"]
                free = any(f in lic.lower() for f in FREE)
                if not free or not d.get("thumb"):
                    continue
                if title.lower().endswith((".svg", ".pdf", ".ogv", ".webm")):
                    continue
                print(f"  [{lic:22}] {d['w']}x{d['h']}  {title[5:]}")


if __name__ == "__main__":
    main()
