# IFC Open Shell Documentation: https://docs.ifcopenshell.org/ifcopenshell-python/hello_world.html
#This is a test 

import ifcopenshell
import pandas as pd
import ifcopenshell.util
import ifcopenshell.util.element

model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

from nicegui import ui

# with ui.dropdown_button('Open me!', auto_close=True):
#     ui.item('Item 1', on_click=lambda: ui.notify('You clicked item 1'))
#     ui.item('Item 2', on_click=lambda: ui.notify('You clicked item 2'))

# ui.run()

dic1 = {"mouse": "hello"}

print(dic1["mouse"])