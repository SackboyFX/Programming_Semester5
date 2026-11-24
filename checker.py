import operator

import ifcopenshell
import ifcopenshell.api.pset
import ifcopenshell.api.style
import ifcopenshell.util.element
import pandas as pd


class Checker:
    """Runs property checks on all IfcElements below one IfcSite.

    The site and its elements are looked up ONCE in __init__.
    Every check method then loops over self.elements and returns a DataFrame.
    """

    #Maps the conditional (text, e.g. from the rule Excel) to the comparison function.
    #Class attribute: it never changes, so it lives outside the methods.
    OPERATIONS = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
    }

    def __init__(self, model, ifcsite_name: str):
        self.model = model                      #the opened IFC model (ifcopenshell.file)
        self.ifcsite_name = ifcsite_name        #e.g. "03 Neu"
        self.elements = self._get_elements()    #all IfcElements below the site, collected once

    def _get_elements(self):
        """Find the site by name and return all IfcElements below it ([] if the site doesn't exist)."""
        sites = [x for x in self.model.by_type("IfcSite") if x.Name == self.ifcsite_name]

        #Check if Site Exists:
        if not sites:
            print(f"Error: No IFC site with the name '{self.ifcsite_name}' found.")
            return []

        site = sites[0]  #Get the first matching site

        inside = ifcopenshell.util.element.get_decomposition(site)  #All elements under the site.
        return [e for e in inside if e.is_a("IfcElement")]          #Only physical elements, as a list.

    def _get_value(self, element, pset: str, property: str):
        """The shared gates of every check: does the Pset exist, does the property exist?

        Returns (value, error):
        - error is None when the value was found
        - otherwise error is "Pset does not exist" or "Property does not exist"
        """
        psets = ifcopenshell.util.element.get_psets(element)

        #Gate 1: Check if the Pset exists for the element
        if pset not in psets:
            return None, "Pset does not exist"

        #Gate 2: Check if the property exists in the Pset
        if property not in psets[pset]:
            return None, "Property does not exist"

        return psets[pset][property], None

    def check_allowed(self, pset: str, property: str, allowed_values: str):
        """PASS if the property value is in allowed_values."""
        results = []

        #Split the text from the Excel cell into a list at every ";". strip() removes spaces around each entry,
        #so "A;B" and "A; B" both work. str() makes sure a single number in the cell doesn't crash split().
        split_allowed_values = [v.strip() for v in str(allowed_values).split(";")]

        for i in self.elements:
            value, error = self._get_value(i, pset, property)

            if error: #if error contains any value other than None, it means the Pset or property does not exist, so it automatically fills in error in the Check column.
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": error, "Check": error})
            elif value in split_allowed_values:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Check": "FAIL"})

        return pd.DataFrame(results)

    def check_type(self, pset: str, property: str, data_type: str):
        """PASS if the property value has the expected data type (e.g. float, str)."""
        results = []
        data_type = str(data_type).lower() #str() so an empty cell (NaN) doesn't crash. This minimizes errors from mistypes as Float or Int
        data_type_converter = {"str": str, "float": float, "int": int}

        if data_type not in data_type_converter:
            print("Error: Data Type check failed. Data Type must be one of the following: str, float, int")
            return None

        for i in self.elements:
            value, error = self._get_value(i, pset, property)

            if error:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": error, "Data Type": "N/A", "Check": error})
            elif isinstance(value, data_type_converter[data_type]):
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Data Type": data_type_converter[data_type].__name__, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Data Type": data_type_converter[data_type].__name__, "Check": "FAIL"})

        return pd.DataFrame(results)

    def check_range(self, pset: str, property: str, conditional: str, compare_value: float):
        """PASS if the comparison 'value <conditional> compare_value' is True (e.g. value > 0)."""

        #Check if the conditional is valid (the keys of OPERATIONS are the allowed conditionals):
        if conditional not in self.OPERATIONS:
            print(f"Error: Invalid conditional '{conditional}'. Allowed conditionals are: {list(self.OPERATIONS)}")
            return None

        compare = self.OPERATIONS[conditional]  #e.g. operator.gt for ">"
        results = []

        for i in self.elements:
            value, error = self._get_value(i, pset, property)

            if error:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": error, "Check": error})
                continue

            #Check if the value is a number. Text or None would crash the comparison or give wrong results.
            #bool is excluded on purpose: True/False count as 1/0, so True > 0 would pass.
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Check": "Not a number"})
            elif compare(value, compare_value):
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, "Pset": pset, "Property": property, "Value": value, "Check": "FAIL"})

        return pd.DataFrame(results)


def rulecheck(checker, ruleset):
    """Runs every rule of the ruleset through the checker.

    Returns the result tables as a dict {sheet name: DataFrame} (useful later for the UI).
    """
    results = {}

    for index, row in ruleset.iterrows():
        check = row["check"]
        excel_row = index + 2  #Excel starts at 1 and row 1 is the header, so the first rule is Excel row 2

        if check == "allowed":
            df = checker.check_allowed(row["pset"], row["property"], row["value"])
        elif check == "type":
            df = checker.check_type(row["pset"], row["property"], row["value"])
        elif check == "range":
            df = checker.check_range(row["pset"], row["property"], row["operator"], row["value"])
        else:
            print(f"Error: Rule in Excel row {excel_row} has an unknown check '{check}'. Skipped.")
            continue

        #None = the check rejected the rule (invalid data type or operator). Nothing to write.
        if df is None or df.empty:
            continue

        #Excel sheet names: max. 31 characters and none of these: [ ] : * ? / \
        sheet_name = f"{excel_row} {check} {row['property']}"
        for char in '[]:*?/\\':
            sheet_name = sheet_name.replace(char, "_")
        results[sheet_name[:31]] = df        

    return results

def savecheck(rulecheck_results, output_path):
    """Saves the results of rulecheck() as one Excel file, one sheet per rule.

    rulecheck_results: the dict returned by rulecheck() {sheet name: DataFrame}.
    output_path: a file path, or an io.BytesIO() to keep the file in memory (for the download button).
    """
    if not rulecheck_results:
        print("Nothing to save.")
        return

    #Write every result table into its own sheet of one Excel file.
    with pd.ExcelWriter(output_path) as writer:
        for sheet_name, df in rulecheck_results.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Report written to {output_path}")

def summarize(rulecheck_results):
    """Counts the results of every rule: one row per rule, for a quick overview in the app.

    rulecheck_results: the dict returned by rulecheck() {sheet name: DataFrame}.
    Returns a DataFrame with the columns Rule | PASS | FAIL | Missing | Not a number | Total.
    "Missing" = the Pset or the property does not exist on the element.
    """
    rows = []

    for sheet_name, df in rulecheck_results.items():
        counts = df["Check"].value_counts()  #e.g. PASS: 824, Property does not exist: 173

        missing = counts.get("Pset does not exist", 0) + counts.get("Property does not exist", 0)
        rows.append({
            "Rule": sheet_name,
            "PASS": int(counts.get("PASS", 0)),
            "FAIL": int(counts.get("FAIL", 0)),
            "Missing": int(missing),
            "Not a number": int(counts.get("Not a number", 0)),
            "Total": len(df),
        })

    return pd.DataFrame(rows)


#Colours for the viewer (RGB from 0 to 1): red = at least one rule failed, green = all rules passed
STATUS_COLOURS = {
    "FAIL": (0.80, 0.15, 0.15),
    "PASS": (0.20, 0.60, 0.25),
}


def _get_colour_style(model, status):
    """Returns the surface style "PsetCheck PASS" / "PsetCheck FAIL", creating it once if it doesn't exist yet."""
    name = f"PsetCheck {status}"
    for style in model.by_type("IfcSurfaceStyle"):
        if style.Name == name:
            return style  #already created by an earlier run: reuse it instead of making a duplicate

    red, green, blue = STATUS_COLOURS[status]
    style = ifcopenshell.api.style.add_style(model, name=name)
    ifcopenshell.api.style.add_surface_style(model, style=style, ifc_class="IfcSurfaceStyleShading", attributes={
        "SurfaceColour": {"Name": None, "Red": red, "Green": green, "Blue": blue},
        "Transparency": 0.0,
    })
    return style


def writeback(checker, rulecheck_results, pset_name="PsetCheck", colour=True):
    """Writes the check results back into the model as one Pset per element.

    checker: the Checker the rules were run with. Its model (checker.model) is CHANGED here.
    rulecheck_results: the dict returned by rulecheck() {sheet name: DataFrame}.

    Every checked element gets one Pset "PsetCheck" with
    - "Status": "PASS" if every rule passed, otherwise e.g. "FAIL (2 of 5)". The 3D view colours from this.
    - one property per rule, named like the report sheet (e.g. "4 range Volumen (m3)"),
      with the result: "PASS", "FAIL (value: 0.0)", "Property does not exist", ...

    colour=True also paints every checked element in the model: red if Status is FAIL, green if PASS.
    Any IFC viewer (BIMcollab, Solibri, usBIM) then shows the result in 3D, without any geometry work in Python.
    Note: the original colours are replaced in the model (only in the downloaded copy, the original file stays).

    Running it again replaces the old PsetCheck, so an element never gets two of them.
    The model is NOT saved here: afterwards use checker.model.write(path) or checker.model.to_string().
    Returns the number of elements that got a PsetCheck.
    """
    model = checker.model

    #The two colour styles, created once and shared by all elements
    if colour:
        colour_styles = {status: _get_colour_style(model, status) for status in STATUS_COLOURS}

    #Step 1: collect the results per element instead of per rule.
    #collected = {GUID: {rule name: result text, ...}, ...}
    collected = {}

    for sheet_name, df in rulecheck_results.items():   #every rule (= every sheet of the report)
        for index, row in df.iterrows():                #every element checked by that rule
            guid = row["GUID"]

            if guid not in collected:                   #first time we see this element: give it an empty dict
                collected[guid] = {}

            #PASS and the error texts are clear on their own. For FAIL and "Not a number" the value shows WHY.
            if row["Check"] in ("FAIL", "Not a number"):
                collected[guid][sheet_name] = f"{row['Check']} (value: {row['Value']})"
            else:
                collected[guid][sheet_name] = str(row["Check"])

    #Step 2: write one Pset per element.
    for guid, rule_results in collected.items():
        element = model.by_guid(guid)

        #Status: count every rule that did not pass.
        not_passed = sum(1 for result in rule_results.values() if result != "PASS")
        if not_passed == 0:
            status = "PASS"
        else:
            status = f"FAIL ({not_passed} of {len(rule_results)})"

        #Status first, so it is the first line in the viewer. Then the rules.
        properties = {"Status": status}
        properties.update(rule_results)

        #Already checked before (e.g. "Check" clicked twice)? Remove the old PsetCheck first,
        #otherwise the element would get a second one.
        old_psets = ifcopenshell.util.element.get_psets(element)
        if pset_name in old_psets:
            old_pset = model.by_id(old_psets[pset_name]["id"])
            ifcopenshell.api.pset.remove_pset(model, product=element, pset=old_pset)

        new_pset = ifcopenshell.api.pset.add_pset(model, product=element, name=pset_name)
        ifcopenshell.api.pset.edit_pset(model, pset=new_pset, properties=properties)

        #Step 3: paint the element. Its geometry ("representations") gets the red or green style.
        #Replaces the element's previous colour; elements without geometry are skipped.
        if colour and element.Representation:
            style = colour_styles["PASS" if status == "PASS" else "FAIL"]
            for representation in element.Representation.Representations:
                ifcopenshell.api.style.assign_representation_styles(model, shape_representation=representation, styles=[style])

    print(f"PsetCheck written to {len(collected)} elements")
    return len(collected)


#Only runs when you start THIS file directly 
if __name__ == "__main__":
    model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

    checker = Checker(model, "03 Neu")

    ruleset = pd.read_excel("PsetCheck_Rules_Template.xlsx", sheet_name="Rules")

    results = rulecheck(checker, ruleset)

    print(summarize(results))

    savecheck(results, r"C:\Users\mikek\Downloads\Check_Results.xlsx")

    writeback(checker, results)
    checker.model.write(r"C:\Users\mikek\Downloads\25.011_GoBau_checked.ifc")  #new name, never overwrite the original
