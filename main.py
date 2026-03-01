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
        "redo_stack": st.session_state.redo_stack,
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
            st.session_state.redo_stack = data.get("redo_stack", [])
            st.session_state.phase = data.get("phase", "setup")
            st.session_state.dealer_idx = data.get("dealer_idx", 0)
            st.session_state.current_picks = data.get("picks", {})
        return True
    return False

# --- INITIALIZE ---
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.players, st.session_state.history, st.session_state.redo_stack = [], [], []
        st.session_state.phase, st.session_state.dealer_idx = "setup", 0
        st.session_state.current_picks = {}

if 'game_log' not in st.session_state: st.session_state.game_log = []
if 'profiles' not in st.session_state: st.session_state.profiles = {}

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished, dealer_idx, current_picks):
    num_rounds = len(history)
    num_players = len(players)
    width = max(1200, (num_players + 1) * 180) 
    calculated_height = max(2000, 1000 + (num_rounds * 210))
    
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(200, 220, 240), width=2)

    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        f_scale = max(45, 85 - (num_players * 4))
        header_font = ImageFont.truetype(font_path, f_scale)
        score_font = ImageFont.truetype(font_path, f_scale - 5)
        tally_font = ImageFont.truetype(font_path, f_scale + 15)
    else:
        header_font = score_font = tally_font = ImageFont.load_default()

    col_width = width // (num_players + 2)
    current_y = 160 
    
    draw.text((col_width, current_y), "Rd", fill=(100, 100, 100), font=header_font, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        picks_count = current_picks.get(name, 0)
        if picks_count > 0 and not is_finished:
            draw.text((x, current_y - 80), "|" * picks_count, fill=(200, 0, 0), font=tally_font, anchor="mt")
        display_name = name[:4].capitalize()
        draw.text((x, current_y), display_name, fill=(40, 40, 90), font=header_font, anchor="mt")
        if i == dealer_idx and not is_finished:
            bbox = draw.textbbox((x, current_y), display_name, font=header_font, anchor="mt")
            draw.line([(bbox[0], bbox[3]+5), (bbox[2], bbox[3]+5)], fill=(40, 40, 90), width=4)
            draw.line([(bbox[0], bbox[3]+12), (bbox[2], bbox[3]+12)], fill=(40, 40, 90), width=4)
    
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
                draw.text((x, current_y), s_txt, fill=(255, 140, 0), font=score_font, anchor="mt")
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

# --- SIDEBAR & PROFILES ---
st.sidebar.title("Navigation")
nav = st.sidebar.radio("Go to:", ["Active Game", "History Log"])

st.sidebar.markdown("---")
with st.sidebar.expander("👤 Manage Profiles"):
    if st.session_state.players:
        p_to_edit = st.selectbox("Select Player:", st.session_state.players)
        img_file = st.file_uploader(f"Upload photo for {p_to_edit}", type=['jpg', 'png', 'jpeg'])
        if img_file:
            st.session_state.profiles[p_to_edit] = img_file.read()
            st.success("Photo updated!")
    else:
        st.write("Start a game to add profiles.")

# --- MAIN UI ---
if nav == "Active Game":
    st.title("🎙️ Score Scribe Pro")
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: cmd = st.text_input("Command:", key="input_box")
    with c2: 
        st.write(" "); 
        if st.button("↩️ Undo"):
            if st.session_state.history:
                st.session_state.redo_stack.append(st.session_state.history.pop())
                st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_checkpoint(); st.rerun()
    with c3:
        st.write(" "); 
        if st.button("↪️ Redo"):
            if st.session_state.redo_stack:
                st.session_state.history.append(st.session_state.redo_stack.pop())
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                save_checkpoint(); st.rerun()

    if cmd:
        raw = cmd.lower().strip()
        if "new game" in raw:
            st.session_state.players, st.session_state.history, st.session_state.redo_stack, st.session_state.phase = [], [], [], "setup"
            st.session_state.dealer_idx, st.session_state.current_picks = 0, {}
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            st.rerun()
        elif "dealer" in raw:
            for i, p in enumerate(st.session_state.players):
                if p.lower() in raw: st.session_state.dealer_idx = i; save_checkpoint(); st.rerun(); break
        elif st.session_state.phase == "setup":
            if "start game" in raw or "complete" in raw:
                if len(st.session_state.players) >= 2: st.session_state.phase = "play"; save_checkpoint(); st.rerun()
            else:
                words = raw.replace(",", " ").split()
                names = [w.capitalize() for w in words if w not in ["and", "winner"] and not w.isdigit()]
                for n in names:
                    if n not in st.session_state.players: st.session_state.players.append(n)
                save_checkpoint()
        elif st.session_state.phase == "play":
            if "pick" in raw:
                for p in st.session_state.players:
                    if p.lower() in raw:
                        count = st.session_state.current_picks.get(p, 0)
                        if count < 3: st.session_state.current_picks[p] = count + 1; save_checkpoint(); break
            elif "game completed" in raw:
                st.session_state.phase = "finished"
                st.session_state.game_log.append({"id": datetime.datetime.now().timestamp(), "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "players": list(st.session_state.players), "history": list(st.session_state.history)})
                if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
                st.balloons()
            elif "winner" in raw:
                score_data = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw); winner_match = re.search(r'winner\s*([a-zA-Z]+)', raw)
                if winner_match:
                    w_name = winner_match.group(1).capitalize(); new_round = {p: 0 for p in st.session_state.players}; sum_p = 0
                    for p_n, p_v in score_data:
                        p_n = p_n.capitalize()
                        if p_n in new_round: new_round[p_n] = -int(p_v); sum_p += int(p_v)
                    if w_name in new_round:
                        new_round[w_name] = sum_p; st.session_state.history.append(new_round); st.session_state.redo_stack = []
                        st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                        st.session_state.current_picks = {p: 0 for p in st.session_state.players}; save_checkpoint()

    if st.session_state.players:
        sheet = generate_sheet(st.session_state.history, st.session_state.players, (st.session_state.phase == "finished"), st.session_state.dealer_idx, st.session_state.current_picks)
        st.image(sheet, use_container_width=True)
        buf = io.BytesIO(); sheet.save(buf, format="PNG")
        st.download_button("📥 Save Image", buf.getvalue(), "scores.png", "image/png")
else:
    st.title("📜 History & Standings")
    if st.sidebar.button("🗑️ Wipe All History"): st.session_state.game_log = []; st.rerun()
    
    if st.session_state.game_log:
        win_counts = {}
        for entry in st.session_state.game_log:
            totals = {p: 0 for p in entry['players']}
            for rnd in entry['history']:
                for p in entry['players']: totals[p] += rnd.get(p, 0)
            if totals:
                winner = max(totals, key=totals.get)
                win_counts[winner] = win_counts.get(winner, 0) + 1
        
        st.subheader("🏆 Series Standings")
        s_cols = st.columns(len(win_counts))
        for i, (player, wins) in enumerate(win_counts.items()):
            with s_cols[i]:
                if player in st.session_state.profiles:
                    st.image(st.session_state.profiles[player], width=80)
                st.metric(label=player, value=f"{wins} Wins")
    
    st.markdown("---")
    # Loop through log with index to allow targeted deletion
    for idx, entry in enumerate(reversed(st.session_state.game_log)):
        actual_idx = len(st.session_state.game_log) - 1 - idx
        with st.expander(f"Game: {entry['date']}"):
            st.image(generate_sheet(entry['history'], entry['players'], True, 0, {}), use_container_width=True)
            if st.button(f"🗑️ Remove Game from Log", key=f"del_{entry['id']}"):
                st.session_state.game_log.pop(actual_idx)
                st.rerun()
