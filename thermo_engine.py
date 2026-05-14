"""DPSIM Thermodynamics Engine — Multi-EOS + Flash + Ternary
Supports: Peng-Robinson, SRK, van der Waals, User-Defined
Flash: Rachford-Rice TP-flash with successive substitution
Author: Dhawal Patel (DPSIM)"""
import math
import numpy as np

R = 8.314  # J/(mol·K)

class CubicEOS:
    """Generic cubic EOS: P = RT/(V-b) - a(T)/[(V+d1*b)(V+d2*b)]
    PR:  d1=1+√2, d2=1-√2
    SRK: d1=1,    d2=0
    vdW: d1=0,    d2=0"""

    def __init__(self, eos_type="PR", custom_params=None):
        self.eos_type = eos_type
        if eos_type == "PR":
            self.Omega_a = 0.45724; self.Omega_b = 0.07780
            self.d1 = 1 + math.sqrt(2); self.d2 = 1 - math.sqrt(2)
            self.kappa_fn = lambda w: 0.37464 + 1.54226*w - 0.26992*w**2
        elif eos_type == "SRK":
            self.Omega_a = 0.42748; self.Omega_b = 0.08664
            self.d1 = 1.0; self.d2 = 0.0
            self.kappa_fn = lambda w: 0.480 + 1.574*w - 0.176*w**2
        elif eos_type == "vdW":
            self.Omega_a = 0.421875; self.Omega_b = 0.125
            self.d1 = 0.0; self.d2 = 0.0
            self.kappa_fn = lambda w: 0.0
        elif eos_type == "Custom" and custom_params:
            cp = custom_params
            self.Omega_a = cp.get("Omega_a", 0.45724)
            self.Omega_b = cp.get("Omega_b", 0.07780)
            self.d1 = cp.get("d1", 1 + math.sqrt(2))
            self.d2 = cp.get("d2", 1 - math.sqrt(2))
            kc = cp.get("kappa_coeffs", [0.37464, 1.54226, -0.26992])
            self.kappa_fn = lambda w, c=kc: c[0] + c[1]*w + c[2]*w**2
        else:
            raise ValueError(f"Unknown EOS: {eos_type}")

    def params(self, Tc, Pc_kPa, omega, T):
        Pc = Pc_kPa * 1000
        kappa = self.kappa_fn(omega)
        if self.eos_type == "vdW":
            alpha = 1.0; da = 0.0
        else:
            alpha = (1 + kappa * (1 - math.sqrt(T / Tc))) ** 2
            da = -self.Omega_a * R**2 * Tc**2 / Pc * kappa * math.sqrt(alpha / (T * Tc)) if T > 0 else 0
        a = self.Omega_a * R**2 * Tc**2 / Pc * alpha
        b = self.Omega_b * R * Tc / Pc
        return a, b, da

    def mix_params(self, comp_list, y, T, kij=None):
        n = len(comp_list)
        al, bl = [], []
        for Tc, Pc, om in comp_list:
            a, b, _ = self.params(Tc, Pc, om, T)
            al.append(a); bl.append(b)
        am = 0.0
        for i in range(n):
            for j in range(n):
                k = kij[i][j] if kij else 0.0
                am += y[i] * y[j] * math.sqrt(al[i] * al[j]) * (1 - k)
        bm = sum(y[i] * bl[i] for i in range(n))
        return am, bm, al, bl

    def solve_Z(self, am, bm, T, P_kPa):
        P = P_kPa * 1000
        A = am * P / (R**2 * T**2)
        B = bm * P / (R * T)
        s = self.d1 + self.d2
        p = self.d1 * self.d2
        c2 = -(1 + B - s * B)
        c1 = A + p * B**2 - s * B * (1 + B)
        c0 = -(A * B + p * B**2 * (1 + B))
        roots = np.roots([1, c2, c1, c0])
        rr = sorted([r.real for r in roots if abs(r.imag) < 1e-10 and r.real > 0])
        if not rr: return None, None
        Zv = max(rr)
        Zl = min(rr) if len(rr) > 1 else Zv
        return Zv, Zl

    def ln_phi_i(self, i, y, comp_list, T, P_kPa, Z, kij=None):
        n = len(comp_list)
        am, bm, al, bl = self.mix_params(comp_list, y, T, kij)
        P = P_kPa * 1000
        B = bm * P / (R * T)
        A = am * P / (R**2 * T**2)
        bi = bl[i]
        ai_sum = sum(y[j] * math.sqrt(al[i] * al[j]) * (1 - (kij[i][j] if kij else 0)) for j in range(n))
        d1, d2 = self.d1, self.d2
        if abs(d1 - d2) > 1e-10:
            ln1 = Z + d1 * B; ln2 = Z + d2 * B
            if ln1 <= 0 or ln2 <= 0: return 0.0
            L = math.log(ln1 / ln2) / (d1 - d2)
        else:
            L = B / (Z + d1 * B) if (Z + d1 * B) > 0 else 0
        return bi / bm * (Z - 1) - math.log(max(Z - B, 1e-30)) - A / B * (2 * ai_sum / am - bi / bm) * L

    def K_wilson(self, comp_list, T, P_kPa):
        K = []
        for Tc, Pc_kPa, omega in comp_list:
            K.append(Pc_kPa / P_kPa * math.exp(5.373 * (1 + omega) * (1 - Tc / T)))
        return K

def rachford_rice(z, K):
    n = len(z)
    def RR(beta):
        return sum(z[i] * (K[i] - 1) / (1 + beta * (K[i] - 1)) for i in range(n))
    def dRR(beta):
        return -sum(z[i] * (K[i] - 1)**2 / (1 + beta * (K[i] - 1))**2 for i in range(n))
    K_max = max(K); K_min = min(K)
    if K_min >= 1.0: return 1.0, z[:], z[:]
    if K_max <= 1.0: return 0.0, z[:], z[:]
    beta_min = max(1 / (1 - K_max) + 1e-10, 0.0)
    beta_max = min(1 / (1 - K_min) - 1e-10, 1.0)
    beta = (beta_min + beta_max) / 2
    for _ in range(100):
        f = RR(beta); df = dRR(beta)
        if abs(df) < 1e-30: break
        bn = beta - f / df
        if bn < beta_min or bn > beta_max:
            if f > 0: beta_min = beta
            else: beta_max = beta
            bn = (beta_min + beta_max) / 2
        beta = bn
        if abs(f) < 1e-12: break
    beta = max(0.0, min(1.0, beta))
    x = [z[i] / (1 + beta * (K[i] - 1)) for i in range(n)]
    y = [K[i] * x[i] for i in range(n)]
    sx = sum(x); sy = sum(y)
    x = [xi / sx for xi in x]; y = [yi / sy for yi in y]
    return beta, x, y

def tp_flash(eos, comp_list, z, T, P_kPa, kij=None, max_iter=100, tol=1e-8):
    n = len(z)
    K = eos.K_wilson(comp_list, T, P_kPa)
    converged = False
    for it in range(max_iter):
        beta, x, y = rachford_rice(z, K)
        am_l, bm_l, _, _ = eos.mix_params(comp_list, x, T, kij)
        am_v, bm_v, _, _ = eos.mix_params(comp_list, y, T, kij)
        Zv, _ = eos.solve_Z(am_v, bm_v, T, P_kPa)
        _, Zl = eos.solve_Z(am_l, bm_l, T, P_kPa)
        if Zv is None or Zl is None: break
        K_new = []
        for i in range(n):
            ln_phi_l = eos.ln_phi_i(i, x, comp_list, T, P_kPa, Zl, kij)
            ln_phi_v = eos.ln_phi_i(i, y, comp_list, T, P_kPa, Zv, kij)
            K_new.append(math.exp(ln_phi_l - ln_phi_v))
        err = sum((math.log(K_new[i] / K[i]))**2 for i in range(n) if K[i] > 0) / n
        K = K_new
        if err < tol: converged = True; break
    beta, x, y = rachford_rice(z, K)
    return beta, x, y, K, converged, it + 1

def ternary_to_xy(a, b, c):
    x = 0.5 * (2 * b + c) / (a + b + c)
    y = (math.sqrt(3) / 2) * c / (a + b + c)
    return x, y

def generate_ternary_flash_data(eos, comp_list, T, P_kPa, kij=None, n_grid=20):
    results = []
    for i in range(n_grid + 1):
        for j in range(n_grid + 1 - i):
            k = n_grid - i - j
            z1 = max(i / n_grid, 0.001); z2 = max(j / n_grid, 0.001); z3 = max(k / n_grid, 0.001)
            zt = z1 + z2 + z3; z = [z1/zt, z2/zt, z3/zt]
            try:
                beta, x, y, K, conv, _ = tp_flash(eos, comp_list, z, T, P_kPa, kij, max_iter=50)
                if conv:
                    results.append({"z":z,"x":x,"y":y,"beta":beta,"K":K,
                        "z_xy":ternary_to_xy(*z),"x_xy":ternary_to_xy(*x),"y_xy":ternary_to_xy(*y)})
            except: pass
    return results
