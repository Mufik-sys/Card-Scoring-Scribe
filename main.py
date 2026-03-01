import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# --- PAGE SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- ROBUST PERSISTENCE ---
SAVE_FILE = "active_game_checkpoint.json"

def save_checkpoint():
    try:
        data = {
            "players": st.session_state.players,
            "history": st.session_state.history,
            "phase": st.session_state.phase,
            "dealer_idx": st.session_state.dealer_idx,
            "picks": st.session_state.current_picks
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def load_checkpoint():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                # Only update if the file has data
                if data.get("players"):
                    st.session_state.players = data.get("players", [])
                    st.session_state.history = data.get("history", [])
                    st.session_state.phase = data.get("phase", "setup")
                    st.session_state.dealer_idx = data.get("dealer_idx", 0)
                    st.session_state.current_picks = data.get("picks", {})
                    return True
        except: return False
    return False

# --- INITIALIZE STATE ---
if 'players' not in st.session_state:
    # Try to load from file first to prevent accidental resets
    if not load_checkpoint():
        st.session_state.update({
            "players": [], "history": [], "phase": "setup", 
            "dealer_idx": 0, "current_picks": {}, "game_log": [], 
            "profiles": {}, "last_msg": "", "msg_time": 0
        })

def set_status(msg):
    st.session_state.last_msg = msg
    st.session_state.msg_time = time.time()

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, dealer_idx, current_picks, is_fin=False, status=""):
    num_rounds, num_players = len(history), len(players)
    width = max(1200, (num_players + 1) * 200) 
    calculated_height = max(2200, 1100 + (num_rounds * 210))
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(225, 235, 250), width=2)

    try:
        f_h = ImageFont.truetype("Caveat-Regular.ttf", 80)
        f_s = ImageFont.truetype("Caveat-Regular.ttf", 70)
    except: f_h = f_s = ImageFont.load_default()

    col_width = width // (num_players + 2)
    current_y = 260 
    
    draw.text((col_width, current_y), "Rd", fill=(120, 120, 120), font=f_h, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        count = current_picks.get(name, 0)
        if count > 0 and not is_fin:
            draw.text((x, current_y - 120), "|" * count, fill=(240, 0, 0), font=f_h, anchor="mt")
        
        display_name = name[:4].capitalize()
        if i == dealer_idx and not is_fin: display_name += " (D)"
        draw.text((x, current_y), display_name, fill=(40, 40, 100), font=f_h, anchor="mt")
    
    current_y += 110
    totals = {p: 0 for p in players}
    for round_idx, round_scores in enumerate(history, 1):
        draw.text((col_width, current_y), str(round_idx), fill=(160, 160, 160), font=f_s, anchor="mt")
        for i, p in enumerate(players):
            val = round_scores.get(p, 0); totals[p] += val
            draw.text(((i + 2) * col_width, current_y), (f"+{val}" if val > 0 else str(val)), (50, 50, 50), f_s, anchor="mt")
        current_y += 100 
        
        if round_idx > 1 and not is_fin:
            max_s = max(totals.values())
            draw.line([(60, current_y-10), (width-60, current_y-10)], fill=(255, 140, 0), width=4) 
            current_y += 20
            for i, p in enumerate(players):
                txt = str(totals[p]) + ("*" if totals[p] == max_s and max_s != 0 else "")
                draw.text(((i + 2) * col_width, current_y), txt, fill=(255, 130, 0), font=f_s, anchor="mt")
            current_y += 110 

    if is_fin:
        max_t = max(totals.values())
        current_y += 40
        draw.line([(60, current_y), (width-60, current_y)], fill=(0, 0, 0), width=6)
        draw.line([(60, current_y+15), (width-60, current_y+15)], fill=(0, 0, 0), width=6)
        current_y += 40
        label = "End" if status != "TG" else "TG"
        draw.text((col_width, current_y), label, fill=(220, 0, 0), font=f_h, anchor="mt")
        for i, p in enumerate(players):
            f_txt = str(totals[p]) + ("*" if totals[p] == max_t and max_t != 0 else "")
            draw.text(((i + 2) * col_width, current_y), f_txt, fill=(220, 0, 0), font=f_h, anchor="mt")
    return img

# --- SIDEBAR ---
st.sidebar.title("Score Scribe")
if st.sidebar.button("🚀 Start Game"):
    if len(st.session_state.players) >= 2:
        st.session_state.phase = "play"; save_checkpoint(); st.rerun()
    else: st.sidebar.warning("Add at least 2 players!")

if st.sidebar.button("🗑️ Reset All Data"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players": [], "history": [], "phase": "setup", "dealer_idx": 0, "current_picks": {}})
    st.rerun()

# --- MAIN SCREEN LOGIC ---
if time.time() - st.session_state.msg_time < 4: st.info(f"⚡ {st.session_state.last_msg}")

st.title("🎙️ Score Scribe Pro")
cmd = st.text_input("Command:", key="in")

c1, c2 = st.columns(2)
with c1:
    if st.button("↩️ Undo") and st.session_state.history:
        st.session_state.history.pop()
        st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
        save_checkpoint(); st.rerun()
with c2:
    if st.button("🚫 TG") and st.session_state.players:
        st.session_state.game_log.append({"date": datetime.datetime.now().strftime("%H:%M"), "players": list(st.session_state.players), "history": list(st.session_state.history), "status": "TG"})
        st.session_state.update({"players":[], "history":[], "phase":"setup"}); save_checkpoint(); st.rerun()

if cmd:
    raw = cmd.lower().strip()
    # FAIL-SAFE: If winner is detected, force Play phase
    if "winner" in raw:
        st.session_state.phase = "play"
        scores = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        win_match = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if win_match:
            winner = win_match.group(1).capitalize()
            new_r = {p: 0 for p in st.session_state.players}
            total_lost = 0
            for p_n, p_v in scores:
                p_n = p_n.capitalize()
                if p_n in new_r: new_r[p_n] = -int(p_v); total_lost += int(p_v)
            if winner in new_r:
                new_r[winner] = total_lost; st.session_state.history.append(new_r)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                set_status(f"Round recorded for {winner}!"); save_checkpoint(); st.rerun()

    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_checkpoint(); st.rerun()
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw: 
                st.session_state.current_picks[p] = st.session_state.current_picks.get(p, 0) + 1
                save_checkpoint(); st.rerun()
    elif st.session_state.phase == "setup":
        names = [w.capitalize() for w in raw.replace(","," ").split() if w not in ["and","start","game"] and not w.isdigit()]
        for n in names:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        save_checkpoint()

if st.session_state.phase == "play": st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
else: st.info("🛠️ Setup Mode. List names, then tap 'Start Game' or record a round.")

if st.session_state.players:
    sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(sheet, use_container_width=True)
