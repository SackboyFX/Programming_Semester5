import operator

import ifcopenshell
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


def rulecheck(checker, ruleset, output_path="PsetCheck_Report.xlsx"):
    """Runs every rule of the ruleset through the checker and writes ONE Excel report.

    Every rule (= every row of the rules Excel) gets its own sheet.
    The sheet name starts with the Excel row of the rule, e.g. "2 allowed Kostenteiler".
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

    #Write every result table into its own sheet of one Excel file.
    with pd.ExcelWriter(output_path) as writer:
        for sheet_name, df in results.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Report written to {output_path}")
    return results


#Only runs when you start THIS file directly (python checker.py), not when another file imports it.
if __name__ == "__main__":
    model = ifcopenshell.open(r"C:\Users\MikeKhayat\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

    checker = Checker(model, "03 Neu")

    ruleset = pd.read_excel("PsetCheck_Rules_Template.xlsx", sheet_name="Rules")

    print(rulecheck(checker, ruleset))
