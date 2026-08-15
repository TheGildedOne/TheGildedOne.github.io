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
    "ancient-necromancy": (
        "File:Nekyia Staatliche Antikensammlungen 1494.jpg",
        "A Greek black-figure vase painting of the underworld, with a bearded figure bent forward pushing a large white boulder.",
        "The underworld on an Attic vase. Every ancient account of consulting the dead is working from a picture like this one."),
    "greek-magical-gems": (
        "File:Abraxas I1679.jpg",
        "A carved oval gemstone showing a figure with a rooster's head, holding a shield and whip, with serpents in place of legs.",
        "A magical gem cut with Abraxas. Not one of the medical types &mdash; but the same craft, the same workshops, and the same unpronounceable words."),
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
    "books-augustus-burned": (
        "File:Augustus as Pontifex Maximus or Via Labicana Augustus (8591667948).jpg",
        "A marble statue of a man in a heavy toga with a fold of the cloth drawn up over his head, both forearms broken away, standing against a dark red wall.",
        "Augustus with his head veiled for sacrifice, in the dress of the priesthood he had waited twenty-three years to hold."),
    "liber-linteus": (
        "File:Lanena knjiga (Liber linteus Zagrebiensis).jpg",
        "Long horizontal strips of ancient linen, stained deep red-brown, each carrying rows of small dark Etruscan letters, mounted against a black backing.",
        "The Liber Linteus, reassembled. Every strip here was once wound around a body."),
    "etruscan-language-lost": (
        "File:The Pyrgi tablets.jpg",
        "Three thin rectangular sheets of gold displayed side by side, each crumpled slightly and covered in rows of incised ancient lettering, with small nail holes around their edges.",
        "The Pyrgi Tablets: two in Etruscan, one in Phoenician. The nearest thing to a bilingual, and not near enough."),
    "claudius-etruscan-history": (
        "File:La Table claudienne - Après 48.jpg",
        "A large bronze plaque engraved with two dense columns of Latin capitals, split by a ragged vertical break down the centre and broken away along the top edge.",
        "The Lyon Tablet. Low in the left-hand column Claudius tells the Senate that the Etruscans called the king Rome knew as Servius Tullius by another name: Mastarna."),
    "delphi-pythia": (
        "File:Themis Aigeus Antikensammlung Berlin F2538 n2.jpg",
        "The interior of a Greek red-figure cup: a woman sits on a tall tripod, head bowed over a shallow bowl held in one hand and a laurel sprig in the other, facing a bearded man in a wreath who stands wrapped in his cloak.",
        "A consultation, painted around 440 BCE. The seated figure is usually identified as Themis rather than the Pythia &mdash; it is still the closest thing we have to a contemporary picture of the procedure."),
    "delphi-gases-hypothesis": (
        "File:Temple of Apollo, floor construction, Delphi, Dlfi412.jpg",
        "Looking down into the excavated stone foundations of the temple of Apollo at Delphi: courses of large limestone blocks around a sunken rectangular space, with a wooded hillside beyond.",
        "Under the floor of the temple. This is where the excavators went looking for a chasm, and did not find one."),
    "dream-incubation-asclepius": (
        "File:Votive relief depicting Amphiaraus and a patient (4th cent. B.C.) at the National Archaeological Museum of Athens on 22 July 2018.jpg",
        "A marble votive relief: a bearded god treats the bare shoulder of a standing young man, while to the right the same young man lies asleep on a couch with a large snake stretched over his shoulder.",
        "Incubation in one panel: the treatment, and the dream. Dedicated by a man named Archinos &mdash; his name is cut along the base &mdash; at the sanctuary of Amphiaraos at Oropos, not Epidaurus. A different healer, the same procedure."),
    "etruscan-lightning-doctrine": (
        "File:Statue of Tinia with thunderbolt, Fiesole, Umbrian workshop, 425-400 BC, bronze, Villa Giulia - The Etruscans exhibition - California Palace of the Legion of Honor - San Francisco, CA - DSC09377.jpg",
        "A slender nude bronze statuette of a standing male figure, one arm extended holding a forked thunderbolt, the other raised holding a small round object.",
        "Tinia, the Etruscan sky god, with the weapon in his hand. Eight other gods were entitled to throw one, and his worst needed permission."),
    "cult-of-isis-rome": (
        "File:Marble statue of Isis, the goddess holds a situla and sistrum, ritual implements used in her worship, from 117 until 138 AD, found at Hadrian's Villa (Pantanello), Palazzo Nuovo, Capitoline Museums (12945630725).jpg",
        "A marble statue of the goddess Isis draped in a fringed mantle, holding a sistrum, with a solar disc and serpent on her head.",
        "Isis, sculpted in Rome under Hadrian. She holds her sistrum; Egypt had left the statue in every way but the stone."),
    "numas-buried-books": (
        "File:Pomponius Molo Denarius 97 BC 680844.jpg",
        "A silver Roman denarius; the reverse shows King Numa Pompilius standing before a lit altar, holding a lituus, about to sacrifice a goat held by a youth.",
        "Numa sacrificing at an altar, on a denarius minted in 97 BCE, nearly six centuries after his traditional reign. The closest thing left to a portrait of the man whose books nobody kept."),
    "roman-augury-sacred-chickens": (
        "File:Denarius reverse (FindID 66682).jpg",
        "The reverse of a Roman silver denarius of Vespasian, showing a set of priestly religious implements including an augur's curved lituus staff.",
        "A lituus on a denarius of Vespasian. The augur's badge of office, not a chicken in sight, and still the symbol the whole discipline ran on."),
    "cult-of-cybele-taurobolium": (
        "File:Taurobolic altar with Cybele and Attis (4th cent. A.D.) at the National Archaeological Museum of Athens on 2 January 2020.jpg",
        "A carved marble altar from the fourth century CE showing Cybele enthroned with her hand on the shoulder of Attis, flanked by pine trees.",
        "A taurobolium altar dedicated around 360 CE, showing Cybele and Attis. Set up by a man who had just undergone the very rite Prudentius later wrote up as savage."),
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

    # MERGE, never replace. optimise_images / modern_images / make_share_images
    # each add derived keys (card, avif, avif_700, share) to this same file.
    # Starting from an empty dict silently strips them, and nothing downstream
    # errors — the pages just quietly stop referencing AVIF and share cards.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

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

        manifest.setdefault(slug, {}).update({
            "file": f"/static/img/{slug}.jpg",
            "alt": alt,
            "caption": caption,
            "credit": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "licence": strip_html(meta.get("LicenseShortName", {}).get("value", "")) or "see source",
            "source": ii.get("descriptionurl", ""),
            "width": ii.get("thumbwidth") or ii.get("width"),
            "height": ii.get("thumbheight") or ii.get("height"),
        })
        print(f"  ok   {slug:38} [{manifest[slug]['licence']}]")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum((OUT / f"{s}.jpg").stat().st_size for s in manifest) // 1024
    print(f"\n  {len(manifest)} images, {total} KB total -> static/img/")


if __name__ == "__main__":
    main()
