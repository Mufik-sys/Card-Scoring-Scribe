import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random
import re

# --- APP CONFIG & STATE ---
if 'players' not in st.session_state: st.session_state.players = []
if 'history' not in st.session_state: st.session_state.history = []
if 'is_finished' not in st.session_state: st.session_state.is_finished = False

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished):
    img = Image.new('RGB', (1000, 1400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(80, 1400, 60): draw.line([(0, y), (1000, y)], fill=(220, 230, 240), width=1)
    try: font = ImageFont.load_default() # On cloud, we use default or uploaded .ttf
    except: font = ImageFont.load_default()
    
    margin, spacing, current_y = 80, 180, 90
    for i, name in enumerate(players):
        draw.text((margin + (i * spacing), current_y), name, fill=(50, 50, 70), font=font)
    
    current_y += 60
    totals = {p: 0 for p in players}
    for round_idx, scores in enumerate(history):
        for i, p in enumerate(players):
            val = scores.get(p, 0)
            totals[p] += val
            txt = f"+{val}" if val > 0 else str(val)
            draw.text((margin + (i * spacing), current_y), txt, fill=(40, 40, 60), font=font)
        current_y += 60
        if (round_idx + 1) % 2 == 0:
            draw.line([(40, current_y), (960, current_y)], fill=(120, 120, 120), width=2)
            current_y += 10
            for i, p in enumerate(players):
                draw.text((margin + (i * spacing), current_y), str(totals[p]), fill=(20, 20, 20), font=font)
            current_y += 80

    if is_finished:
        draw.line([(40, current_y), (960, current_y)], fill=(0, 0, 0), width=5)
        current_y += 20
        for i, p in enumerate(players):
            draw.text((margin + (i * spacing), current_y), str(totals[p]), fill=(255, 0, 0), font=font)
    return img

# --- UI & VOICE LOGIC ---
st.title("Card Score Scribe")
cmd = st.text_input("Voice Command (Speak or Type):", placeholder="e.g. 'new game' or 'Mufi 40 Arwa 80 winner Amena'")

if cmd:
    cmd = cmd.lower()
    if "new game" in cmd:
        st.session_state.players, st.session_state.history, st.session_state.is_finished = [], [], False
        st.success("New game started! List the player names.")
    elif "game completed" in cmd:
        st.session_state.is_finished = True
        st.balloons()
    elif "winner" in cmd and st.session_state.players:
        points = re.findall(r'(\w+)\s+(\d+)', cmd)
        winner_match = re.search(r'winner\s+(\w+)', cmd)
        if winner_match:
            winner = winner_match.group(1).capitalize()
            round_data = {p: 0 for p in st.session_state.players}
            total_lost = 0
            for n, v in points:
                n = n.capitalize()
                if n in round_data:
                    round_data[n] = -int(v)
                    total_lost += int(v)
            if winner in round_data: round_data[winner] = total_lost
            st.session_state.history.append(round_data)
    else: # Adding names
        names = [n.capitalize() for n in cmd.replace(",", " ").split() if n not in ["and", "complete"]]
        st.session_state.players.extend(names)

if st.session_state.players:
    img = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.is_finished)
    st.image(img)
