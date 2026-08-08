#!/usr/bin/env python3
"""Download the chosen Wikimedia Commons images and write a credits manifest.

Every image here is public domain, CC0, CC BY or CC BY-SA. The CC licences
require attribution, so the manifest carries author + licence + source URL and
build.py renders them under each image. Run:  python tools/fetch_images.py
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "VeiledAntiquity-ImageFetch/1.0 (https://veiledantiquity.com; blog illustration)"
OUT = Path(__file__).parent.parent / "static" / "img"
MANIFEST = Path(__file__).parent.parent / "content" / "images.json"

# slug -> (Commons file, alt text, caption)
PICKS = {
    "mithraism-seven-grades": (
        "File:36.11-1 Mosaic 1st degree.tif",
        "A black-and-white Roman mosaic panel showing a raven, a small drinking cup and a herald's staff, set in a plain border.",
        "The first rung: Corax, the Raven. A bird, a cup, and Mercury's staff, laid into the floor at Ostia."),
    "ancient-binding-spells-law": (
        "File:Pella leaded tablet (katadesmos) 4th Century.JPG",
        "A thin rectangular sheet of grey lead covered in small scratched Greek letters.",
        "A lead binding tablet from Pella, fourth century BCE. Not a judicial curse itself, but the same cheap technology every courtroom curse used."),
    "evil-eye-ancient-world": (
        "File:Tintinnabulum Pompeii MAN Napoli Inv27840.jpg",
        "A bronze wind chime from Pompeii in the form of a winged phallus, with small bells suspended beneath it on chains.",
        "A tintinnabulum from Pompeii. Hung in a doorway or garden, it caught the light, made noise, and was meant to be funny."),
    "ancient-mystery-cults-guide": (
        "File:Great Eleusinian Relief.jpg",
        "Marble relief showing Demeter handing grain to the boy Triptolemos, with Persephone standing behind him holding a torch.",
        "The Great Eleusinian Relief: Demeter, Triptolemos and Persephone. Around 440&ndash;430 BCE."),
    "eleusinian-mysteries-telesterion": (
        "File:Archaeological Site of Eleusis - Telesterion 03.jpg",
        "The excavated foundations of the Telesterion at Eleusis, a large square hall cut into a rocky hillside.",
        "What remains of the Telesterion &mdash; the hall that held several thousand initiates at once."),
    "eleusinian-kykeon-psychedelic": (
        "File:Votive relief showing Demeter, Persephone and Triptolemos, Eleusis, 4th c BC.jpg",
        "A votive marble relief from Eleusis depicting Demeter, Persephone and Triptolemos with sheaves of grain.",
        "Grain, and the goddesses who controlled it. Votive relief from Eleusis, fourth century BCE."),
    "orphic-gold-tablets": (
        "File:Orphic Gold Tablet (Petelia - British Museum, London).jpg",
        "A small rectangular sheet of gold leaf covered in tiny incised Greek letters, displayed in a museum case.",
        "The Petelia tablet. Instructions for the dead, small enough to fold into a palm."),
    "mithras-tauroctony-decoded": (
        "File:Mithras tauroctony Louvre Ma3441.jpg",
        "A carved marble relief of Mithras in a Phrygian cap kneeling on a bull and stabbing its neck, with a dog, snake and scorpion.",
        "The tauroctony. The same scene appears in almost every mithraeum ever excavated."),
    "villa-of-the-mysteries-frescoes": (
        "File:Roman fresco Villa dei Misteri Pompeii 005.jpg",
        "A wide section of Roman wall painting on a deep red ground, showing near-life-size robed figures standing in a row.",
        "Part of the frieze in Room 5. Twenty-nine figures, and no agreement about what they are doing."),
    "greek-magical-papyri": (
        "File:Graeco-Egyptian Magical Papyrus I; Louvre; Roman Epoch; 30-395 AD;Demotic, Greek,Coptic; Various Recipes; Magical Formulars are written Red.jpg",
        "A fragment of ancient papyrus densely written in Greek and Demotic script, with some lines picked out in red ink.",
        "A working spellbook from Roman Egypt. The instructions are in black; the formulae in red."),
    "ancient-curse-tablets": (
        "File:A metal curse tablet (defixio) with a complaint about the theft of a Vilbia.jpg",
        "A small irregular sheet of grey lead covered in scratched Latin lettering.",
        "A lead curse tablet from Bath, complaining about a theft. Scratched, folded, and thrown into the spring."),
    "sibylline-books-rome": (
        "File:Cumae Cave of the Sibyl AvL.JPG",
        "A long trapezoidal rock-cut corridor at Cumae, lit by openings along one side, receding into darkness.",
        "The corridor at Cumae, long identified with the Sibyl's cave."),
    "damnatio-memoriae": (
        "File:Portrait of family of Septimius Severus - Altes Museum - Berlin - Germany 2017.jpg",
        "A circular painted panel showing the Roman imperial family, with the face of one of the two sons deliberately scraped away.",
        "The Severan Tondo. Geta's face was removed by hand, on his brother's orders."),
    "library-of-alexandria-what-was-lost": (
        "File:The Serapeum of Alexandria (I).jpg",
        "Ruined stone foundations and a tall standing column at the Serapeum site in Alexandria.",
        "The Serapeum of Alexandria. What is left of the daughter library."),
    "oracle-of-the-dead-ephyra": (
        "File:Nekromanteion of Acheron.jpg",
        "Thick polygonal stone walls of a ruined Hellenistic building standing on a low hill.",
        "The building at Mesopotamos. Thick walls, a big cellar, and a granary."),
    "piacenza-liver-etruscan": (
        "File:Piacenza liver.jpg",
        "A bronze model of a sheep's liver, its flat surface divided into many small compartments each carrying an inscription.",
        "The Piacenza Liver. Forty compartments, forty gods, and a map of the sky."),
    "samothrace-great-gods": (
        "File:Nike of Samothrake Louvre Ma2369.jpg",
        "A headless, armless marble statue of a winged woman in wind-blown drapery, standing on the prow of a ship.",
        "The Nike of Samothrace, unearthed in the Sanctuary of the Great Gods in 1863."),
    "bacchanalia-186-bce": (
        "File:Senatus consultum de bacchanalibus.jpg",
        "A rectangular bronze tablet densely inscribed with Latin text, its surface worn and pitted with age.",
        "The Senatus consultum de Bacchanalibus. Found at Tiriolo in 1640, still readable."),
    "cult-of-isis-rome": (
        "File:Marble statue of Isis, the goddess holds a situla and sistrum, ritual implements used in her worship, from 117 until 138 AD, found at Hadrian's Villa (Pantanello), Palazzo Nuovo, Capitoline Museums (12945630725).jpg",
        "A marble statue of the goddess Isis draped in a fringed mantle, holding a sistrum, with a solar disc and serpent on her head.",
        "Isis, sculpted in Rome under Hadrian. She holds her sistrum; Egypt had left the statue in every way but the stone."),
}


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for slug, (title, alt, caption) in PICKS.items():
        d = api({"action": "query", "titles": title, "prop": "imageinfo",
                 "iiprop": "url|size|extmetadata", "iiurlwidth": "1500"})
        pages = d.get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        if "imageinfo" not in page:
            print(f"  MISSING  {slug}: {title}")
            continue

        ii = page["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        url = ii.get("thumburl") or ii["url"]

        dest = OUT / f"{slug}.jpg"
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"  have {slug:38} {dest.stat().st_size//1024:>5} KB  (skipped)")
        else:
            # Wikimedia rate-limits bulk downloads; back off and retry politely.
            for attempt in range(5):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        dest.write_bytes(r.read())
                    break
                except urllib.error.HTTPError as e:
                    if e.code != 429 or attempt == 4:
                        raise
                    wait = 15 * (attempt + 1)
                    print(f"  429 on {slug}; waiting {wait}s")
                    time.sleep(wait)
            time.sleep(2)

        manifest[slug] = {
            "file": f"/static/img/{slug}.jpg",
            "alt": alt,
            "caption": caption,
            "credit": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "licence": strip_html(meta.get("LicenseShortName", {}).get("value", "")) or "see source",
            "source": ii.get("descriptionurl", ""),
            "width": ii.get("thumbwidth") or ii.get("width"),
            "height": ii.get("thumbheight") or ii.get("height"),
        }
        print(f"  ok   {slug:38} [{manifest[slug]['licence']}]")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum((OUT / f"{s}.jpg").stat().st_size for s in manifest) // 1024
    print(f"\n  {len(manifest)} images, {total} KB total -> static/img/")


if __name__ == "__main__":
    main()
