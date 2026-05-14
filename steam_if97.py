"""IAPWS-IF97 Steam Properties — Regions 1, 2, 4
Matches ASME Steam Tables. Valid: 273.15-863.15 K, up to 100 MPa
Author: Dhawal Patel (DPSIM)"""
import math

R = 0.461526  # kJ/(kg·K)

# Region 4 — Saturation
_n4 = [0.11670521452767e4,-0.72421316703206e6,-0.17073846940092e2,
       0.12020824702470e5,-0.32325550322333e7,0.14915108613530e2,
       -0.48232657361591e4,0.40511340542057e6,-0.23855557567849,0.65017534844798e3]

def Psat_T(T):
    th=T+_n4[8]/(T-_n4[9]); A=th**2+_n4[0]*th+_n4[1]; B=_n4[2]*th**2+_n4[3]*th+_n4[4]; C=_n4[5]*th**2+_n4[6]*th+_n4[7]
    return (2*C/(-B+math.sqrt(B**2-4*A*C)))**4

def Tsat_P(P):
    beta=P**0.25; E=beta**2+_n4[2]*beta+_n4[5]; F=_n4[0]*beta**2+_n4[3]*beta+_n4[6]; G=_n4[1]*beta**2+_n4[4]*beta+_n4[7]
    D=2*G/(-F-math.sqrt(F**2-4*E*G))
    return (_n4[9]+D-math.sqrt((_n4[9]+D)**2-4*(_n4[8]+_n4[9]*D)))/2

# Region 1 — Liquid
_I1=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,2,2,2,2,2,3,3,3,4,4,4,5,8,8,21,23,29,30,31,32]
_J1=[-2,-1,0,1,2,3,4,5,-9,-7,-1,0,1,3,-3,0,1,3,17,-4,0,6,-5,-2,10,-8,-11,-6,-29,-31,-38,-39,-40,-41]
_n1=[0.14632971213167e0,-0.84548187169114e0,-0.37563603672040e1,0.33855169168385e1,-0.95791963387872e0,
     0.15772038513228e0,-0.16616417199501e-1,0.81214629983568e-3,0.28319080123804e-3,-0.60706301565874e-3,
     -0.18990068218419e-1,-0.32529748770505e-1,-0.21841717175414e-1,-0.52838357969930e-4,-0.47184321073267e-3,
     -0.30001780793026e-3,0.47661393906987e-4,-0.44141845330846e-5,-0.72694996297594e-15,-0.31679644845054e-4,
     -0.28270797985312e-5,-0.85205128120103e-9,-0.22425281908000e-5,-0.65171222895601e-6,-0.14341729937924e-12,
     -0.40516996860117e-6,-0.12734301741682e-8,-0.17424871230634e-9,-0.68762131295531e-18,0.14478307828521e-19,
     0.26335781662795e-22,-0.11947622640071e-22,0.18228094581404e-23,-0.93537087292458e-25]

def region1(T, P):
    pi=P/16.53; tau=1386.0/T
    g=gt=gp=gtt=0.0
    for i in range(34):
        x=_n1[i]*(7.1-pi)**_I1[i]*(tau-1.222)**_J1[i]
        g+=x
        if _J1[i]!=0: gt+=x*_J1[i]/(tau-1.222)
        if _I1[i]!=0: gp+=-x*_I1[i]/(7.1-pi)
        if _J1[i]>1 or _J1[i]<0: gtt+=x*_J1[i]*(_J1[i]-1)/(tau-1.222)**2
    h=tau*gt*R*T; s=(tau*gt-g)*R; v=gp*R*T/(P*1000); u=(tau*gt-pi*gp)*R*T
    cp=-tau**2*gtt*R; rho=P*1000/(gp*R*T)
    return {"T_K":T,"T_C":T-273.15,"P_MPa":P,"P_kPa":P*1000,"P_bar":P*10,
            "h":h,"s":s,"v":1/rho,"u":u,"cp":cp,"rho":rho,"phase":"Liquid","x":0.0}

# Region 2 — Vapor
_J0_2=[0,1,-5,-4,-3,-2,-1,2,3]
_n0_2=[-0.96927686500217e1,0.10086655024209e2,-0.56087911283020e-2,0.71452738081455e-1,
       -0.40710498223928e0,0.14240819171444e1,-0.43839511319450e1,-0.28408632460772e0,0.21268463753307e-1]
_I2=[1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,5,6,6,6,7,7,7,8,8,9,10,10,10,16,16,18,20,20,20,21,22,23,24,24,24]
_J2=[0,1,2,3,6,1,2,4,7,36,0,1,3,6,35,1,2,3,7,3,16,35,0,11,25,8,36,13,4,10,14,29,50,57,20,35,48,21,53,39,26,40,58]
_n2=[-0.17731742473213e-2,-0.17834862292358e-1,-0.45996013696365e-1,-0.57581259083432e-1,-0.50325278727930e-1,
     -0.33032641670203e-4,-0.18948987516315e-3,-0.39392777243355e-2,-0.43797295650573e-1,-0.26674547914087e-4,
     0.20481737692309e-7,0.43870667284435e-6,-0.32277677238570e-4,-0.15033924542148e-2,-0.40668253562649e-4,
     -0.78847309559367e-9,0.12790717852285e-7,0.48225372718507e-6,0.22922076337661e-5,-0.16714766451061e-10,
     -0.21171472321355e-2,-0.23895741934104e2,-0.59059564324270e-17,-0.12621808899101e-5,-0.38946842435739e-1,
     0.11256211360459e-10,-0.82311340897998e1,0.19809712802088e-7,0.10406965210174e-18,-0.10234747095929e-12,
     -0.10018179379511e-8,-0.80882908646985e-10,0.10693031879409e0,-0.33662250574171e0,0.89185845355421e-24,
     0.30629316876232e-12,-0.42002467698208e-5,-0.59056029685639e-25,0.37826947613457e-5,-0.12768608934681e-14,
     0.73087610595061e-28,0.55414715350778e-16,-0.94369707241210e-6]

def region2(T, P):
    pi=P/1.0; tau=540.0/T
    g0=math.log(pi); g0t=0.0; g0tt=0.0
    for j in range(9):
        g0+=_n0_2[j]*tau**_J0_2[j]
        if _J0_2[j]!=0: g0t+=_n0_2[j]*_J0_2[j]*tau**(_J0_2[j]-1)
        if _J0_2[j]!=0 and _J0_2[j]!=1: g0tt+=_n0_2[j]*_J0_2[j]*(_J0_2[j]-1)*tau**(_J0_2[j]-2)
    gr=grt=grp=grtt=0.0
    for i in range(43):
        x=_n2[i]*pi**_I2[i]*(tau-0.5)**_J2[i]
        gr+=x
        if _J2[i]!=0: grt+=x*_J2[i]/(tau-0.5)
        grp+=x*_I2[i]/pi if pi>0 else 0
        if _J2[i]>1 or _J2[i]<0: grtt+=x*_J2[i]*(_J2[i]-1)/(tau-0.5)**2
    h=R*T*tau*(g0t+grt); s=R*(tau*(g0t+grt)-(g0+gr))
    v=R*T/(P*1000)*pi*(1/pi+grp); cp=-R*tau**2*(g0tt+grtt)
    rho=1/v if v>0 else 0; u=h-P*v*1000
    return {"T_K":T,"T_C":T-273.15,"P_MPa":P,"P_kPa":P*1000,"P_bar":P*10,
            "h":h,"s":s,"v":v,"u":u,"cp":cp,"rho":rho,"phase":"Vapor","x":1.0}

def sat_props(T=None, P=None):
    if T is not None: Ps=Psat_T(T); Ts=T
    elif P is not None: Ts=Tsat_P(P); Ps=P
    else: return None
    liq=region1(Ts,Ps); vap=region2(Ts,Ps)
    return {"T_K":Ts,"T_C":Ts-273.15,"P_MPa":Ps,"P_kPa":Ps*1000,
            "hf":liq["h"],"hg":vap["h"],"hfg":vap["h"]-liq["h"],
            "sf":liq["s"],"sg":vap["s"],"sfg":vap["s"]-liq["s"],
            "vf":liq["v"],"vg":vap["v"],"uf":liq["u"],"ug":vap["u"],
            "cpf":liq["cp"],"cpg":vap["cp"],"rhof":liq["rho"],"rhog":vap["rho"],
            "liquid":liq,"vapor":vap}

def wet_steam(P, x):
    sp=sat_props(P=P); h=sp["hf"]+x*sp["hfg"]; s=sp["sf"]+x*sp["sfg"]
    v=sp["vf"]+x*(sp["vg"]-sp["vf"]); u=sp["uf"]+x*(sp["ug"]-sp["uf"])
    return {"T_K":sp["T_K"],"T_C":sp["T_C"],"P_MPa":P,"P_kPa":P*1000,
            "h":h,"s":s,"v":v,"u":u,"rho":1/v if v>0 else 0,"x":x,
            "phase":f"Wet Steam (x={x:.4f})"}

def steam_props(T_C=None, P_kPa=None, x=None):
    if P_kPa is not None and x is not None and 0<=x<=1:
        return wet_steam(P_kPa/1000, x)
    if T_C is None or P_kPa is None: return None
    T=T_C+273.15; P=P_kPa/1000
    if T<273.15 or T>863.15 or P<0.000611 or P>100: return None
    try: Ps=Psat_T(min(T,647.096))
    except: Ps=22.064
    if T<=623.15:
        if P>Ps*1.00001: return region1(T,P)
        elif P<Ps*0.99999: return region2(T,P)
        else: return sat_props(T=T)["liquid"]
    else: return region2(T,P)

def generate_saturation_data(n_points=100):
    temps=[273.15+1+i*(647.0-274.15)/(n_points-1) for i in range(n_points)]
    data=[]
    for T in temps:
        try:
            sp=sat_props(T=T)
            if sp: data.append(sp)
        except: continue
    return data
