from __future__ import annotations

import json

import requests
import streamlit as st


st.set_page_config(page_title="Due Diligence Agent", layout="wide")
st.title("Enterprise AI Due Diligence Agent")

api_base = st.text_input("API Base URL", value="http://localhost:8000")
company = st.text_input("Company", value="Stripe")
focus = st.text_input("Focus (comma separated)", value="pricing, competitors")
depth = st.selectbox("Depth", ["quick", "standard", "deep"], index=1)
use_memory = st.checkbox("Use Memory", value=True)

if st.button("Run Research"):
    payload = {
        "company": company,
        "focus": [x.strip() for x in focus.split(",") if x.strip()],
        "depth": depth,
        "use_memory": use_memory,
    }
    with st.spinner("Generating report..."):
        resp = requests.post(f"{api_base}/research", json=payload, timeout=180)
        if resp.status_code >= 400:
            st.error(resp.text)
        else:
            data = resp.json()
            st.subheader("Executive Summary")
            st.write(data.get("executive_summary", ""))
            for sec in data.get("sections", []):
                st.markdown(f"### {sec['title']}")
                st.markdown(sec["content"])
                with st.expander("Citations"):
                    st.code(json.dumps(sec.get("citations", []), indent=2), language="json")
