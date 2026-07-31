import streamlit as st
from modules.secure_personal_vault import *

# Execute/render the module UI
if __name__ == "__main__":
    if "main" in dir():
        main()
    elif "render" in dir():
        render()
    elif "show" in dir():
        show()
