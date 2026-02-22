import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.title("Water System Simulation")

st.write(
    """
    This is a simple simulation of the water system. 
    The simulation is not perfect and uses assupmtions and simplifications, 
    but it should give a rough idea of how the system works and how the different components interact with each other. 
    Adjust the settings below and hit run to see the results.
    """
)

#Simulation Settings
st.header("Simulation Settings")
sim_length = st.number_input("Simulation Length (hours)", min_value=1, value=48)
step_minutes = st.number_input("Step length (minutes)", min_value=1, value=10)
steps = int(sim_length * 60 / step_minutes)
start_hour = st.number_input("Start time (hour 0-23)", min_value=0, max_value=23, value=6)

#Town Water System
st.header("Town Water System Settings")
town_capacity = st.number_input("Town water Tank capacity", min_value=0, value=10000)
town_inflow = st.number_input("Town water flow rate (L/h)", min_value = 0, value = 2400)
town_on_pct = st.slider("Town tank ON threshold (%)", 0, 100, 10) /100
town_off_pct = st.slider("Town tank OFF threshold (%)", 0, 100, 80) /100
town_low_alarm_timer = st.number_input("Town Low Alarm Timer (min)", min_value = 0, value = 60) / step_minutes
town_low_alarm_timestamp = 0
town_low_alarm_active = False
town_column_on = False

if town_on_pct > town_off_pct:
    town_off_pct, town_on_pct = town_on_pct, town_off_pct

town_on_level = int(town_capacity * town_on_pct)
town_off_level = int(town_capacity * town_off_pct)
town_inflow_step = town_inflow * step_minutes / 60

town_level = int(town_capacity * town_off_pct)
if town_level <= town_on_level:
    town_column_on = True
else:
    town_column_on = False

#Soft Water System
st.header("Soft Water Settings")
soft_capacity = st.number_input("Tank capacity", min_value=0, value = 25000)
softener_regen_threshold = st.number_input("Softener regen threshold (L)", 0, value = 16000)
soft_inflow = st.number_input("Soft water flow rate (L/h)", min_value = 0, value = 4200)
soft_on_pct = st.slider("ON threshold (%)", 0, 100, 60) / 100
soft_off_pct = st.slider("OFF threshold (%)", 0, 100, 80) / 100

if soft_on_pct > soft_off_pct:
    soft_on_pct, soft_off_pct = soft_off_pct, soft_on_pct

soft_on_level = soft_capacity * soft_on_pct
soft_off_level = soft_capacity * soft_off_pct
soft_inflow_step = soft_inflow * step_minutes / 60
soft_column_on = False

soft_level = int(soft_capacity * soft_off_pct)
if soft_level <= soft_on_level:
    soft_column_on = True
else:
    soft_column_on = False

soft_regen = False
total_regens = 0


#RO Water System
st.header("RO System Settings")
ro_capacity = st.number_input("RO tank capacity", min_value=0, value=5500)
ro_low_limit = st.number_input("Low limit", min_value=0, value=1000)
ro_start_level = st.number_input("Start RO level", min_value=0, value=4670, max_value=ro_capacity)
ro_permeate_flow = st.number_input("Permeate flow (L/h)", min_value=0, value=600)
ro_recovery_ptc = st.slider("Recovery rate (%)", min_value=0, max_value=100, value=50) / 100
ro_soft_usage = ro_permeate_flow / ro_recovery_ptc

ro_on_pct = st.slider("ON threshold (%)", 0, 100, 75) / 100
ro_off_pct = st.slider("OFF threshold (%)", 0, 100, 85) / 100
start_ro_plant_on = st.checkbox("Start RO plant ON?", value=True)

st.subheader("RO Usage Settings")

usage_df = pd.DataFrame(
    [
        {"Category": "Saws",        "RO Usage (L/h)" : 480,       "Start Time (h)": 6,    "Finish Time (h)": 20},
        {"Category": "Cleaning",    "RO Usage (L/h)" : 120,       "Start Time (h)": 20,   "Finish Time (h)": 21},
        {"Category": "Other",       "RO Usage (L/h)" : 360,       "Start Time (h)": 6,    "Finish Time (h)": 9},
    ]
)

st.write("Double-Click in the table below to Input the usages for each category in L/h, and the hours during which they occur.")
edited_df = st.data_editor(usage_df)

# allow a small random variation in the hourly usage
random_pct = st.slider("Usage random variation (%)", 0, 100, 20, step = 5) / 100


# Ensure thresholds are consistent
if ro_on_pct > ro_off_pct:
    ro_on_pct, ro_off_pct = ro_off_pct, ro_on_pct

ro_on_level = ro_capacity * ro_on_pct
ro_off_level = ro_capacity * ro_off_pct

ro_permeate_step = ro_permeate_flow * step_minutes / 60
ro_soft_usage_step = ro_soft_usage * step_minutes / 60

# initial plant state based on thresholds
ro_level = ro_start_level
if ro_level <= ro_on_level:
    ro_plant_on = True
elif ro_level >= ro_off_level:
    ro_plant_on = False
else:
    ro_plant_on = start_ro_plant_on

# Simulation state variables
town_total_made = 0
soft_total_made = 0
soft_total_salt_used = 0
ro_total_made = 0
ro_total_waste = 0

times = []
hours = []

town_levels = []
town_total_mades = []
town_column_states = []
town_capacity_limits = []

soft_levels = []
soft_column_states = []
soft_total_mades = []
soft_capacity_limits = []
soft_regens = []

ro_levels = []
ro_low_limits = []
ro_plant_states = []
ro_capacity_limits = []

town_inflows = []
soft_inflows = []
ro_inflows = []
outflows = []

test = []

current_time = datetime(2026, 1, 1, start_hour, 0)  # arbitrary start date

last_usage_hour = None
hour_multiplier = 1.0

for step in range(steps):
    
    if town_column_on:
        town_inflow_applied = town_inflow_step
        town_level += town_inflow_applied
        
        
        town_total_made += town_inflow_applied
    else:
        town_inflow_applied = 0
    
    if soft_column_on:
        soft_inflow_applied = min(soft_inflow_step, town_level)
        town_level -= soft_inflow_applied
        soft_level += soft_inflow_applied
        soft_total_made += soft_inflow_applied
    else:
        soft_inflow_applied = 0
    
    if soft_total_made // softener_regen_threshold > total_regens and not soft_regen:
        soft_regen = True
        soft_total_salt_used += 6.8  # arbitrary salt usage per regen
        total_regens += 1
    else:
        soft_regen = False
    
    soft_regens.append(soft_regen)

    if ro_plant_on:
        ro_soft_applied = min(ro_soft_usage_step, soft_level)
        soft_level -= ro_soft_applied
        
        ro_permeate_applied = ro_soft_applied * ro_recovery_ptc
        ro_level += ro_permeate_applied

        ro_total_made += ro_permeate_applied
        ro_total_waste += ro_soft_applied * (1 - ro_recovery_ptc)
    else:
        ro_permeate_applied = 0

    # Usage calculation
    hour = current_time.hour

    # if moved into a new hour, pick new random multiplier
    if hour != last_usage_hour:
        hour_multiplier = 1 + np.random.uniform(-random_pct, random_pct)
        last_usage_hour = hour

    mask = (
        (usage_df["Start Time (h)"] <= hour) &
        (hour < usage_df["Finish Time (h)"])
    )
    total_usage_this_hour = usage_df.loc[mask, "RO Usage (L/h)"].sum()
    total_usage_this_hour *= hour_multiplier

    # convert to per step volume
    usage_volume = total_usage_this_hour * step_minutes / 60
    
    ro_level -= usage_volume
     
    ro_level = max(0, min(ro_level, ro_capacity))  # clamp

    # save outputs
    times.append(current_time)
    hours.append(step_minutes * step / 60)

    town_levels.append(town_level)
    soft_levels.append(soft_level)
    ro_levels.append(ro_level)
    
    town_capacity_limits.append(town_capacity)
    soft_capacity_limits.append(soft_capacity)
    ro_capacity_limits.append(ro_capacity)
    ro_low_limits.append(ro_low_limit)
    
    town_inflows.append(town_inflow_applied)
    soft_inflows.append(soft_inflow_applied)
    ro_inflows.append(ro_permeate_applied)
    
    outflows.append(usage_volume)
    
    town_column_states.append(town_column_on)
    soft_column_states.append(soft_column_on)
    ro_plant_states.append(ro_plant_on)

    # advance time
    current_time += timedelta(minutes=step_minutes)

    # hysteresis logic
    if town_low_alarm_active and town_low_alarm_timestamp + town_low_alarm_timer > step:
        town_low_alarm_active = False

    if town_column_on and town_level >= town_off_level:
        town_column_on = False
    elif not town_column_on and town_level <= town_on_level:
        town_column_on = True
        town_low_alarm_active = True
        town_low_alarm_timestamp = step

    town_tank_empty = town_level <= 0

    if town_tank_empty or soft_column_on and soft_level >= soft_off_level:
        soft_column_on = False
    elif not town_tank_empty and soft_level <= soft_on_level and not town_low_alarm_active:
        soft_column_on = True

    if ro_plant_on and ro_level >= ro_off_level:
        ro_plant_on = False
    elif soft_level > 0 and ro_level <= ro_on_level:
        ro_plant_on = True


df = pd.DataFrame({
    "Time": times,
    "Hour": hours,
    "Steps": steps,
    "townTankLevel": town_levels,
    "softTankLevel": soft_levels,
    "softRegens": soft_regens,
    "roTankLevel": ro_levels,
    "townCapacity": town_capacity_limits,
    "softCapacity": soft_capacity_limits,
    "roCapacity": ro_capacity_limits,
    "RoLowLimit": ro_low_limits,
    "townInflowApplied" : town_inflows,
    "softInflowApplied" : soft_inflows,
    "roInflowApplied": ro_inflows,
    "RoOutflow": outflows,
    "PlantOn": ["ON" if x else "OFF" for x in ro_plant_states]
})

#Charts

st.header("Simulation Results")

st.subheader("RO Outflow (Usage)")
st.line_chart(df, x="Hour", y="RoOutflow", y_label="Liters per Hour", height=500)

st.subheader("RO Tank Levels")
st.line_chart(df, x="Hour", y=["roTankLevel", "RoLowLimit", "roCapacity"], height=500)

st.subheader("Soft Tank Level")
st.line_chart(df, x="Hour", y=["softTankLevel", "softCapacity"], height=500)

st.subheader("Town Tank Level")
st.line_chart(df, x="Hour", y=["townTankLevel", "townCapacity"], height=500)

st.subheader("RO Plant ON/OFF Status")
st.line_chart({
    "Status" : [1 if x else 0 for x in ro_plant_states],
    "Level" : [x / ro_capacity for x in ro_levels]
})

st.subheader("Soft Column Status")
st.line_chart({
    "Column State" : [1 if x else 0 for x in soft_column_states],
    "Level" : [x / soft_capacity for x in soft_levels],
    "Regen" : [1 if x else 0 for x in soft_regens]
})

st.subheader("Town Column Status")
st.line_chart({
    "Column State" : [1 if x else 0 for x in town_column_states],
    "Level" : [x / town_capacity for x in town_levels]
})

df2 = pd.DataFrame({
    "Total RO Made": [ro_total_made],
    "Total RO Waste": [ro_total_waste],
    "Total Soft Used": [ro_total_waste + ro_total_made],
    "Total Soft Made": [soft_total_made],
    "Total Town Made": [town_total_made],
    "Total Salt Used": [soft_total_salt_used]
})

st.write("Show Total Made/Waste Table")
st.table(df2)

# Optional: show table
if st.checkbox("Show Data Table"):
    st.dataframe(df)
