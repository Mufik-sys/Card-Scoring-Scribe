import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re
import os
import io
import datetime
import json

# --- PAGE SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- PERSISTENCE ---
SAVE_FILE = "active_game_checkpoint.json"

def save_checkpoint():
    data = {
        "players": st.session_state.players,
        "history": st.session_state.history,
        "phase": st.session_state.phase,
        "dealer_idx": st.session_state.dealer_idx,
        "picks": st.session_state.current_picks
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
            st.session_state.dealer_idx = data.get("dealer_idx", 0)
            st.session_state.current_picks = data.get("picks", {})
        return True
    return False

# --- INITIALIZE STATE ---
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.players, st.session_state.history = [], []
        st.session_state.phase, st.session_state.dealer_idx = "setup", 0
        st.session_state.current_picks = {}

if 'game_log' not in st.session_state:
    st.session_state.game_log = []

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished, dealer_idx, current_picks):
    num_rounds = len(history)
    num_players = len(players)
    width = max(1200, (num_players + 1) * 160) 
    calculated_height = max(2000, 1000 + (num_rounds * 210))
    
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Lined Paper
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(200, 220, 240), width=2)

    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        f_scale = max(50, 80 - (num_players * 3))
        header_font = ImageFont.truetype(font_path, f_scale)
        score_font = ImageFont.truetype(font_path, f_scale - 5)
        tally_font = ImageFont.truetype(font_path, f_scale + 10)
    else:
        header_font = score_font = tally_font = ImageFont.load_default()

    col_width = width // (num_players + 2)
    current_y = 160 # Lowered slightly to make room for tallies above
    
    # Headers & Tallies
    draw.text((col_width, current_y), "Rd", fill=(100, 100, 100), font=header_font, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        
        # Draw Tally Marks above Name
        picks_count = current_picks.get(name, 0)
        if picks_count > 0 and not is_finished:
            tally_marks = "|" * picks_count
            draw.text((x, current_y - 70), tally_marks, fill=(200, 0, 0), font=tally_font, anchor="mt")
            
        display_name = name[:4].capitalize()
        if i == dealer_idx and not is_finished:
            display_name += " (D)"
        draw.text((x, current_y), display_name, fill=(40, 40, 90), font=header_font, anchor="mt")
    
    current_y += 100
    totals = {p: 0 for p in players}

    for round_idx, round_scores in enumerate(history, 1):
        draw.text((col_width, current_y), str(round_idx), fill=(150, 150, 150), font=score_font, anchor="mt")
        for i, p in enumerate(players):
            val = round_scores.get(p, 0)
            totals[p] += val
            x = (i + 2) * col_width
            txt = f"+{val}" if val > 0 else str(val)
            draw.text((x, current_y), txt, fill=(60, 60, 60), font=score_font, anchor="mt")
        current_y += 100 

        if round_idx > 1 and not is_finished:
            max_s = max(totals.values()) if totals else 0
            draw.line([(50, current_y - 10), (width - 50, current_y - 10)], fill=(180, 180, 180), width=3)
            current_y += 15
            for i, p in enumerate(players):
                x = (i + 2) * col_width
                s_txt = str(totals[p])
                if totals[p] == max_s and max_s != 0: s_txt += "*"
                draw.text((x, current_y), s_txt, fill=(0, 80, 200), font=score_font, anchor="mt")
            current_y += 110 

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

# --- UI ---
st.sidebar.title("Navigation")
nav = st.sidebar.radio("Go to:", ["Active Game", "History Log"])

if nav == "Active Game":
    st.title("🎙️ Score Scribe Pro")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        cmd = st.text_input("Command:", key="input_box")
    with col2:
        st.write(" ")
        if st.button("↩️ Undo"):
            if st.session_state.history: 
                st.session_state.history.pop()
                st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_checkpoint()
                st.rerun()

    if st.session_state.phase == "setup":
        st.info("🛠️ **Setup.** Say names, then 'Start Game'.")
    elif st.session_state.phase == "play":
        current_dealer = st.session_state.players[st.session_state.dealer_idx]
        st.success(f"🎴 **Playing.** Dealer: **{current_dealer}**")

    if cmd:
        raw = cmd.lower().strip()
        
        if "new game" in raw:
            st.session_state.players, st.session_state.history, st.session_state.phase = [], [], "setup"
            st.session_state.dealer_idx, st.session_state.current_picks = 0, {}
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            st.rerun()

        elif "dealer" in raw:
            for i, p in enumerate(st.session_state.players):
                if p.lower() in raw:
                    st.session_state.dealer_idx = i
                    save_checkpoint(); st.toast(f"Dealer set to {p}!"); break

        elif "pick" in raw and st.session_state.phase == "play":
            for p in st.session_state.players:
                if p.lower() in raw:
                    count = st.session_state.current_picks.get(p, 0)
                    if count < 3:
                        st.session_state.current_picks[p] = count + 1
                        save_checkpoint(); st.toast(f"{p} picked a card!"); break

        elif st.session_state.phase == "setup":
            if "start game" in raw or "complete" in raw:
                if len(st.session_state.players) >= 2:
                    st.session_state.phase = "play"
                    st.session_state.current_picks = {p: 0 for p in st.session_state.players}
                    save_checkpoint(); st.rerun()
            else:
                names = [n.capitalize() for n in raw.replace(",", " ").split() if n not in ["and"]]
                for n in names:
                    if n not in st.session_state.players: st.session_state.players.append(n)
                save_checkpoint()

        elif st.session_state.phase == "play":
            if "game completed" in raw:
                st.session_state.phase = "finished"
                st.session_state.game_log.append({"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "players": list(st.session_state.players), "history": list(st.session_state.history)})
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
                            new_round[p_n] = -int(p_v); sum_p += int(p_v)
                    if w_name in new_round:
                        new_round[w_name] = sum_p
                        st.session_state.history.append(new_round)
                        st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                        # RESET PICKS FOR NEXT ROUND
                        st.session_state.current_picks = {p: 0 for p in st.session_state.players}
                        save_checkpoint()

    if st.session_state.players:
        sheet = generate_sheet(st.session_state.history, st.session_state.players, (st.session_state.phase == "finished"), st.session_state.dealer_idx, st.session_state.current_picks)
        st.image(sheet, use_container_width=True)
        buf = io.BytesIO()
        sheet.save(buf, format="PNG")
        st.download_button("📥 Save Image", buf.getvalue(), "scores.png", "image/png")
else:
    st.title("📜 History")
    if st.sidebar.button("🗑️ Clear History"): st.session_state.game_log = []; st.rerun()
    for entry in reversed(st.session_state.game_log):
        with st.expander(f"Game: {entry['date']}"):
            st.image(generate_sheet(entry['history'], entry['players'], True, 0, {}), use_container_width=True)
