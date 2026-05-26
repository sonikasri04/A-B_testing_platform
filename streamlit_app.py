import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Point DB to a writable path on Streamlit Cloud
os.environ["DB_PATH"] = "data/ab_platform.db"

# Import core functions directly (no API needed)
from core.database import (
    init_db, create_experiment, log_assignment,
    log_event, get_experiment, get_all_experiments,
    get_experiment_counts, update_experiment_status
)
from core.stats import assign_variant, calculate_results
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import random

init_db()

st.set_page_config(page_title="A/B Testing Platform", layout="wide")
st.title("A/B Experimentation Platform")

tab1, tab2, tab3 = st.tabs(["Create Experiment", "Live Results", "All Experiments"])

with tab1:
    st.subheader("Create New Experiment")
    name = st.text_input("Experiment name", placeholder="e.g. recommender_v2_vs_baseline")
    description = st.text_area("Description", placeholder="What are you testing?")
    metric = st.text_input("Metric to track", placeholder="e.g. click, purchase, play")
    split = st.slider("Traffic split (treatment %)", 0.1, 0.9, 0.5)

    if st.button("Create Experiment"):
        if not name or not metric:
            st.error("Name and metric are required.")
        else:
            exp_id = create_experiment(name, description, metric, split)
            st.success(f"Experiment created! ID: `{exp_id}`")

with tab2:
    st.subheader("Live Experiment Results")
    all_exps = get_all_experiments()
    if not all_exps:
        st.info("No experiments yet. Create one in the first tab.")
    else:
        options = {f"{e['name']} ({e['id']})": e['id'] for e in all_exps}
        selected = st.selectbox("Select Experiment", list(options.keys()))
        exp_id = options[selected]
        exp = get_experiment(exp_id)
        counts = get_experiment_counts(exp_id, exp["metric"])
        c, t = counts["control"], counts["treatment"]

        if c["total"] == 0 or t["total"] == 0:
            st.warning("Not enough data yet — run a simulation below.")
        else:
            result = calculate_results(
                c["conversions"], c["total"],
                t["conversions"], t["total"],
                experiment_id=exp_id
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Control rate", f"{result.control_rate*100:.2f}%")
            col2.metric("Treatment rate", f"{result.treatment_rate*100:.2f}%",
                       delta=f"{result.relative_lift:+.1f}% lift")
            col3.metric("p-value", f"{result.p_value:.4f}")
            col4.metric("Significant", "Yes" if result.is_significant else "Not yet")

            if result.is_significant:
                st.success(f"🎉 {result.recommended_action}")
            else:
                st.info(f"{result.recommended_action}")

            fig = go.Figure()
            for variant, color in [("control", "#636EFA"), ("treatment", "#EF553B")]:
                vc = counts[variant]
                rate = vc["conversions"] / vc["total"] * 100 if vc["total"] > 0 else 0
                fig.add_trace(go.Bar(
                    name=variant.capitalize(), x=[variant.capitalize()], y=[rate],
                    marker_color=color,
                    text=f"{rate:.2f}%<br>{vc['conversions']}/{vc['total']} users",
                    textposition="outside"
                ))
            fig.update_layout(
                title="Conversion Rate: Control vs Treatment",
                yaxis_title="Conversion Rate (%)",
                yaxis=dict(range=[0, 25]),
                showlegend=False, height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            ci = result.confidence_interval
            diff = result.treatment_rate - result.control_rate
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=[ci[0]*100, diff*100, ci[1]*100], y=[0, 0, 0],
                mode="lines+markers",
                line=dict(color="#EF553B", width=3),
                marker=dict(size=[8, 14, 8])
            ))
            fig2.add_vline(x=0, line_dash="dash", line_color="gray")
            fig2.update_layout(
                title="Confidence Interval of Lift",
                xaxis_title="Difference in conversion rate (%)",
                height=250, showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

            if exp["status"] == "running":
                if st.button("Stop Experiment"):
                    update_experiment_status(exp_id, "stopped")
                    st.success("Experiment stopped.")
                    st.rerun()

        st.divider()
        st.subheader("Demo: Simulate Users")
        sim_users = st.slider("Number of simulated users", 500, 5000, 2000, step=500)
        control_rate_sim = st.slider("Control conversion rate %", 5, 30, 12)
        treatment_rate_sim = st.slider("Treatment conversion rate %", 5, 30, 18)

        if st.button("Run Simulation"):
            progress = st.progress(0, text="Simulating users...")
            for i in range(sim_users):
                user_id = f"sim_user_{i}"
                variant = assign_variant(user_id, exp_id, exp["traffic_split"])
                log_assignment(user_id, exp_id, variant)
                rate = treatment_rate_sim/100 if variant == "treatment" else control_rate_sim/100
                if random.random() < rate:
                    log_event(user_id, exp_id, variant, exp["metric"])
                if i % 100 == 0:
                    progress.progress(i/sim_users, text=f"Simulating... {i}/{sim_users}")
            progress.progress(1.0, text="Done!")
            st.success(f"Simulated {sim_users} users!")
            st.rerun()

with tab3:
    st.subheader("All Experiments")
    exps = get_all_experiments()
    if not exps:
        st.info("No experiments yet.")
    else:
        df = pd.DataFrame(exps)[["id", "name", "metric", "status", "traffic_split", "created_at"]]
        df.columns = ["ID", "Name", "Metric", "Status", "Split", "Created"]
        st.dataframe(df, use_container_width=True)