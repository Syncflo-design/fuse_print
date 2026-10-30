# Fuse Print

Sticker and label printing for Fuse: each step of a run recorded at its workstation on a phone,
tablet or scanner, the waste there with a reason, and what it costs. Frappe / ERPNext v16.
Requires `erpnext`, `fuse_core` and `fuse_manufacturing`.

## Rules this app keeps

- **ERPNext makes things; this app adds where the waste happened and why.** A product is an
  ordinary BOM with operations and a % Process Loss as its standard waste. A run is an ordinary
  Work Order with a Job Card per step, finished by an ordinary Manufacture entry that backflushes
  the materials from the BOM and which `fuse_manufacturing` posts to Intacct where posting is on.
- **ERPNext's process loss is a running total.** A job card's Process Loss is the run less what that
  card passed on, so it includes every step before it, and the Manufacture entry books the largest
  as the run's loss. That stays as it is. What one step spoiled is kept beside it as
  **Waste at this Step** (`fp_waste_qty`): what reached the step, less what it passed on.
- **No waste without a reason.** A job card whose step spoiled anything cannot be submitted until
  its **Waste Reason** (`fp_waste_reason`) is chosen.
- **The floor is a front door, not a second engine.** The Print Floor writes the same job card time
  log, quantity and reason the desk form does. ERPNext still decides whether a step may start.

## What is in it

| Area | What |
|---|---|
| Print Floor (`fuse-print-floor`) | For a station PC with a scanner, a tablet or a phone. Scan the job ticket (or the phone's camera, or type the end of the works order number), or tap the workstation; Start; say how many good ones went on, tap why any were spoiled, add a note; Done. The last step finishes the run: the Manufacture entry backflushes the materials and puts the good ones, and any offcuts, into stock. If that fails (usually short stock) the step stays recorded and the floor says why. |
| Job Ticket | Print format on Work Order: the run's barcode (the works order number), customer, product, run and steps, with blank columns for when the screen is down. |
| Job Card | `fp_waste_qty` (read only, set on every save), `fp_waste_reason` (setup and colour match, misprint, media fault, lamination fault, cut out of register, weeding damage, end of roll, other) and `fp_waste_note` (the operator's note, typed or spoken) |
| Report | **Print Waste**: one row per submitted job card with what reached the step, what it passed on, what it spoiled, why, the operator's note, media lost in m² and material cost; chart by reason; summary of the waste rate against the recipes' standard |
| Fuse Home | **Print Floor** and **Print Waste** tiles, one switch `fp_waste` |

The note box gets a mic where **Nest Assistant** is installed and switched on (Nest Assistant
Settings → Enabled; no API key is needed to dictate). Without it, the note is typed.

## Install

1. Push the repo, add it to the Fuse bench (Frappe Cloud → Apps → Add from GitHub), **Deploy**
   (not just Update: Update skips `bench build`, so the floor's page script, its stylesheet and
   the list script would be missing).
2. Install on the site. `after_install` adds the custom fields and the module switch.
3. If `after_migrate` did not fire, run **`fuse_print.install.after_install`** as System Manager.

## Demo

Work Order list → menu → **Load Sticker Printing Demo** (System Manager, demo site only: site config
`fuse_demo_site`). Give it the presenter login, which must already exist. The first load makes the
company **Sticker Printing** and six weeks of history; every later load only makes the live steps
again once a demo has used them. See `demo/sticker_printing.py` for what it makes. Back up the demo
site first (`S:\Products\Fuse\demo_profiles\PROFILES.md`). The presenter's run sheet is
`S:\Products\Fuse\docs\StickerPrinting\sticker-printing-demo-guide.html`.

The loader never changes a login's roles or permissions. Given a presenter, it sets only the
login's Module Profile (which tiles Fuse Home shows) and its default company.

Receiving and Picking list the company's own purchase and sales orders because it has no Intacct
entity and posting is off; that needs the `fuse_manufacturing` change of 2026-10-29.

Keep **Post Stock Movements** off on the demo site while this profile is on it: the company has no
Intacct entity, so its movements have nowhere to post.

## Checks

```
python -m unittest discover -s fuse_print/tests -t .
python -m ruff check .
```
