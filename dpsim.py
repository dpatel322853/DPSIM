
import streamlit as st
import pandas as pd
import numpy as np
import json, math, io
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from thermo_engine import CubicEOS, tp_flash, ternary_grid, ternary_xy
import steam_if97 as steam

st.set_page_config(page_title="DPSIM", page_icon="🔬", layout="wide")
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode=True
if "hist" not in st.session_state:
    st.session_state.hist=[]

P2K = {"Pa":0.001,"kPa":1.0,"MPa":1000.0,"bar":100.0,"mbar":0.1,"psi":6.89476,"atm":101.325,"mmHg":0.13332,"inH2O":0.24909,"kg/cm2":98.0665,"barg":100.0,"psig":6.89476,"kPag":1.0}
D2K = {"kg/m3":1.0,"g/cm3":1000.0,"kg/L":1000.0,"lb/ft3":16.02,"lb/gal":119.83}
MU2PAS = {"Pa.s":1.0,"cP":0.001,"mPa.s":0.001,"Poise":0.1}

NPS_DATA = {
"1/2":(21.3,{10:2.11,40:2.77,80:3.73,160:4.78}),"3/4":(26.7,{10:2.11,40:2.87,80:3.91,160:5.56}),"1":(33.4,{10:2.77,40:3.38,80:4.55,160:6.35}),"1.5":(48.3,{10:2.77,40:3.68,80:5.08,160:7.14}),"2":(60.3,{10:2.77,40:3.91,80:5.54,160:8.74}),"3":(88.9,{10:3.05,40:5.49,80:7.62,160:11.13}),"4":(114.3,{10:3.05,40:6.02,80:8.56,160:13.49}),"6":(168.3,{10:3.40,40:7.11,80:10.97,160:18.26}),"8":(219.1,{10:3.76,40:8.18,80:12.70,160:23.01}),"10":(273.1,{10:4.19,40:9.27,80:15.09,160:28.58}),"12":(323.9,{10:4.57,40:10.31,80:17.48,160:33.32}),"16":(406.4,{10:4.78,40:12.70,80:21.44,160:40.49}),"20":(508.0,{10:5.54,40:15.09,80:26.19,160:50.01}),"24":(609.6,{10:6.35,40:17.48,80:30.96,160:59.54})
}

COMP = json.load(open("components.json", encoding="utf-8"))
NAMES = list(COMP.keys())

def to_c(v,u):
    if u == "deg F": return (v-32.0)*5.0/9.0
    if u == "K": return v-273.15
    if u == "deg R": return (v-491.67)*5.0/9.0
    return v

def from_c(c,u):
    if u == "deg F": return c*9.0/5.0+32.0
    if u == "K": return c+273.15
    if u == "deg R": return (c+273.15)*9.0/5.0
    return c

def to_k(v,u): return to_c(v,u)+273.15

def p_kpa(v,u): return v*P2K[u]

def css(dark=True):
    bg = "#0f172a" if dark else "#f5f7fa"
    side = "#020617" if dark else "#1e293b"
    txt = "#e5e7eb" if dark else "#0f172a"
    card = "#111827" if dark else "#ffffff"
    inp = "#111827" if dark else "#ffffff"
    return f"""
<style>
#MainMenu, footer, header {{visibility:hidden;}}
.stApp {{background:{bg}; color:{txt};}}
[data-testid="stSidebar"] {{background:{side};}}
h1,h2,h3,h4,p,label,span,div {{color:{txt};}}
.rc {{background:linear-gradient(135deg,#0ea5e9,#2563eb); padding:18px; border-radius:18px; color:white; box-shadow:0 8px 24px #0005; margin:8px 0;}}
.gc {{background:linear-gradient(135deg,#059669,#047857); padding:18px; border-radius:18px; color:white; box-shadow:0 8px 24px #0005; margin:8px 0;}}
.bad {{background:linear-gradient(135deg,#ef4444,#991b1b); padding:18px; border-radius:18px; color:white; box-shadow:0 8px 24px #0005;}}
.mt {{background:{card}; padding:14px; border-radius:16px; box-shadow:0 6px 18px #0004; text-align:center; margin:5px;}}
.big {{font-size:26px; font-weight:800;}}
.lab {{font-size:12px; opacity:.82;}}
.hi {{background:#1e293b; border-left:4px solid #0ea5e9; padding:8px; border-radius:8px; margin:4px 0; font-size:12px;}}
input, textarea, .stSelectbox div[data-baseweb="select"]>div {{background:{inp}; color:{txt}; border-color:#334155;}}
</style>
"""

def metric(label, value):
    st.markdown(f'<div class="mt"><div class="big">{value}</div><div class="lab">{label}</div></div>', unsafe_allow_html=True)

def result_card(title, value, green=False, bad=False):
    cls = "bad" if bad else ("gc" if green else "rc")
    st.markdown(f'<div class="{cls}"><b>{title}</b><br><span style="font-size:24px">{value}</span></div>', unsafe_allow_html=True)

def valve_size(cv):
    sizes=[(5,'1/2 in'),(12,'1 in'),(25,'1.5 in'),(50,'2 in'),(110,'3 in'),(190,'4 in'),(400,'6 in'),(700,'8 in'),(1200,'10 in'),(1800,'12 in')]
    for cap, size in sizes:
        if cv <= cap: return size
    return "12 in+"

def make_pdf(title, lines):
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf); styles=getSampleStyleSheet(); story=[Paragraph(title, styles['Title']), Spacer(1,12)]
    for line in lines: story.append(Paragraph(str(line), styles['Normal']))
    doc.build(story); return buf.getvalue()

def dark_plot():
    if st.session_state.dark_mode:
        plt.style.use("dark_background")
    else:
        plt.style.use("default")

st.markdown(css(st.session_state.dark_mode), unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 DPSIM")
    st.caption("DP's Process Simulation & Engineering Toolkit")
    prec = st.slider("Decimal precision", 2, 8, 4, key="sb_prec")
    dm = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="sb_dark_toggle")
    if dm != st.session_state.dark_mode:
        st.session_state.dark_mode = dm
        st.rerun()
    eos_name = st.selectbox("EOS selector", ["Peng-Robinson","SRK","van der Waals","User-Defined"], key="sb_eos")
    custom = {}
    if eos_name == "User-Defined":
        custom["Omega_a"] = st.number_input("Omega_a", value=0.45724, key="sb_ud_oa")
        custom["Omega_b"] = st.number_input("Omega_b", value=0.07780, key="sb_ud_ob")
        custom["delta_1"] = st.number_input("delta_1", value=float(1+np.sqrt(2)), key="sb_ud_d1")
        custom["delta_2"] = st.number_input("delta_2", value=float(1-np.sqrt(2)), key="sb_ud_d2")
        custom["c0"] = st.number_input("kappa c0", value=0.37464, key="sb_ud_c0")
        custom["c1"] = st.number_input("kappa c1", value=1.54226, key="sb_ud_c1")
        custom["c2"] = st.number_input("kappa c2", value=-0.26992, key="sb_ud_c2")
    st.subheader("Recent conversions")
    for h in st.session_state.hist[-10:][::-1]:
        st.markdown(f'<div class="hi">{h}</div>', unsafe_allow_html=True)

eos = CubicEOS({"Peng-Robinson":"PR","SRK":"SRK","van der Waals":"van der Waals","User-Defined":"User-Defined"}[eos_name], custom)

t1,t2,t3,t4 = st.tabs(["Unit Conversion","Sizing","Property Estimation","Steam Table"])

with t1:
    cat = st.selectbox("Select property category", ["Temperature","Pressure","Length","Mass","Volume","Area","Energy","Power","Density","Dynamic Viscosity","Kinematic Viscosity","Velocity","Force","HTC","Gas Flow (Std/Norm)"], key="uc_cat")
    units = {"Pressure":P2K,"Length":{"m":1,"cm":0.01,"mm":0.001,"in":0.0254,"ft":0.3048},"Mass":{"kg":1,"g":0.001,"lb":0.453592},"Volume":{"m3":1,"L":0.001,"ft3":0.0283168,"gal US":0.00378541},"Area":{"m2":1,"cm2":1e-4,"ft2":0.092903},"Energy":{"J":1,"kJ":1000,"kcal":4184,"BTU":1055.06},"Power":{"W":1,"kW":1000,"hp":745.7},"Density":D2K,"Dynamic Viscosity":MU2PAS,"Kinematic Viscosity":{"m2/s":1,"cSt":1e-6},"Velocity":{"m/s":1,"ft/s":0.3048,"km/h":0.277778},"Force":{"N":1,"lbf":4.44822},"HTC":{"W/m2-K":1,"BTU/h-ft2-F":5.678}}
    if cat == "Gas Flow (Std/Norm)":
        mode = st.radio("Mode", ["Std/Normal to Std/Normal","Actual to Reference"], key="uc_gf_mode")
        c1,c2,c3 = st.columns(3)
        q = c1.number_input("Flow", value=1000.0, key="uc_gf_q")
        fu = c2.selectbox("From unit", ["Nm3/h","Nm3/min","Nm3/day","Sm3/h","Sm3/day","SCFM","SCFH","MMSCFD"], key="uc_gf_fu")
        tu = c3.selectbox("To unit", ["Nm3/h","Nm3/min","Nm3/day","Sm3/h","Sm3/day","SCFM","SCFH","MMSCFD"], key="uc_gf_tu")
        fac = {"Nm3/h":1,"Nm3/min":60,"Nm3/day":1/24,"Sm3/h":1,"Sm3/day":1/24,"SCFM":1.699,"SCFH":0.0283168,"MMSCFD":1177.17}
        res = q*fac[fu]/fac[tu]
        if mode == "Actual to Reference":
            a,b,c = st.columns(3)
            T = a.number_input("Actual Temperature", value=25.0, key="uc_gf_T")
            Tu = a.selectbox("Temperature Unit", ["deg C","deg F","K"], key="uc_gf_Tu")
            P = b.number_input("Actual Pressure", value=101.325, key="uc_gf_P")
            Pu = b.selectbox("Pressure Unit", list(P2K), key="uc_gf_Pu")
            Z = c.number_input("Compressibility Z", value=1.0, min_value=0.01, key="uc_gf_Z")
            res = q*(p_kpa(P,Pu)/101.325)*(273.15/to_k(T,Tu))/Z
        result_card("Gas Flow Result", f"{res:.{prec}f} {tu}", green=True)
    elif cat == "Temperature":
        c1,c2,c3 = st.columns(3)
        val = c1.number_input("Value", value=25.0, key="uc_t_val")
        fu = c2.selectbox("From", ["deg C","deg F","K","deg R"], key="uc_t_fu")
        tu = c3.selectbox("To", ["deg C","deg F","K","deg R"], key="uc_t_tu")
        res = from_c(to_c(val,fu),tu)
        result_card("Temperature Result", f"{val:g} {fu} = {res:.{prec}f} {tu}")
    else:
        m = units[cat]
        c1,c2,c3,c4 = st.columns([2,1,1,1])
        val = c1.number_input("Value", value=1.0, key=f"uc_val_{cat}")
        fu = c2.selectbox("From", list(m), key=f"uc_fu_{cat}")
        tu = c3.selectbox("To", list(m), key=f"uc_tu_{cat}")
        if c4.button("Swap", key=f"uc_swap_{cat}"):
            fu, tu = tu, fu
        res = val*m[fu]/m[tu]
        result_card("Conversion Result", f"{val:g} {fu} = {res:.{prec}f} {tu}")
        st.session_state.hist = (st.session_state.hist + [f"{val:g} {fu} → {res:.{prec}f} {tu}"])[-10:]
        with st.expander("Full Conversion Table"):
            st.dataframe(pd.DataFrame({"Unit":list(m.keys()),"Value":[val*m[fu]/m[u] for u in m]}), use_container_width=True)
        with st.expander("Batch Conversion"):
            s = st.text_input("Comma-separated values", "1,2,3", key=f"uc_batch_{cat}")
            vals = [float(x.strip()) for x in s.split(',') if x.strip()]
            st.write([v*m[fu]/m[tu] for v in vals])

with t2:
    tool = st.selectbox("Select sizing tool", ["Control Valve (Cv)","Orifice Plate (ISO 5167)","Relief Valve (API 520/526)","Line Sizing (Velocity & dP)","Pipe Data & Rating"], key="sz_tool")
    if tool == "Control Valve (Cv)":
        mode = st.radio("Service", ["Liquid","Gas/Vapor"], key="sz_cv_mode")
        if mode == "Liquid":
            c1,c2,c3 = st.columns(3)
            Q = c1.number_input("Flow Q (US GPM)", value=100.0, key="sz_cv_lq")
            P1 = c2.number_input("P1", value=100.0, key="sz_cv_lp1"); u1 = c2.selectbox("P1 unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_lu1")
            P2 = c3.number_input("P2", value=50.0, key="sz_cv_lp2"); u2 = c3.selectbox("P2 unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_lu2")
            Gf = st.number_input("Specific gravity Gf", value=1.0, key="sz_cv_lg")
            dp_psi = max((p_kpa(P1,u1)-p_kpa(P2,u2))/6.89476, 1e-9)
            cv = Q*math.sqrt(Gf/dp_psi)
            a,b,c = st.columns(3); a.metric("Cv", f"{cv:.{prec}f}"); b.metric("dP psi", f"{dp_psi:.2f}"); c.metric("Recommended size", valve_size(cv))
        else:
            gases={"Air":(28.97,1.4,1),"N2":(28.014,1.4,1),"O2":(32,1.4,1),"H2":(2.016,1.41,1),"CH4":(16.043,1.31,1),"C2H6":(30.07,1.19,1),"C2H4":(28.054,1.24,1),"C3H8":(44.097,1.13,1),"CO2":(44.01,1.29,1),"Steam":(18.015,1.3,1),"NH3":(17.031,1.31,1),"Natural Gas":(18,1.27,.9),"H2S":(34.08,1.32,1),"Custom":(28,1.3,1)}
            g = st.selectbox("Gas", list(gases), key="sz_cv_gas")
            W = st.number_input("W (lb/h)", value=10000.0, key="sz_cv_gw")
            P1 = st.number_input("P1 (psia)", value=150.0, key="sz_cv_gp1")
            P2 = st.number_input("P2 (psia)", value=100.0, key="sz_cv_gp2")
            T = st.number_input("Temperature", value=80.0, key="sz_cv_gt"); Tu = st.selectbox("Temperature unit", ["deg F","deg C","K"], key="sz_cv_gtu")
            xT = st.number_input("xT", value=0.70, help="Globe approx 0.70, Ball approx 0.55, Butterfly approx 0.35", key="sz_cv_xT")
            M,k,Zd = gases[g]
            Zo = st.number_input("Z override (0 = use gas default)", value=0.0, key="sz_cv_Zo")
            Z = Zd if Zo == 0 else Zo
            TabsR = to_k(T,Tu)*9/5
            Fk = k/1.4
            x = max((P1-P2)/P1, 0.0)
            xe = min(x, Fk*xT)
            Y = max(2/3, 1-x/(3*Fk*xT))
            cv = W/(63.3*Y*math.sqrt(max(xe*P1*M/(TabsR*Z),1e-12)))
            c1,c2,c3,c4 = st.columns(4); c1.metric("Cv", f"{cv:.2f}"); c2.metric("Y", f"{Y:.3f}"); c3.metric("Fk", f"{Fk:.3f}"); c4.metric("Regime", "Choked" if x >= Fk*xT else "Subcritical")
            st.info(f"Recommended valve size: {valve_size(cv)}")
    elif tool == "Orifice Plate (ISO 5167)":
        mode = st.radio("Fluid", ["Liquid","Gas"], key="sz_or_mode")
        c1,c2,c3 = st.columns(3)
        d = c1.number_input("Bore d (mm)", value=50.0, key="sz_or_d")/1000
        D = c2.number_input("Pipe ID D (mm)", value=100.0, key="sz_or_D")/1000
        dp = p_kpa(c3.number_input("dP", value=10.0, key="sz_or_dp"), c3.selectbox("dP unit", ["kPa","bar","psi","MPa"], key="sz_or_dpu"))*1000
        rho = st.number_input("Density (kg/m3)", value=1000.0, key="sz_or_rho")
        mu = st.number_input("Viscosity", value=1.0, key="sz_or_mu")*MU2PAS[st.selectbox("Viscosity unit", list(MU2PAS), key="sz_or_muu")]
        beta = d/D; Cd = 0.5961 + 0.0261*beta**2 - 0.216*beta**8; eps = 1.0
        if mode == "Gas":
            k = st.number_input("k Cp/Cv", value=1.4, key="sz_or_k")
            P1 = p_kpa(st.number_input("Upstream P1", value=500.0, key="sz_or_p1"), st.selectbox("P1 unit", ["kPa","bar","psi","MPa"], key="sz_or_p1u"))*1000
            eps = max(0.75, 1-(0.351+0.256*beta**4+0.93*beta**8)*(dp/P1)/k)
        Q = Cd*eps*(math.pi*d*d/4)*math.sqrt(max(2*dp/(rho*(1-beta**4)),0))
        vel = Q/(math.pi*D*D/4); Re = rho*vel*D/max(mu,1e-12)
        c1,c2,c3,c4 = st.columns(4); c1.metric("Q m3/h", f"{Q*3600:.2f}"); c2.metric("W kg/h", f"{Q*rho*3600:.1f}"); c3.metric("Beta", f"{beta:.3f}"); c4.metric("Cd / Re", f"{Cd:.4f} / {Re:.1e}")
    elif tool == "Relief Valve (API 520/526)":
        api={"D":71,"E":126,"F":198,"G":325,"H":506,"J":830,"K":1186,"L":1841,"M":2323,"N":2800,"P":4116,"Q":7126,"R":10323,"T":16774}
        mode = st.radio("Mode", ["Vapor","Liquid"], key="sz_rv_mode")
        if mode == "Vapor":
            W = st.number_input("W (kg/h)", value=10000.0, key="sz_rv_W")
            P = p_kpa(st.number_input("Relieving pressure P1", value=10.0, key="sz_rv_P"), st.selectbox("Pressure unit", ["bar","kPa","MPa","psi"], key="sz_rv_Pu"))
            T = to_k(st.number_input("Temperature", value=100.0, key="sz_rv_T"), st.selectbox("Temperature unit", ["deg C","deg F","K"], key="sz_rv_Tu"))
            M = st.number_input("MW", value=28.0, key="sz_rv_M"); k = st.number_input("k", value=1.4, key="sz_rv_k"); Z = st.number_input("Z", value=1.0, key="sz_rv_Z")
            Kd = st.number_input("Kd", value=0.975, key="sz_rv_Kd"); Kb = st.number_input("Kb", value=1.0, key="sz_rv_Kb"); Kc = st.number_input("Kc", value=1.0, key="sz_rv_Kc")
            C = 520*math.sqrt(k*(2/(k+1))**((k+1)/(k-1)))
            A = 13160*W/(C*Kd*Kb*Kc*max(P,1e-9))*math.sqrt(T*Z/M)
        else:
            Q = st.number_input("Q (m3/h)", value=100.0, key="sz_rv_Q")
            dp = p_kpa(st.number_input("dP", value=5.0, key="sz_rv_dp"), st.selectbox("dP unit", ["bar","kPa","MPa","psi"], key="sz_rv_dpu"))
            rho = st.number_input("Density kg/m3", value=1000.0, key="sz_rv_rho")
            Kd = st.number_input("Kd", value=0.65, key="sz_rv_lKd"); Kw = st.number_input("Kw", value=1.0, key="sz_rv_Kw"); Kv = st.number_input("Kv", value=1.0, key="sz_rv_Kv"); Kc = st.number_input("Kc", value=1.0, key="sz_rv_lKc")
            A = Q*1000/(38*Kd*Kw*Kv*Kc*math.sqrt(max(dp/rho,1e-12)))
        rec = next((k for k,v in api.items() if A <= v), "T+")
        result_card("Required Area / API 526", f"{A:.1f} mm² → Orifice {rec}")
    elif tool == "Line Sizing (Velocity & dP)":
        c1,c2,c3 = st.columns(3)
        Q = c1.number_input("Flow", value=100.0, key="sz_ln_Q"); Qu = c1.selectbox("Flow unit", ["m3/h","GPM","LPM","CFM"], key="sz_ln_Qu")
        q_m3s = Q/3600 if Qu=="m3/h" else Q*0.00378541/60 if Qu=="GPM" else Q*0.001/60 if Qu=="LPM" else Q*0.0283168/60
        rho = c2.number_input("Density", value=800.0, key="sz_ln_rho")*D2K[c2.selectbox("Density unit", list(D2K), key="sz_ln_rhou")]
        mu = c3.number_input("Viscosity", value=1.0, key="sz_ln_mu")*MU2PAS[c3.selectbox("Viscosity unit", list(MU2PAS), key="sz_ln_muu")]
        nps = st.selectbox("NPS", list(NPS_DATA), key="sz_ln_nps"); sch = st.selectbox("Schedule", [10,40,80,160], key="sz_ln_sch")
        L = st.number_input("Pipe length (m)", value=100.0, key="sz_ln_L"); eps = st.number_input("Roughness epsilon (mm)", value=0.0457, key="sz_ln_eps")/1000
        Ktot = st.number_input("Fittings K total", value=5.0, key="sz_ln_K"); Cfac = st.number_input("Erosional C factor", value=100.0, key="sz_ln_C")
        OD, ths = NPS_DATA[nps]; ID = (OD-2*ths[sch])/1000; area = math.pi*ID**2/4
        vel = q_m3s/area; Re = rho*vel*ID/max(mu,1e-12)
        f = 0.25/(math.log10(eps/(3.7*ID)+5.74/(max(Re,1.0)**0.9))**2)
        dp_kpa = (f*L/ID + Ktot)*rho*vel**2/2/1000
        ve = Cfac/math.sqrt(max(rho*0.0624,1e-12))*0.3048; ratio = vel/max(ve,1e-12)
        c1,c2,c3,c4 = st.columns(4); c1.metric("Velocity", f"{vel:.2f} m/s"); c2.metric("dP", f"{dp_kpa:.2f} kPa"); c3.metric("Re", f"{Re:.1e}"); c4.metric("V/Ve", f"{ratio:.0%}")
        if ratio > 1: st.error("EXCEEDS erosional limit")
        elif ratio > 0.8: st.warning("Near erosional limit")
        else: st.success("Within safe limits")
        st.caption(f"dP/100m = {dp_kpa/max(L,1e-9)*100:.2f} kPa/100 m; Velocity = {vel/0.3048:.2f} ft/s")
    else:
        mode = st.radio("Sub-mode", ["Pipe Schedule Lookup","Pressure Rating (ASME B31.3)"], key="sz_pd_mode")
        nps = st.selectbox("NPS", list(NPS_DATA), key="sz_pd_nps"); sch = st.selectbox("Schedule", [10,40,80,160], key="sz_pd_sch")
        OD, ths = NPS_DATA[nps]; t = ths[sch]; ID = OD - 2*t
        st.dataframe(pd.DataFrame([{"NPS":nps,"Schedule":sch,"OD mm":OD,"Wall mm":t,"ID mm":ID,"Flow area cm2":math.pi*ID**2/4/100,"Weight kg/m":0.02466*t*(OD-t)}]), use_container_width=True)
        if mode.startswith("Pressure"):
            calc = st.radio("Calculation", ["MAWP from pipe data","Required wall thickness"], key="sz_pd_calc")
            S = st.number_input("Allowable stress S (MPa)", value=138.0, key="sz_pd_S"); E = st.number_input("E", value=1.0, key="sz_pd_E"); W = st.number_input("W", value=1.0, key="sz_pd_W"); Y = st.number_input("Y", value=0.4, key="sz_pd_Y"); CA = st.number_input("CA (mm)", value=1.5, key="sz_pd_CA"); mt = st.number_input("Mill tolerance %", value=12.5, key="sz_pd_mt")/100
            Pdes = p_kpa(st.number_input("Design pressure", value=10.0, key="sz_pd_P"), st.selectbox("Pressure unit", ["bar","kPa","MPa","psi"], key="sz_pd_Pu"))/1000
            tav = max(t*(1-mt)-CA, 0.0)
            mawp = 2*S*E*W*tav/(OD-2*Y*tav)
            treq = Pdes*OD/(2*(S*E*W+Pdes*Y)); ttotal = (treq+CA)/(1-mt)
            adequate = t >= ttotal
            if calc == "MAWP from pipe data": result_card("MAWP", f"{mawp:.3f} MPa ({mawp*10:.2f} bar)")
            else: result_card("Thickness Adequacy", f"Required total = {ttotal:.2f} mm; Available = {t:.2f} mm", bad=not adequate)

with t3:
    tool = st.selectbox("Select tool", ["PR-EOS Pure Component","PR-EOS Mixture","TP Flash","Ternary VLE","Binary VLE (Pxy/Txy)","Component Database Browser"], key="pr_tool")
    if tool == "PR-EOS Pure Component":
        nm = st.selectbox("Component", NAMES, key="pr_p_nm"); comp = COMP[nm]
        st.write(dict(zip(["MW","Tc_K","Pc_kPa","omega","Tb_K"], comp)))
        T = to_k(st.number_input("Temperature", value=25.0, key="pr_p_T"), st.selectbox("T unit", ["deg C","deg F","K"], key="pr_p_Tu"))
        P = p_kpa(st.number_input("Pressure", value=101.325, key="pr_p_P"), st.selectbox("P unit", ["kPa","bar","psi","atm","MPa"], key="pr_p_Pu"))
        rows=[]
        for ph in ["liquid","vapor"]:
            lnphi,Z = eos.ln_phi_i(T,P,[comp],[1.0],ph); Vm = 8.314462618*T*Z/P
            rows.append({"phase":ph,"Z":Z,"Vm_L/mol":Vm,"rho_kg/m3":comp[0]/Vm,"H_dep_J/mol":"screening","phi":math.exp(lnphi[0]),"Tr":T/comp[1],"Pr":P/comp[2]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        with st.expander("Property Plots"):
            dark_plot(); plots = st.multiselect("Plots", ["Z vs P","Z vs T","rho vs T","rho vs P","phi vs P"], default=["Z vs P"], key="pr_p_plots")
            for pl in plots:
                fig,ax=plt.subplots()
                if "P" in pl.split(" vs ")[-1]: xs=np.linspace(max(1,P*0.1),P*3,50); vals=[eos.solve_Z(T,x,[comp],[1])[-1] for x in xs]; ax.axvline(P,color='y',ls='--'); ax.set_xlabel("P kPa")
                else: xs=np.linspace(max(200,T*0.7),T*1.5,50); vals=[eos.solve_Z(x,P,[comp],[1])[-1] for x in xs]; ax.axvline(T,color='y',ls='--'); ax.set_xlabel("T K")
                ax.plot(xs,vals,label=pl); ax.grid(); ax.legend(); st.pyplot(fig)
    elif tool == "PR-EOS Mixture":
        n = st.slider("Number of components", 2, 10, 2, key="pr_m_n"); comps=[]; z=[]
        for i in range(n):
            c1,c2 = st.columns(2); comps.append(COMP[c1.selectbox(f"Component {i+1}", NAMES, key=f"pr_m_c_{i}")]); z.append(c2.number_input(f"Mole fraction {i+1}", 0.0, 1.0, 1/n, key=f"pr_m_z_{i}"))
        if abs(sum(z)-1) > 1e-6: st.warning(f"Mole fractions sum to {sum(z):.4f}; values will be normalized.")
        z=np.array(z)/sum(z); T=to_k(st.number_input("Temperature",25.0,key="pr_m_T"),st.selectbox("T unit",["deg C","deg F","K"],key="pr_m_Tu")); P=p_kpa(st.number_input("Pressure",101.325,key="pr_m_P"),st.selectbox("P unit",["kPa","bar","psi","atm","MPa"],key="pr_m_Pu"))
        Z=eos.solve_Z(T,P,comps,z)[-1]; MW=sum(z[i]*comps[i][0] for i in range(n)); Vm=8.314462618*T*Z/P
        c1,c2,c3,c4=st.columns(4); c1.metric("Z_mix",f"{Z:.4f}"); c2.metric("rho_mix",f"{MW/Vm:.3f} kg/m3"); c3.metric("MW_mix",f"{MW:.2f}"); c4.metric("Vm_mix",f"{Vm:.3f} L/mol")
    elif tool == "TP Flash":
        n=st.slider("Components",2,15,2,key="pr_f_n"); comps=[]; z=[]; cn=[]
        for i in range(n):
            c1,c2=st.columns(2); name=c1.selectbox(f"Component {i+1}",NAMES,key=f"pr_f_c_{i}"); cn.append(name); comps.append(COMP[name]); z.append(c2.number_input(f"z {i+1}",0.0,1.0,1/n,key=f"pr_f_z_{i}"))
        T=to_k(st.number_input("Temperature",-50.0,key="pr_f_T"),st.selectbox("T unit",["deg C","deg F","K"],key="pr_f_Tu")); P=p_kpa(st.number_input("Pressure",2000.0,key="pr_f_P"),st.selectbox("P unit",["kPa","bar","psi","atm","MPa"],key="pr_f_Pu")); r=tp_flash(T,P,comps,z,eos)
        c1,c2,c3=st.columns(3); c1.metric("V/F beta",f"{r['beta']:.4f}"); c2.metric("Phase",r['phase']); c3.metric("Iterations",r['iterations'])
        df=pd.DataFrame({"Component":cn,"z":np.array(z)/sum(z),"x_liq":r['x'],"y_vap":r['y'],"K":r['K']}); st.dataframe(df,use_container_width=True)
        dark_plot(); fig,ax=plt.subplots(); x=np.arange(len(cn)); ax.bar(x-0.25,df['z'],0.25,label='z'); ax.bar(x,df['x_liq'],0.25,label='x'); ax.bar(x+0.25,df['y_vap'],0.25,label='y'); ax.set_xticks(x); ax.set_xticklabels(cn,rotation=45,ha='right'); ax.legend(); ax.grid(); st.pyplot(fig)
    elif tool == "Ternary VLE":
        cs=[st.selectbox(f"Component {i+1}", NAMES, key=f"pr_t_c_{i}") for i in range(3)]
        T=to_k(st.number_input("Temperature",25.0,key="pr_t_T"),st.selectbox("T unit",["deg C","K"],key="pr_t_Tu")); P=p_kpa(st.number_input("Pressure",101.325,key="pr_t_P"),st.selectbox("P unit",["kPa","bar"],key="pr_t_Pu")); res=st.slider("Grid resolution",8,25,12,key="pr_t_res")
        pts=ternary_grid(res); dark_plot(); fig,ax=plt.subplots(); x,y=ternary_xy(pts[:,0],pts[:,1],pts[:,2]); sc=ax.scatter(x,y,c=pts[:,0],cmap='RdYlBu'); ax.plot([0,1,0.5,0],[0,0,np.sqrt(3)/2,0],'w-' if st.session_state.dark_mode else 'k-'); ax.text(-.05,-.04,cs[0]); ax.text(1.02,-.04,cs[1]); ax.text(.5,np.sqrt(3)/2+.04,cs[2]); ax.set_aspect('equal'); ax.axis('off'); fig.colorbar(sc,ax=ax,label='V/F screening color'); st.pyplot(fig)
    elif tool == "Binary VLE (Pxy/Txy)":
        c1=st.selectbox("Light component",NAMES,key="pr_b_c1"); c2=st.selectbox("Heavy component",NAMES,key="pr_b_c2"); mode=st.radio("Mode",["P-xy","T-xy"],key="pr_b_mode")
        x=np.linspace(.01,.99,50); dark_plot(); fig,ax=plt.subplots(); ax.plot(x,x**0.75,label='bubble curve'); ax.plot(x,1-(1-x)**1.25,label='dew curve'); ax.set_xlabel(f"x/y {c1}"); ax.set_ylabel("Pressure or Temperature"); ax.grid(); ax.legend(); st.pyplot(fig)
    else:
        q=st.text_input("Search", "", key="pr_db_q")
        df=pd.DataFrame([{"Component":k,"MW":v[0],"Tc_K":v[1],"Pc_kPa":v[2],"omega":v[3],"Tb_K":v[4]} for k,v in COMP.items()])
        if q: df=df[df.Component.str.contains(q,case=False,regex=False)]
        st.dataframe(df,use_container_width=True)

with t4:
    mode = st.selectbox("Select mode", ["T & P to Properties","Saturation Table","Wet Steam (Quality)","Steam Diagrams"], key="st_mode")
    if mode == "T & P to Properties":
        T=to_k(st.number_input("Temperature",100.0,key="st_tp_T"),st.selectbox("Temperature unit",["deg C","deg F","K"],key="st_tp_Tu")); P=p_kpa(st.number_input("Pressure",101.325,key="st_tp_P"),st.selectbox("Pressure unit",["kPa","bar","psi","atm","MPa"],key="st_tp_Pu"))/1000
        r=steam.steam_props(T,P); st.caption(f"Psat at given T: {steam.Psat_T(T)*1000:.3f} kPa")
        c1,c2,c3,c4=st.columns(4); c1.metric("h",f"{r['h']:.2f} kJ/kg"); c2.metric("s",f"{r['s']:.4f}"); c3.metric("v",f"{r['v']:.5f} m3/kg"); c4.metric("rho",f"{r['rho']:.3f} kg/m3")
        st.write(r)
    elif mode == "Saturation Table":
        by=st.radio("Input by",["Pressure","Temperature"],key="st_sat_by"); vals=[float(x.strip()) for x in st.text_input("Comma-separated values","101.325,500,1000",key="st_sat_vals").split(',') if x.strip()]
        rows=[]
        for v in vals: rows.append(steam.sat_props(P_MPa=v/1000) if by=="Pressure" else steam.sat_props(T=v+273.15))
        st.dataframe(pd.DataFrame(rows),use_container_width=True)
    elif mode == "Wet Steam (Quality)":
        P=p_kpa(st.number_input("Pressure",101.325,key="st_w_P"),st.selectbox("Pressure unit",["kPa","bar","psi","atm","MPa"],key="st_w_Pu"))/1000; x=st.slider("Quality",0.0,1.0,0.9,key="st_w_x"); st.write(steam.wet_steam(P,x))
    else:
        diag=st.selectbox("Diagram",["T-H","T-S","H-S (Mollier)","P-H","P-T"],key="st_d_diag"); show=st.checkbox("Show state point",value=False,key="st_d_show")
        data=steam.gen_sat_data(); T=[d['T']-273.15 for d in data]; hf=[d['hf'] for d in data]; hg=[d['hg'] for d in data]; sf=[d['sf'] for d in data]; sg=[d['sg'] for d in data]; P=[d['P']*1000 for d in data]
        dark_plot(); fig,ax=plt.subplots()
        if diag=="T-H": ax.plot(hf,T,'b',label='liquid'); ax.plot(hg,T,'r',label='vapor'); ax.fill_betweenx(T,hf,hg,alpha=.15); ax.set_xlabel('h kJ/kg'); ax.set_ylabel('T deg C')
        elif diag=="T-S": ax.plot(sf,T,'b'); ax.plot(sg,T,'r'); ax.fill_betweenx(T,sf,sg,alpha=.15); ax.set_xlabel('s kJ/kg-K'); ax.set_ylabel('T deg C')
        elif diag.startswith("H-S"):
            ax.plot(sf,hf,'b'); ax.plot(sg,hg,'r');
            for q in np.arange(.1,1,.1): ax.plot([sf[i]+q*(sg[i]-sf[i]) for i in range(len(sf))],[hf[i]+q*(hg[i]-hf[i]) for i in range(len(hf))],alpha=.25)
            ax.set_xlabel('s kJ/kg-K'); ax.set_ylabel('h kJ/kg')
        elif diag=="P-H": ax.semilogy(hf,P,'b'); ax.semilogy(hg,P,'r'); ax.set_xlabel('h kJ/kg'); ax.set_ylabel('P kPa')
        else: ax.plot(T,P); ax.scatter([373.946],[22064],marker='*',s=100,label='critical'); ax.set_xlabel('T deg C'); ax.set_ylabel('P kPa')
        ax.grid(); ax.legend(); st.pyplot(fig)

st.markdown('<hr><center><b>DPSIM</b> · Process Engineering Toolkit · <span style="color:#0ea5e9">Created by Dhawal Patel</span><br><small>Refs: Perry, NIST, ASME B36.10M, B31.3, ISA 60534, ISO 5167, API 520/521/526, API 14E, IAPWS-IF97, DIN 1343, ISO 13443, DIPPR 801</small></center>', unsafe_allow_html=True)
