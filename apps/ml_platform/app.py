import streamlit as st
from streamlit_auth import login_sidebar

st.set_page_config(page_title="ML Platform", layout="wide")
login_sidebar()
st.switch_page("pages/0_Overview.py")
