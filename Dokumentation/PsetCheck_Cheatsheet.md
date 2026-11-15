# PsetCheck – Cheat Sheet

Living reference for the PsetCheck project. Updated as new things come up.
*Last updated: 15 Nov 2026*

---

## 1. Opening a model

```python
import ifcopenshell
import ifcopenshell.util.element

model = ifcopenshell.open(r"C:\...\25.011_GoBau.ifc")   # from a file path on disk
model = ifcopenshell.file.from_string(data.decode())    # from uploaded bytes (no file needed)

model.schema        # "IFC4X3", "IFC2X3" … (a value, no brackets)
```

- `ifcopenshell.open()` needs a **path**. An upload gives **bytes**, so use `from_string`.
- `.decode()` turns bytes into text. Works because `.ifc` is a text file.

---

## 2. Getting elements

```python
courses = model.by_type("IfcCourse")     # list of all IfcCourse
len(courses)                             # how many
course = courses[0]                      # the first one

course.Name                              # attribute, e.g. "AC T 22 S, d=100mm"
course.GlobalId                          # the GUID
course.get_info()                        # all attributes as a labelled dictionary
```

- `by_type("IfcWall")` also returns subtypes (e.g. `IfcWallStandardCase` in IFC2X3).
- Loop directly: `for course in courses:` (no need for `range(len(...))`).
- `by_type()` belongs to the **model**. It doesn't exist on a list or set of elements – filter those with `is_a` instead (see 2b).

---

## 2b. Spatial structure (Project → Site → Road → RoadPart → Course)

The tree in your viewer:

```
IfcProject  "25.011 Sanierung Gimenenstrasse"
 ├── IfcSite "02 Abbruch"
 └── IfcSite "03 Neu"
      └── IfcRoad "Gimenenstrasse"
           └── IfcRoadPart "Strassenabschnitt"
                └── IfcRoadPart "Gehweg Oberbau 2"
                     └── IfcCourse "Rasengittersteine, d=120mm"
```

**Find one branch by name:**

```python
site = [s for s in model.by_type("IfcSite") if s.Name == "03 Neu"][0]
```

**Everything below it (all levels down):**

```python
inside = ifcopenshell.util.element.get_decomposition(site)
```

`inside` is a **set**. Each item is one normal IFC element – `get_psets(e)`, `e.Name`, `e.is_a()` all work on it. Printed raw, an element looks like the line in the `.ifc` file:

```
#40634 = IfcRoadPart('1KS5LVSjb2SPMdZ6MIvq9D', #40633, 'Fahrbahn Oberbau 2', $, '-', $, ...)
  IFC id   class         GUID                   OwnerHistory  Name          $ = empty
```

- `#40633` inside the brackets = a **reference** to another element (line #40633).
- Attributes are always in the same order for a class (fixed by the IFC standard). `e.get_info()` shows them with names.

**Print it readably:**

```python
for e in inside:
    print(e.is_a(), "|", e.Name)        # IfcRoadPart | Fahrbahn Oberbau 2
```

**Filter what you need:**

```python
courses  = [e for e in inside if e.is_a("IfcCourse")]    # only courses ("by_type" for one branch)
elements = [e for e in inside if e.is_a("IfcElement")]   # all physical objects
```

- `inside` also contains the **containers** (`IfcRoad`, `IfcRoadPart`). They're folders in the tree, not physical objects, and usually have no `GoBau_*` Psets.
- `IfcElement` is the parent class of all physical things (courses, pipes, kerbs …), so filtering by it drops the containers.

**Count what's in there per class:**

```python
from collections import Counter
print(Counter(e.is_a() for e in elements))   # {'IfcCourse': 90, 'IfcPipeSegment': 12, ...}
```

**Going up – where does an element sit?**

```python
ifcopenshell.util.element.get_container(course)   # direct container, e.g. the IfcRoadPart
ifcopenshell.util.element.get_aggregate(part)     # the parent it's aggregated into
```

- `e.is_a("IfcCourse")` → True/False: "is this an IfcCourse?". `e.is_a()` without argument → the class name.
- Alternative in the GoBau model: filter by Pset, `psets["GoBau_Struktur"]["Stufe_2"] == "03 Neu"`.

### List comprehension explained

```python
[ s   for s in model.by_type("IfcSite")   if s.Name == "03 Neu" ]
  ↑   ↑                                   ↑
  keep this   go through every site       but only if this is true
```

Same as the written-out loop:

```python
matches = []
for s in model.by_type("IfcSite"):
    if s.Name == "03 Neu":
        matches.append(s)      # ← the first "s" is what goes in here
site = matches[0]
```

- The **first `s`** = what to put into the list. Can be something else: `[s.Name for s in ...]` → list of names.
- `[0]` takes the first item. Empty list → `IndexError` (usually a spelling mismatch).
- Both versions do the same thing – use whichever is easier to read.
- A list comprehension always returns a **list** (square brackets), even if it loops over a set.

---

## 3. Psets and properties ⭐

`get_psets` returns a **dictionary of dictionaries**:

```python
psets = ifcopenshell.util.element.get_psets(course)
# {
#   "GoBau_Menge":         {"Volumen (m3)": 1.677, "Fläche (m2)": 5.02, ..., "id": 38972},
#   "GoBau_Ausschreibung": {"Code": "R 1.1.201", "Einheitspreis": 0.0, ..., "id": 42540},
# }
```

**Pick one value, one bracket per level:**

```python
psets["GoBau_Menge"]                      # whole Pset (a dictionary)
psets["GoBau_Menge"]["Volumen (m3)"]      # one value
```

- 1st bracket = which **Pset**, 2nd bracket = which **property**.
- Names must match **exactly** (spaces, brackets, capitals, umlauts).
- `"id"` is the Pset's own IFC number, **not a property** – skip it in checks.

**Safe version (no crash if missing → gives `None`):**

```python
psets.get("GoBau_Menge", {}).get("Volumen (m3)")
```

A `None` here = "fehlt" → that's a finding for the check.

**See everything in one Pset, with types:**

```python
for name, value in psets["GoBau_Menge"].items():
    print(name, "→", value, type(value))
```

**Collect all distinct values of one property (e.g. to build an allowed list):**

```python
values = set()
for course in courses:
    psets = ifcopenshell.util.element.get_psets(course)
    values.add(psets.get("GoBau_Ausschreibung", {}).get("Kostenteiler"))
print(values)       # {'ZUG:100%', 'WWZ-EW:100%', 'WWZ-WV:100%'}
```

**Options:**

```python
get_psets(course, psets_only=True)   # only property sets
get_psets(course, qtos_only=True)    # only quantity sets (Qto_…); {} if none exported
```

**Company Psets in the GoBau model:** `GoBau_Struktur`, `GoBau_Menge`, `GoBau_Ausschreibung`.
Ignore CAD junk: `Properties`, `Misc`, `General`, `3D Visualization`, `Geometry`.

**Quantities vs properties:** quantities (`Qto_…`) are often not exported at all (e.g. NEST model walls). The GoBau model stores quantities as normal properties in `GoBau_Menge`.

---

## 3b. Lists, sets, dictionaries

| | List `[...]` | Set `{...}` / `set()` | Dictionary `{key: value}` |
|---|---|---|---|
| Order | kept | none | kept |
| `x[0]` | ✅ | ❌ | by key: `x["Name"]` |
| Duplicates | allowed | each item once | each key once |
| Add | `.append(x)` | `.add(x)` | `d["key"] = x` |
| Empty | `[]` | `set()` | `{}` |

- `{}` is an empty **dictionary**, not a set → use `set()`.
- Set → list: `list(my_set)`.
- `x in my_set` / `x in my_list` → True/False (used for allowed-value checks).
- `key in my_dict` → True/False: does this key exist? (e.g. `"GoBau_Menge" in psets`)

**Comparison operators** (each one gives `True` / `False`; used as the *condition* of an `if`):

| Operator | Means |
|---|---|
| `==` | equal |
| `!=` | not equal |
| `>` / `<` | greater / less than |
| `>=` / `<=` | greater or equal / less or equal |
| `in` / `not in` | is in the list/set/dict |
| `is None` / `is not None` | is (not) missing |

- `=` assigns a value, `==` compares. `if x = 5` is a SyntaxError.
- Chain them: `if 0 < value <= 500:` (= between, used in `check_range`).
- Combine with `and`, `or`, `not`.

**Operator from text (e.g. `">"` from the rule Excel):**

A `">"` in a variable is just **text** – Python only compares when `>` is written in the code itself (`pset_properties conditional value` → SyntaxError). Translate text → function:

```python
import operator          # built in, no pip

OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt,
       ">=": operator.ge, "==": operator.eq, "!=": operator.ne}

OPS[">"]                 # step 1: look up the text → the function operator.gt
OPS[">"](5, 0)           # step 2: call it → same as 5 > 0 → True

if conditional not in OPS:                          # validate the input
    ...
if OPS[conditional](pset_properties, compare_value):  # the actual comparison
    ...
```

- Functions are values: `compare = operator.gt` (no brackets) stores it, `compare(5, 0)` calls it.
- The dictionary is the short form of an `if conditional == ">": ... elif conditional == "<": ...` chain.
- Don't use `eval()` for this – it runs any text as code.
- Check "is it a number?" before `<`, `>`, `<=`, `>=` (`"10" > "9"` is False; `"5" > 3` → TypeError).
- **Empty check:** `if not my_list:` → True if empty. Works for lists, sets, dicts and strings.
- **Truthiness:** `if x:` is True for anything with content (`"text"`, `5`, `[1]`) and False for `None`, `""`, `0`, `[]`, `{}`. So `if error:` = "if error contains a message".
- A list comprehension with no matches gives `[]`, **not** `None` → `[] is None` is False. Check `if not sites:` before using `sites[0]`.

---

## 4. Data types

| Python type | Means | Typical IFC type |
|---|---|---|
| `str` | text | IfcLabel, IfcText |
| `float` | decimal number | IfcReal, IfcLengthMeasure, IfcVolumeMeasure … |
| `int` | whole number | IfcInteger |
| `bool` | true/false | IfcBoolean |
| `None` | missing | – |

```python
type(value)                  # <class 'float'>
isinstance(value, float)     # True / False – use this in checks
```

- A number stored as text in the IFC comes back as `str` → wrong type, caught.
- Limitation: Python can't tell `IfcReal` from `IfcVolumeMeasure` (both `float`). Fine for PsetCheck.

---

## 4b. Checks and results ⭐

**Three check types:**

| Check | Question | Example |
|---|---|---|
| Present | does the value exist? | `None` / `KeyError` → "fehlt" |
| Type | is it the right data type? | `Volumen (m3)` must be `float` |
| Allowed value / range | is the value OK? | Kostenteiler in list; `Menge > 0` |

**The check cascade (your plan) – each gate only runs if the previous one passed:**

```
(before the loop)  Any elements at all?   no → "Keine Elemente zu prüfen"
1. Pset exists?                            no → "Pset fehlt"
2. Property exists?                        no → "Property fehlt"
3. (later) Right data type?                no → "falscher Typ"
4. Value allowed?                          no → "unzulässiger Wert"
                                           yes → "erfüllt"
```

- Use **early return**: at each failed gate, `return` immediately – no nested ifs.
- Test whether a key exists with `in`: `if pset not in psets: return None, "Pset fehlt"`.
- Keep the statuses separate – the report then says *what* to fix (whole Pset vs one value).

**Catching missing values with try/except:**

```python
try:
    value = ifcopenshell.util.element.get_psets(i)["GoBau_Ausschreibung"]["Kostenteiler"]
except KeyError:
    value = None          # missing Pset or property – the loop keeps going
```

- `try:` runs the code; `except KeyError:` runs instead of crashing when a key is missing.
- Missing values are **findings to report**, not something to hide.

**The safe loop pattern – decide first, append once at the end:**

```python
results = []
allowed = {"ZUG:100%", "WWZ-EW:100%", "WWZ-WV:100%"}

for i in elements:
    try:
        value = ifcopenshell.util.element.get_psets(i)["GoBau_Ausschreibung"]["Kostenteiler"]
        status = "erfüllt" if value in allowed else "unzulässiger Wert"
    except KeyError:
        value, status = None, "fehlt"

    results.append({                      # one row per element, always runs
        "GUID": i.GlobalId,
        "Klasse": i.is_a(),
        "Name": i.Name,
        "Kostenteiler": value,
        "Status": status,
    })

df = pd.DataFrame(results)
print(df)
print(df[df["Status"] != "erfüllt"])      # only the problems
```

- `status = "a" if condition else "b"` = one-line if/else.
- `value, status = None, "fehlt"` = set two variables at once.
- ⚠️ **Stale variable trap:** in the `except`, don't reuse the variable from `try` – it still holds the **previous element's** value. Set it to `None` explicitly.

**Two ways to build a table – same result:**

```python
# list of dictionaries = by ROW (recommended: each element's values stay together)
results = [{"GUID": "1KS5…", "Name": "Baum", "Status": "erfüllt"}, ...]

# dictionary of lists = by COLUMN
data = {"GUID": ["1KS5…", ...], "Name": ["Baum", ...], "Status": ["erfüllt", ...]}

pd.DataFrame(results)   # == pd.DataFrame(data)
```

With dictionary-of-lists, forgetting one `.append` in one branch makes columns different lengths → `All arrays must be of the same length`.

**Viewing a DataFrame properly (like Spyder's variable explorer):**

```python
df.to_csv("check_result.csv", index=False)   # then: right-click file → "Open in Data Wrangler"
print(df.to_string())                        # print ALL rows instead of "..."
df.to_excel("check.xlsx", index=False)       # open in Excel
```

- **Data Wrangler** (VS Code extension, Microsoft): sorting, filtering, and per-column stats (missing, distinct, % per value).
- Debugger route (F5 → breakpoint on the line *after* `df = ...` → Run and Debug → Variables → right-click `df` → "View Value in Data Viewer") may not work with every Python version – the CSV route always works.
- Breakpoints stop **before** their line runs. Don't click "Set Value" in the Variables menu.
- Add `*.csv` to `.gitignore` – results contain company model data.

**Reusable check function (next step):**

```python
def check_allowed(element, pset, prop, allowed):
    # gates: Pset exists? → Property exists? → value allowed?
    ...
    return value, status                  # hand two things back

value, status = check_allowed(i, "GoBau_Ausschreibung", "Kostenteiler", allowed)
```

Siblings later: `check_type(element, pset, prop, expected_type)`, `check_range(element, pset, prop, minimum)`.

**Building the rule set:**

1. Find the real values first (collect them in a `set()`), then write the allowed list.
2. Hardcode rules first → get the logic working → then move them into Excel.
3. Rules depend on the **project phase**: e.g. `Einheitspreis` is empty on purpose in the tender phase (contractors fill it in) → not a rule for this model.

**Rule ideas for the GoBau model:**

| Pset | Property | Check |
|---|---|---|
| GoBau_Ausschreibung | Kostenteiler | allowed: ZUG:100%, WWZ-EW:100%, WWZ-WV:100% |
| GoBau_Ausschreibung | Code | present, text |
| GoBau_Ausschreibung | Mengeneinheit | allowed: m3, m2, m, Stk (check real values) |
| GoBau_Ausschreibung | Menge | float, > 0 |
| GoBau_Menge | Volumen (m3) | float, > 0 |
| GoBau_Struktur | Stufe_2 | allowed: 02 Abbruch, 03 Neu |

---

## 4c. break, continue, return

| Keyword | Leaves | Use when |
|---|---|---|
| `break` | the **loop** (code after the loop still runs) | you found what you were looking for – stop searching |
| `continue` | only **this round** of the loop, jumps to the next item | skip this item, keep going with the rest |
| `return` | the whole **function** (and hands a value back) | the function has its answer – e.g. a failed gate in the check cascade |

```python
# break: stop at the first match
for s in model.by_type("IfcSite"):
    if s.Name == "03 Neu":
        site = s
        break

# continue: skip containers, check the rest
for e in inside:
    if not e.is_a("IfcElement"):
        continue
    ...check e...

# return: early exit in a check function
def check_allowed(element, pset, prop, allowed):
    psets = ifcopenshell.util.element.get_psets(element)
    if pset not in psets:
        return None, "Pset fehlt"
    ...
```

- `break` only works **inside a loop**. Outside one → `SyntaxError: 'break' outside loop`.
- In the check loop over all elements, **don't** `break` on a failure – you'd stop checking the remaining elements.

---

## 5. NiceGUI basics

```python
from nicegui import ui

model = None                                  # lives outside functions

async def load_ifc(document):                 # runs when a file is uploaded
    global model                              # "I mean the model outside"
    data = await document.file.read()         # the file's bytes
    model = ifcopenshell.file.from_string(data.decode())
    show_overview()                           # call the next steps

def show_overview():                          # normal def, only READS model
    info.text = f"{len(model.by_type('IfcCourse'))} IfcCourse found"

async def reject_file(document):              # rejected file has NO .file
    ui.notify("Only .IFC files allowed")

ui.upload(on_upload=load_ifc,
          on_rejected=reject_file,
          auto_upload=True).props("accept=.ifc")
info = ui.label("No model loaded")

ui.run()
```

**Two phases – the key idea:**

| When | What runs |
|---|---|
| App starts (once) | everything at top level: `model = None`, `ui.upload(...)`, `ui.label(...)` |
| Later, on an event | only the function connected to it (`on_upload`, `on_click` …) |

- Anything that needs the model goes **inside** a function that runs after the upload.
- NiceGUI does **not** re-run the file (Streamlit does).
- **One function per event**, which calls the helper functions in order.
- `global model` only where you **assign** `model = ...`. Reading needs no `global`.
- `async def` + `await` only where you wait for something (reading the upload).
- Function and parameter names are free: `load_ifc(document)`, `load_ifc(e)` – same thing.

**Useful pieces:**

| Code | Does |
|---|---|
| `ui.label("text")` | text on the page; change with `label.text = ...` |
| `ui.button("Prüfen", on_click=run_check)` | button that runs a function |
| `ui.notify("msg")` | pop-up message |
| `.props("accept=.ifc")` | passes an HTML/Quasar setting (here: file filter, checked in the browser) |
| `.classes("max-w-full")` | passes CSS styling classes |
| `lambda: ui.notify("x")` | mini one-line function to run later; use `def` for anything longer |

---

## 6. Text vs binary files

```python
import io
import pandas as pd

text  = data.decode()                     # text files: .ifc, .txt, .csv
rules = pd.read_excel(io.BytesIO(data))   # binary files: .xlsx (no saving needed)
```

`.decode()` on a binary file (`.xlsx`, `.ifczip`, images) → `UnicodeDecodeError`.

---

## 7. Files, imports, classes

- `from IfcModel import ifcmodel` → **file name** (without `.py`) `import` **class name**.
- Names are **case-sensitive**: `IfcModel` ≠ `ifcmodel`.
- Importable file names **can't start with a digit** (`0_IfcModel.py` ✗, `ifc_model_0.py` ✓).
- Save before running (tab dot = unsaved → Python runs the old version).
- Don't put `ifcopenshell.open(...)` at the top of a file you import – it runs on every import.
- Name variables after what they hold (`value`, not `psets`, when it's one property value).

**Classes:**

```python
class RuleSet:
    def __init__(self, data: bytes):   # runs on RuleSet(data); never async, never return
        self.rules = ...               # self.x = what the object remembers

    def count(self):                   # method; call with obj.count()
        return len(self.rules)
```

- `RuleSet` = blueprint, `RuleSet(data)` = an actual object.
- Use classes for **your own logic** (rules, checks). Don't wrap IfcOpenShell just to redefine its functions.

**Planned: the `Checker` class** (in `checks.py`) – removes the repeated "find site → get elements" from every check:

```python
class Checker:
    def __init__(self, model, site_name):
        # find the site + collect self.elements ONCE
        ...

    def check_allowed(self, pset, property, allowed_values): ...   # loops over self.elements
    def check_type(self, pset, property, expected_type): ...
    def check_range(self, pset, property, minimum): ...
```

```python
# Streamlit.py
from checks import Checker
checker = Checker(model, "03 Neu")
df1 = checker.check_allowed("GoBau_Ausschreibung", "Kostenteiler", {...})
df2 = checker.check_type("GoBau_Menge", "Volumen (m3)", float)
```

Order: build `check_type` as a plain function first → once two checks exist, move both into `Checker`.

---

## 8. Debugging

- Read the **last line** of an error first. Everything above is the path through Python's internals.
- `print(type(x))` → what is it? `print(dir(x))` → what can it do?
- `'NoneType' object has no attribute ...` → the variable is still `None`, usually because code ran **before** the upload.
- `KeyError: 'GoBau_Menge'` → that Pset/property doesn't exist on this element → use `.get()`, `in` or `try/except`.
- `has no attribute 'file'` in `reject_file` → rejected files never reach Python.
- `SyntaxError: 'break' outside loop` → `break` only works inside `for`/`while`; in a function use `return`.
- `IndexError: list index out of range` after `[...][0]` → the filter found nothing (check the exact name).
- `'set' object is not subscriptable` → you used `[0]` on a set → `list(x)[0]`.
- `'set' object has no attribute 'append'` → sets use `.add()`.
- `All arrays must be of the same length` → dictionary-of-lists with a missing `.append` in one branch.
- A table value that "can't be right" (e.g. a Kostenteiler on an element that has none) → stale variable from the previous loop round.

---

## 9. Git routine

**Start of session:** Sync (circular arrows, bottom left).
**End of session:** Source Control → type message → Commit → Sync.

- Stay on `main`. Commit + Sync before switching computers.
- **Never** "Discard All Changes" (deletes uncommitted files).
- Empty commit message → VS Code opens `COMMIT_EDITMSG` and waits. Close it, type in the box instead.
- `U` = untracked (not in Git), `M` = modified, `A` = added, red `!` = conflict.

**.gitignore:**
```
.venv/
venv/
*.ifc
__pycache__/
```
Already-tracked files ignore `.gitignore` → untrack them (files stay on disk):
```
git rm -r --cached --ignore-unmatch -- "*.ifc" .venv __pycache__
```

**Conflict:** open the file → Accept Current / Incoming / Both → save → `git add .` → `git commit`.
Run terminal commands **one line at a time**.

---

## 10. Docs

- NiceGUI: nicegui.io/documentation
- IfcOpenShell: docs.ifcopenshell.org (code examples page)
- Python tutorial: docs.python.org/3/tutorial (7.2 = reading/writing files)
