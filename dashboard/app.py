import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="A/B Testing Platform", layout="wide")
st.title("A/B Experimentation Platform")

tab1, tab2, tab3 = st.tabs(["Create Experiment", "Live Results", "All Experiments"])

# ── TAB 1: Create ──────────────────────────────────────────────
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
            res = requests.post(f"{API}/experiments", json={
                "name": name, "description": description,
                "metric": metric, "traffic_split": split
            })
            if res.status_code == 200:
                data = res.json()
                st.success(f"Experiment created! ID: `{data['experiment_id']}`")
                st.code(f"""
# Assign a user
POST /assign
{{"user_id": "user_123", "experiment_id": "{data['experiment_id']}"}}

# Log a conversion
POST /events
{{"user_id": "user_123", "experiment_id": "{data['experiment_id']}", "event_type": "{metric}"}}
                """)
            else:
                st.error("Failed to create experiment.")

# ── TAB 2: Live Results ────────────────────────────────────────
with tab2:
    st.subheader("Live Experiment Results")
    
    all_exps = requests.get(f"{API}/experiments").json()
    if not all_exps:
        st.info("No experiments yet. Create one in the first tab.")
        st.stop()
    
    options = {f"{e['name']} ({e['id']})": e['id'] for e in all_exps}
    selected = st.selectbox("Select Experiment", list(options.keys()))
    exp_id = options[selected]

    if exp_id:
        res = requests.get(f"{API}/results/{exp_id}")
        if res.status_code == 200:
            data = res.json()

            if "message" in data:
                st.warning(data["message"])
            else:
                exp = data["experiment"]
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Control rate", f"{data['control_rate']*100:.2f}%")
                col2.metric("Treatment rate", f"{data['treatment_rate']*100:.2f}%",
                           delta=f"{data['relative_lift']:+.1f}% lift")
                col3.metric("p-value", f"{data['p_value']:.4f}")
                col4.metric("Significant", "✅ Yes" if data["is_significant"] else "❌ Not yet")

                # Significance banner
                if data["is_significant"]:
                    st.success(f"{data['recommended_action']}")
                else:
                    st.info(f"{data['recommended_action']}")

                # Conversion rate chart
                counts = data["counts"]
                fig = go.Figure()
                for variant, color in [("control", "#636EFA"), ("treatment", "#EF553B")]:
                    c = counts[variant]
                    rate = c["conversions"] / c["total"] * 100 if c["total"] > 0 else 0
                    fig.add_trace(go.Bar(
                        name=variant.capitalize(),
                        x=[variant.capitalize()],
                        y=[rate],
                        marker_color=color,
                        text=f"{rate:.2f}%<br>{c['conversions']}/{c['total']} users",
                        textposition="outside"
                    ))
                fig.update_layout(
                    title="Conversion Rate: Control vs Treatment",
                    yaxis_title="Conversion Rate (%)",
                    showlegend=False, height=500
                )
                st.plotly_chart(fig, use_container_width=True)

                # Confidence interval chart
                ci = data["confidence_interval"]
                diff = data["treatment_rate"] - data["control_rate"]
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=[ci[0]*100, diff*100, ci[1]*100],
                    y=[0, 0, 0],
                    mode="lines+markers",
                    line=dict(color="#EF553B", width=3),
                    marker=dict(size=[8, 14, 8]),
                    name="95% CI"
                ))
                fig2.add_vline(x=0, line_dash="dash", line_color="gray")
                fig2.update_layout(
                    title="Confidence Interval of Lift",
                    xaxis_title="Difference in conversion rate (%)",
                    height=250, showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)

                # Stop experiment
                if exp["status"] == "running":
                    if st.button("Stop Experiment"):
                        requests.post(f"{API}/experiments/{exp_id}/stop")
                        st.success("Experiment stopped.")
                        st.rerun()
        else:
            st.error("Experiment not found.")

        # Simulate button
        st.divider()
        st.subheader("Demo: Simulate Users")
        st.caption("click to generate experiment data instantly.")
        
        sim_users = st.slider("Number of simulated users", 500, 5000, 2000, step=500)
        control_rate = st.slider("Control conversion rate %", 5, 30, 12)
        treatment_rate = st.slider("Treatment conversion rate %", 5, 30, 18)

        if st.button("▶ Run Simulation"):
            if not exp_id:
                st.error("Enter an experiment ID first.")
            else:
                import random
                progress = st.progress(0, text="Simulating users...")
                for i in range(sim_users):
                    user_id = f"sim_user_{i}"
                    r = requests.post(f"{API}/assign", json={
                        "user_id": user_id, "experiment_id": exp_id
                    })
                    if r.status_code == 200:
                        variant = r.json()["variant"]
                        rate = treatment_rate/100 if variant == "treatment" else control_rate/100
                        if random.random() < rate:
                            requests.post(f"{API}/events", json={
                                "user_id": user_id,
                                "experiment_id": exp_id,
                                "event_type": requests.get(f"{API}/experiments/{exp_id}").json()["metric"]
                            })
                    if i % 100 == 0:
                        progress.progress(i/sim_users, text=f"Simulating users... {i}/{sim_users}")
                progress.progress(1.0, text="Done!")
                st.success(f"Simulated {sim_users} users. Scroll up to see results!")
                st.rerun()

# ── TAB 3: All Experiments ─────────────────────────────────────
with tab3:
    st.subheader("All Experiments")
    res = requests.get(f"{API}/experiments")
    if res.status_code == 200:
        exps = res.json()
        if not exps:
            st.info("No experiments yet.")
        else:
            df = pd.DataFrame(exps)[["id", "name", "metric", "status", "traffic_split", "created_at"]]
            df.columns = ["ID", "Name", "Metric", "Status", "Split", "Created"]
            st.dataframe(df, use_container_width=True)
    else:
        st.error("Could not fetch experiments.")