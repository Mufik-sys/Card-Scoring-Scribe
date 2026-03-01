import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. SETUP (Must be the first command)
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. PERSISTENCE (Lightweight JSON)
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
                st.session_state.update({
                    "players": data.get("players", []),
                    "history": data.get("history", []),
                    "phase": data.get("phase", "setup"),
                    "dealer_idx": data.get("dealer_idx", 0),
                    "current_picks": data.get("picks", {})
                })
            return True
        except: return False
    return False

# 3. INITIALIZE STATE (Robust check for AttributeError fix)
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.update({
            "players": [], "history": [], "phase": "setup", 
            "dealer_idx": 0, "current_picks": {}, 
            "last_msg": "", "msg_time": 0.0, "game_log": []
        })

def set_status(msg):
    st.session_state.last_msg = msg
    st.session_state.msg_time = time.time()

# 4. DRAWING ENGINE (Matches the stable "2nd photo" style)
def generate_sheet(history, players, dealer_idx, current_picks, is_fin=False):
    num_rounds, num_players = len(history), len(players)
    width = max(1200, (num_players + 1) * 200) 
    calculated_height = max(2200, 1100 + (num_rounds * 210))
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Paper Lines
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(225, 235, 250), width=2)

    try:
        f_h = ImageFont.truetype("Caveat-Regular.ttf", 85)
        f_s = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: f_h = f_s = ImageFont.load_default()

    col_width = width // (num_players + 2)
    current_y = 260 
    
    draw.text((col_width, current_y), "Rd", fill=(120, 120, 120), font=f_h, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        
        # Tally Marks (Capped at 3)
        count = current_picks.get(name, 0)
        if count > 0 and not is_fin:
            draw.text((x, current_y - 120), "|" * count, fill=(240, 0, 0), font=f_h, anchor="mt")
        
        # Name + Dealer Indicator (D)
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
        
        # Orange Subtotal Lines
        if round_idx > 1 and not is_fin:
            max_s = max(totals.values()) if totals else 0
            draw.line([(60, current_y-10), (width-60, current_y-10)], fill=(255, 140, 0), width=4) 
            current_y += 20
            for i, p in enumerate(players):
                txt = str(totals[p]) + ("*" if totals[p] == max_s and max_s != 0 else "")
                draw.text(((i + 2) * col_width, current_y), txt, fill=(255, 130, 0), font=f_s, anchor="mt")
            current_y += 110 
    return img

# 5. UI & COMMANDS
st.title("🎙️ Score Scribe Pro")

# Status Message Bar
if time.time() - st.session_state.msg_time < 4:
    st.info(f"⚡ {st.session_state.last_msg}")

cmd = st.text_input("Command:", key="in")

c1, c2 = st.columns(2)
with c1:
    if st.button("↩️ Undo") and st.session_state.history:
        st.session_state.history.pop()
        st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
        save_checkpoint(); st.rerun()
with c2:
    if st.button("🗑️ Reset Game"):
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.session_state.update({"players": [], "history": [], "phase": "setup", "dealer_idx": 0, "current_picks": {}})
        st.rerun()

if cmd:
    raw = cmd.lower().strip()
    # Winner Command (Auto-Phase Switch)
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
                for p in st.session_state.players: st.session_state.current_picks[p] = 0 # Reset picks
                set_status(f"Round recorded for {winner}!"); save_checkpoint(); st.rerun()

    # Dealer Command
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_checkpoint(); st.rerun()
            
    # Pick Command (Capped at 3)
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                cur = st.session_state.current_picks.get(p, 0)
                if cur < 3:
                    st.session_state.current_picks[p] = cur + 1
                    set_status(f"Tally added for {p}."); save_checkpoint(); st.rerun()
                break

    # Setup Phase (Names)
    elif st.session_state.phase == "setup":
        names = [w.capitalize() for w in raw.replace(","," ").split() if w not in ["and"] and not w.isdigit()]
        for n in names:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        save_checkpoint()

# 6. DISPLAY
if st.session_state.phase == "play":
    st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")

if st.session_state.players:
    sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(sheet, use_container_width=True)
