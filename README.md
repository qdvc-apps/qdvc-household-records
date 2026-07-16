# QDVC Household Records

A small desktop app to help a household organise a folder full of PDFs — bank
statements, payslips, insurance documents, rent receipts, electricity bills and
so on. It is a viewer/editor over plain-text files: your documents stay as
ordinary files on disk, and the app keeps human-readable YAML catalogues
alongside them.

Built with **Python 3 + GTK 3** (primary) and a parallel **GTK 4 / libadwaita**
front-end, following the
[QDVC Python GTK app specification](https://github.com/qdvc-apps/qdvc-python-gtk-app-specification).

## What it does

The app has three tabs:

- **Home** — a welcome page listing every periodic account whose records are
  *fresh* or *stale*, each with a button to jump straight to it in the Organiser.
- **Organiser** — the heart of the app, a four-pane master–detail view:
  1. **Zones** (e.g. *Freja Bank Statements*, *Shared Electricity*)
  2. **Accounts** within the selected zone (e.g. *Bank of Atlantis*)
  3. **Documents** within the selected account (the actual files)
  4. **File catalogue** for the selected document (statement number, date
     issued, notes)
- **Setup** — choose the workspace **data folder**, and configure the list of
  **people** and the list of **zoneblocks** whose combination produces the zones.

### Zones = people × zoneblocks

Each zoneblock is marked *individual*, *shared*, or *both*, and carries a
symbolic icon. Given people `[Freja, Ludvig]` and zoneblocks:

| Zoneblock       | Scope            |
|-----------------|------------------|
| Bank Statements | individual + both |
| Payslips        | individual only  |
| Electricity     | shared only      |
| Rent            | shared only      |

you get zones such as *Freja Bank Statements*, *Ludvig Bank Statements*,
*Shared Bank Statements*, *Freja Payslips*, *Ludvig Payslips*,
*Shared Electricity*, *Shared Rent*.

### Freshness

An account may be marked **periodic** with a **cycle (days)**. Its records are
**fresh** if `today − cycle_days` is chronologically before the newest
*date issued* among its documents (as currently found in its folder); otherwise
they are **stale**. Non-periodic accounts are not tracked for freshness.

### Workspace folder vs data folder

These are two different things:

- The **workspace folder** (chosen per workspace, opened from the File menu)
  holds this workspace's YAML catalogue files. You can keep several workspaces.
- The **data folder** is a single, app-wide location (configured in
  **Preferences**, stored in the app's XDG config) that holds the PDFs. The app
  treats it as **read-only**: it never creates, moves, deletes, or modifies
  anything inside it — it only reads. Think of it as possibly a read-only mount.

Each account is pointed at a **folder inside the data folder**. The top-level
PDFs in that folder automatically become the account's documents — no more and
no less. There is no importing or adding of files: to change an account's
documents, change what's in its folder. Set an account's folder by
right-clicking the account and choosing "Set folder…"; the folder must be inside
the data folder. The default data folder is
`$XDG_DATA_HOME/qdvc-household-records/data` (usually
`~/.local/share/qdvc-household-records/data`), changeable in Preferences.

The zones list (Pane 1) is sorted alphabetically and shows how many accounts
each zone holds. **Add an account** by right-clicking a zone in Pane 1, or
right-clicking the empty area of the accounts list. Right-click an existing
account for its settings, folder options, or to remove it.

Only PDFs directly in the folder are listed; if the folder contains subfolders,
a warning appears and those are ignored. Each document is shown with a PDF icon
and a label describing its catalogue tags (e.g. "No. 53 (13 May 2026, 15d ago)",
or "(not tagged yet)" before you tag it) — not its filename. A file you had
catalogued that later disappears is shown greyed as *missing*, with its tags
kept. Selecting a document shows its catalogue (statement no., date issued,
notes) but does not open it — use the **Open** button. To change an account's
periodic/cycle/notes settings, right-click it in the Accounts pane.

## Requirements

- Python 3.10+
- PyGObject and **one** of:
  - GTK 3 — `python3-gi`, `gir1.2-gtk-3.0` (default), or
  - GTK 4 + libadwaita — `gir1.2-gtk-4.0`, `gir1.2-adw-1`
- PyYAML

On Debian/Ubuntu:

```
sudo apt install python3-gi gir1.2-gtk-3.0 python3-yaml
# optional GTK4 front-end:
sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1
```

## Running

```
python3 qdvc_household_records.py            # GTK3 (default)
python3 qdvc_household_records.py --gtk4      # GTK4 / libadwaita
python3 qdvc_household_records.py /path/to/workspace
```

The backend can also be chosen in **Edit → Preferences** (GTK3) or the primary
menu → **Preferences** (GTK4); the change takes effect on the next launch.

## Desktop launcher

Install a launcher at `~/.local/share/applications/qdvc-household-records.desktop`:

```
[Desktop Entry]
Type=Application
Name=QDVC Household Records
Comment=Organise a household folder of PDF documents
Exec=python3 /full/path/to/qdvc_household_records.py %U
Path=/full/path/to
Icon=folder-documents
Terminal=false
Categories=Office;Utility;
StartupNotify=true
StartupWMClass=qdvc-household-records
```

Then refresh and validate:

```
update-desktop-database ~/.local/share/applications
desktop-file-validate ~/.local/share/applications/qdvc-household-records.desktop
```

`StartupWMClass` must equal the `set_prgname` value (`qdvc-household-records`).

## Testing without a display

```
python3 -m py_compile qdvc/*.py qdvc/gtk3/*.py qdvc/gtk4/*.py qdvc_household_records.py
PYTHONPATH=. python3 tests/test_model.py
PYTHONPATH=. python3 tests/test_import_smoke.py
```
