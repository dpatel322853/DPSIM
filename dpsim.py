import streamlit as st
import pandas as pd
import numpy as np
import math, re, json, datetime
from pathlib import Path
from io import BytesIO
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm as RL_MM
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from steam_if97 import steam_props, sat_props, Psat_T, Tsat_P, generate_saturation_data, wet_steam
    HAS_STEAM = True
except ImportError:
    HAS_STEAM = False

from thermo_engine import CubicEOS, tp_flash, rachford_rice, ternary_to_xy, generate_ternary_flash_data

st.set_page_config(page_title="DPSIM", page_icon="🔬", layout="wide")
R_GAS = 8.314

# ═══════ CSS ═══════
def get_css(dk):
    bg="#0f172a" if dk else "#f5f7fa"; sb="#020617" if dk else "#1e293b"
    tb="#1e293b" if dk else "white"; tbr="#334155" if dk else "#e2e8f0"
    tn="#e2e8f0" if dk else "#1e293b"; tl="#94a3b8" if dk else "#64748b"
    c="<style>"
    c+=f'[data-testid="stAppViewContainer"]{{background:{bg}}}'
    c+=f'section[data-testid="stSidebar"]{{background:{sb}}}'
    c+='section[data-testid="stSidebar"] *{color:#e2e8f0 !important}'
    c+='.rc{background:linear-gradient(135deg,#0ea5e9,#2563eb);border-radius:14px;padding:24px 28px;margin:12px 0;color:white;text-align:center;box-shadow:0 4px 20px rgba(37,99,235,.25)}'
    c+='.rc .v{font-size:2rem;font-weight:700}.rc .l{font-size:.9rem;opacity:.85;margin-top:4px}'
    c+='.gc{background:linear-gradient(135deg,#059669,#047857);border-radius:14px;padding:20px 24px;margin:12px 0;color:white;text-align:center}'
    c+='.gc .v{font-size:1.6rem;font-weight:700}.gc .l{font-size:.85rem;opacity:.85;margin-top:4px}'
    c+=f'.mt{{background:{tb};border-radius:10px;padding:14px 16px;border:1px solid {tbr};text-align:center}}'
    c+=f'.mt .n{{font-size:1.5rem;font-weight:700;color:{tn}}}.mt .l{{font-size:.78rem;color:{tl};margin-top:2px}}'
    c+=f'.hi{{background:{"#1e293b" if dk else "#334155"};border-radius:8px;padding:8px 12px;margin:4px 0;font-size:.82rem;color:#cbd5e1;border-left:3px solid #0ea5e9}}'
    if dk:
        c+=f'[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4{{color:{tn} !important}}'
        c+=f'[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] span,[data-testid="stAppViewContainer"] label{{color:{tn} !important}}'
        c+=f'[data-testid="stAppViewContainer"] .stTextInput input,[data-testid="stAppViewContainer"] .stNumberInput input{{background:#1e293b;color:#e2e8f0;border-color:#334155}}'
        c+=f'[data-testid="stAppViewContainer"] .stSelectbox [data-baseweb="select"]{{background:#1e293b}}'
        c+=f'[data-testid="stAppViewContainer"] .stSelectbox [data-baseweb="select"] *{{color:#e2e8f0 !important}}'
        c+=f'[data-testid="stAppViewContainer"] [data-baseweb="tab"]{{color:#94a3b8 !important}}'
        c+=f'[data-testid="stAppViewContainer"] [aria-selected="true"]{{color:#0ea5e9 !important}}'
        c+=f'[data-testid="stAppViewContainer"] .stCaption{{color:#94a3b8 !important}}'
        c+=f'[data-testid="stAppViewContainer"] .stAlert p{{color:#1e293b !important}}'
    c+='#MainMenu{visibility:hidden}footer{visibility:hidden}header{visibility:hidden}</style>'
    return c

def apply_mpl():
    dk=st.session_state.dark_mode
    matplotlib.rcParams.update({'figure.facecolor':'#0f172a' if dk else 'white',
        'axes.facecolor':'#1e293b' if dk else 'white','text.color':'#e2e8f0' if dk else '#1e293b',
        'axes.labelcolor':'#e2e8f0' if dk else '#1e293b','xtick.color':'#94a3b8' if dk else '#64748b',
        'ytick.color':'#94a3b8' if dk else '#64748b','axes.edgecolor':'#94a3b8' if dk else '#64748b'})

# ═══════ COMPONENT DB ═══════
@st.cache_data
def load_db():
    p=Path("components.json")
    return json.loads(p.read_text()) if p.exists() else {}
COMP_DB=load_db(); COMP_NAMES=sorted(COMP_DB.keys())

# ═══════ UNIT DATA ═══════
CATEGORIES={"🌡️ Temp":{"units":["°C","°F","K","°R"],"type":"temperature"},
    "📐 Length":{"u":{"m":1,"mm":1e-3,"cm":1e-2,"km":1e3,"in":0.0254,"ft":0.3048,"yd":0.9144,"mile":1609.344}},
    "⚖️ Mass":{"u":{"kg":1,"g":1e-3,"mg":1e-6,"tonne":1e3,"lb":0.4536,"oz":0.02835}},
    "🔴 Pressure":{"u":{"Pa":1,"kPa":1e3,"MPa":1e6,"bar":1e5,"mbar":1e2,"psi":6894.76,"atm":101325,"mmHg":133.32,"inH2O":249.09,"kg/cm2":98066.5,"barg":1e5,"psig":6894.76,"kPag":1e3}},
    "🌊 Vol.Flow":{"u":{"m3/h":1,"m3/s":3600,"m3/min":60,"L/h":1e-3,"LPM":0.06,"L/s":3.6,"GPM":0.22712,"GPH":0.003785,"CFM":1.699,"bbl/day":0.006624,"bbl/h":0.158987}},
    "⚡ MassFlow":{"u":{"kg/h":1,"kg/s":3600,"kg/min":60,"g/s":3.6,"lb/h":0.4536,"lb/s":1632.9,"lb/min":27.22,"tonne/h":1000}},
    "📦 Volume":{"u":{"m3":1,"L":1e-3,"mL":1e-6,"ft3":0.02832,"US gal":0.003785,"barrel":0.158987}},
    "📏 Area":{"u":{"m2":1,"cm2":1e-4,"mm2":1e-6,"ft2":0.0929,"in2":6.452e-4,"acre":4046.86,"hectare":1e4}},
    "🔥 Energy":{"u":{"J":1,"kJ":1e3,"MJ":1e6,"GJ":1e9,"BTU":1055.06,"MMBTU":1.055e9,"kcal":4184,"kWh":3.6e6}},
    "⚡ Power":{"u":{"W":1,"kW":1e3,"MW":1e6,"hp":745.7,"BTU/h":0.29307,"MMBTU/h":293071,"kcal/h":1.163}},
    "🧪 Density":{"u":{"kg/m3":1,"g/cm3":1000,"kg/L":1000,"lb/ft3":16.02,"lb/gal":119.83}},
    "💧 Viscosity":{"u":{"Pa.s":1,"cP":1e-3,"mPa.s":1e-3,"Poise":0.1}},
    "💨 KinVisc":{"u":{"m2/s":1,"cSt":1e-6,"Stokes":1e-4}},
    "🌬️ Velocity":{"u":{"m/s":1,"km/h":0.27778,"ft/s":0.3048,"ft/min":0.00508,"mph":0.44704}},
    "🔄 Force":{"u":{"N":1,"kN":1e3,"lbf":4.44822,"kgf":9.80665}},
    "♨️ HTC":{"u":{"W/(m2.K)":1,"BTU/(h.ft2.F)":5.67826,"kcal/(h.m2.C)":1.163}},}
for ck in CATEGORIES:
    if "u" in CATEGORIES[ck]: CATEGORIES[ck]["units_to_base"]=CATEGORIES[ck].pop("u")

PIPE_SCH={"1/2":{"od":0.840,10:0.083,40:0.109,80:0.147,160:None},"3/4":{"od":1.050,10:0.083,40:0.113,80:0.154,160:None},
    "1":{"od":1.315,10:0.109,40:0.133,80:0.179,160:0.250},"1.5":{"od":1.900,10:0.109,40:0.145,80:0.200,160:None},
    "2":{"od":2.375,10:0.109,40:0.154,80:0.218,160:0.344},"3":{"od":3.500,10:0.120,40:0.216,80:0.300,160:0.438},
    "4":{"od":4.500,10:0.120,40:0.237,80:0.337,160:0.531},"6":{"od":6.625,10:0.134,40:0.280,80:0.432,160:0.719},
    "8":{"od":8.625,10:0.148,40:0.322,80:0.500,160:0.906},"10":{"od":10.750,10:0.165,40:0.365,80:0.500,160:1.125},
    "12":{"od":12.750,10:0.180,40:0.406,80:0.500,160:1.312},"14":{"od":14.000,10:0.250,40:0.438,80:0.594,160:1.406},
    "16":{"od":16.000,10:0.250,40:0.500,80:0.656,160:1.594},"20":{"od":20.000,10:0.250,40:0.594,80:0.812,160:1.969},
    "24":{"od":24.000,10:0.250,40:0.688,80:0.969,160:2.344}}
MATERIALS={"A106 Gr.B":{"S":20000,"n":"CS"},"A333 Gr.6":{"S":20000,"n":"LT-CS"},"A312 TP304":{"S":20000,"n":"SS304"},
    "A312 TP316":{"S":20000,"n":"SS316"},"A312 TP304L":{"S":16700,"n":"SS304L"},"A312 TP316L":{"S":16700,"n":"SS316L"},
    "API 5L Gr.B":{"S":20000,"n":"LinePipe"},"API 5L X52":{"S":31200,"n":"X52"},"API 5L X65":{"S":39000,"n":"X65"},"Custom":{"S":20000,"n":"User"}}
GASES={"Air":{"M":28.97,"k":1.40,"Z":1.0},"Nitrogen":{"M":28.01,"k":1.40,"Z":1.0},"Oxygen":{"M":32.0,"k":1.40,"Z":1.0},
    "Hydrogen":{"M":2.016,"k":1.41,"Z":1.0},"Methane":{"M":16.04,"k":1.31,"Z":0.998},"Ethane":{"M":30.07,"k":1.19,"Z":0.991},
    "Ethylene":{"M":28.05,"k":1.24,"Z":0.994},"Propane":{"M":44.10,"k":1.13,"Z":0.979},"CO2":{"M":44.01,"k":1.29,"Z":0.994},
    "Steam":{"M":18.015,"k":1.33,"Z":0.98},"NH3":{"M":17.03,"k":1.31,"Z":0.99},"Natural Gas":{"M":18.0,"k":1.27,"Z":0.95},
    "H2S":{"M":34.08,"k":1.32,"Z":0.99},"Custom":{"M":28.97,"k":1.40,"Z":1.0}}
REF_COND={"Normal (0°C, 101.325 kPa)":{"T_K":273.15,"P_kPa":101.325},"Std ISO (15°C, 101.325 kPa)":{"T_K":288.15,"P_kPa":101.325},
    "Std US (60°F, 14.696 psia)":{"T_K":288.706,"P_kPa":101.325}}
GF_UNITS={"Nm3/h":{"f":1.0},"Nm3/min":{"f":60.0},"Nm3/day":{"f":1/24},"Sm3/h":{"f":273.15/288.15},
    "Sm3/day":{"f":273.15/288.15/24},"SCFM":{"f":0.02832*60*273.15/288.706},"SCFH":{"f":0.02832*273.15/288.706},
    "MMSCFD":{"f":0.02832*1e6*273.15/288.706/24}}
UNIT_ALIASES={"pa":("🔴 Pressure","Pa"),"kpa":("🔴 Pressure","kPa"),"bar":("🔴 Pressure","bar"),
    "psi":("🔴 Pressure","psi"),"atm":("🔴 Pressure","atm"),"barg":("🔴 Pressure","barg"),
    "degc":("🌡️ Temp","°C"),"degf":("🌡️ Temp","°F"),"celsius":("🌡️ Temp","°C"),
    "mm":("📐 Length","mm"),"ft":("📐 Length","ft"),"inch":("📐 Length","in"),
    "kg":("⚖️ Mass","kg"),"lb":("⚖️ Mass","lb"),"tonne":("⚖️ Mass","tonne"),
    "gpm":("🌊 Vol.Flow","GPM"),"m3/h":("🌊 Vol.Flow","m3/h"),"cfm":("🌊 Vol.Flow","CFM"),
    "kg/h":("⚡ MassFlow","kg/h"),"lb/h":("⚡ MassFlow","lb/h"),
    "btu":("🔥 Energy","BTU"),"kj":("🔥 Energy","kJ"),"kcal":("🔥 Energy","kcal"),
    "kw":("⚡ Power","kW"),"hp":("⚡ Power","hp"),"cp":("💧 Viscosity","cP"),
    "cst":("💨 KinVisc","cSt"),"m/s":("🌬️ Velocity","m/s"),"ft/s":("🌬️ Velocity","ft/s")}
STD_ORIFICES=[("D",71),("E",126),("F",198),("G",325),("H",506),("J",830),("K",1186),("L",1841),("M",2323),("N",2800),("P",4116),("Q",7126),("R",10323),("T",16774)]

# ═══════ FUNCTIONS ═══════
def temp_cv(v,fu,tu):
    c={"°C":lambda v:v,"°F":lambda v:(v-32)*5/9,"K":lambda v:v-273.15,"°R":lambda v:(v-491.67)*5/9}[fu](v)
    return {"°C":lambda:c,"°F":lambda:c*9/5+32,"K":lambda:c+273.15,"°R":lambda:(c+273.15)*9/5}[tu]()
def do_cv(v,ck,fu,tu):
    cat=CATEGORIES[ck]
    if cat.get("type")=="temperature": return temp_cv(v,fu,tu)
    return v*cat["units_to_base"][fu]/cat["units_to_base"][tu]
def get_units(ck):
    cat=CATEGORIES[ck]
    return cat["units"] if cat.get("type")=="temperature" else list(cat["units_to_base"].keys())
def rec_size(cv):
    for mx,sz in [(10,'1"'),(30,'1.5"'),(75,'2"'),(150,'3"'),(300,'4"'),(500,'6"'),(1000,'8"'),(2000,'10"')]:
        if cv<=mx: return sz
    return '12"+'
def parse_nl(text):
    m=re.match(r"(?:convert\s+)?(-?\d+\.?\d*(?:e[+-]?\d+)?)\s+(.+?)\s+(?:to|in|into)\s+(.+)",text.strip(),re.IGNORECASE)
    if m:
        v,f,t=float(m.group(1)),m.group(2).strip().lower(),m.group(3).strip().lower()
        fi,ti=UNIT_ALIASES.get(f),UNIT_ALIASES.get(t)
        if fi and ti and fi[0]==ti[0]: return {"val":v,"from":fi[1],"to":ti[1],"cat":fi[0],"result":do_cv(v,fi[0],fi[1],ti[1])}
    return None
def gas_flow_cv(v,fu,tu): return v*GF_UNITS[fu]["f"]/GF_UNITS[tu]["f"]
def act_to_ref(Qa,Tk,Pk,Z,rk): r=REF_COND[rk]; return Qa*(Pk/r["P_kPa"])*(r["T_K"]/Tk)/Z
def ref_to_act(Qr,Tk,Pk,Z,rk): r=REF_COND[rk]; return Qr*(r["P_kPa"]/Pk)*(Tk/r["T_K"])*Z
def pr_params(Tc,Pc_kPa,om,T):
    Pc=Pc_kPa*1000;kappa=0.37464+1.54226*om-0.26992*om**2
    alpha=(1+kappa*(1-math.sqrt(T/Tc)))**2;a=0.45724*R_GAS**2*Tc**2/Pc*alpha;b=0.07780*R_GAS*Tc/Pc
    da=-0.45724*R_GAS**2*Tc**2/Pc*kappa*math.sqrt(alpha/(T*Tc)) if T>0 and Tc>0 else 0
    return a,b,da
def pr_solve_Z(am,bm,T,P_kPa):
    P=P_kPa*1000;A=am*P/(R_GAS**2*T**2);B=bm*P/(R_GAS*T)
    roots=np.roots([1,-(1-B),A-3*B**2-2*B,-(A*B-B**2-B**3)])
    rr=sorted([r.real for r in roots if abs(r.imag)<1e-10 and r.real>0])
    if not rr: return None,None
    return max(rr),min(rr) if len(rr)>1 else max(rr)
def pr_full(T,P_kPa,MW,Tc,Pc,om):
    a,b,da=pr_params(Tc,Pc,om,T);Zv,Zl=pr_solve_Z(a,b,T,P_kPa)
    if Zv is None: return None
    P=P_kPa*1000;s2=math.sqrt(2);res={}
    for lb,Z in [("vapor",Zv),("liquid",Zl)]:
        Vm=Z*R_GAS*T/P;rho=(MW/1000)/Vm;B_=b*P/(R_GAS*T);A_=a*P/(R_GAS**2*T**2)
        a1=Z+(1+s2)*B_;a2=Z+(1-s2)*B_
        lnt=math.log(a1/a2) if a1>0 and a2>0 else 0
        Hd=R_GAS*T*(Z-1)+(T*da-a)/(2*s2*b)*lnt if b>0 else 0
        lnp=(Z-1)-math.log(max(Z-B_,1e-30))-A_/(2*s2*max(B_,1e-30))*lnt
        res[lb]={"Z":Z,"Vm_Lmol":Vm*1000,"rho":rho,"H_dep":Hd,"phi":math.exp(lnp),"ln_phi":lnp,"Tr":T/Tc,"Pr":P_kPa/Pc}
    return res
def sweep_prop(comp,var,rng,fixed,key):
    d=COMP_DB[comp];MW,Tc,Pc,om=d[0],d[1],d[2],d[3];xs,yv,yl=[],[],[]
    for x in rng:
        try:
            T=x+273.15 if var=="T" else fixed+273.15;P=fixed if var=="T" else x
            r=pr_full(T,P,MW,Tc,Pc,om)
            if r: xs.append(x);yv.append(r["vapor"][key]);yl.append(r["liquid"][key])
        except: pass
    return xs,yv,yl
def orifice_Cd(beta,ReD):
    A=(-2.457*math.log((7/ReD)**0.9+0.27*0.000457))**16 if ReD>0 else 0;B=(37530/ReD)**16
    return 0.5961+0.0261*beta**2-0.216*beta**8+0.000521*(1e6*beta/ReD)**0.7+(0.0188+0.0063*((19000*beta/ReD)**0.8 if ReD>0 else 0))*beta**3.5*(1e6/ReD)**0.3
def orifice_liquid(d_mm,D_mm,dP,rho,mu=1e-3):
    d=d_mm/1000;D=D_mm/1000;beta=d/D;A=math.pi/4*d**2;E=1/math.sqrt(1-beta**4);Cd=0.61
    for _ in range(10):
        Q=Cd*E*A*math.sqrt(2*dP*1000/rho);V=Q/(math.pi/4*D**2) if D>0 else 0;ReD=rho*V*D/mu if mu>0 else 1e6
        Cn=orifice_Cd(beta,ReD)
        if abs(Cn-Cd)<1e-6: break
        Cd=Cn
    return Q*3600,Cd,ReD,beta
def orifice_gas(d_mm,D_mm,dP,P1,rho1,k,mu=1.8e-5):
    d=d_mm/1000;D=D_mm/1000;beta=d/D;A=math.pi/4*d**2;E=1/math.sqrt(1-beta**4)
    eps=max(1-(0.41+0.35*beta**4)*dP/(k*P1),0.1) if k>0 and P1>0 else 1;Cd=0.61
    for _ in range(10):
        W=Cd*E*eps*A*math.sqrt(2*dP*1000*rho1);V=W/(rho1*math.pi/4*D**2) if rho1>0 and D>0 else 0
        ReD=rho1*V*D/mu if mu>0 else 1e6;Cn=orifice_Cd(beta,ReD)
        if abs(Cn-Cd)<1e-6: break
        Cd=Cn
    return W*3600,Cd,ReD,beta,eps
def rv_vapor(W,P1,T_K,M,k,Z=1.0,Kd=0.975):
    C=0.03948*math.sqrt(k*(2/(k+1))**((k+1)/(k-1)));return 13160*W/(C*Kd*P1)*math.sqrt(T_K*Z/M),C
def rv_liquid(Q,dP,rho,Kd=0.65): return 11.78*Q*1000/60/Kd*math.sqrt(rho/1000/dP)
def churchill_f(Re,eD):
    if Re<1: return 0
    A=(-2.457*math.log((7/Re)**0.9+0.27*eD))**16;B=(37530/Re)**16
    return 8*((8/Re)**12+1/(A+B)**1.5)**(1/12)
def pipe_dp(Q,rho,mu,D_mm,L,eps=0.0457,K=0):
    D=D_mm/1000;A=math.pi/4*D**2;Qm=Q/3600;V=Qm/A if A>0 else 0
    Re=rho*V*D/mu if mu>0 else 0;f=churchill_f(Re,eps/1000/D if D>0 else 0)
    dP=f*(L/D)*(rho*V**2/2)+K*(rho*V**2/2) if D>0 else 0
    return dP/1000,V,Re,f
def erosional_v(rho,C=100): return C/math.sqrt(rho) if rho>0 else 0
def mk_pdf(title,secs):
    if not HAS_PDF: return None
    buf=BytesIO();d=SimpleDocTemplate(buf,pagesize=A4,topMargin=20*RL_MM,bottomMargin=15*RL_MM,leftMargin=15*RL_MM,rightMargin=15*RL_MM)
    sty=getSampleStyleSheet();st2=[Paragraph(title,sty["Title"]),Spacer(1,6*RL_MM)]
    for s in secs:
        if s.get("h"): st2+=[Paragraph(s["h"],sty["Heading2"]),Spacer(1,2*RL_MM)]
        for ln in s.get("l",[]): st2+=[Paragraph(str(ln),sty["Normal"]),Spacer(1,1*RL_MM)]
        st2.append(Spacer(1,4*RL_MM))
    d.build(st2);return buf.getvalue()
FAV_FILE=Path("favorites.json")
def load_fav():
    if FAV_FILE.exists():
        try: return json.loads(FAV_FILE.read_text())
        except: return []
    return []
def save_fav(f): FAV_FILE.write_text(json.dumps(f,indent=2))
for k,v in [("favorites",None),("history",[]),("from_u",None),("to_u",None),("prev_cat",None),("precision",4),("dark_mode",False)]:
    if k not in st.session_state: st.session_state[k]=load_fav() if k=="favorites" else v
def add_hist(i,fu,r,tu,c):
    e=f"{i:.6g} {fu} -> {r:.6g} {tu}";h=st.session_state.history
    if not h or h[0]!=e: h.insert(0,e)
    if len(h)>25: h.pop()

# ═══════════════════════════════════════════
# UI: SIDEBAR + 12 TABS
# ═══════════════════════════════════════════
st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)
dk=st.session_state.dark_mode

with st.sidebar:
    st.markdown("## 🔬 DPSIM"); st.caption("Process Engineering Toolkit")
    st.markdown("---")
    category=st.selectbox("📂 Category",list(CATEGORIES.keys()),index=3,key="cs")
    prec=st.select_slider("🔢 Precision",[2,3,4,5,6,8],value=4,key="pr"); st.session_state.precision=prec
    st.markdown("---")
    dm=st.toggle("🌙 Dark Mode",value=dk,key="dm")
    if dm!=dk: st.session_state.dark_mode=dm; st.rerun()
    st.markdown("---")
    st.markdown("### 🔬 EOS")
    eos_ch=st.selectbox("EOS",["Peng-Robinson","SRK","van der Waals","User-Defined"],key="eos_ch")
    cp_=None
    if eos_ch=="Peng-Robinson": eos_t="PR"
    elif eos_ch=="SRK": eos_t="SRK"
    elif eos_ch=="van der Waals": eos_t="vdW"
    else:
        eos_t="Custom"
        cOa=st.number_input("Ωa",value=0.45724,format="%.5f",key="cOa")
        cOb=st.number_input("Ωb",value=0.07780,format="%.5f",key="cOb")
        cd1=st.number_input("δ₁",value=1+math.sqrt(2),format="%.6f",key="cd1")
        cd2=st.number_input("δ₂",value=1-math.sqrt(2),format="%.6f",key="cd2")
        st.caption("κ(ω)=c₀+c₁ω+c₂ω²")
        ck0=st.number_input("c₀",value=0.37464,format="%.5f",key="ck0")
        ck1=st.number_input("c₁",value=1.54226,format="%.5f",key="ck1")
        ck2=st.number_input("c₂",value=-0.26992,format="%.5f",key="ck2")
        cp_={"Omega_a":cOa,"Omega_b":cOb,"d1":cd1,"d2":cd2,"kappa_coeffs":[ck0,ck1,ck2]}
    eos=CubicEOS(eos_t,cp_)
    st.caption(f"Active: {eos_ch}")
    st.markdown("---")
    st.markdown("### ⭐ Pinned")
    for fav in st.session_state.favorites[:5]:
        st.markdown(f'<div class="hi">{fav["category"].split(" ")[0]} {fav["from"]}->{fav["to"]}</div>',unsafe_allow_html=True)
    if not st.session_state.favorites: st.caption("None yet")
    st.markdown("---")
    st.markdown("### 🕒 Recent")
    for h in st.session_state.history[:8]:
        st.markdown(f'<div class="hi">{h}</div>',unsafe_allow_html=True)
    if not st.session_state.history: st.caption("None yet")

st.markdown("## 🔬 DPSIM — Process Engineering Toolkit")
qc1,qc2=st.columns([5,1])
with qc1: qq=st.text_input("Q",placeholder="⚡ Quick: 150 psi to bar | 500 gpm to m3/h",label_visibility="collapsed",key="qq")
with qc2: st.button("Convert",type="primary",use_container_width=True,key="qg")
if qq:
    parsed=parse_nl(qq)
    if parsed:
        p=st.session_state.precision
        st.markdown(f'<div class="rc"><div class="l">{parsed["cat"]}</div><div class="v">{parsed["val"]:.{p}f} {parsed["from"]} = {parsed["result"]:.{p}f} {parsed["to"]}</div></div>',unsafe_allow_html=True)
        add_hist(parsed["val"],parsed["from"],parsed["result"],parsed["to"],parsed["cat"])
    elif qq.strip(): st.warning("Try: `150 psi to bar`")

ulist=get_units(category)
if category!=st.session_state.prev_cat:
    st.session_state.from_u=ulist[0];st.session_state.to_u=ulist[min(1,len(ulist)-1)];st.session_state.prev_cat=category

t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12=st.tabs(["🔄 Convert","🌬️ Gas","🔧 Cv","🔘 Orifice","🔒 Relief","📏 Pipe","🔩 Data","🧮 Rating","🧬 PR-EOS","🌊 Steam","⚡ Flash","🔺 VLE"])

# ══════ T1: CONVERTER ══════
with t1:
    p=st.session_state.precision
    def swap(): st.session_state.from_u,st.session_state.to_u=st.session_state.to_u,st.session_state.from_u
    def si(n,l,d=0): return l.index(n) if n in l else d
    fi=si(st.session_state.from_u,ulist);ti=si(st.session_state.to_u,ulist,min(1,len(ulist)-1))
    c1,cs,c2=st.columns([4,1,4])
    with c1: fu=st.selectbox("From",ulist,index=fi,key="fs");iv=st.number_input("Value",value=1.0,format="%.6g",key="iv")
    with cs: st.markdown("");st.markdown("");st.markdown("");st.button("🔄",on_click=swap,use_container_width=True)
    with c2: tu=st.selectbox("To",ulist,index=ti,key="ts");rv=do_cv(iv,category,fu,tu);st.text_input("Result",value=f"{rv:.{p}f}",disabled=True,key="rd")
    st.session_state.from_u=fu;st.session_state.to_u=tu
    st.markdown(f'<div class="rc"><div class="l">{category}</div><div class="v">{iv:.{p}f} {fu} = {rv:.{p}f} {tu}</div></div>',unsafe_allow_html=True)
    add_hist(iv,fu,rv,tu,category)
    b1,b2=st.columns(2)
    with b1:
        if st.button("⭐ Pin",key="pn",use_container_width=True):
            e={"category":category,"from":fu,"to":tu}
            if e not in st.session_state.favorites: st.session_state.favorites.append(e);save_fav(st.session_state.favorites);st.toast("Pinned!")
    with b2:
        pdf=mk_pdf("Conversion",[{"h":"Result","l":[f"{iv:.{p}f} {fu} = {rv:.{p}f} {tu}"]}])
        if pdf: st.download_button("📄 PDF",pdf,"conv.pdf","application/pdf",key="p1",use_container_width=True)
    with st.expander("📊 Full Table"):
        st.dataframe(pd.DataFrame([{"Unit":u,f"1 {fu} =":f"{do_cv(1,category,fu,u):.{p}f}"} for u in ulist]),use_container_width=True,hide_index=True)

# ══════ T2: GAS FLOW ══════
with t2:
    p=st.session_state.precision;gm=st.radio("Mode",["Std↔Std","Actual↔Ref"],horizontal=True,key="gm")
    if gm=="Std↔Std":
        gl=list(GF_UNITS.keys());gc1,_,gc2=st.columns([4,1,4])
        with gc1: gfu=st.selectbox("From",gl,key="gfu");gv=st.number_input("Value",value=1000.0,format="%.6g",key="gv")
        with gc2: gtu=st.selectbox("To",gl,index=3,key="gtu");gr=gas_flow_cv(gv,gfu,gtu);st.text_input("Result",f"{gr:.{p}f}",disabled=True,key="grd")
        st.markdown(f'<div class="gc"><div class="l">Gas Flow</div><div class="v">{gv:.{p}f} {gfu} = {gr:.{p}f} {gtu}</div></div>',unsafe_allow_html=True)
    else:
        dr=st.radio("Dir",["Act→Ref","Ref→Act"],horizontal=True,key="gd")
        ac1,ac2=st.columns(2)
        with ac1: rk=st.selectbox("Ref",list(REF_COND.keys()),key="rk");Tin=st.number_input("T(°C)",value=25.0,key="gt");Pin=st.number_input("P(kPa abs)",value=500.0,key="gp");Zin=st.number_input("Z",value=1.0,min_value=0.01,format="%.4f",key="gz")
        with ac2:
            Tk=Tin+273.15;ru="Nm3/h" if "Normal" in rk else "Sm3/h"
            if dr=="Act→Ref":
                Qa=st.number_input("Act(m3/h)",value=100.0,key="qa");Qr=act_to_ref(Qa,Tk,Pin,Zin,rk)
                st.markdown(f'<div class="gc"><div class="v">{Qa:.{p}f} m3/h = {Qr:.{p}f} {ru}</div></div>',unsafe_allow_html=True)
            else:
                Qr2=st.number_input(f"Ref({ru})",value=100.0,key="qr");Qa2=ref_to_act(Qr2,Tk,Pin,Zin,rk)
                st.markdown(f'<div class="gc"><div class="v">{Qr2:.{p}f} {ru} = {Qa2:.{p}f} m3/h</div></div>',unsafe_allow_html=True)

# ══════ T3: Cv ══════
with t3:
    p=st.session_state.precision;svc=st.radio("Service",["Liquid","Gas/Vapor"],horizontal=True,key="sv")
    if svc=="Liquid":
        lc1,lc2=st.columns(2)
        with lc1: Q=st.number_input("Q(GPM)",value=500.0,key="cq");P1=st.number_input("P1(psia)",value=150.0,key="cp1");P2=st.number_input("P2(psia)",value=100.0,key="cp2");Gf=st.number_input("Gf",value=1.0,min_value=0.01,key="cg")
        with lc2:
            dP=P1-P2
            if dP<=0: st.error("P1>P2!")
            else: Cv=Q*math.sqrt(Gf/dP);st.markdown(f'<div class="rc"><div class="l">Liquid Cv</div><div class="v">Cv={Cv:.{p}f}</div><div class="l">{rec_size(Cv)} dP={dP:.2f}psi</div></div>',unsafe_allow_html=True)
    else:
        gc1,gc2=st.columns(2)
        with gc1:
            W=st.number_input("W(lb/h)",value=10000.0,key="cw");P1g=st.number_input("P1(psia)",value=150.0,key="cp1g");P2g=st.number_input("P2(psia)",value=100.0,key="cp2g")
            Tf=st.number_input("T(°F)",value=200.0,key="ctf");gs=st.selectbox("Gas",list(GASES.keys()),key="cgs")
            M=GASES[gs]["M"];k=GASES[gs]["k"];Z=GASES[gs]["Z"]
            if gs=="Custom": M=st.number_input("M",value=28.97,key="cm");k=st.number_input("k",value=1.4,key="ck");Z=st.number_input("Z",value=1.0,format="%.4f",key="cz")
            xT=st.number_input("xT",value=0.70,min_value=0.1,max_value=1.0,step=0.01,key="cxt")
            Zo=st.number_input("Z override(0=def)",value=0.0,format="%.4f",key="czo")
            if Zo>0: Z=Zo
        with gc2:
            dPg=P1g-P2g
            if dPg<=0: st.error("P1>P2!")
            else:
                TR=Tf+459.67;Fk=k/1.4;x=dPg/P1g;xl=Fk*xT;chk=x>=xl;xe=min(x,xl);Y=max(1-xe/(3*Fk*xT),2/3)
                dn=63.3*Y*math.sqrt(xe*P1g*M/(TR*Z));Cvg=W/dn if dn>0 else 0
                st.markdown(f'<div class="rc"><div class="l">Gas Cv{" ⚠️CHOKED" if chk else ""}</div><div class="v">Cv={Cvg:.{p}f}</div><div class="l">{rec_size(Cvg)} Y={Y:.4f} Z={Z:.4f}</div></div>',unsafe_allow_html=True)

# ══════ T4: ORIFICE ══════
with t4:
    p=st.session_state.precision;osvc=st.radio("Service",["Liquid","Gas"],horizontal=True,key="osvc")
    oc1,oc2=st.columns(2)
    with oc1:
        od=st.number_input("Bore d(mm)",value=50.0,min_value=1.0,key="od");oD=st.number_input("Pipe ID D(mm)",value=100.0,min_value=1.0,key="oD")
        odP=st.number_input("dP(kPa)",value=25.0,min_value=0.001,key="odP")
        if osvc=="Liquid": orho=st.number_input("ρ(kg/m3)",value=1000.0,key="orho");omu=st.number_input("μ(Pa.s)",value=1e-3,format="%.6g",key="omu")
        else: oP1=st.number_input("P1(kPa)",value=500.0,key="oP1");orho1=st.number_input("ρ1(kg/m3)",value=5.0,key="orho1");ok=st.number_input("k",value=1.4,key="ok");omu=st.number_input("μ(Pa.s)",value=1.8e-5,format="%.6g",key="omu2")
    with oc2:
        if osvc=="Liquid":
            Qo,Cd,Re,beta=orifice_liquid(od,oD,odP,orho,omu)
            st.markdown(f'<div class="rc"><div class="l">Liquid Orifice</div><div class="v">Q={Qo:.{p}f} m3/h</div><div class="l">β={beta:.4f} Cd={Cd:.4f} Re={Re:.0f}</div></div>',unsafe_allow_html=True)
        else:
            Wo,Cd,Re,beta,eps=orifice_gas(od,oD,odP,oP1,orho1,ok,omu)
            st.markdown(f'<div class="rc"><div class="l">Gas Orifice</div><div class="v">W={Wo:.{p}f} kg/h</div><div class="l">β={beta:.4f} Cd={Cd:.4f} ε={eps:.4f}</div></div>',unsafe_allow_html=True)

# ══════ T5: RELIEF VALVE ══════
with t5:
    p=st.session_state.precision;rsvc=st.radio("Svc",["Vapor","Liquid"],horizontal=True,key="rsvc")
    rc1,rc2=st.columns(2)
    if rsvc=="Vapor":
        with rc1: rW=st.number_input("W(kg/h)",value=5000.0,key="rW");rP1=st.number_input("P1(kPa abs)",value=1200.0,key="rP1");rT=st.number_input("T(°C)",value=150.0,key="rT");rM=st.number_input("M",value=28.97,key="rM");rkv=st.number_input("k",value=1.4,min_value=1.01,key="rk2");rZ=st.number_input("Z",value=1.0,format="%.4f",key="rZ")
        with rc2:
            A_rv,C_rv=rv_vapor(rW,rP1,rT+273.15,rM,rkv,rZ)
            st.markdown(f'<div class="rc"><div class="l">Vapor Relief</div><div class="v">A={A_rv:.2f} mm²</div></div>',unsafe_allow_html=True)
            sel="—"
            for ltr,area in STD_ORIFICES:
                if area>=A_rv: sel=f"{ltr} ({area} mm²)";break
            st.info(f"Orifice: **{sel}**")
    else:
        with rc1: rQ=st.number_input("Q(m3/h)",value=50.0,key="rQ");rdP=st.number_input("P1-Pb(kPa)",value=500.0,key="rdP");rrho=st.number_input("ρ(kg/m3)",value=800.0,key="rrho")
        with rc2:
            A_rl=rv_liquid(rQ,rdP,rrho)
            st.markdown(f'<div class="rc"><div class="l">Liquid Relief</div><div class="v">A={A_rl:.2f} mm²</div></div>',unsafe_allow_html=True)
            sel="—"
            for ltr,area in STD_ORIFICES:
                if area>=A_rl: sel=f"{ltr} ({area} mm²)";break
            st.info(f"Orifice: **{sel}**")

# ══════ T6: PIPE V/dP ══════
with t6:
    p=st.session_state.precision;vc1,vc2=st.columns(2)
    with vc1:
        vQ=st.number_input("Q(m3/h)",value=100.0,key="vQ");vrho=st.number_input("ρ(kg/m3)",value=1000.0,key="vrho");vmu=st.number_input("μ(Pa.s)",value=1e-3,format="%.6g",key="vmu")
        vnps=st.selectbox("NPS",list(PIPE_SCH.keys()),index=7,key="vnps");vsch=st.selectbox("Sch",[10,40,80,160],index=1,key="vsch")
        vL=st.number_input("Length(m)",value=100.0,key="vL");veps=st.number_input("ε(mm)",value=0.0457,format="%.4f",key="veps")
        vK=st.number_input("K fittings",value=0.0,key="vK");vC=st.number_input("Erosional C",value=100.0,key="vC")
    with vc2:
        pipe=PIPE_SCH[vnps];wt=pipe.get(vsch)
        if wt is None: st.error("N/A")
        else:
            Did=pipe["od"]-2*wt;Dmm=Did*25.4;dPk,V,Re,ff=pipe_dp(vQ,vrho,vmu,Dmm,vL,veps,vK);Ve=erosional_v(vrho,vC);pct=V/Ve*100 if Ve>0 else 0
            st.markdown(f'<div class="rc"><div class="l">NPS {vnps}" Sch {vsch}</div><div class="v">V={V:.2f} m/s | ΔP={dPk:.{p}f} kPa</div></div>',unsafe_allow_html=True)
            clr="#059669" if pct<80 else "#f59e0b" if pct<100 else "#ef4444"
            mc=st.columns(4)
            with mc[0]: st.markdown(f'<div class="mt"><div class="n">{V:.2f}</div><div class="l">V m/s</div></div>',unsafe_allow_html=True)
            with mc[1]: st.markdown(f'<div class="mt"><div class="n">{dPk:.2f}</div><div class="l">ΔP kPa</div></div>',unsafe_allow_html=True)
            with mc[2]: st.markdown(f'<div class="mt"><div class="n">{Ve:.2f}</div><div class="l">Ve m/s</div></div>',unsafe_allow_html=True)
            with mc[3]: st.markdown(f'<div class="mt"><div class="n" style="color:{clr}">{pct:.1f}%</div><div class="l">V/Ve</div></div>',unsafe_allow_html=True)
            if pct>=100: st.error("⚠️ EXCEEDS erosional limit!")
            elif pct>=80: st.warning("Near erosional limit")
            else: st.success("✅ Within limits")

# ══════ T7: PIPE DATA ══════
with t7:
    pc1,pc2=st.columns(2)
    with pc1: snps=st.selectbox("NPS",list(PIPE_SCH.keys()),index=7,key="ns2")
    with pc2: du=st.radio("Units",["inches","mm"],horizontal=True,key="pu")
    mul=25.4 if du=="mm" else 1;pipe=PIPE_SCH[snps];od=pipe["od"]
    st.markdown(f'#### NPS {snps}" — OD={od*mul:.3f} {du}')
    dr=[]
    for s in [10,40,80,160]:
        w=pipe.get(s)
        if w:
            i=od-2*w;a=math.pi/4*i**2
            if du=="mm": dr.append({"Sch":str(s),"Wall":f"{w*mul:.2f}","ID":f"{i*mul:.2f}","Area":f"{a*645.16:.1f}"})
            else: dr.append({"Sch":str(s),"Wall":f"{w:.4f}","ID":f"{i:.4f}","Area":f"{a:.4f}"})
        else: dr.append({"Sch":str(s),"Wall":"—","ID":"—","Area":"—"})
    st.dataframe(pd.DataFrame(dr),use_container_width=True,hide_index=True)

# ══════ T8: RATING ══════
with t8:
    p=st.session_state.precision;mode=st.radio("Calc:",["MAWP","Reqd thickness"],horizontal=True,key="pm")
    rc1,rc2=st.columns(2)
    with rc1:
        pnps=st.selectbox("NPS",list(PIPE_SCH.keys()),index=7,key="pn");psch=st.selectbox("Sch",[10,40,80,160],index=1,key="ps")
        pp=PIPE_SCH[pnps];pod=pp["od"];pwt=pp.get(psch)
        mat=st.selectbox("Material",list(MATERIALS.keys()),key="pmat");Sv=float(MATERIALS[mat]["S"]) if mat!="Custom" else st.number_input("S(psi)",value=20000.0,key="pSv")
        Ev=st.number_input("E",value=1.0,key="pE");Wv=st.number_input("W",value=1.0,key="pW");Yv=st.number_input("Y",value=0.4,key="pY")
        CA=st.number_input("CA(in)",value=0.0625,key="pCA");mt_p=st.number_input("Mill%",value=12.5,key="pMT")
    with rc2:
        if pwt is None: st.error("N/A")
        else:
            ta=pwt*(1-mt_p/100)-CA
            if mode=="MAWP":
                if ta<=0: st.error("Wall<=0!")
                else: MAWP=(2*Sv*Ev*Wv*ta)/(pod-2*Yv*ta);st.markdown(f'<div class="rc"><div class="l">MAWP</div><div class="v">{MAWP:.1f} psi</div></div>',unsafe_allow_html=True)
            else:
                Pd=st.number_input("Design P(psi)",value=300.0,key="pPd");tc=(Pd*pod)/(2*(Sv*Ev*Wv+Pd*Yv));tca=tc+CA;tmt=tca/(1-mt_p/100)
                ok=pwt>=tmt;c_="linear-gradient(135deg,#0ea5e9,#2563eb)" if ok else "linear-gradient(135deg,#ef4444,#dc2626)"
                st.markdown(f'<div class="rc" style="background:{c_}"><div class="l">{"✅ OK" if ok else "❌ NOT OK"}</div><div class="v">Reqd:{tmt:.4f} Avail:{pwt:.4f} in</div></div>',unsafe_allow_html=True)

# ══════ T9: PR-EOS ══════
with t9:
    p=st.session_state.precision;st.markdown(f"##### 🧬 PR-EOS Property Estimator ({eos_ch})")
    comp=st.selectbox("Component",COMP_NAMES,index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0,key="prc")
    if comp in COMP_DB:
        d=COMP_DB[comp];MW,Tc,Pc,om,Tb=d[0],d[1],d[2],d[3],d[4]
        st.caption(f"MW={MW:.3f} Tc={Tc:.2f}K Pc={Pc:.0f}kPa ω={om:.4f} Tb={Tb:.1f}K")
        pc1,pc2=st.columns(2)
        with pc1: eT=st.number_input("T(°C)",value=25.0,key="eT");eP=st.number_input("P(kPa)",value=101.325,min_value=0.01,key="eP")
        with pc2:
            props=pr_full(eT+273.15,eP,MW,Tc,Pc,om)
            if props:
                vp=props["vapor"];lp=props["liquid"]
                st.markdown(f'<div class="gc"><div class="l">{comp} @ {eT:.1f}°C</div><div class="v">Z={vp["Z"]:.6f} ρ={vp["rho"]:.4f} kg/m³</div></div>',unsafe_allow_html=True)
                rows=[["Z",f"{vp['Z']:.6f}",f"{lp['Z']:.6f}"],["Vm(L/mol)",f"{vp['Vm_Lmol']:.6f}",f"{lp['Vm_Lmol']:.6f}"],
                      ["ρ(kg/m³)",f"{vp['rho']:.4f}",f"{lp['rho']:.4f}"],["H_dep(J/mol)",f"{vp['H_dep']:.2f}",f"{lp['H_dep']:.2f}"],
                      ["φ",f"{vp['phi']:.6f}",f"{lp['phi']:.6f}"],["Tr",f"{vp['Tr']:.4f}",f"{lp['Tr']:.4f}"]]
                st.dataframe(pd.DataFrame(rows,columns=["Property","Vapor","Liquid"]),use_container_width=True,hide_index=True)
        # Plots
        with st.expander("📊 Property Plots"):
            plot_sel=st.multiselect("Select",["Z vs P","Z vs T","ρ vs T","ρ vs P","φ vs P","H_dep vs T"],default=["Z vs P","ρ vs T"],key="prplt")
            if plot_sel and st.button("Generate",key="gpr"):
                P_rng=np.linspace(max(10,eP*0.1),eP*10,50);T_rng=np.linspace(max(-200,Tb-273.15-50),min(600,Tc-273.15+100),50)
                apply_mpl()
                for pn in plot_sel:
                    if "vs P" in pn:
                        var,key="P",{"Z vs P":"Z","ρ vs P":"rho","φ vs P":"phi","H_dep vs P":"H_dep"}.get(pn,"Z")
                        xs,yv,yl=sweep_prop(comp,"P",P_rng,eT,key)
                        fig,ax=plt.subplots(figsize=(9,5));ax.plot(xs,yv,color="#0ea5e9",lw=2,label="Vapor")
                        if any(y!=v for y,v in zip(yl,yv)): ax.plot(xs,yl,color="#ef4444",lw=2,ls="--",label="Liquid")
                        ax.axvline(eP,color="#f59e0b",ls=":",alpha=0.7);ax.set_xlabel("P (kPa)");ax.set_ylabel(pn.split(" vs")[0]);ax.set_title(f"{comp} — {pn}",fontweight="bold");ax.legend();ax.grid(alpha=0.2);fig.tight_layout();st.pyplot(fig);plt.close(fig)
                    else:
                        var,key="T",{"Z vs T":"Z","ρ vs T":"rho","φ vs T":"phi","H_dep vs T":"H_dep"}.get(pn,"Z")
                        xs,yv,yl=sweep_prop(comp,"T",T_rng,eP,key)
                        fig,ax=plt.subplots(figsize=(9,5));ax.plot(xs,yv,color="#0ea5e9",lw=2,label="Vapor")
                        if any(y!=v for y,v in zip(yl,yv)): ax.plot(xs,yl,color="#ef4444",lw=2,ls="--",label="Liquid")
                        ax.axvline(eT,color="#f59e0b",ls=":",alpha=0.7);ax.set_xlabel("T (°C)");ax.set_ylabel(pn.split(" vs")[0]);ax.set_title(f"{comp} — {pn}",fontweight="bold");ax.legend();ax.grid(alpha=0.2);fig.tight_layout();st.pyplot(fig);plt.close(fig)
        # PDF
        if props:
            pdf_pr=mk_pdf(f"PR-EOS: {comp}",[{"h":f"{comp} @ {eT:.1f}°C, {eP:.1f}kPa",
                "l":[f"Z_vap={vp['Z']:.6f}, Z_liq={lp['Z']:.6f}",f"ρ_vap={vp['rho']:.4f}, ρ_liq={lp['rho']:.4f} kg/m³",
                     f"φ_vap={vp['phi']:.6f}",f"H_dep_vap={vp['H_dep']:.2f} J/mol"]}])
            if pdf_pr: st.download_button("📄 PDF",pdf_pr,f"PREOS_{comp}.pdf","application/pdf",key="pdf_pr")
    with st.expander("📖 Database"):
        sr=st.text_input("Search",key="csearch")
        fl={k:v for k,v in COMP_DB.items() if sr.lower() in k.lower()} if sr else COMP_DB
        st.dataframe(pd.DataFrame([{"Name":n,"MW":f"{v[0]:.3f}","Tc":f"{v[1]:.2f}","Pc":f"{v[2]:.0f}","ω":f"{v[3]:.4f}"} for n,v in sorted(fl.items())]),use_container_width=True,hide_index=True,height=300)

# ══════ T10: STEAM ══════
with t10:
    if not HAS_STEAM: st.error("steam_if97.py not found!")
    else:
        p=st.session_state.precision;stm=st.radio("Mode",["T&P→Props","Sat Table","Wet Steam","📊 Diagrams"],horizontal=True,key="stm")
        if stm=="T&P→Props":
            sc1,sc2=st.columns(2)
            with sc1: sT=st.number_input("T(°C)",value=200.0,max_value=590.0,key="sT");sP=st.number_input("P(kPa)",value=101.325,min_value=0.7,key="sP")
            with sc2:
                try:
                    sp=steam_props(T_C=sT,P_kPa=sP)
                    if sp:
                        st.markdown(f'<div class="rc"><div class="l">{sp["phase"]} @ {sT:.1f}°C</div><div class="v">h={sp["h"]:.2f} kJ/kg</div></div>',unsafe_allow_html=True)
                        res=[["Phase",sp["phase"]],["h(kJ/kg)",f"{sp['h']:.4f}"],["s(kJ/kg·K)",f"{sp['s']:.6f}"],["v(m³/kg)",f"{sp['v']:.6g}"],["ρ(kg/m³)",f"{sp['rho']:.4f}"]]
                        st.dataframe(pd.DataFrame(res,columns=["Prop","Value"]),use_container_width=True,hide_index=True)
                except Exception as e: st.error(str(e))
        elif stm=="Sat Table":
            ps=st.text_input("P(kPa)",value="10,50,101.325,500,1000,5000,10000,20000",key="sat_p")
            try:
                pvs=[float(v.strip()) for v in ps.split(",") if v.strip()];rows=[]
                for pk in pvs:
                    try:
                        sp=sat_props(P=pk/1000);rows.append({"P":f"{pk:.1f}","Tsat":f"{sp['T_C']:.2f}","hf":f"{sp['hf']:.2f}","hg":f"{sp['hg']:.2f}","hfg":f"{sp['hfg']:.2f}","sf":f"{sp['sf']:.4f}","sg":f"{sp['sg']:.4f}"})
                    except: pass
                if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            except: st.error("Invalid input")
        elif stm=="Wet Steam":
            wc1,wc2=st.columns(2)
            with wc1: wP=st.number_input("P(kPa)",value=500.0,min_value=0.7,max_value=22064.0,key="wP");wx=st.slider("x",0.0,1.0,0.5,0.01,key="wx")
            with wc2:
                try:
                    wp=wet_steam(wP/1000,wx)
                    st.markdown(f'<div class="gc"><div class="l">{wp["phase"]}</div><div class="v">h={wp["h"]:.2f} kJ/kg T={wp["T_C"]:.2f}°C</div></div>',unsafe_allow_html=True)
                except Exception as e: st.error(str(e))
        else:
            apply_mpl();pt=st.selectbox("Diagram",["T-H","T-S","H-S (Mollier)","P-H","P-T"],key="plt")
            with st.spinner("Building..."):
                sd=generate_saturation_data(70)
            Tc_l=[d["T_C"] for d in sd];hf_l=[d["hf"] for d in sd];hg_l=[d["hg"] for d in sd];sf_l=[d["sf"] for d in sd];sg_l=[d["sg"] for d in sd];Pk_l=[d["P_kPa"] for d in sd]
            upT=st.number_input("Point T(°C)",value=200.0,key="upT");upP=st.number_input("Point P(kPa)",value=101.325,key="upP")
            upt=None
            try: upt=steam_props(T_C=upT,P_kPa=upP)
            except: pass
            fig,ax=plt.subplots(figsize=(10,6))
            if pt=="T-H":
                ax.plot(hf_l,Tc_l,color="#0ea5e9",lw=2.5,label="Sat Liq");ax.plot(hg_l,Tc_l,color="#ef4444",lw=2.5,label="Sat Vap")
                ax.fill_betweenx(Tc_l,hf_l,hg_l,alpha=0.08,color="#94a3b8")
                if upt: ax.plot(upt["h"],upt["T_C"],"*",color="#f59e0b",ms=18,zorder=5)
                ax.set_xlabel("h (kJ/kg)");ax.set_ylabel("T (°C)");ax.set_title("T-H Diagram",fontweight="bold")
            elif pt=="T-S":
                ax.plot(sf_l,Tc_l,color="#0ea5e9",lw=2.5,label="Sat Liq");ax.plot(sg_l,Tc_l,color="#ef4444",lw=2.5,label="Sat Vap")
                if upt: ax.plot(upt["s"],upt["T_C"],"*",color="#f59e0b",ms=18,zorder=5)
                ax.set_xlabel("s (kJ/kg·K)");ax.set_ylabel("T (°C)");ax.set_title("T-S Diagram",fontweight="bold")
            elif pt=="H-S (Mollier)":
                ax.plot(sf_l,hf_l,color="#0ea5e9",lw=2.5);ax.plot(sg_l,hg_l,color="#ef4444",lw=2.5)
                for xq in [0.1,0.3,0.5,0.7,0.9]:
                    hx=[d["hf"]+xq*d["hfg"] for d in sd];sx=[d["sf"]+xq*d["sfg"] for d in sd]
                    ax.plot(sx,hx,lw=0.5,alpha=0.35,color="#94a3b8")
                if upt: ax.plot(upt["s"],upt["h"],"*",color="#f59e0b",ms=18,zorder=5)
                ax.set_xlabel("s");ax.set_ylabel("h");ax.set_title("H-S Mollier",fontweight="bold")
            elif pt=="P-H":
                ax.semilogy(hf_l,Pk_l,color="#0ea5e9",lw=2.5);ax.semilogy(hg_l,Pk_l,color="#ef4444",lw=2.5)
                if upt: ax.plot(upt["h"],upt["P_kPa"],"*",color="#f59e0b",ms=18,zorder=5)
                ax.set_xlabel("h");ax.set_ylabel("P (kPa)");ax.set_title("P-H",fontweight="bold")
            else:
                ax.semilogy(Tc_l,Pk_l,color="#0ea5e9",lw=3);ax.plot(373.946,22064,"o",color="#ef4444",ms=10,label="Critical")
                ax.set_xlabel("T (°C)");ax.set_ylabel("P (kPa)");ax.set_title("P-T Saturation",fontweight="bold")
            ax.legend(fontsize=8);ax.grid(alpha=0.2);fig.tight_layout();st.pyplot(fig);plt.close(fig)

# ══════ T11: FLASH ══════
with t11:
    p=st.session_state.precision;st.markdown(f"##### ⚡ TP Flash — {eos_ch}")
    nc=st.slider("Components",2,15,3,key="fnc");comp_names=[];z_feed=[]
    for i in range(nc):
        cc1,cc2=st.columns([3,1])
        with cc1: cn=st.selectbox(f"Comp {i+1}",COMP_NAMES,index=min(i,len(COMP_NAMES)-1),key=f"fc{i}")
        with cc2: zi=st.number_input(f"z{i+1}",value=round(1/nc,4),min_value=0.0001,max_value=1.0,format="%.4f",key=f"fz{i}")
        comp_names.append(cn);z_feed.append(zi)
    zt=sum(z_feed)
    if abs(zt-1)>0.001: st.warning(f"Sum={zt:.4f}, will normalize");z_feed=[z/zt for z in z_feed]
    fc1,fc2=st.columns(2)
    with fc1: fT=st.number_input("T(°C)",value=25.0,key="fT");fP=st.number_input("P(kPa)",value=101.325,key="fP")
    if st.button("⚡ Run Flash",type="primary",key="run_flash"):
        cl=[(COMP_DB[cn][1],COMP_DB[cn][2],COMP_DB[cn][3]) for cn in comp_names]
        with st.spinner("Flashing..."):
            beta,x,y,K,conv,iters=tp_flash(eos,cl,z_feed,fT+273.15,fP,max_iter=200)
        if conv:
            ph="Two-Phase" if 0.001<beta<0.999 else ("All Vapor" if beta>0.999 else "All Liquid")
            st.markdown(f'<div class="rc"><div class="l">{ph} | {eos_ch}</div><div class="v">V/F={beta:.6f}</div><div class="l">{iters} iterations</div></div>',unsafe_allow_html=True)
            rows=[{"Comp":comp_names[i],"z":f"{z_feed[i]:.4f}","x":f"{x[i]:.6f}","y":f"{y[i]:.6f}","K":f"{K[i]:.6f}"} for i in range(nc)]
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            apply_mpl();fig,axes=plt.subplots(1,2,figsize=(10,4))
            xp=np.arange(nc);w=0.25
            axes[0].bar(xp-w,z_feed,w,label="z",color="#64748b");axes[0].bar(xp,x,w,label="x",color="#0ea5e9");axes[0].bar(xp+w,y,w,label="y",color="#ef4444")
            axes[0].set_xticks(xp);axes[0].set_xticklabels([c[:6] for c in comp_names],rotation=45,fontsize=7);axes[0].legend(fontsize=7);axes[0].set_title("Composition");axes[0].grid(alpha=0.2)
            axes[1].barh(xp,K,color="#8b5cf6");axes[1].set_yticks(xp);axes[1].set_yticklabels([c[:6] for c in comp_names],fontsize=7)
            axes[1].axvline(1,color="#f59e0b",ls="--");axes[1].set_title("K-values");axes[1].grid(alpha=0.2)
            fig.tight_layout();st.pyplot(fig);plt.close(fig)
        else: st.error(f"Did not converge ({iters} iters)")

# ══════ T12: TERNARY / BINARY VLE ══════
with t12:
    p=st.session_state.precision;vle_mode=st.radio("Type",["🔺 Ternary","📈 Binary Pxy/Txy"],horizontal=True,key="vle_m")
    if vle_mode=="🔺 Ternary":
        st.markdown(f"##### Ternary Phase Diagram — {eos_ch}")
        tc1,tc2,tc3=st.columns(3)
        with tc1: tn1=st.selectbox("Comp 1",COMP_NAMES,index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0,key="tn1")
        with tc2: tn2=st.selectbox("Comp 2",COMP_NAMES,index=COMP_NAMES.index("Ethane") if "Ethane" in COMP_NAMES else 1,key="tn2")
        with tc3: tn3=st.selectbox("Comp 3",COMP_NAMES,index=COMP_NAMES.index("Propane") if "Propane" in COMP_NAMES else 2,key="tn3")
        ttc1,ttc2,ttc3=st.columns(3)
        with ttc1: tT=st.number_input("T(°C)",value=25.0,key="tT")
        with ttc2: tP=st.number_input("P(kPa)",value=101.325,key="tP")
        with ttc3: tN=st.slider("Grid",8,25,12,key="tN")
        if st.button("🔺 Generate",type="primary",key="gen_tern"):
            clt=[(COMP_DB[cn][1],COMP_DB[cn][2],COMP_DB[cn][3]) for cn in [tn1,tn2,tn3]]
            with st.spinner(f"Running ~{(tN+1)*(tN+2)//2} flashes..."):
                td=generate_ternary_flash_data(eos,clt,tT+273.15,tP,n_grid=tN)
            if td:
                apply_mpl();fig,ax=plt.subplots(figsize=(9,8))
                ax.plot([0,1,0.5,0],[0,0,math.sqrt(3)/2,0],color='#94a3b8',lw=2)
                lc='#e2e8f0' if dk else '#1e293b'
                ax.text(-0.05,-0.05,tn1[:10],fontsize=10,fontweight='bold',ha='center',color=lc)
                ax.text(1.05,-0.05,tn2[:10],fontsize=10,fontweight='bold',ha='center',color=lc)
                ax.text(0.5,math.sqrt(3)/2+0.04,tn3[:10],fontsize=10,fontweight='bold',ha='center',color=lc)
                tp_=[d for d in td if 0.001<d["beta"]<0.999]
                bx,by,dx,dy=[],[],[],[]
                for d in tp_:
                    bx.append(d["x_xy"][0]);by.append(d["x_xy"][1]);dx.append(d["y_xy"][0]);dy.append(d["y_xy"][1])
                    ax.plot([d["x_xy"][0],d["y_xy"][0]],[d["x_xy"][1],d["y_xy"][1]],color='#94a3b8',alpha=0.15,lw=0.5)
                ax.scatter(bx,by,color="#0ea5e9",s=12,zorder=3,label="Bubble",alpha=0.7)
                ax.scatter(dx,dy,color="#ef4444",s=12,zorder=3,label="Dew",alpha=0.7)
                for d in td: zx,zy=d["z_xy"];ax.scatter(zx,zy,color=plt.cm.RdYlBu_r(d["beta"]),s=4,alpha=0.3)
                ax.set_xlim(-0.1,1.1);ax.set_ylim(-0.1,math.sqrt(3)/2+0.1);ax.set_aspect('equal');ax.axis('off')
                ax.set_title(f"Ternary VLE — {eos_ch}\n{tT:.1f}°C, {tP:.1f} kPa",fontsize=12,fontweight='bold')
                ax.legend(fontsize=8);sm=plt.cm.ScalarMappable(cmap='RdYlBu_r',norm=plt.Normalize(0,1));sm.set_array([])
                fig.colorbar(sm,ax=ax,shrink=0.5,label="V/F");fig.tight_layout();st.pyplot(fig)
                buf=BytesIO()
                with PdfPages(buf) as pdf: pdf.savefig(fig)
                st.download_button("📄 PDF",buf.getvalue(),"ternary.pdf","application/pdf",key="pdf_tern")
                plt.close(fig)
            else: st.error("No valid results")
    else:
        st.markdown(f"##### Binary VLE — {eos_ch}")
        bc1,bc2=st.columns(2)
        with bc1: bn1=st.selectbox("Light",COMP_NAMES,index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0,key="bn1")
        with bc2: bn2=st.selectbox("Heavy",COMP_NAMES,index=COMP_NAMES.index("Propane") if "Propane" in COMP_NAMES else 2,key="bn2")
        bm=st.radio("Type",["P-xy (isothermal)","T-xy (isobaric)"],horizontal=True,key="bmode")
        if bm=="P-xy (isothermal)":
            bT=st.number_input("T(°C)",value=25.0,key="bT");bPmn=st.number_input("Pmin(kPa)",value=10.0,key="bPmn");bPmx=st.number_input("Pmax(kPa)",value=5000.0,key="bPmx")
        else:
            bP=st.number_input("P(kPa)",value=101.325,key="bP");bTmn=st.number_input("Tmin(°C)",value=-150.0,key="bTmn");bTmx=st.number_input("Tmax(°C)",value=100.0,key="bTmx")
        if st.button("📈 Generate",type="primary",key="gen_bin"):
            clb=[(COMP_DB[bn1][1],COMP_DB[bn1][2],COMP_DB[bn1][3]),(COMP_DB[bn2][1],COMP_DB[bn2][2],COMP_DB[bn2][3])]
            z1r=np.linspace(0.01,0.99,35);bub,dew=[],[]
            with st.spinner("Computing VLE..."):
                if bm=="P-xy (isothermal)":
                    for P in np.linspace(max(bPmn,1),bPmx,50):
                        for z1 in z1r:
                            try:
                                bt,x,y,K,cv,_=tp_flash(eos,clb,[z1,1-z1],bT+273.15,P,max_iter=60)
                                if cv and 0.001<bt<0.999: bub.append((x[0],P));dew.append((y[0],P))
                            except: pass
                else:
                    for T in np.linspace(bTmn+273.15,bTmx+273.15,50):
                        if T<10: continue
                        for z1 in z1r:
                            try:
                                bt,x,y,K,cv,_=tp_flash(eos,clb,[z1,1-z1],T,bP,max_iter=60)
                                if cv and 0.001<bt<0.999: bub.append((x[0],T-273.15));dew.append((y[0],T-273.15))
                            except: pass
            if bub:
                apply_mpl();fig,ax=plt.subplots(figsize=(9,6))
                bx,by=zip(*sorted(bub));dx,dy=zip(*sorted(dew))
                ax.plot(bx,by,'o',color="#0ea5e9",ms=3,label="Bubble");ax.plot(dx,dy,'o',color="#ef4444",ms=3,label="Dew")
                ax.set_xlabel(f"x,y {bn1}");ax.set_ylabel("P (kPa)" if "P-xy" in bm else "T (°C)")
                ax.set_title(f"{'P-xy' if 'P-xy' in bm else 'T-xy'}: {bn1}/{bn2} ({eos_ch})",fontweight='bold')
                ax.legend();ax.grid(alpha=0.2);fig.tight_layout();st.pyplot(fig)
                buf=BytesIO()
                with PdfPages(buf) as pdf: pdf.savefig(fig)
                st.download_button("📄 PDF",buf.getvalue(),"binary_vle.pdf","application/pdf",key="pdf_bin")
                plt.close(fig)
            else: st.warning("No two-phase data. Try wider range.")

# ═══════ FOOTER ═══════
st.markdown("---")
_f1="#e2e8f0" if dk else "#1e293b";_f2="#94a3b8" if dk else "#64748b";_f3="#64748b" if dk else "#94a3b8"
st.markdown(f'<div style="text-align:center;padding:20px 0;">'
    f'<p style="color:{_f1};font-size:1.1rem;font-weight:700;">🔬 DPSIM</p>'
    f'<p style="color:{_f2};font-size:.85rem;">Process Engineering Toolkit</p>'
    f'<p style="color:#0ea5e9;font-size:.9rem;font-weight:600;">Created by Dhawal Patel</p>'
    f'<p style="color:{_f3};font-size:.7rem;">'
    "Perry&#39;s &#8226; NIST &#8226; ASME B36.10M &#8226; B31.3 &#8226; ISA 60534 &#8226; ISO 5167 &#8226; API 520/521 &#8226; API 14E &#8226; IAPWS-IF97 &#8226; DIPPR 801"
    '</p></div>',unsafe_allow_html=True)
