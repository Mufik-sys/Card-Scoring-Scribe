import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import re, os, io, datetime, json, time

# 1. INITIAL SETUP
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. PERSISTENCE ENGINE
SAVE_FILE = "active_game_checkpoint.json"

def save_checkpoint():
    try:
        data = {
            "players": st.session_state.players,
            "history": st.session_state.history,
            "redo_stack": st.session_state.redo_stack,
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
                st.session_state.update({
                    "players": data.get("players", []),
                    "history": data.get("history", []),
                    "redo_stack": data.get("redo_stack", []),
                    "phase": data.get("phase", "setup"),
                    "dealer_idx": data.get("dealer_idx", 0),
                    "current_picks": data.get("picks", {})
                })
            return True
        except: return False
    return False

# 3. STATE INITIALIZATION
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.update({
            "players": [], "history": [], "redo_stack": [],
            "phase": "setup", "dealer_idx": 0, "current_picks": {},
            "game_log": [], "profiles": {}, "last_msg": "", "msg_time": 0
        })

def set_status(msg):
    st.session_state.last_msg = msg
    st.session_state.msg_time = time.time()

# 4. DRAWING ENGINE
def generate_sheet(history, players, dealer_idx, current_picks, is_fin=False, status=""):
    num_rounds, num_players = len(history), len(players)
    width = max(1200, (num_players + 1) * 200) 
    calc_height = max(2200, 1100 + (num_rounds * 210))
    img = Image.new('RGB', (width, calc_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(100, calc_height, 80):
        draw.line([(0, y), (width, y)], fill=(225, 235, 250), width=2)

    try:
        f_h = ImageFont.truetype("Caveat-Regular.ttf", 85)
        f_s = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: f_h = f_s = ImageFont.load_default()

    cx = width // (num_players + 2)
    draw.text((cx, 260), "Rd", (120, 120, 120), f_h, anchor="mt")
    
    for i, name in enumerate(players):
        x = (i + 2) * cx
        # Tallies
        p_picks = current_picks.get(name, 0)
        if p_picks > 0 and not is_fin:
            draw.text((x, 140), "|" * p_picks, (240, 0, 0), f_h, anchor="mt")
        # Name + Dealer (D)
        disp = name[:4].capitalize()
        if i == dealer_idx and not is_fin: disp += " (D)"
        draw.text((x, 260), disp, (40, 40, 100), f_h, anchor="mt")
    
    y, totals = 380, {p: 0 for p in players}
    for r_idx, r_scores in enumerate(history, 1):
        draw.text((cx, y), str(r_idx), (160, 160, 160), f_s, anchor="mt")
        for i, p in enumerate(players):
            val = r_scores.get(p, 0); totals[p] += val
            draw.text(((i + 2) * cx, y), (f"+{val}" if val > 0 else str(val)), (50, 50, 50), f_s, anchor="mt")
        y += 100 
        
        if r_idx > 1 and not is_fin:
            max_s = max(totals.values())
            draw.line([(60, y-10), (width-60, y-10)], (255, 140, 0), 4)
            y += 20
            for i, p in enumerate(players):
                txt = str(totals[p]) + ("*" if totals[p] == max_s and max_s != 0 else "")
                draw.text(((i + 2) * cx, y), txt, (255, 130, 0), f_s, anchor="mt")
            y += 110 

    if is_fin:
        max_t = max(totals.values())
        y += 40
        draw.line([(60, y), (width-60, y)], (0, 0, 0), 6)
        draw.line([(60, y+15), (width-60, y+15)], (0, 0, 0), 6)
        y += 40
        lbl = "End" if status != "TG" else "TG"
        draw.text((cx, y), lbl, (220, 0, 0), f_h, anchor="mt")
        for i, p in enumerate(players):
            f_txt = str(totals[p]) + ("*" if totals[p] == max_t and max_t != 0 else "")
            draw.text(((i + 2) * cx, y), f_txt, (220, 0, 0), f_h, anchor="mt")
    return img

# 5. SIDEBAR
st.sidebar.title("Score Scribe")
if st.sidebar.button("🚀 Start Game"):
    if len(st.session_state.players) >= 2:
        st.session_state.phase = "play"; save_checkpoint(); st.rerun()

if st.sidebar.button("🗑️ Reset All Data"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "redo_stack":[], "phase":"setup", "dealer_idx":0, "current_picks":{}})
    st.rerun()

# 6. MAIN UI
if time.time() - st.session_state.msg_time < 4: st.info(f"⚡ {st.session_state.last_msg}")

st.title("🎙️ Score Scribe Pro")
cmd = st.text_input("Command:", key="in_box")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("↩️ Undo") and st.session_state.history:
        st.session_state.redo_stack.append(st.session_state.history.pop())
        st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
        save_checkpoint(); st.rerun()
with c2:
    if st.button("↪️ Redo") and st.session_state.redo_stack:
        st.session_state.history.append(st.session_state.redo_stack.pop())
        st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
        save_checkpoint(); st.rerun()
with c3:
    if st.button("🚫 TG") and st.session_state.players:
        st.session_state.game_log.append({"date": datetime.datetime.now().strftime("%H:%M"), "players": list(st.session_state.players), "history": list(st.session_state.history), "status": "TG"})
        st.session_state.update({"players":[], "history":[], "phase":"setup", "dealer_idx": 0, "redo_stack": []})
        save_checkpoint(); st.rerun()

# 7. COMMAND PROCESSOR
if cmd:
    raw = cmd.lower().strip()
    if "winner" in raw:
        st.session_state.phase = "play"
        sc = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        wm = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if wm:
            winner = wm.group(1).capitalize()
            new_r = {p: 0 for p in st.session_state.players}
            t_lost = 0
            for p_n, p_v in sc:
                p_n = p_n.capitalize()
                if p_n in new_r: new_r[p_n] = -int(p_v); t_lost += int(p_v)
            if winner in new_r:
                new_r[winner] = t_lost
                st.session_state.history.append(new_r)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                st.session_state.redo_stack = []
                set_status(f"Round recorded!"); save_checkpoint(); st.rerun()

    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_checkpoint(); st.rerun()
    
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                cur = st.session_state.current_picks.get(p, 0)
                if cur < 3: st.session_state.current_picks[p] = cur + 1
                save_checkpoint(); st.rerun()

    elif st.session_state.phase == "setup":
        nms = [w.capitalize() for w in raw.replace(","," ").split() if w not in ["and","start","game"] and not w.isdigit()]
        for n in nms:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        save_checkpoint()

# 8. RENDER
if st.session_state.phase == "play": st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
else: st.info("🛠️ Setup. List names, then record a round to start.")

if st.session_state.players:
    sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(sheet, use_container_width=True)
