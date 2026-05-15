
import math
import numpy as np
R = 0.461526  # kJ/kg-K
TC = 647.096
PC_MPA = 22.064

def Psat_T(T):
    """Saturation pressure in MPa from temperature in K. Antoine/Wagner-style screening correlation."""
    Tc = T - 273.15
    if Tc <= 0:
        return 0.000611657
    if T >= TC:
        return PC_MPA
    # Antoine segments, pressure in mmHg then MPa; adequate near common engineering range
    if Tc < 99.0:
        A,B,C = 8.07131, 1730.63, 233.426
    else:
        A,B,C = 8.14019, 1810.94, 244.485
    p_mmhg = 10**(A - B/(C+Tc))
    return p_mmhg*0.133322/1000.0

def Tsat_P(P_MPa):
    lo, hi = 273.16, TC
    for _ in range(80):
        mid = 0.5*(lo+hi)
        if Psat_T(mid) < P_MPa:
            lo = mid
        else:
            hi = mid
    return 0.5*(lo+hi)

def _sat_hfg(T):
    Tc = max(0.0, min(T-273.15, 373.946))
    return max(0.0, 2500.9 - 2.36*Tc)

def sat_props(P_MPa=None, T=None):
    if T is None:
        T = Tsat_P(P_MPa)
    if P_MPa is None:
        P_MPa = Psat_T(T)
    Tc = T - 273.15
    hf = 4.186*Tc
    hfg = _sat_hfg(T)
    hg = hf + hfg
    sf = 4.186*math.log(T/273.15) if T > 273.15 else 0.0
    sg = sf + hfg/T if T > 0 else sf
    vf = 0.001*(1 + 0.00035*Tc)
    vg = R*T/(max(P_MPa,1e-12)*1000.0)
    return {"T":T,"P":P_MPa,"hf":hf,"hg":hg,"hfg":hfg,"sf":sf,"sg":sg,"vf":vf,"vg":vg}

def region1(T, P_MPa):
    Tc = T - 273.15
    cp = 4.186
    v = 0.001*(1 + 0.00035*Tc)
    h = cp*Tc + v*(P_MPa-0.101325)*1000.0*0.02
    s = cp*math.log(T/273.15) if T > 273.15 else 0.0
    u = h - P_MPa*1000.0*v
    return {"h":h,"s":s,"v":v,"u":u,"cp":cp,"rho":1.0/v,"phase":"Subcooled Liquid"}

def region2(T, P_MPa):
    cp = 2.08
    h = 2675.5 + cp*(T-373.15)
    s = 7.354 + cp*math.log(T/373.15) - R*math.log(max(P_MPa,1e-12)/0.101325)
    v = R*T/(max(P_MPa,1e-12)*1000.0)
    u = h - P_MPa*1000.0*v
    return {"h":h,"s":s,"v":v,"u":u,"cp":cp,"rho":1.0/v,"phase":"Superheated Vapor"}

def wet_steam(P_MPa, x):
    x = max(0.0, min(1.0, float(x)))
    sp = sat_props(P_MPa=P_MPa)
    h = sp["hf"] + x*sp["hfg"]
    s = sp["sf"] + x*(sp["sg"]-sp["sf"])
    v = sp["vf"] + x*(sp["vg"]-sp["vf"])
    u = h - P_MPa*1000.0*v
    return {"T":sp["T"],"P":P_MPa,"h":h,"s":s,"v":v,"u":u,"cp":None,"rho":1.0/v,"phase":f"Wet Steam x={x:.3f}"}

def steam_props(T, P_MPa):
    ps = Psat_T(T)
    if abs(P_MPa-ps)/max(ps,1e-9) <= 0.02:
        return wet_steam(P_MPa, 1.0)
    if P_MPa > ps:
        r = region1(T, P_MPa)
    else:
        r = region2(T, P_MPa)
    r.update({"T":T,"P":P_MPa})
    return r

def gen_sat_data(n=120):
    Ts = np.linspace(273.16, 646.5, n)
    return [sat_props(T=float(T)) for T in Ts]
