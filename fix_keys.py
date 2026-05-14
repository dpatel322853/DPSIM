
# DPSIM Key Fix Patch
# Run: python fix_keys.py
# This fixes duplicate widget keys in dpsim.py

with open("dpsim.py", "r", encoding="utf-8") as f:
    code = f.read()

# Fix 1: Tab 8 (Rating) NPS selectbox — "pn" conflicts with Pin button in Tab 1
code = code.replace('st.selectbox("NPS",list(PIPE_SCH.keys()),index=7,key="pn")', 
                     'st.selectbox("NPS",list(PIPE_SCH.keys()),index=7,key="r_nps")')

# Fix 2: Tab 8 Schedule selectbox — "ps" just in case  
code = code.replace('st.selectbox("Sch",[10,40,80,160],index=1,key="ps")',
                     'st.selectbox("Sch",[10,40,80,160],index=1,key="r_sch")')

# Fix 3: Tab 8 mode radio — "pm" just in case
code = code.replace('st.radio("Calc:",["MAWP","Reqd thickness"],horizontal=True,key="pm")',
                     'st.radio("Calc:",["MAWP","Reqd thickness"],horizontal=True,key="r_mode")')

with open("dpsim.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed! Run: streamlit run dpsim.py")
