import ifcopenshell
import pandas as pd
import ifcopenshell.util
import ifcopenshell.util.element


class ifcmodel:
    def __init__(self, data: bytes):
        self.model = ifcopenshell.file.from_string(data.decode())       # decoding the bytes to a string and opening it directly from memory
        # state["model"] = model    
        # print("A file arrived:", document.file.name)



