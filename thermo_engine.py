
import numpy as np
R = 8.314462618  # J/mol-K

class CubicEOS:
    """Generic cubic EOS: P=RT/(V-b)-a(T)/((V+d1*b)*(V+d2*b))."""
    def __init__(self, eos="PR", custom=None):
        self.eos = eos
        self.custom = custom or {}

    def constants(self, omega=0.0):
        if self.eos == "SRK":
            return 0.42748, 0.08664, 1.0, 0.0, 0.480 + 1.574*omega - 0.176*omega**2
        if self.eos == "van der Waals":
            return 27.0/64.0, 1.0/8.0, 0.0, 0.0, 0.0
        if self.eos == "User-Defined":
            c = self.custom
            kap = c.get("c0",0.37464) + c.get("c1",1.54226)*omega + c.get("c2",-0.26992)*omega**2
            return c.get("Omega_a",0.45724), c.get("Omega_b",0.07780), c.get("delta_1",1+np.sqrt(2)), c.get("delta_2",1-np.sqrt(2)), kap
        return 0.45724, 0.07780, 1+np.sqrt(2), 1-np.sqrt(2), 0.37464 + 1.54226*omega - 0.26992*omega**2

    def ai_bi(self, T, comp):
        MW, Tc, Pc_kPa, omega, Tb = comp
        Oa, Ob, d1, d2, kappa = self.constants(omega)
        Tr = T / Tc
        alpha = 1.0 if self.eos == "van der Waals" else (1.0 + kappa*(1.0-np.sqrt(Tr)))**2
        a = Oa * R**2 * Tc**2 / (Pc_kPa*1000.0) * alpha
        b = Ob * R * Tc / (Pc_kPa*1000.0)
        return a, b

    def params(self, T, P_kPa, comp):
        a, b = self.ai_bi(T, comp)
        A = a*(P_kPa*1000.0)/(R*T)**2
        B = b*(P_kPa*1000.0)/(R*T)
        return A, B, a, b

    def mix_params(self, T, comps, z, kij=None):
        z = np.array(z, dtype=float); z = z/z.sum()
        a = np.array([self.ai_bi(T, c)[0] for c in comps])
        b = np.array([self.ai_bi(T, c)[1] for c in comps])
        kij = np.zeros((len(z),len(z))) if kij is None else np.array(kij, dtype=float)
        aij = np.sqrt(np.outer(a,a))*(1-kij)
        am = float(z @ aij @ z)
        bm = float(z @ b)
        return am, bm, a, b, aij

    def solve_Z(self, T, P_kPa, comps, z=None):
        if z is None:
            comps = [comps]
            z = [1.0]
        am, bm, a, b, aij = self.mix_params(T, comps, z)
        A = am*(P_kPa*1000.0)/(R*T)**2
        B = bm*(P_kPa*1000.0)/(R*T)
        _, _, d1, d2, _ = self.constants(0.0)
        c3 = 1.0
        c2 = B*(d1+d2-1.0) - 1.0
        c1 = A + B**2*d1*d2 - B**2*(d1+d2) - B*(d1+d2)
        c0 = -(A*B + d1*d2*B**2*(B+1.0))
        roots = np.roots([c3,c2,c1,c0])
        real = np.sort(np.real(roots[np.isclose(np.imag(roots),0.0,atol=1e-8)]))
        real = real[real > B + 1e-10]
        if len(real) == 0:
            return np.array([max(B+1e-8, 1.0)])
        return real

    def ln_phi_i(self, T, P_kPa, comps, z, phase="vapor"):
        z = np.array(z, dtype=float); z = z/z.sum()
        P = P_kPa*1000.0
        am, bm, a, b, aij = self.mix_params(T, comps, z)
        A = am*P/(R*T)**2
        B = bm*P/(R*T)
        Zs = self.solve_Z(T, P_kPa, comps, z)
        Z = Zs[-1] if phase == "vapor" else Zs[0]
        _, _, d1, d2, _ = self.constants(0.0)
        sum_aij = aij @ z
        if abs(d1-d2) < 1e-12:
            I = B/Z if Z != 0 else 0.0
        else:
            I = np.log((Z+d1*B)/(Z+d2*B))/(d1-d2)
        lnphi = []
        for i in range(len(z)):
            t1 = b[i]/bm*(Z-1.0) - np.log(max(Z-B,1e-30))
            t2 = (A/B)*(2.0*sum_aij[i]/am - b[i]/bm)*I if B != 0 and am != 0 else 0.0
            lnphi.append(t1 - t2)
        return np.array(lnphi), float(Z)

    def K_wilson(self, T, P_kPa, comps):
        K = []
        for c in comps:
            MW, Tc, Pc_kPa, omega, Tb = c
            K.append((Pc_kPa/P_kPa)*np.exp(5.373*(1+omega)*(1-Tc/T)))
        return np.array(K, dtype=float)

def rr_value(beta, z, K):
    return float(np.sum(z*(K-1.0)/(1.0+beta*(K-1.0))))

def solve_rr(z, K):
    z = np.array(z, dtype=float); K = np.array(K, dtype=float)
    if np.sum(z*K) <= 1.0:
        return 0.0
    if np.sum(z/K) <= 1.0:
        return 1.0
    lo, hi, beta = 0.0, 1.0, 0.5
    for _ in range(100):
        f = rr_value(beta, z, K)
        df = -np.sum(z*(K-1.0)**2/(1.0+beta*(K-1.0))**2)
        nb = beta - f/df if df != 0 else 0.5*(lo+hi)
        if (not np.isfinite(nb)) or nb <= lo or nb >= hi:
            nb = 0.5*(lo+hi)
        if rr_value(lo, z, K)*f <= 0:
            hi = beta
        else:
            lo = beta
        if abs(nb-beta) < 1e-12:
            return float(nb)
        beta = nb
    return float(beta)

def tp_flash(T, P_kPa, comps, z, eos=None, max_iter=200, tol=1e-8):
    eos = eos or CubicEOS("PR")
    z = np.array(z, dtype=float); z = z/z.sum()
    K = np.clip(eos.K_wilson(T, P_kPa, comps), 1e-8, 1e8)
    if np.sum(z*K) <= 1.0:
        return {"beta":0.0,"x":z,"y":z,"K":K,"phase":"All Liquid","converged":True,"iterations":0}
    if np.sum(z/K) <= 1.0:
        return {"beta":1.0,"x":z,"y":z,"K":K,"phase":"All Vapor","converged":True,"iterations":0}
    beta = 0.5
    for it in range(1, max_iter+1):
        beta = solve_rr(z, K)
        x = z/(1.0+beta*(K-1.0)); y = K*x
        x = x/x.sum(); y = y/y.sum()
        lnL, _ = eos.ln_phi_i(T, P_kPa, comps, x, "liquid")
        lnV, _ = eos.ln_phi_i(T, P_kPa, comps, y, "vapor")
        Knew = np.clip(np.exp(lnL-lnV), 1e-8, 1e8)
        err = float(np.max(np.abs(np.log(Knew/K))))
        K = 0.5*K + 0.5*Knew
        if err < tol:
            return {"beta":float(beta),"x":x,"y":y,"K":K,"phase":"Two-Phase","converged":True,"iterations":it}
    return {"beta":float(beta),"x":x,"y":y,"K":K,"phase":"Two-Phase","converged":False,"iterations":max_iter}

def ternary_grid(n=15):
    pts = []
    for i in range(n+1):
        for j in range(n+1-i):
            pts.append((i/n, j/n, 1-i/n-j/n))
    return np.array(pts, dtype=float)

def ternary_xy(a, b, c):
    return b + 0.5*c, (np.sqrt(3)/2.0)*c
