import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re
import os
import io
import datetime
import json

# --- PAGE SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- PERSISTENCE LOGIC ---
SAVE_FILE = "active_game_checkpoint.json"

def save_checkpoint():
    data = {
        "players": st.session_state.players,
        "history": st.session_state.history,
        "phase": st.session_state.phase
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

def load_checkpoint():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            st.session_state.players = data.get("players", [])
            st.session_state.history = data.get("history", [])
            st.session_state.phase = data.get("phase", "setup")
        return True
    return False

# --- INITIALIZE STATE ---
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.players = []
        st.session_state.history = []
        st.session_state.phase = "setup"

if 'game_log' not in st.session_state:
    st.session_state.game_log = []

# --- UPDATED IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished):
    num_rounds = len(history)
    # Dynamic height calculation to accommodate more subtotal lines
    base_height = 1000
    calculated_height = max(2000, base_height + (num_rounds * 200))
    width = 1200
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Lined Paper background
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(200, 220, 240), width=2)

    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        header_font = ImageFont.truetype(font_path, 80)
        score_font = ImageFont.truetype(font_path, 75)
    else:
        header_font = score_font = ImageFont.load_default()

    num_cols = len(players) + 1
    col_width = width // (num_cols + 1)
    current_y = 110 
    
    # Headers
    draw.text((col_width, current_y), "Rd", fill=(100, 100, 100), font=header_font, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        draw.text((x, current_y), name[:4].capitalize(), fill=(40, 40, 90), font=header_font, anchor="mt")
    
    current_y += 100
    totals = {p: 0 for p in players}

    # Rounds loop
    for round_idx, round_scores in enumerate(history, 1):
        # Draw Round Number
        draw.text((col_width, current_y), str(round_idx), fill=(150, 150, 150), font=score_font, anchor="mt")
        
        # Draw Round Scores
        for i, p in enumerate(players):
            val = round_scores.get(p, 0)
            totals[p] += val
            x = (i + 2) * col_width
            txt = f"+{val}" if val > 0 else str(val)
            draw.text((x, current_y), txt, fill=(60, 60, 60), font=score_font, anchor="mt")
        current_y += 100 

        # UPDATED SUB-TOTAL LOGIC: Show after every round EXCEPT Round 1
        if round_idx > 1 and not is_finished:
            max_s = max(totals.values()) if totals else 0
            # Draw subtotal divider
            draw.line([(50, current_y - 10), (width - 50, current_y - 10)], fill=(180, 180, 180), width=3)
            current_y += 15
            for i, p in enumerate(players):
                x = (i + 2) * col_width
                s_txt = str(totals[p])
                # Leader Star logic
                if totals[p] == max_s and max_s != 0: s_txt += "*"
                draw.text((x, current_y), s_txt, fill=(20, 20, 20), font=score_font, anchor="mt")
            current_y += 110 

    # Grand Total at the end of the game
    if is_finished:
        max_t = max(totals.values()) if totals else 0
        current_y += 30
        draw.line([(50, current_y), (width-50, current_y)], fill=(0, 0, 0), width=6)
        draw.line([(50, current_y+12), (width-50, current_y+12)], fill=(0, 0, 0), width=6)
        current_y += 40
        draw.text((col_width, current_y), "End", fill=(220, 0, 0), font=header_font, anchor="mt")
        for i, p in enumerate(players):
            x = (i + 2) * col_width
            f_txt = str(totals[p])
            if totals[p] == max_t and max_t != 0: f_txt += "*" 
            draw.text((x, current_y), f_txt, fill=(220, 0, 0), font=header_font, anchor="mt")
            
    return img

# --- UI LOGIC ---
st.sidebar.title("Navigation")
nav = st.sidebar.radio("Go to:", ["Active Game", "History Log"])

if nav == "Active Game":
    st.title("🎙️ Score Scribe Pro")
    
    # Checkpoint recovery for phone browser refreshes
    if os.path.exists(SAVE_FILE) and st.session_state.phase == "setup" and not st.session_state.players:
        if st.button("♻️ Resume Previous Game?"):
            load_checkpoint()
            st.rerun()

    if st.session_state.phase == "setup":
        st.info("🛠️ **Setup.** Say names, then 'Start Game'.")
    elif st.session_state.phase == "play":
        st.success(f"🎴 **Playing.** Round {len(st.session_state.history) + 1}")
    else:
        st.warning("🏁 **Finished.**")

    cmd = st.text_input("Command:", key="input_box")

    if cmd:
        raw = cmd.lower().strip()
        
        if "new game" in raw:
            st.session_state.players, st.session_state.history, st.session_state.phase = [], [], "setup"
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            st.rerun()

        if st.session_state.phase == "setup":
            if "start game" in raw or "complete" in raw:
                if len(st.session_state.players) >= 2:
                    st.session_state.phase = "play"
                    save_checkpoint()
                    st.rerun()
            else:
                names = [n.capitalize() for n in raw.replace(",", " ").split() if n not in ["and"]]
                for n in names:
                    if n not in st.session_state.players: st.session_state.players.append(n)
                save_checkpoint()

        elif st.session_state.phase == "play":
            if "undo" in raw:
                if st.session_state.history: 
                    st.session_state.history.pop()
                    save_checkpoint()
            elif "game completed" in raw:
                st.session_state.phase = "finished"
                st.session_state.game_log.append({
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "players": list(st.session_state.players),
                    "history": list(st.session_state.history)
                })
                if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
                st.balloons()
            elif "winner" in raw:
                score_data = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
                winner_match = re.search(r'winner\s*([a-zA-Z]+)', raw)
                if winner_match:
                    w_name = winner_match.group(1).capitalize()
                    new_round = {p: 0 for p in st.session_state.players}
                    sum_p = 0
                    for p_n, p_v in score_data:
                        p_n = p_n.capitalize()
                        if p_n in new_round:
                            new_round[p_n] = -int(p_v)
                            sum_p += int(p_v)
                    if w_name in new_round:
                        new_round[w_name] = sum_p
                        st.session_state.history.append(new_round)
                        save_checkpoint()

    if st.session_state.players:
        sheet = generate_sheet(st.session_state.history, st.session_state.players, (st.session_state.phase == "finished"))
        st.image(sheet, use_container_width=True)
        buf = io.BytesIO()
        sheet.save(buf, format="PNG")
        st.download_button("📥 Save Sheet Image", buf.getvalue(), "scores.png", "image/png")

else:
    st.title("📜 History Log")
    if not st.session_state.game_log:
        st.write("No completed games yet.")
    else:
        for entry in reversed(st.session_state.game_log):
            with st.expander(f"Game: {entry['date']}"):
                h_sheet = generate_sheet(entry['history'], entry['players'], True)
                st.image(h_sheet, use_container_width=True)
