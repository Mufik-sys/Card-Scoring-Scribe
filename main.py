import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, json, zlib, base64

# --- 1. ROBUST SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

SAVE_FILE = "scribe_state.json"

def save_state():
    data = {"p": st.session_state.players, "h": st.session_state.history, "d": st.session_state.dealer, "pk": st.session_state.picks, "m": st.session_state.mode}
    # 1. Save to Local File
    try:
        with open(SAVE_FILE, "w") as f: json.dump(data, f)
    except: pass
    
    # 2. Save to URL (This survives server sleep/restarts!)
    try:
        json_str = json.dumps(data)
        compressed = zlib.compress(json_str.encode())
        b64_str = base64.urlsafe_b64encode(compressed).decode()
        st.query_params["save"] = b64_str
    except: pass

def load_state():
    # 1. Check URL Memory first (Strongest)
    if "save" in st.query_params:
        try:
            b64_str = st.query_params["save"]
            compressed = base64.urlsafe_b64decode(b64_str.encode())
            json_str = zlib.decompress(compressed).decode()
            d = json.loads(json_str)
            st.session_state.update({"players": d['p'], "history": d['h'], "dealer": d['d'], "picks": d['pk'], "mode": d['m']})
            return True
        except: pass
    # 2. Check Local File
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.update({"players": d['p'], "history": d['h'], "dealer": d['d'], "picks": d['pk'], "mode": d['m']})
            return True
        except: pass
    return False

if 'players' not in st.session_state:
    if not load_state():
        st.session_state.update({"players": [], "history": [], "dealer": 0, "picks": {}, "mode": "setup"})

# --- 2. THE SPATIAL DRAWING ENGINE ---
def draw_notebook(history, players, dealer_idx, picks):
    num_p = len(players)
    width = max(1000, num_p * 250)
    height = max(800, 400 + (len(history) * 200))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(80, height, 80):
        draw.line([(0, y), (width, y)], fill=(220, 230, 245), width=2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: font = ImageFont.load_default()
    
    cx = width / num_p
    for i, p in enumerate(players):
        x = (i + 0.5) * cx
        tk = picks.get(p, 0)
        if tk > 0: draw.text((x, 60), "|" * tk, fill=(230, 0, 0), font=font, anchor="mt")
        disp = p.capitalize()
        if i == dealer_idx: disp += " (D)"
        draw.text((x, 150), disp, fill=(40, 40, 100), font=font, anchor="mt")

    y = 280
    totals = {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((40, y), str(r_idx), fill=(160, 160, 160), font=font, anchor="mt")
        for i, p in enumerate(players):
            x = (i + 0.5) * cx
            val = r_sc.get(p, 0); totals[p] += val
            draw.text((x, y), str(val), fill=(50, 50, 50), font=font, anchor="mt")
        
        y += 80
        draw.line([(20, y), (width-20, y)], fill=(255, 140, 0), width=3)
        y += 10
        for i, p in enumerate(players):
            x = (i + 0.5) * cx
            draw.text((x, y), str(totals[p]), fill=(255, 130, 0), font=font, anchor="mt")
        y += 100
    return img

# --- 3. THE UI ---
st.title("🎙️ Score Scribe Pro")

if st.button("🚨 EMERGENCY RESET"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.query_params.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- 4. THE FORM ---
with st.form("input_form", clear_on_submit=True):
    cmd = st.text_input("Enter Command (Names or Scores):")
    submitted = st.form_submit_button("Submit Command")

if submitted and cmd:
    raw = cmd.strip()
    
    if st.session_state.mode == "setup" and "winner" not in raw.lower():
        words = [w.strip(",").capitalize() for w in raw.split() if not w.isdigit() and w.lower() != "and"]
        for w in words:
            if w not in st.session_state.players:
                st.session_state.players.append(w); st.session_state.picks[w] = 0
        save_state(); st.rerun()
        
    elif "winner" in raw.lower():
        st.session_state.mode = "play"
        nums = [int(n) for n in re.findall(r'\d+', raw)]
        win_match = re.search(r'winner\s+([a-zA-Z]+)', raw, re.IGNORECASE)
        
        winner_name = None
        if win_match:
            w_str = win_match.group(1).lower()
            for p in st.session_state.players:
                if w_str in p.lower() or p.lower() in w_str:
                    winner_name = p; break
                    
        if winner_name and nums:
            losers = []
            for word in raw.split():
                for p in st.session_state.players:
                    if p != winner_name and (p.lower() in word.lower() or word.lower() in p.lower()):
                        if p not in losers: losers.append(p)
                        
            new_r = {p: 0 for p in st.session_state.players}
            pot = 0
            for i, loser in enumerate(losers):
                if i < len(nums):
                    new_r[loser] = -nums[i]; pot += nums[i]
                    
            new_r[winner_name] = pot
            st.session_state.history.append(new_r)
            st.session_state.dealer = (st.session_state.dealer + 1) % len(st.session_state.players)
            st.session_state.picks = {p: 0 for p in st.session_state.players}
            save_state(); st.rerun()
            
    elif "pick" in raw.lower():
        for p in st.session_state.players:
            if p.lower() in raw.lower():
                st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1)
                save_state(); st.rerun()

# --- 5. RENDER THE PAGE ---
if st.session_state.players:
    if st.session_state.mode == "setup":
        if st.button("🚀 LOCK NAMES & START"):
            st.session_state.mode = "play"; save_state(); st.rerun()
            
    if st.session_state.mode == "play":
        col1, col2 = st.columns(2)
        with col1: st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer]}")
        with col2:
            if st.button("↩️ Undo last round"):
                if st.session_state.history:
                    st.session_state.history.pop()
                    st.session_state.dealer = (st.session_state.dealer - 1) % len(st.session_state.players)
                    save_state(); st.rerun()
    
    paper = draw_notebook(st.session_state.history, st.session_state.players, st.session_state.dealer, st.session_state.picks)
    st.image(paper, use_container_width=True)
    
    if st.session_state.history:
        st.write("### 📊 Live Totals")
        st.table([{p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}])
        
    # --- MANUAL BACKUP TOOL ---
    with st.expander("💾 Manual Save / Load (Use to resume games later)"):
        st.write("If you want to close your phone entirely and resume later, copy this code:")
        current_code = st.query_params.get("save", "")
        if current_code: st.code(current_code)
        
        st.write("Paste a code below to restore a previous game:")
        restore_code = st.text_input("Paste Game Code:")
        if st.button("Restore Game"):
            if restore_code:
                try:
                    compressed = base64.urlsafe_b64decode(restore_code.encode())
                    json_str = zlib.decompress(compressed).decode()
                    d = json.loads(json_str)
                    st.session_state.update({"players": d['p'], "history": d['h'], "dealer": d['d'], "picks": d['pk'], "mode": d['m']})
                    save_state(); st.rerun()
                except:
                    st.error("Invalid Code!")
