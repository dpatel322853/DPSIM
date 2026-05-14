# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)
dk = st.session_state.dark_mode

with st.sidebar:
    st.markdown("## 🔬 DPSIM")
    st.caption("DP's Process Simulation & Engineering Toolkit")
    st.markdown("---")
    sb_prec = st.select_slider("🔢 Decimal Precision", [2,3,4,5,6,8], value=4, key="sb_prec")
    st.session_state.precision = sb_prec
    st.markdown("---")
    sb_dm = st.toggle("🌙 Dark Mode", value=dk, key="sb_dm")
    if sb_dm != dk:
        st.session_state.dark_mode = sb_dm
        st.rerun()
    st.markdown("---")
    st.markdown("### 🔬 Equation of State")
    sb_eos = st.selectbox("EOS", ["Peng-Robinson","SRK","van der Waals","User-Defined"], key="sb_eos")
    eos_cp = None
    if sb_eos == "Peng-Robinson": eos_t = "PR"
    elif sb_eos == "SRK": eos_t = "SRK"
    elif sb_eos == "van der Waals": eos_t = "vdW"
    else:
        eos_t = "Custom"
        sb_Oa = st.number_input("Ωa", value=0.45724, format="%.5f", key="sb_Oa")
        sb_Ob = st.number_input("Ωb", value=0.07780, format="%.5f", key="sb_Ob")
        sb_d1 = st.number_input("δ₁", value=1+math.sqrt(2), format="%.6f", key="sb_d1")
        sb_d2 = st.number_input("δ₂", value=1-math.sqrt(2), format="%.6f", key="sb_d2")
        st.caption("κ(ω) = c₀ + c₁ω + c₂ω²")
        sb_k0 = st.number_input("c₀", value=0.37464, format="%.5f", key="sb_k0")
        sb_k1 = st.number_input("c₁", value=1.54226, format="%.5f", key="sb_k1")
        sb_k2 = st.number_input("c₂", value=-0.26992, format="%.5f", key="sb_k2")
        eos_cp = {"Oa":sb_Oa,"Ob":sb_Ob,"d1":sb_d1,"d2":sb_d2,"kc":[sb_k0,sb_k1,sb_k2]}
    eos = CubicEOS(eos_t, eos_cp)
    st.caption(f"Active: {sb_eos}")
    st.markdown("---")
    st.markdown("### 🕒 Recent")
    for h in st.session_state.history[:10]:
        st.markdown(f'<div class="hi">{h}</div>', unsafe_allow_html=True)
    if not st.session_state.history:
        st.caption("No conversions yet")

# ═══════════════════════════════════════
# MAIN TITLE + TABS
# ═══════════════════════════════════════
st.markdown("## 🔬 DPSIM — Process Engineering Toolkit")
p = st.session_state.precision

tab1, tab2, tab3, tab4 = st.tabs(["🔄 Unit Conversion", "🔧 Sizing", "🧬 Property Estimation", "🌊 Steam Table"])

# ═══════════════════════════════════════
# TAB 1: UNIT CONVERSION
# ═══════════════════════════════════════
with tab1:
    uc_cat = st.selectbox("Select Property", list(U.keys()), key="uc_cat")
    cat_data = U[uc_cat]

    if uc_cat == "Temperature":
        uc1, uc_sw, uc2 = st.columns([4,1,4])
        t_units = cat_data["units"]
        with uc1:
            uc_fu = st.selectbox("From", t_units, key="uc_fu")
            uc_val = st.number_input("Value", value=100.0, format="%.6g", key="uc_val")
        with uc_sw:
            st.markdown(""); st.markdown(""); st.markdown("")
            if st.button("🔄", key="uc_swap", use_container_width=True):
                pass  # visual only, user picks units
        with uc2:
            uc_tu = st.selectbox("To", t_units, index=1, key="uc_tu")
            res = temp_cv(uc_val, uc_fu, uc_tu)
            st.text_input("Result", value=f"{res:.{p}f}", disabled=True, key="uc_res")
        st.markdown(f'<div class="rc"><div class="l">{uc_cat}</div><div class="v">{uc_val:.{p}f} {uc_fu} = {res:.{p}f} {uc_tu}</div></div>', unsafe_allow_html=True)
        add_hist(f"{uc_val:.6g} {uc_fu} → {res:.6g} {uc_tu}")

    elif uc_cat == "Gas Flow (Std/Norm)":
        gf_mode = st.radio("Mode", ["Std/Normal ↔ Std/Normal", "Actual ↔ Reference"], horizontal=True, key="uc_gfm")
        if gf_mode == "Std/Normal ↔ Std/Normal":
            gl = list(cat_data.keys())
            gc1, _, gc2 = st.columns([4,1,4])
            with gc1:
                gfu = st.selectbox("From", gl, key="uc_gfu")
                gv = st.number_input("Value", value=1000.0, format="%.6g", key="uc_gfv")
            with gc2:
                gtu = st.selectbox("To", gl, index=3, key="uc_gtu")
                gr = gv * cat_data[gfu] / cat_data[gtu]
                st.text_input("Result", f"{gr:.{p}f}", disabled=True, key="uc_gfr")
            st.markdown(f'<div class="gc"><div class="l">Gas Flow</div><div class="v">{gv:.{p}f} {gfu} = {gr:.{p}f} {gtu}</div></div>', unsafe_allow_html=True)
            add_hist(f"{gv:.6g} {gfu} → {gr:.6g} {gtu}")
        else:
            gf_dir = st.radio("Direction", ["Actual → Reference", "Reference → Actual"], horizontal=True, key="uc_gfd")
            ac1, ac2 = st.columns(2)
            with ac1:
                gf_ref = st.selectbox("Reference Basis", list(REF_COND.keys()), key="uc_gfref")
                gc_t1, gc_t2 = st.columns([3,1])
                with gc_t1:
                    gf_T = st.number_input("Actual Temperature", value=25.0, key="uc_gfT")
                with gc_t2:
                    gf_Tu = st.selectbox("Unit", ["°C","°F","K"], key="uc_gfTu")
                gf_Tk = to_C(gf_T, gf_Tu) + 273.15
                gc_p1, gc_p2 = st.columns([3,1])
                with gc_p1:
                    gf_P = st.number_input("Actual Pressure", value=500.0, min_value=0.01, key="uc_gfP")
                with gc_p2:
                    gf_Pu = st.selectbox("Unit", list(P_U.keys()), key="uc_gfPu")
                gf_Pk = to_kPa(gf_P, gf_Pu)
                gf_Z = st.number_input("Z (compressibility)", value=1.0, min_value=0.01, max_value=2.0, format="%.4f", key="uc_gfZ")
            with ac2:
                ru = "Nm3/h" if "Normal" in gf_ref else "Sm3/h"
                if gf_dir == "Actual → Reference":
                    gf_Qa = st.number_input("Actual Flow (m³/h)", value=100.0, key="uc_gfQa")
                    gf_Qr = act_to_ref(gf_Qa, gf_Tk, gf_Pk, gf_Z, gf_ref)
                    st.markdown(f'<div class="gc"><div class="l">Actual → Reference</div><div class="v">{gf_Qa:.{p}f} m³/h = {gf_Qr:.{p}f} {ru}</div><div class="l">T={gf_Tk:.1f}K | P={gf_Pk:.1f}kPa | Z={gf_Z:.4f}</div></div>', unsafe_allow_html=True)
                else:
                    gf_Qr2 = st.number_input(f"Reference Flow ({ru})", value=100.0, key="uc_gfQr")
                    gf_Qa2 = ref_to_act(gf_Qr2, gf_Tk, gf_Pk, gf_Z, gf_ref)
                    st.markdown(f'<div class="gc"><div class="l">Reference → Actual</div><div class="v">{gf_Qr2:.{p}f} {ru} = {gf_Qa2:.{p}f} m³/h (actual)</div><div class="l">T={gf_Tk:.1f}K | P={gf_Pk:.1f}kPa | Z={gf_Z:.4f}</div></div>', unsafe_allow_html=True)
    else:
        unit_list = list(cat_data.keys())
        uc1, uc_sw, uc2 = st.columns([4,1,4])
        with uc1:
            uc_fu2 = st.selectbox("From", unit_list, key="uc_fu2")
            uc_val2 = st.number_input("Value", value=1.0, format="%.6g", key="uc_val2")
        with uc_sw:
            st.markdown(""); st.markdown(""); st.markdown("")
            st.button("🔄", key="uc_swap2", use_container_width=True)
        with uc2:
            uc_tu2 = st.selectbox("To", unit_list, index=min(1,len(unit_list)-1), key="uc_tu2")
            res2 = uc_val2 * cat_data[uc_fu2] / cat_data[uc_tu2]
            st.text_input("Result", value=f"{res2:.{p}f}", disabled=True, key="uc_res2")
        st.markdown(f'<div class="rc"><div class="l">{uc_cat}</div><div class="v">{uc_val2:.{p}f} {uc_fu2} = {res2:.{p}f} {uc_tu2}</div></div>', unsafe_allow_html=True)
        add_hist(f"{uc_val2:.6g} {uc_fu2} → {res2:.6g} {uc_tu2}")

        with st.expander("📊 Full Conversion Table"):
            rows = [{"Unit": u, f"1 {uc_fu2} =": f"{cat_data[uc_fu2]/cat_data[u]:.{p}f}"} for u in unit_list]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("📋 Batch Conversion"):
            uc_batch = st.text_input("Values (comma-separated)", value="1, 5, 10, 50, 100, 500, 1000", key="uc_batch")
            if uc_batch:
                try:
                    vs = [float(v.strip()) for v in uc_batch.split(",") if v.strip()]
                    st.dataframe(pd.DataFrame([{uc_fu2: f"{v:.{p}f}", uc_tu2: f"{v*cat_data[uc_fu2]/cat_data[uc_tu2]:.{p}f}"} for v in vs]), use_container_width=True, hide_index=True)
                except:
                    st.error("Enter valid numbers.")

# ═══════════════════════════════════════
# TAB 2: SIZING
# ═══════════════════════════════════════
with tab2:
    sz_tool = st.selectbox("Select Sizing Tool", ["Control Valve (Cv)", "Orifice Plate", "Relief Valve (API 520/526)", "Line Sizing (Velocity & ΔP)", "Pipe Data & Rating"], key="sz_tool")

    if sz_tool == "Control Valve (Cv)":
        sz_svc = st.radio("Service", ["Liquid", "Gas/Vapor"], horizontal=True, key="sz_cv_svc")
        if sz_svc == "Liquid":
            lc1, lc2 = st.columns(2)
            with lc1:
                cv_Q = st.number_input("Flow Rate (US GPM)", value=500.0, key="sz_cv_Q")
                cv_p1c, cv_p1u = st.columns([3,1])
                with cv_p1c:
                    cv_P1 = st.number_input("Upstream P₁", value=150.0, key="sz_cv_P1")
                with cv_p1u:
                    cv_P1u = st.selectbox("Unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_P1u")
                cv_p2c, cv_p2u = st.columns([3,1])
                with cv_p2c:
                    cv_P2 = st.number_input("Downstream P₂", value=100.0, key="sz_cv_P2")
                with cv_p2u:
                    cv_P2u = st.selectbox("Unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_P2u")
                cv_Gf = st.number_input("Specific Gravity (Gf)", value=1.0, min_value=0.01, key="sz_cv_Gf")
            with lc2:
                # Convert to psi for Cv formula
                P1_psi = cv_P1 * P_U.get(cv_P1u,1) / P_U["psi"]
                P2_psi = cv_P2 * P_U.get(cv_P2u,1) / P_U["psi"]
                dP = P1_psi - P2_psi
                if dP <= 0:
                    st.error("P₁ must be greater than P₂!")
                else:
                    Cv = cv_Q * math.sqrt(cv_Gf / dP)
                    st.markdown(f'<div class="rc"><div class="l">Liquid Cv Sizing</div><div class="v">Cv = {Cv:.{p}f}</div><div class="l">Size: {rec_size(Cv)} | ΔP = {dP:.2f} psi</div></div>', unsafe_allow_html=True)
                    mc = st.columns(3)
                    with mc[0]:
                        st.markdown(f'<div class="mt"><div class="n">{dP:.2f}</div><div class="l">ΔP (psi)</div></div>', unsafe_allow_html=True)
                    with mc[1]:
                        st.markdown(f'<div class="mt"><div class="n">{cv_Gf:.3f}</div><div class="l">Gf</div></div>', unsafe_allow_html=True)
                    with mc[2]:
                        st.markdown(f'<div class="mt"><div class="n">{rec_size(Cv)}</div><div class="l">Valve Size</div></div>', unsafe_allow_html=True)
        else:
            gc1, gc2 = st.columns(2)
            with gc1:
                cv_W = st.number_input("Mass Flow W (lb/h)", value=10000.0, key="sz_cv_W")
                cv_gp1c, cv_gp1u = st.columns([3,1])
                with cv_gp1c:
                    cv_P1g = st.number_input("Upstream P₁", value=150.0, key="sz_cv_P1g")
                with cv_gp1u:
                    cv_P1gu = st.selectbox("Unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_P1gu")
                cv_gp2c, cv_gp2u = st.columns([3,1])
                with cv_gp2c:
                    cv_P2g = st.number_input("Downstream P₂", value=100.0, key="sz_cv_P2g")
                with cv_gp2u:
                    cv_P2gu = st.selectbox("Unit", ["psi","kPa","bar","kg/cm2","atm"], key="sz_cv_P2gu")
                cv_tc, cv_tcu = st.columns([3,1])
                with cv_tc:
                    cv_Tf = st.number_input("Temperature", value=200.0, key="sz_cv_Tf")
                with cv_tcu:
                    cv_Tfu = st.selectbox("Unit", ["°F","°C","K"], key="sz_cv_Tfu")
                cv_gas = st.selectbox("Gas", list(GASES.keys()), key="sz_cv_gas")
                M = GASES[cv_gas]["M"]; k = GASES[cv_gas]["k"]; Z = GASES[cv_gas]["Z"]
                if cv_gas == "Custom":
                    M = st.number_input("M (mol wt)", value=28.97, key="sz_cv_M")
                    k = st.number_input("k (Cp/Cv)", value=1.4, key="sz_cv_k")
                    Z = st.number_input("Z", value=1.0, format="%.4f", key="sz_cv_Z")
                cv_xT = st.number_input("xT", value=0.70, min_value=0.1, max_value=1.0, step=0.01, key="sz_cv_xT", help="Globe≈0.70, Ball≈0.55, Butterfly≈0.35")
                cv_Zo = st.number_input("Z override (0=use default)", value=0.0, format="%.4f", key="sz_cv_Zo")
                if cv_Zo > 0: Z = cv_Zo
            with gc2:
                P1g_psi = cv_P1g * P_U.get(cv_P1gu,1) / P_U["psi"]
                P2g_psi = cv_P2g * P_U.get(cv_P2gu,1) / P_U["psi"]
                T_F = from_C(to_C(cv_Tf, cv_Tfu), "°F")
                dPg = P1g_psi - P2g_psi
                if dPg <= 0:
                    st.error("P₁ must be greater than P₂!")
                else:
                    TR = T_F + 459.67; Fk = k/1.4; x = dPg/P1g_psi; xl = Fk*cv_xT
                    chk = x >= xl; xe = min(x, xl); Y = max(1-xe/(3*Fk*cv_xT), 2/3)
                    dn = 63.3*Y*math.sqrt(xe*P1g_psi*M/(TR*Z)); Cvg = cv_W/dn if dn > 0 else 0
                    tag = " ⚠️ CHOKED" if chk else ""
                    st.markdown(f'<div class="rc"><div class="l">Gas Cv{tag}</div><div class="v">Cv = {Cvg:.{p}f}</div><div class="l">Size: {rec_size(Cvg)} | Y={Y:.4f} | Z={Z:.4f}</div></div>', unsafe_allow_html=True)
                    mc = st.columns(4)
                    with mc[0]:
                        st.markdown(f'<div class="mt"><div class="n">{x:.4f}</div><div class="l">x (ΔP/P₁)</div></div>', unsafe_allow_html=True)
                    with mc[1]:
                        st.markdown(f'<div class="mt"><div class="n">{xl:.4f}</div><div class="l">Fk·xT</div></div>', unsafe_allow_html=True)
                    with mc[2]:
                        st.markdown(f'<div class="mt"><div class="n">{Z:.4f}</div><div class="l">Z</div></div>', unsafe_allow_html=True)
                    with mc[3]:
                        st.markdown(f'<div class="mt"><div class="n">{"CHK" if chk else "Sub"}</div><div class="l">Flow</div></div>', unsafe_allow_html=True)

    elif sz_tool == "Orifice Plate":
        sz_osvc = st.radio("Service", ["Liquid","Gas"], horizontal=True, key="sz_o_svc")
        oc1, oc2 = st.columns(2)
        with oc1:
            sz_od = st.number_input("Orifice bore d (mm)", value=50.0, min_value=1.0, key="sz_o_d")
            sz_oD = st.number_input("Pipe ID D (mm)", value=100.0, min_value=1.0, key="sz_o_D")
            sz_odpc, sz_odpu = st.columns([3,1])
            with sz_odpc:
                sz_odP = st.number_input("Differential Pressure", value=25.0, min_value=0.001, key="sz_o_dP")
            with sz_odpu:
                sz_odPu = st.selectbox("Unit", ["kPa","bar","psi","mmH2O","inH2O"], key="sz_o_dPu")
            dP_kPa = to_kPa(sz_odP, sz_odPu) if sz_odPu in P_U else sz_odP
            if sz_osvc == "Liquid":
                sz_orho = st.number_input("Density (kg/m³)", value=1000.0, key="sz_o_rho")
                sz_omu = st.number_input("Viscosity (Pa·s)", value=1e-3, format="%.6g", key="sz_o_mu")
            else:
                sz_oP1c, sz_oP1u = st.columns([3,1])
                with sz_oP1c:
                    sz_oP1 = st.number_input("Upstream P₁", value=500.0, key="sz_o_P1")
                with sz_oP1u:
                    sz_oP1uu = st.selectbox("Unit", ["kPa","bar","psi","atm"], key="sz_o_P1u")
                P1_kPa = to_kPa(sz_oP1, sz_oP1uu)
                sz_orho1 = st.number_input("Upstream ρ (kg/m³)", value=5.0, key="sz_o_rho1")
                sz_ok = st.number_input("k (Cp/Cv)", value=1.4, key="sz_o_k")
                sz_omu = st.number_input("Viscosity (Pa·s)", value=1.8e-5, format="%.6g", key="sz_o_mu2")
        with oc2:
            if sz_osvc == "Liquid":
                Qo,Cd,Re,beta = orifice_liquid(sz_od, sz_oD, dP_kPa, sz_orho, sz_omu)
                st.markdown(f'<div class="rc"><div class="l">Liquid Orifice (ISO 5167)</div><div class="v">Q = {Qo:.{p}f} m³/h</div><div class="l">β={beta:.4f} | Cd={Cd:.4f} | Re={Re:.0f}</div></div>', unsafe_allow_html=True)
                st.markdown(f"**{Qo*0.22712:.{p}f} GPM** | **{Qo*1000/60:.{p}f} LPM**")
            else:
                Wo,Cd,Re,beta,eps = orifice_gas(sz_od, sz_oD, dP_kPa, P1_kPa, sz_orho1, sz_ok, sz_omu)
                st.markdown(f'<div class="rc"><div class="l">Gas Orifice (ISO 5167)</div><div class="v">W = {Wo:.{p}f} kg/h</div><div class="l">β={beta:.4f} | Cd={Cd:.4f} | ε={eps:.4f} | Re={Re:.0f}</div></div>', unsafe_allow_html=True)
                st.markdown(f"**{Wo/0.4536:.{p}f} lb/h**")
            mc = st.columns(3)
            with mc[0]:
                st.markdown(f'<div class="mt"><div class="n">{beta:.4f}</div><div class="l">β ratio</div></div>', unsafe_allow_html=True)
            with mc[1]:
                st.markdown(f'<div class="mt"><div class="n">{Cd:.4f}</div><div class="l">Cd</div></div>', unsafe_allow_html=True)
            with mc[2]:
                st.markdown(f'<div class="mt"><div class="n">{Re:.0f}</div><div class="l">Re</div></div>', unsafe_allow_html=True)

    elif sz_tool == "Relief Valve (API 520/526)":
        sz_rsvc = st.radio("Service", ["Vapor","Liquid"], horizontal=True, key="sz_r_svc")
        rc1, rc2 = st.columns(2)
        if sz_rsvc == "Vapor":
            with rc1:
                rv_W = st.number_input("Relief Rate W (kg/h)", value=5000.0, key="sz_r_W")
                rv_p1c, rv_p1u = st.columns([3,1])
                with rv_p1c:
                    rv_P1 = st.number_input("Relieving Pressure P₁", value=1200.0, key="sz_r_P1")
                with rv_p1u:
                    rv_P1u = st.selectbox("Unit", ["kPa","bar","psi","atm","MPa"], key="sz_r_P1u")
                rv_tc, rv_tcu = st.columns([3,1])
                with rv_tc:
                    rv_T = st.number_input("Relieving Temperature", value=150.0, key="sz_r_T")
                with rv_tcu:
                    rv_Tu = st.selectbox("Unit", ["°C","°F","K"], key="sz_r_Tu")
                rv_M = st.number_input("Molecular Weight M", value=28.97, min_value=1.0, key="sz_r_M")
                rv_k = st.number_input("k (Cp/Cv)", value=1.4, min_value=1.01, max_value=2.0, key="sz_r_k")
                rv_Z = st.number_input("Z (compressibility)", value=1.0, min_value=0.01, format="%.4f", key="sz_r_Z")
                rv_Kd = st.number_input("Kd (discharge coeff)", value=0.975, key="sz_r_Kd")
                rv_Kb = st.number_input("Kb (backpressure)", value=1.0, key="sz_r_Kb")
                rv_Kc = st.number_input("Kc (combination)", value=1.0, key="sz_r_Kc")
            with rc2:
                P1_kPa_rv = to_kPa(rv_P1, rv_P1u)
                T_K_rv = to_C(rv_T, rv_Tu) + 273.15
                A_rv, C_rv = rv_vapor(rv_W, P1_kPa_rv, T_K_rv, rv_M, rv_k, rv_Z, rv_Kd, rv_Kb, rv_Kc)
                sel = api526_select(A_rv)
                st.markdown(f'<div class="rc"><div class="l">Vapor Relief — API 520</div><div class="v">A = {A_rv:.2f} mm²</div><div class="l">C = {C_rv:.4f}</div></div>', unsafe_allow_html=True)
                st.info(f"**API 526 Orifice: {sel}**")
                mc = st.columns(3)
                with mc[0]:
                    st.markdown(f'<div class="mt"><div class="n">{A_rv:.1f}</div><div class="l">A (mm²)</div></div>', unsafe_allow_html=True)
                with mc[1]:
                    st.markdown(f'<div class="mt"><div class="n">{C_rv:.4f}</div><div class="l">C coeff</div></div>', unsafe_allow_html=True)
                with mc[2]:
                    st.markdown(f'<div class="mt"><div class="n">{sel.split(" ")[0]}</div><div class="l">API 526</div></div>', unsafe_allow_html=True)
        else:
            with rc1:
                rv_Q = st.number_input("Relief Rate Q (m³/h)", value=50.0, key="sz_r_Q")
                rv_dpc, rv_dpu = st.columns([3,1])
                with rv_dpc:
                    rv_dP = st.number_input("P₁ - Pback", value=500.0, key="sz_r_dP")
                with rv_dpu:
                    rv_dPu = st.selectbox("Unit", ["kPa","bar","psi"], key="sz_r_dPu")
                dP_rv = to_kPa(rv_dP, rv_dPu)
                rv_rho = st.number_input("Density (kg/m³)", value=800.0, key="sz_r_rho")
                rv_Kd2 = st.number_input("Kd", value=0.65, key="sz_r_Kd2")
                rv_Kw = st.number_input("Kw (backpressure)", value=1.0, key="sz_r_Kw")
                rv_Kv = st.number_input("Kv (viscosity)", value=1.0, key="sz_r_Kv")
                rv_Kc2 = st.number_input("Kc", value=1.0, key="sz_r_Kc2")
            with rc2:
                A_rl = rv_liquid(rv_Q, dP_rv, rv_rho, rv_Kd2, rv_Kw, rv_Kc2, rv_Kv)
                sel2 = api526_select(A_rl)
                st.markdown(f'<div class="rc"><div class="l">Liquid Relief — API 520</div><div class="v">A = {A_rl:.2f} mm²</div></div>', unsafe_allow_html=True)
                st.info(f"**API 526 Orifice: {sel2}**")

    elif sz_tool == "Line Sizing (Velocity & ΔP)":
        vc1, vc2 = st.columns(2)
        with vc1:
            ls_qc, ls_qu = st.columns([3,1])
            with ls_qc:
                ls_Q = st.number_input("Flow Rate", value=100.0, key="sz_ls_Q")
            with ls_qu:
                ls_Qu = st.selectbox("Unit", list(F_U.keys()), key="sz_ls_Qu")
            Q_m3h = ls_Q * F_U[ls_Qu]
            ls_rhoc, ls_rhou = st.columns([3,1])
            with ls_rhoc:
                ls_rho = st.number_input("Density", value=1000.0, key="sz_ls_rho")
            with ls_rhou:
                ls_rhou_sel = st.selectbox("Unit", ["kg/m3","lb/ft3","g/cm3"], key="sz_ls_rhou")
            rho_kgm3 = ls_rho * U["Density"][ls_rhou_sel]
            ls_muc, ls_muu = st.columns([3,1])
            with ls_muc:
                ls_mu = st.number_input("Viscosity", value=1.0, key="sz_ls_mu")
            with ls_muu:
                ls_muu_sel = st.selectbox("Unit", ["cP","Pa.s","mPa.s"], key="sz_ls_muu")
            mu_Pas = ls_mu * VIS_U[ls_muu_sel]
            ls_nps = st.selectbox("Pipe NPS", list(PIPE_SCH.keys()), index=7, key="sz_ls_nps")
            ls_sch = st.selectbox("Schedule", [10,40,80,160], index=1, key="sz_ls_sch")
            ls_L = st.number_input("Pipe Length (m)", value=100.0, key="sz_ls_L")
            ls_eps = st.number_input("Roughness ε (mm)", value=0.0457, format="%.4f", key="sz_ls_eps", help="CS=0.046, SS=0.015")
            ls_K = st.number_input("Fittings K (total)", value=0.0, key="sz_ls_K")
            ls_C = st.number_input("Erosional C (API 14E)", value=100.0, key="sz_ls_C", help="100=continuous, 150=intermittent")
        with vc2:
            pipe = PIPE_SCH[ls_nps]; wt = pipe.get(ls_sch)
            if wt is None:
                st.error(f"Schedule {ls_sch} not available for NPS {ls_nps}")
            else:
                Did = pipe["od"] - 2*wt; Dmm = Did*25.4
                dPk, V, Re, ff = pipe_dp(Q_m3h, rho_kgm3, mu_Pas, Dmm, ls_L, ls_eps, ls_K)
                Ve = erosional_v(rho_kgm3, ls_C); pct = V/Ve*100 if Ve > 0 else 0
                st.markdown(f'<div class="rc"><div class="l">NPS {ls_nps}" Sch {ls_sch} | ID={Dmm:.1f}mm</div><div class="v">V = {V:.2f} m/s | ΔP = {dPk:.{p}f} kPa</div><div class="l">Re={Re:.0f} | f={ff:.6f}</div></div>', unsafe_allow_html=True)
                clr = "#059669" if pct < 80 else "#f59e0b" if pct < 100 else "#ef4444"
                mc = st.columns(4)
                with mc[0]:
                    st.markdown(f'<div class="mt"><div class="n">{V:.2f}</div><div class="l">V (m/s)</div></div>', unsafe_allow_html=True)
                with mc[1]:
                    st.markdown(f'<div class="mt"><div class="n">{dPk:.2f}</div><div class="l">ΔP (kPa)</div></div>', unsafe_allow_html=True)
                with mc[2]:
                    st.markdown(f'<div class="mt"><div class="n">{Ve:.2f}</div><div class="l">Ve (m/s)</div></div>', unsafe_allow_html=True)
                with mc[3]:
                    st.markdown(f'<div class="mt"><div class="n" style="color:{clr}">{pct:.1f}%</div><div class="l">V/Ve</div></div>', unsafe_allow_html=True)
                if pct >= 100: st.error("⚠️ EXCEEDS erosional limit!")
                elif pct >= 80: st.warning("⚠️ Near erosional limit (>80%)")
                else: st.success("✅ Within safe limits")
                st.markdown(f"**ΔP/100m = {dPk/ls_L*100:.{p}f} kPa** | **{V*3.28084:.2f} ft/s**")

    else:  # Pipe Data & Rating
        sz_pd_mode = st.radio("Mode", ["Pipe Schedule Lookup", "Pressure Rating (ASME B31.3)"], horizontal=True, key="sz_pd_mode")
        if sz_pd_mode == "Pipe Schedule Lookup":
            pd1, pd2 = st.columns(2)
            with pd1:
                pd_nps = st.selectbox("NPS (inches)", list(PIPE_SCH.keys()), index=7, key="sz_pd_nps")
            with pd2:
                pd_u = st.radio("Display Units", ["inches","mm"], horizontal=True, key="sz_pd_u")
            mul = 25.4 if pd_u == "mm" else 1; pipe = PIPE_SCH[pd_nps]; od = pipe["od"]
            st.markdown(f'#### NPS {pd_nps}" — OD = {od*mul:.3f} {pd_u}')
            dr = []
            for s in [10,40,80,160]:
                w = pipe.get(s)
                if w:
                    idv = od-2*w; area = math.pi/4*idv**2; wt_ft = 10.6906*(od-w)*w
                    if pd_u == "mm":
                        dr.append({"Sch":str(s),"Wall":f"{w*mul:.2f}","ID":f"{idv*mul:.2f}","Area (mm²)":f"{area*645.16:.1f}","Wt (kg/m)":f"{wt_ft*1.488:.2f}"})
                    else:
                        dr.append({"Sch":str(s),"Wall":f"{w:.4f}","ID":f"{idv:.4f}","Area (in²)":f"{area:.4f}","Wt (lb/ft)":f"{wt_ft:.2f}"})
                else:
                    dr.append({"Sch":str(s),"Wall":"—","ID":"—","Area (mm²)" if pd_u=="mm" else "Area (in²)":"—","Wt (kg/m)" if pd_u=="mm" else "Wt (lb/ft)":"—"})
            st.dataframe(pd.DataFrame(dr), use_container_width=True, hide_index=True)
        else:
            pr_mode = st.radio("Calculate:", ["MAWP from pipe data", "Required wall thickness"], horizontal=True, key="sz_pr_mode")
            rc1, rc2 = st.columns(2)
            with rc1:
                pr_nps = st.selectbox("NPS", list(PIPE_SCH.keys()), index=7, key="sz_pr_nps")
                pr_sch = st.selectbox("Schedule", [10,40,80,160], index=1, key="sz_pr_sch")
                pp = PIPE_SCH[pr_nps]; pod = pp["od"]; pwt = pp.get(pr_sch)
                st.caption(f"OD={pod:.3f} in | Wall={'N/A' if pwt is None else f'{pwt:.4f} in'}")
                pr_mat = st.selectbox("Material", list(MATERIALS.keys()), key="sz_pr_mat")
                Sv = float(MATERIALS[pr_mat]["S"]) if pr_mat != "Custom" else st.number_input("S (psi)", value=20000.0, key="sz_pr_S")
                if pr_mat != "Custom": st.caption(f"S = {Sv:.0f} psi — {MATERIALS[pr_mat]['n']}")
                pr_E = st.number_input("E (Joint Eff.)", value=1.0, min_value=0.5, max_value=1.0, step=0.05, key="sz_pr_E")
                pr_W = st.number_input("W (Weld Factor)", value=1.0, min_value=0.5, max_value=1.0, step=0.05, key="sz_pr_W")
                pr_Y = st.number_input("Y Coefficient", value=0.4, min_value=0.0, max_value=0.7, step=0.05, key="sz_pr_Y")
                pr_CA = st.number_input("CA (in)", value=0.0625, min_value=0.0, step=0.0625, key="sz_pr_CA")
                pr_MT = st.number_input("Mill Tolerance (%)", value=12.5, min_value=0.0, max_value=25.0, key="sz_pr_MT")
            with rc2:
                if pwt is None:
                    st.error(f"Schedule {pr_sch} not available for NPS {pr_nps}")
                else:
                    ta = pwt*(1-pr_MT/100) - pr_CA
                    if pr_mode == "MAWP from pipe data":
                        if ta <= 0:
                            st.error("Available wall ≤ 0 after CA & mill tolerance!")
                        else:
                            MAWP = (2*Sv*pr_E*pr_W*ta)/(pod-2*pr_Y*ta)
                            barlow = (2*Sv*ta)/pod
                            st.markdown(f'<div class="rc"><div class="l">Pressure Rating</div><div class="v">MAWP = {MAWP:.1f} psi</div><div class="l">Barlow = {barlow:.1f} psi | Avail. wall = {ta:.4f} in</div></div>', unsafe_allow_html=True)
                    else:
                        pr_pdc, pr_pdu = st.columns([3,1])
                        with pr_pdc:
                            pr_Pd = st.number_input("Design Pressure", value=300.0, key="sz_pr_Pd")
                        with pr_pdu:
                            pr_Pdu = st.selectbox("Unit", ["psi","kPa","bar"], key="sz_pr_Pdu")
                        Pd_psi = pr_Pd * P_U.get(pr_Pdu,1) / P_U["psi"] if pr_Pdu != "psi" else pr_Pd
                        tc = (Pd_psi*pod)/(2*(Sv*pr_E*pr_W+Pd_psi*pr_Y))
                        tca = tc + pr_CA; tmt = tca/(1-pr_MT/100)
                        ok = pwt >= tmt
                        c_ = "linear-gradient(135deg,#0ea5e9,#2563eb)" if ok else "linear-gradient(135deg,#ef4444,#dc2626)"
                        lb = "✅ ADEQUATE" if ok else "❌ NOT ADEQUATE"
                        st.markdown(f'<div class="rc" style="background:{c_}"><div class="l">{lb}</div><div class="v">Required: {tmt:.4f} in | Available: {pwt:.4f} in</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════
# TAB 3: PROPERTY ESTIMATION
# ═══════════════════════════════════════
with tab3:
    pr_sub = st.selectbox("Select Tool", ["PR-EOS Pure Component", "PR-EOS Mixture", "TP Flash", "Ternary VLE", "Binary VLE (Pxy/Txy)", "Component Database"], key="pr_sub")

    if pr_sub == "PR-EOS Pure Component":
        st.markdown(f"##### 🧬 Peng-Robinson EOS — {sb_eos}")
        pr_comp = st.selectbox("Component", COMP_NAMES, index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0, key="pr_comp")
        if pr_comp in COMP_DB:
            d = COMP_DB[pr_comp]; MW,Tc,Pc,om,Tb = d[0],d[1],d[2],d[3],d[4]
            st.caption(f"MW={MW:.3f} | Tc={Tc:.2f} K ({Tc-273.15:.1f}°C) | Pc={Pc:.0f} kPa ({Pc/100:.1f} bar) | ω={om:.4f} | Tb={Tb:.1f} K")
            pc1, pc2 = st.columns(2)
            with pc1:
                pr_tc, pr_tcu = st.columns([3,1])
                with pr_tc:
                    pr_T = st.number_input("Temperature", value=25.0, key="pr_T")
                with pr_tcu:
                    pr_Tu = st.selectbox("Unit", ["°C","°F","K"], key="pr_Tu")
                pr_pc, pr_pcu = st.columns([3,1])
                with pr_pc:
                    pr_P = st.number_input("Pressure", value=101.325, min_value=0.01, key="pr_P")
                with pr_pcu:
                    pr_Pu = st.selectbox("Unit", ["kPa","bar","psi","atm","MPa"], key="pr_Pu")
            T_K = to_C(pr_T, pr_Tu) + 273.15
            P_kPa = to_kPa(pr_P, pr_Pu)
            with pc2:
                props = pr_full(T_K, P_kPa, MW, Tc, Pc, om)
                if props:
                    vp = props["vapor"]; lp = props["liquid"]
                    st.markdown(f'<div class="gc"><div class="l">{pr_comp} @ {T_K-273.15:.1f}°C, {P_kPa:.1f} kPa</div><div class="v">Z = {vp["Z"]:.6f} | ρ = {vp["rho"]:.4f} kg/m³</div></div>', unsafe_allow_html=True)
                    rows = [["Z",f"{vp['Z']:.6f}",f"{lp['Z']:.6f}"],["Vm (L/mol)",f"{vp['Vm']:.6f}",f"{lp['Vm']:.6f}"],
                            ["ρ (kg/m³)",f"{vp['rho']:.4f}",f"{lp['rho']:.4f}"],["H_dep (J/mol)",f"{vp['Hd']:.2f}",f"{lp['Hd']:.2f}"],
                            ["φ",f"{vp['phi']:.6f}",f"{lp['phi']:.6f}"],["Tr",f"{vp['Tr']:.4f}",""],["Pr",f"{vp['Pr']:.4f}",""]]
                    st.dataframe(pd.DataFrame(rows, columns=["Property","Vapor","Liquid"]), use_container_width=True, hide_index=True)
                else:
                    st.error("Could not solve PR-EOS at these conditions.")
            with st.expander("📊 Property Plots"):
                pr_psel = st.multiselect("Select", ["Z vs P","Z vs T","ρ vs T","ρ vs P","φ vs P","H_dep vs T"], default=["Z vs P","ρ vs T"], key="pr_psel")
                if pr_psel and st.button("Generate Plots", key="pr_gen"):
                    Prng = np.linspace(max(10,P_kPa*0.1), P_kPa*10, 50)
                    Trng = np.linspace(max(-200,Tb-273.15-50), min(600,Tc-273.15+100), 50)
                    apply_mpl()
                    for pn in pr_psel:
                        if "vs P" in pn:
                            key = {"Z vs P":"Z","ρ vs P":"rho","φ vs P":"phi","H_dep vs P":"Hd"}.get(pn,"Z")
                            xs,yv,yl = sweep_prop(pr_comp,"P",Prng,T_K-273.15,key)
                        else:
                            key = {"Z vs T":"Z","ρ vs T":"rho","φ vs T":"phi","H_dep vs T":"Hd"}.get(pn,"Z")
                            xs,yv,yl = sweep_prop(pr_comp,"T",Trng,P_kPa,key)
                        fig,ax = plt.subplots(figsize=(9,5))
                        ax.plot(xs,yv,color="#0ea5e9",lw=2,label="Vapor")
                        if any(y!=v for y,v in zip(yl,yv)):
                            ax.plot(xs,yl,color="#ef4444",lw=2,ls="--",label="Liquid")
                        ax.set_xlabel("P (kPa)" if "vs P" in pn else "T (°C)")
                        ax.set_ylabel(pn.split(" vs")[0])
                        ax.set_title(f"{pr_comp} — {pn}", fontweight="bold")
                        ax.legend(); ax.grid(alpha=0.2); fig.tight_layout()
                        st.pyplot(fig); plt.close(fig)

    elif pr_sub == "PR-EOS Mixture":
        st.markdown("##### Mixture Properties")
        pr_nc = st.slider("Number of components", 2, 10, 2, key="pr_nc")
        comps = []; ys = []
        for i in range(pr_nc):
            cc1, cc2 = st.columns([3,1])
            with cc1:
                cn = st.selectbox(f"Component {i+1}", COMP_NAMES, index=min(i,len(COMP_NAMES)-1), key=f"pr_mc{i}")
            with cc2:
                yi = st.number_input(f"y{i+1}", value=round(1/pr_nc,4), min_value=0.0, max_value=1.0, format="%.4f", key=f"pr_my{i}")
            comps.append(cn); ys.append(yi)
        yt = sum(ys)
        if abs(yt-1) > 0.001: st.warning(f"Sum = {yt:.4f} (should be 1.0)")
        pr_mtc, pr_mtcu = st.columns([3,1])
        with pr_mtc:
            pr_mT = st.number_input("Temperature", value=25.0, key="pr_mT")
        with pr_mtcu:
            pr_mTu = st.selectbox("Unit", ["°C","°F","K"], key="pr_mTu")
        pr_mpc, pr_mpcu = st.columns([3,1])
        with pr_mpc:
            pr_mP = st.number_input("Pressure", value=101.325, key="pr_mP")
        with pr_mpcu:
            pr_mPu = st.selectbox("Unit", ["kPa","bar","psi","atm"], key="pr_mPu")
        if st.button("Calculate", type="primary", key="pr_mcalc"):
            T_K = to_C(pr_mT, pr_mTu) + 273.15; P_kPa = to_kPa(pr_mP, pr_mPu)
            cl = []; MW_m = 0
            for cn, yi in zip(comps, ys):
                if cn in COMP_DB:
                    dd = COMP_DB[cn]; cl.append((dd[1],dd[2],dd[3])); MW_m += yi*dd[0]
            if len(cl) == pr_nc:
                am,bm,_,_ = eos.mix_params(cl, ys, T_K)
                Zv,Zl = eos.solve_Z(am, bm, T_K, P_kPa)
                if Zv:
                    Vm = Zv*R_GAS*T_K/(P_kPa*1000); rho = (MW_m/1000)/Vm
                    st.markdown(f'<div class="gc"><div class="l">Mixture @ {T_K-273.15:.1f}°C, {P_kPa:.1f} kPa</div><div class="v">Z={Zv:.6f} | ρ={rho:.4f} kg/m³ | MW={MW_m:.3f}</div></div>', unsafe_allow_html=True)
                else: st.error("Could not solve.")

    elif pr_sub == "TP Flash":
        st.markdown(f"##### ⚡ TP Flash — {sb_eos}")
        fl_nc = st.slider("Components", 2, 15, 3, key="pr_fl_nc")
        fl_comps = []; fl_z = []
        for i in range(fl_nc):
            cc1, cc2 = st.columns([3,1])
            with cc1:
                cn = st.selectbox(f"Comp {i+1}", COMP_NAMES, index=min(i,len(COMP_NAMES)-1), key=f"pr_fl_c{i}")
            with cc2:
                zi = st.number_input(f"z{i+1}", value=round(1/fl_nc,4), min_value=0.0001, max_value=1.0, format="%.4f", key=f"pr_fl_z{i}")
            fl_comps.append(cn); fl_z.append(zi)
        zt = sum(fl_z)
        if abs(zt-1) > 0.001: st.warning(f"Sum = {zt:.4f}. Will normalize."); fl_z = [z/zt for z in fl_z]
        fl_tc, fl_tcu = st.columns([3,1])
        with fl_tc:
            fl_T = st.number_input("Temperature", value=25.0, key="pr_fl_T")
        with fl_tcu:
            fl_Tu = st.selectbox("Unit", ["°C","°F","K"], key="pr_fl_Tu")
        fl_pc, fl_pcu = st.columns([3,1])
        with fl_pc:
            fl_P = st.number_input("Pressure", value=101.325, key="pr_fl_P")
        with fl_pcu:
            fl_Pu = st.selectbox("Unit", ["kPa","bar","psi","atm"], key="pr_fl_Pu")
        if st.button("⚡ Run Flash", type="primary", key="pr_fl_run"):
            T_K = to_C(fl_T, fl_Tu) + 273.15; P_kPa = to_kPa(fl_P, fl_Pu)
            cl = [(COMP_DB[cn][1],COMP_DB[cn][2],COMP_DB[cn][3]) for cn in fl_comps]
            with st.spinner("Running flash..."):
                beta,x,y,K,conv,iters = tp_flash(eos, cl, fl_z, T_K, P_kPa, max_iter=200)
            if conv:
                ph = "Two-Phase" if 0.001<beta<0.999 else ("All Vapor" if beta>0.999 else "All Liquid")
                st.markdown(f'<div class="rc"><div class="l">{ph} | {sb_eos}</div><div class="v">V/F = {beta:.6f}</div><div class="l">{iters} iterations</div></div>', unsafe_allow_html=True)
                rows = [{"Component":fl_comps[i],"z":f"{fl_z[i]:.4f}","x (liq)":f"{x[i]:.6f}","y (vap)":f"{y[i]:.6f}","K":f"{K[i]:.6f}"} for i in range(fl_nc)]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                apply_mpl()
                fig, axes = plt.subplots(1,2, figsize=(10,4))
                xp = np.arange(fl_nc); w = 0.25
                axes[0].bar(xp-w, fl_z, w, label="z (feed)", color="#64748b")
                axes[0].bar(xp, x, w, label="x (liquid)", color="#0ea5e9")
                axes[0].bar(xp+w, y, w, label="y (vapor)", color="#ef4444")
                axes[0].set_xticks(xp); axes[0].set_xticklabels([c[:7] for c in fl_comps], rotation=45, fontsize=7)
                axes[0].legend(fontsize=7); axes[0].set_title("Composition Split"); axes[0].grid(alpha=0.2)
                axes[1].barh(xp, K, color="#8b5cf6")
                axes[1].set_yticks(xp); axes[1].set_yticklabels([c[:7] for c in fl_comps], fontsize=7)
                axes[1].axvline(1, color="#f59e0b", ls="--"); axes[1].set_title("K-values"); axes[1].grid(alpha=0.2)
                fig.tight_layout(); st.pyplot(fig); plt.close(fig)
            else: st.error(f"Did not converge in {iters} iterations.")

    elif pr_sub == "Ternary VLE":
        st.markdown(f"##### 🔺 Ternary Phase Diagram — {sb_eos}")
        tc1,tc2,tc3 = st.columns(3)
        with tc1: tn1 = st.selectbox("Comp 1 (bottom-left)", COMP_NAMES, index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0, key="pr_tn1")
        with tc2: tn2 = st.selectbox("Comp 2 (bottom-right)", COMP_NAMES, index=COMP_NAMES.index("Ethane") if "Ethane" in COMP_NAMES else 1, key="pr_tn2")
        with tc3: tn3 = st.selectbox("Comp 3 (top)", COMP_NAMES, index=COMP_NAMES.index("Propane") if "Propane" in COMP_NAMES else 2, key="pr_tn3")
        tt1, tt2, tt3 = st.columns(3)
        with tt1:
            tvc, tvu = st.columns([3,1])
            with tvc: tT = st.number_input("Temperature", value=25.0, key="pr_tT")
            with tvu: tTu = st.selectbox("Unit", ["°C","°F","K"], key="pr_tTu")
        with tt2:
            tpc, tpu = st.columns([3,1])
            with tpc: tP = st.number_input("Pressure", value=101.325, key="pr_tP")
            with tpu: tPu = st.selectbox("Unit", ["kPa","bar","psi"], key="pr_tPu")
        with tt3:
            tN = st.slider("Grid resolution", 8, 25, 12, key="pr_tN")
        if st.button("🔺 Generate Ternary", type="primary", key="pr_tgen"):
            T_K = to_C(tT, tTu) + 273.15; P_kPa = to_kPa(tP, tPu)
            clt = [(COMP_DB[cn][1],COMP_DB[cn][2],COMP_DB[cn][3]) for cn in [tn1,tn2,tn3]]
            with st.spinner(f"Running ~{(tN+1)*(tN+2)//2} flash calculations..."):
                td = gen_ternary(eos, clt, T_K, P_kPa, n_grid=tN)
            if td:
                apply_mpl(); fig, ax = plt.subplots(figsize=(9,8))
                ax.plot([0,1,0.5,0],[0,0,math.sqrt(3)/2,0], color='#94a3b8', lw=2)
                lc = '#e2e8f0' if dk else '#1e293b'
                ax.text(-0.05,-0.05, tn1[:10], fontsize=10, fontweight='bold', ha='center', color=lc)
                ax.text(1.05,-0.05, tn2[:10], fontsize=10, fontweight='bold', ha='center', color=lc)
                ax.text(0.5, math.sqrt(3)/2+0.04, tn3[:10], fontsize=10, fontweight='bold', ha='center', color=lc)
                tp_ = [d for d in td if 0.001 < d["beta"] < 0.999]
                for d in tp_:
                    ax.plot([d["x_xy"][0],d["y_xy"][0]], [d["x_xy"][1],d["y_xy"][1]], color='#94a3b8', alpha=0.15, lw=0.5)
                    ax.scatter(d["x_xy"][0], d["x_xy"][1], color="#0ea5e9", s=12, zorder=3, alpha=0.7)
                    ax.scatter(d["y_xy"][0], d["y_xy"][1], color="#ef4444", s=12, zorder=3, alpha=0.7)
                for d in td:
                    zx,zy = d["z_xy"]; ax.scatter(zx, zy, color=plt.cm.RdYlBu_r(d["beta"]), s=4, alpha=0.3)
                ax.set_xlim(-0.1,1.1); ax.set_ylim(-0.1,math.sqrt(3)/2+0.1); ax.set_aspect('equal'); ax.axis('off')
                ax.set_title(f"Ternary VLE — {sb_eos}", fontsize=12, fontweight='bold')
                sm = plt.cm.ScalarMappable(cmap='RdYlBu_r', norm=plt.Normalize(0,1)); sm.set_array([])
                fig.colorbar(sm, ax=ax, shrink=0.5, label="V/F")
                fig.tight_layout(); st.pyplot(fig); plt.close(fig)
            else: st.error("No valid results.")

    elif pr_sub == "Binary VLE (Pxy/Txy)":
        st.markdown(f"##### 📈 Binary VLE — {sb_eos}")
        bc1, bc2 = st.columns(2)
        with bc1: bn1 = st.selectbox("Light component", COMP_NAMES, index=COMP_NAMES.index("Methane") if "Methane" in COMP_NAMES else 0, key="pr_bn1")
        with bc2: bn2 = st.selectbox("Heavy component", COMP_NAMES, index=COMP_NAMES.index("Propane") if "Propane" in COMP_NAMES else 2, key="pr_bn2")
        bm = st.radio("Diagram Type", ["P-xy (isothermal)","T-xy (isobaric)"], horizontal=True, key="pr_bm")
        if bm == "P-xy (isothermal)":
            bTc, bTu = st.columns([3,1])
            with bTc: bT = st.number_input("Temperature", value=25.0, key="pr_bT")
            with bTu: bTuu = st.selectbox("Unit", ["°C","°F","K"], key="pr_bTu")
            bPmn = st.number_input("P min (kPa)", value=10.0, key="pr_bPmn")
            bPmx = st.number_input("P max (kPa)", value=5000.0, key="pr_bPmx")
        else:
            bPc, bPu = st.columns([3,1])
            with bPc: bP = st.number_input("Pressure", value=101.325, key="pr_bP")
            with bPu: bPuu = st.selectbox("Unit", ["kPa","bar","psi"], key="pr_bPu")
            bTmn = st.number_input("T min (°C)", value=-150.0, key="pr_bTmn")
            bTmx = st.number_input("T max (°C)", value=100.0, key="pr_bTmx")
        if st.button("📈 Generate VLE Diagram", type="primary", key="pr_bgen"):
            clb = [(COMP_DB[bn1][1],COMP_DB[bn1][2],COMP_DB[bn1][3]),(COMP_DB[bn2][1],COMP_DB[bn2][2],COMP_DB[bn2][3])]
            z1r = np.linspace(0.01,0.99,35); bub = []; dew = []
            with st.spinner("Computing VLE..."):
                if bm == "P-xy (isothermal)":
                    T_K = to_C(bT, bTuu) + 273.15
                    for P in np.linspace(max(bPmn,1), bPmx, 50):
                        for z1 in z1r:
                            try:
                                bt,x,y,K,cv,_ = tp_flash(eos, clb, [z1,1-z1], T_K, P, max_iter=60)
                                if cv and 0.001<bt<0.999: bub.append((x[0],P)); dew.append((y[0],P))
                            except: pass
                else:
                    P_kPa = to_kPa(bP, bPuu)
                    for T in np.linspace(bTmn+273.15, bTmx+273.15, 50):
                        if T < 10: continue
                        for z1 in z1r:
                            try:
                                bt,x,y,K,cv,_ = tp_flash(eos, clb, [z1,1-z1], T, P_kPa, max_iter=60)
                                if cv and 0.001<bt<0.999: bub.append((x[0],T-273.15)); dew.append((y[0],T-273.15))
                            except: pass
            if bub:
                apply_mpl(); fig, ax = plt.subplots(figsize=(9,6))
                bxp,byp = zip(*sorted(bub)); dxp,dyp = zip(*sorted(dew))
                ax.plot(bxp,byp,'o',color="#0ea5e9",ms=3,label="Bubble (x)")
                ax.plot(dxp,dyp,'o',color="#ef4444",ms=3,label="Dew (y)")
                ax.set_xlabel(f"Mole fraction {bn1}")
                ax.set_ylabel("Pressure (kPa)" if "P-xy" in bm else "Temperature (°C)")
                ax.set_title(f"{'P-xy' if 'P-xy' in bm else 'T-xy'}: {bn1} / {bn2} ({sb_eos})", fontweight='bold')
                ax.legend(); ax.grid(alpha=0.2); fig.tight_layout()
                st.pyplot(fig); plt.close(fig)
            else: st.warning("No two-phase data found. Try wider range.")

    else:  # Component Database
        sr = st.text_input("🔍 Search component", key="pr_dbsearch")
        fl = {k:v for k,v in COMP_DB.items() if sr.lower() in k.lower()} if sr else COMP_DB
        st.dataframe(pd.DataFrame([{"Component":n,"MW":f"{v[0]:.3f}","Tc (K)":f"{v[1]:.2f}","Pc (kPa)":f"{v[2]:.0f}","ω":f"{v[3]:.4f}","Tb (K)":f"{v[4]:.1f}"} for n,v in sorted(fl.items())]), use_container_width=True, hide_index=True, height=500)
        st.caption(f"Showing {len(fl)} of {len(COMP_DB)} components")

# ═══════════════════════════════════════
# TAB 4: STEAM TABLE
# ═══════════════════════════════════════
with tab4:
    if not HAS_STEAM:
        st.error("⚠️ steam_if97.py not found! Place it in the same folder as dpsim.py.")
    else:
        st_mode = st.selectbox("Mode", ["T & P → Properties", "Saturation Table", "Wet Steam (Quality)", "📊 Steam Diagrams"], key="st_mode")

        if st_mode == "T & P → Properties":
            sc1, sc2 = st.columns(2)
            with sc1:
                st_tc, st_tcu = st.columns([3,1])
                with st_tc:
                    st_T = st.number_input("Temperature", value=200.0, key="st_T")
                with st_tcu:
                    st_Tu = st.selectbox("Unit", ["°C","°F","K"], key="st_Tu")
                st_pc, st_pcu = st.columns([3,1])
                with st_pc:
                    st_P = st.number_input("Pressure", value=101.325, min_value=0.7, key="st_P")
                with st_pcu:
                    st_Pu = st.selectbox("Unit", ["kPa","bar","psi","atm","MPa"], key="st_Pu")
                T_C = to_C(st_T, st_Tu); P_kPa = to_kPa(st_P, st_Pu)
                try:
                    Ps_at_T = Psat_T(T_C+273.15)*1000 if T_C+273.15 < 647.096 else 22064
                    st.caption(f"Psat at {T_C:.1f}°C = {Ps_at_T:.2f} kPa ({Ps_at_T/100:.3f} bar)")
                except: pass
            with sc2:
                try:
                    sp = steam_props(T_C=T_C, P_kPa=P_kPa)
                    if sp:
                        st.markdown(f'<div class="rc"><div class="l">{sp["phase"]} @ {T_C:.1f}°C, {P_kPa:.1f} kPa</div><div class="v">h = {sp["h"]:.2f} kJ/kg</div></div>', unsafe_allow_html=True)
                        mc = st.columns(4)
                        with mc[0]: st.markdown(f'<div class="mt"><div class="n">{sp["h"]:.2f}</div><div class="l">h (kJ/kg)</div></div>', unsafe_allow_html=True)
                        with mc[1]: st.markdown(f'<div class="mt"><div class="n">{sp["s"]:.4f}</div><div class="l">s (kJ/kg·K)</div></div>', unsafe_allow_html=True)
                        with mc[2]: st.markdown(f'<div class="mt"><div class="n">{sp["v"]:.6g}</div><div class="l">v (m³/kg)</div></div>', unsafe_allow_html=True)
                        with mc[3]: st.markdown(f'<div class="mt"><div class="n">{sp["rho"]:.4f}</div><div class="l">ρ (kg/m³)</div></div>', unsafe_allow_html=True)
                        res = [["Phase",sp["phase"]],["T (°C)",f"{sp['T_C']:.2f}"],["P (kPa)",f"{sp['P_kPa']:.2f}"],
                               ["P (bar)",f"{sp['P_kPa']/100:.4f}"],["P (psi)",f"{sp['P_kPa']*0.14504:.2f}"],
                               ["h (kJ/kg)",f"{sp['h']:.4f}"],["h (BTU/lb)",f"{sp['h']*0.42992:.4f}"],
                               ["s (kJ/kg·K)",f"{sp['s']:.6f}"],["v (m³/kg)",f"{sp['v']:.6g}"],
                               ["u (kJ/kg)",f"{sp['u']:.4f}"],["ρ (kg/m³)",f"{sp['rho']:.4f}"]]
                        if "cp" in sp: res.append(["cp (kJ/kg·K)",f"{sp['cp']:.4f}"])
                        st.dataframe(pd.DataFrame(res, columns=["Property","Value"]), use_container_width=True, hide_index=True)
                    else: st.error("Out of range (0-590°C, 0.7-100000 kPa)")
                except Exception as e: st.error(f"Error: {e}")

        elif st_mode == "Saturation Table":
            sat_by = st.radio("Input by", ["Pressure","Temperature"], horizontal=True, key="st_sat_by")
            if sat_by == "Pressure":
                sat_ps = st.text_input("Pressures (kPa, comma-separated)", value="10, 50, 101.325, 200, 500, 1000, 2000, 5000, 10000, 15000, 20000", key="st_sat_ps")
                try:
                    pvs = [float(v.strip()) for v in sat_ps.split(",") if v.strip()]; rows = []
                    for pk in pvs:
                        try:
                            sp = sat_props(P=pk/1000)
                            rows.append({"P (kPa)":f"{pk:.1f}","Tsat (°C)":f"{sp['T_C']:.2f}","hf":f"{sp['hf']:.2f}","hg":f"{sp['hg']:.2f}","hfg":f"{sp['hfg']:.2f}","sf":f"{sp['sf']:.4f}","sg":f"{sp['sg']:.4f}","vf":f"{sp['vf']:.6f}","vg":f"{sp['vg']:.4f}"})
                        except: pass
                    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                except: st.error("Enter valid pressures.")
            else:
                sat_ts = st.text_input("Temperatures (°C, comma-separated)", value="10, 25, 50, 75, 100, 150, 200, 250, 300, 350", key="st_sat_ts")
                try:
                    tvs = [float(v.strip()) for v in sat_ts.split(",") if v.strip()]; rows = []
                    for tc in tvs:
                        try:
                            sp = sat_props(T=tc+273.15)
                            rows.append({"T (°C)":f"{tc:.1f}","Psat (kPa)":f"{sp['P_kPa']:.3f}","hf":f"{sp['hf']:.2f}","hg":f"{sp['hg']:.2f}","hfg":f"{sp['hfg']:.2f}","sf":f"{sp['sf']:.4f}","sg":f"{sp['sg']:.4f}","vf":f"{sp['vf']:.6f}","vg":f"{sp['vg']:.4f}"})
                        except: pass
                    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                except: st.error("Enter valid temperatures.")

        elif st_mode == "Wet Steam (Quality)":
            wc1, wc2 = st.columns(2)
            with wc1:
                ws_pc, ws_pu = st.columns([3,1])
                with ws_pc: ws_P = st.number_input("Pressure", value=500.0, min_value=0.7, key="st_wP")
                with ws_pu: ws_Pu = st.selectbox("Unit", ["kPa","bar","psi"], key="st_wPu")
                ws_x = st.slider("Quality (x)", 0.0, 1.0, 0.5, 0.01, key="st_wx")
            with wc2:
                try:
                    P_kPa_w = to_kPa(ws_P, ws_Pu)
                    wp = wet_steam(P_kPa_w/1000, ws_x)
                    st.markdown(f'<div class="gc"><div class="l">{wp["phase"]} @ {P_kPa_w:.1f} kPa</div><div class="v">h = {wp["h"]:.2f} kJ/kg | T = {wp["T_C"]:.2f}°C</div></div>', unsafe_allow_html=True)
                    mc = st.columns(4)
                    with mc[0]: st.markdown(f'<div class="mt"><div class="n">{wp["h"]:.2f}</div><div class="l">h kJ/kg</div></div>', unsafe_allow_html=True)
                    with mc[1]: st.markdown(f'<div class="mt"><div class="n">{wp["s"]:.4f}</div><div class="l">s kJ/kg·K</div></div>', unsafe_allow_html=True)
                    with mc[2]: st.markdown(f'<div class="mt"><div class="n">{wp["v"]:.6g}</div><div class="l">v m³/kg</div></div>', unsafe_allow_html=True)
                    with mc[3]: st.markdown(f'<div class="mt"><div class="n">{ws_x:.2f}</div><div class="l">Quality x</div></div>', unsafe_allow_html=True)
                except Exception as e: st.error(f"Error: {e}")

        else:  # Steam Diagrams
            apply_mpl()
            st_diag = st.selectbox("Select Diagram", ["T-H (Temperature vs Enthalpy)","T-S (Temperature vs Entropy)","H-S (Mollier Diagram)","P-H (Pressure vs Enthalpy)","P-T (Saturation Curve)"], key="st_diag")
            st.markdown("**📍 Plot a state point (optional):**")
            spc1, spc2, spc3 = st.columns(3)
            with spc1: sp_T = st.number_input("T (°C)", value=200.0, key="st_spT")
            with spc2: sp_P = st.number_input("P (kPa)", value=101.325, key="st_spP")
            with spc3: sp_show = st.checkbox("Show on plot", value=True, key="st_spshow")
            upt = None
            if sp_show:
                try: upt = steam_props(T_C=sp_T, P_kPa=sp_P)
                except: pass
            with st.spinner("Generating saturation dome..."):
                sd = gen_sat_data(70)
            Tc_l=[d["T_C"] for d in sd]; hf_l=[d["hf"] for d in sd]; hg_l=[d["hg"] for d in sd]
            sf_l=[d["sf"] for d in sd]; sg_l=[d["sg"] for d in sd]; Pk_l=[d["P_kPa"] for d in sd]

            fig, ax = plt.subplots(figsize=(10,6))
            if st_diag == "T-H (Temperature vs Enthalpy)":
                ax.plot(hf_l, Tc_l, color="#0ea5e9", lw=2.5, label="Sat. Liquid")
                ax.plot(hg_l, Tc_l, color="#ef4444", lw=2.5, label="Sat. Vapor")
                ax.fill_betweenx(Tc_l, hf_l, hg_l, alpha=0.08, color="#94a3b8")
                if upt: ax.plot(upt["h"], upt["T_C"], "*", color="#f59e0b", ms=18, zorder=5, label=f"({sp_T:.0f}°C, {sp_P:.0f}kPa)")
                ax.set_xlabel("Enthalpy h (kJ/kg)"); ax.set_ylabel("Temperature T (°C)")
                ax.set_title("T-H Diagram (IAPWS-IF97)", fontweight="bold")
            elif st_diag == "T-S (Temperature vs Entropy)":
                ax.plot(sf_l, Tc_l, color="#0ea5e9", lw=2.5, label="Sat. Liquid")
                ax.plot(sg_l, Tc_l, color="#ef4444", lw=2.5, label="Sat. Vapor")
                ax.fill_betweenx(Tc_l, sf_l, sg_l, alpha=0.08, color="#94a3b8")
                if upt: ax.plot(upt["s"], upt["T_C"], "*", color="#f59e0b", ms=18, zorder=5)
                ax.set_xlabel("Entropy s (kJ/kg·K)"); ax.set_ylabel("Temperature T (°C)")
                ax.set_title("T-S Diagram", fontweight="bold")
            elif st_diag == "H-S (Mollier Diagram)":
                ax.plot(sf_l, hf_l, color="#0ea5e9", lw=2.5, label="Sat. Liquid")
                ax.plot(sg_l, hg_l, color="#ef4444", lw=2.5, label="Sat. Vapor")
                for xq in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]:
                    hx=[d["hf"]+xq*d["hfg"] for d in sd]; sx=[d["sf"]+xq*d["sfg"] for d in sd]
                    ax.plot(sx, hx, lw=0.5, alpha=0.35, color="#94a3b8")
                    mid=len(sx)//2
                    if mid>0: ax.annotate(f"x={xq:.1f}", (sx[mid],hx[mid]), fontsize=6, alpha=0.5, color='#e2e8f0' if dk else '#64748b')
                if upt: ax.plot(upt["s"], upt["h"], "*", color="#f59e0b", ms=18, zorder=5)
                ax.set_xlabel("Entropy s (kJ/kg·K)"); ax.set_ylabel("Enthalpy h (kJ/kg)")
                ax.set_title("H-S (Mollier) Diagram", fontweight="bold")
            elif st_diag == "P-H (Pressure vs Enthalpy)":
                ax.semilogy(hf_l, Pk_l, color="#0ea5e9", lw=2.5, label="Sat. Liquid")
                ax.semilogy(hg_l, Pk_l, color="#ef4444", lw=2.5, label="Sat. Vapor")
                if upt: ax.plot(upt["h"], upt["P_kPa"], "*", color="#f59e0b", ms=18, zorder=5)
                ax.set_xlabel("Enthalpy h (kJ/kg)"); ax.set_ylabel("Pressure P (kPa)")
                ax.set_title("P-H Diagram (log scale)", fontweight="bold")
            else:  # P-T
                ax.semilogy(Tc_l, Pk_l, color="#0ea5e9", lw=3)
                ax.fill_between(Tc_l, Pk_l, min(Pk_l), alpha=0.1, color="#0ea5e9")
                ax.annotate("LIQUID", (100,5000), fontsize=14, alpha=0.4, color='#e2e8f0' if dk else '#1e293b', fontweight='bold')
                ax.annotate("VAPOR", (300,50), fontsize=14, alpha=0.4, color='#e2e8f0' if dk else '#1e293b', fontweight='bold')
                ax.plot(373.946, 22064, "o", color="#ef4444", ms=12, label="Critical Point (374°C, 22064 kPa)")
                if sp_show: ax.plot(sp_T, sp_P, "*", color="#f59e0b", ms=18, zorder=5)
                ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("Pressure (kPa)")
                ax.set_title("P-T Saturation Curve", fontweight="bold")
            ax.legend(fontsize=8); ax.grid(alpha=0.2); fig.tight_layout()
            st.pyplot(fig); plt.close(fig)

        st.caption("IAPWS-IF97 (Regions 1, 2, 4). Accuracy matches ASME Steam Tables. Valid: 0-590°C, 0.7-100000 kPa.")

# ═══════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════
st.markdown("---")
_f1 = "#e2e8f0" if dk else "#1e293b"
_f2 = "#94a3b8" if dk else "#64748b"
_f3 = "#64748b" if dk else "#94a3b8"
_fh = f'<div style="text-align:center;padding:20px 0 10px 0;">'
_fh += f'<p style="color:{_f1};font-size:1.1rem;font-weight:700;margin-bottom:4px;">🔬 DPSIM</p>'
_fh += f'<p style="color:{_f2};font-size:.85rem;margin-bottom:2px;">Process Engineering Toolkit</p>'
_fh += f'<p style="color:#0ea5e9;font-size:.9rem;font-weight:600;margin-bottom:8px;">Created by Dhawal Patel</p>'
_fh += f'<p style="color:{_f3};font-size:.72rem;">'
_fh += "Perry&#39;s ChE Handbook &#8226; NIST &#8226; ASME B36.10M &#8226; ASME B31.3 &#8226; ISA/IEC 60534 &#8226; ISO 5167 &#8226; API 520/521/526 &#8226; API RP 14E &#8226; IAPWS-IF97 &#8226; DIN 1343 &#8226; ISO 13443 &#8226; DIPPR 801"
_fh += '</p></div>'
st.markdown(_fh, unsafe_allow_html=True)
