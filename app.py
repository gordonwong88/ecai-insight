import streamlit as st

st.set_page_config(
    page_title="EC-AI Insight v7",
    layout="wide"
)

st.title("EC-AI Insight v7")
st.subheader("AI Business Intelligence Workspace")

st.markdown("### AI Generated Key Insights")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("🚀 **Revenue Concentration**")
    st.write("Revenue heavily concentrated in Causeway Bay.")
    st.write("**Evidence:** HK$86.4K (~50%)")

with col2:
    st.markdown("📊 **Category Momentum**")
    st.write("Outerwear and Activewear driving category growth.")
    st.write("**Evidence:** HK$69.6K revenue")

with col3:
    st.markdown("⚠️ **Margin Observation**")
    st.write("Accessories margin declining week-over-week.")
    st.write("**Evidence:** -3.2pp margin change")

st.markdown("---")

st.markdown("### Executive Dashboard")
st.info("Charts will appear here when dataset is loaded.")

st.markdown("---")

st.markdown("### Ask EC-AI")

question = st.text_input("Ask a business question")

if question:
    st.write("**AI Response (demo):**")
    st.write(
        "Based on current sales distribution, consider diversifying promotions "
        "to stores beyond Causeway Bay to reduce revenue concentration risk."
    )
