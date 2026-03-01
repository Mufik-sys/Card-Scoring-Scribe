import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. SETUP - Must be the first line
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. PERSISTENCE
SAVE_FILE = "active_game_checkpoint.json"

def save_game():
    try:
        data = {
            "players": st.session_state.players,
            "history": st.session_state.history,
            "redo": st.session_state.redo_stack,
            "phase": st.session_state.phase,
            "dealer": st.session_state.dealer_idx,
            "picks": st.session_state.current_picks
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.players = d.get("players", [])
                st.session_state.history = d.get("history", [])
                st.session_state.redo_stack = d.get("redo", [])
                st.session_state.phase = d.get("phase", "setup")
                st.session_state.dealer_idx = d.get("dealer", 0)
                st.session_state.current_picks = d.get("picks", {})
            return True
        except: return False
    return False

# 3. INITIALIZE ALL STATE KEYS
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.players = []
        st.session_state.history = []
        st.session_state.redo_stack = []
        st.session_state.phase = "setup"
        st.session_state.dealer_idx = 0
        st.session_state.current_picks = {}
        st.session_state.game_log = []
        st.session_state.profiles = {}
        st.session_state.last_msg = ""
        st.session_state.msg_time = 0.0

# 4. DRAWING ENGINE
def generate_sheet(history, players, dealer_idx, current_picks, is_fin=False):
    num_rounds, num_players = len(history), len(players)
    width = max(1200, (num_players + 1) * 200)
    height = max(2200, 1100 + (num_rounds * 210))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Paper Lines
    for line_y in range(100, height, 80):
        draw.line([(0, line_y), (width, line_y)], fill=(225, 235, 250), width=2)

    try:
        f_h = ImageFont.truetype("Caveat-Regular.ttf", 85)
        f_s = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: f_h = f_s = ImageFont.load_default()

    cx = width // (num_players + 2)
    draw.text((cx, 260), "Rd", (120, 120, 120), f_h, anchor="mt")
    
    for i, name in enumerate(players):
        x = (i + 2) * cx
        # Tally Marks (Max 3)
        pk = current_picks.get(name, 0)
        if pk > 0 and not is_fin:
            draw.text((x, 140), "|" * pk, (240, 0, 0), f_h, anchor="mt")
        # Name + Dealer (D)
        display = name[:4].capitalize()
        if i == dealer_idx and not is_fin: display += " (D)"
        draw.text((x, 260), display, (40, 40, 100), f_h, anchor="mt")
    
    y_pos, totals = 380, {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, y_pos), str(r_idx), (160, 160, 160), f_s, anchor="mt")
        for i, p in enumerate(players):
            val = r_sc.get(p, 0); totals[p] += val
            draw.text(((i + 2) * cx, y_pos), (f"+{val}" if val > 0 else str(val)), (50, 50, 50), f_s, anchor="mt")
        y_pos += 100 
        if r_idx > 1 and not is_fin:
            max_s = max(totals.values())
            draw.line([(60, y_pos-10), (width-60, y_pos-10)], (255, 140, 0), 4)
            y_pos += 20
            for i, p in enumerate(players):
                txt = str(totals[p]) + ("*" if totals[p] == max_s and max_s != 0 else "")
                draw.text(((i + 2) * cx, y_pos), txt, (255, 130, 0), f_s, anchor="mt")
            y_pos += 110 
    return img

# 5. UI CONTROLS
st.title("🎙️ Score Scribe Pro")

# Status Message
if time.time() - st.session_state.msg_time < 4:
    st.info(f"⚡ {st.session_state.last_msg}")

cmd = st.text_input("Command:", key="main_input")

# Action Buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("↩️ Undo") and st.session_state.history:
        st.session_state.redo_stack.append(st.session_state.history.pop())
        st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
        save_game(); st.rerun()
with col2:
    if st.button("↪️ Redo") and st.session_state.redo_stack:
        st.session_state.history.append(st.session_state.redo_stack.pop())
        st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
        save_game(); st.rerun()
with col3:
    if st.button("🚫 TG") and st.session_state.players:
        st.session_state.game_log.append({"date": datetime.datetime.now().strftime("%H:%M"), "players": list(st.session_state.players), "history": list(st.session_state.history)})
        st.session_state.update({"players":[], "history":[], "phase":"setup", "dealer_idx": 0, "redo_stack": []})
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.rerun()

# 6. COMMAND LOGIC
if cmd:
    raw = cmd.lower().strip()
    
    # RESET COMMAND
    if "new game" in raw:
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.session_state.update({"players":[], "history":[], "phase":"setup", "dealer_idx": 0, "redo_stack": []})
        st.rerun()

    # WINNER COMMAND (Calculates scores)
    elif "winner" in raw:
        st.session_state.phase = "play"
        scores_found = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        win_found = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if win_found:
            winner_name = win_found.group(1).capitalize()
            new_round = {p: 0 for p in st.session_state.players}
            total_pot = 0
            for p_name, p_val in scores_found:
                p_name = p_name.capitalize()
                if p_name in new_round:
                    new_round[p_name] = -int(p_val)
                    total_pot += int(p_val)
            if winner_name in new_round:
                new_round[winner_name] = total_pot
                st.session_state.history.append(new_round)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                st.session_state.redo_stack = []
                st.session_state.last_msg = f"Round saved for {winner_name}"; st.session_state.msg_time = time.time()
                save_game(); st.rerun()

    # DEALER COMMAND
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_game(); st.rerun()

    # PICK COMMAND (Tallies)
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                current_count = st.session_state.current_picks.get(p, 0)
                if current_count < 3:
                    st.session_state.current_picks[p] = current_count + 1
                    save_game(); st.rerun()

    # SETUP COMMAND (Add Names)
    elif st.session_state.phase == "setup":
        names_to_add = [n.capitalize() for n in raw.replace(","," ").split() if n not in ["and"] and not n.isdigit()]
        for name in names_to_add:
            if name not in st.session_state.players:
                st.session_state.players.append(name)
                st.session_state.current_picks[name] = 0
        save_game()

# 7. DISPLAY
if st.session_state.phase == "play":
    st.success(f"🎴 **Dealer:** {st.session_state.players[st.session_state.dealer_idx]}")
else:
    st.info("🛠️ Setup Mode. Enter names to start.")

if st.session_state.players:
    final_sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(final_sheet, use_container_width=True)
