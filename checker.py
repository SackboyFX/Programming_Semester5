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

    def check_allowed(self, pset: str, property: str, allowed_values: set):
        """PASS if the property value is in allowed_values."""
        results = []

        for i in self.elements:
            value, error = self._get_value(i, pset, property)

            if error:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: error, "Check": error})
            elif value in allowed_values:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Check": "FAIL"})

        return pd.DataFrame(results)

    def check_type(self, pset: str, property: str, data_type: type):
        """PASS if the property value has the expected data type (e.g. float, str)."""
        results = []

        for i in self.elements:
            value, error = self._get_value(i, pset, property)

            if error:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: error, "Data Type": "N/A", "Check": error})
            elif isinstance(value, data_type):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Data Type": data_type.__name__, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Data Type": data_type.__name__, "Check": "FAIL"})

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
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: error, "Check": error})
                continue

            #Check if the value is a number. Text or None would crash the comparison or give wrong results.
            #bool is excluded on purpose: True/False count as 1/0, so True > 0 would pass.
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Check": "Not a number"})
            elif compare(value, compare_value):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Check": "PASS"})
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: value, "Check": "FAIL"})

        return pd.DataFrame(results)


#Only runs when you start THIS file directly (python checker.py), not when another file imports it.
if __name__ == "__main__":
    model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

    checker = Checker(model, "03 Neu")
    print(f"{len(checker.elements)} elements found")

    kostenteilerset = {"WWZ-WV:100%", "ZUG:100%", "WWZ-EW:100%"}

    print(checker.check_allowed("GoBau_Ausschreibung", "Kostenteiler", kostenteilerset))
    print(checker.check_type("GoBau_Menge", "Volumen (m3)", float))
    print(checker.check_range("GoBau_Menge", "Volumen (m3)", ">", 0))
