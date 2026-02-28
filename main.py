import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re
import os
import io
import datetime

st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- INITIALIZE STATE ---
if 'players' not in st.session_state: st.session_state.players = []
if 'history' not in st.session_state: st.session_state.history = []
if 'is_finished' not in st.session_state: st.session_state.is_finished = False
if 'game_log' not in st.session_state: st.session_state.game_log = []

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished):
    width, height = 1200, 2200
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw Lined Paper
    line_spacing = 80
    for y in range(100, height, line_spacing):
        draw.line([(0, y), (width, y)], fill=(200, 220, 240), width=2)

    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        header_font = ImageFont.truetype(font_path, 80)
        score_font = ImageFont.truetype(font_path, 75)
        round_font = ImageFont.truetype(font_path, 60)
    else:
        header_font = score_font = round_font = ImageFont.load_default()

    num_cols = len(players) + 1
    col_width = width // (num_cols + 1)
    current_y = 110 
    
    # Headers
    draw.text((col_width, current_y), "Rd", fill=(100, 100, 100), font=header_font, anchor="mt")
    for i, name in enumerate(players):
        short_name = name[:4].capitalize()
        x = (i + 2) * col_width
        draw.text((x, current_y), short_name, fill=(40, 40, 90), font=header_font, anchor="mt")
    
    current_y += line_spacing
    totals = {p: 0 for p in players}

    # Rounds
    for round_idx, round_scores in enumerate(history, 1):
        draw.text((col_width, current_y), str(round_idx), fill=(150, 150, 150), font=round_font, anchor="mt")
        
        for i, p in enumerate(players):
            val = round_scores.get(p, 0)
            totals[p] += val
            x = (i + 2) * col_width
            txt = f"+{val}" if val > 0 else str(val)
            draw.text((x, current_y), txt, fill=(60, 60, 60), font=score_font, anchor="mt")
        current_y += line_spacing

        # Subtotals & Leader Star
        if round_idx % 2 == 0 and not is_finished:
            # Find current leader
            max_score = max(totals.values()) if totals else 0
            
            draw.line([(50, current_y), (width-50, current_y)], fill=(180, 180, 180), width=3)
            current_y += 15
            for i, p in enumerate(players):
                x = (i + 2) * col_width
                score_text = str(totals[p])
                # Add star if leader
                if totals[p] == max_score and max_score != 0:
                    score_text = f"{score_text}*" # Simple star
                draw.text((x, current_y), score_text, fill=(20, 20, 20), font=score_font, anchor="mt")
            current_y += line_spacing

    # Grand Total
    if is_finished:
        max_total = max(totals.values()) if totals else 0
        current_y += 30
        draw.line([(50, current_y), (width-50, current_y)], fill=(0, 0, 0), width=6)
        draw.line([(50, current_y+12), (width-50, current_y+12)], fill=(0, 0, 0), width=6)
        current_y += 40
        draw.text((col_width, current_y), "End", fill=(220, 0, 0), font=header_font, anchor="mt")
        for i, p in enumerate(players):
            x = (i + 2) * col_width
            final_txt = str(totals[p])
            if totals[p] == max_total and max_total != 0:
                final_txt = f"{final_txt}*" 
            draw.text((x, current_y), final_txt, fill=(220, 0, 0), font=header_font, anchor="mt")
            
    return img

# --- NAVIGATION ---
page = st.sidebar.radio("Navigation", ["Active Game", "History Log"])

if page == "Active Game":
    st.title("🎙️ Score Scribe Pro")
    
    cmd = st.text_input("Voice Input:", key="active_input")

    if cmd:
        raw = cmd.lower().strip()
        if "new game" in raw:
            st.session_state.players, st.session_state.history, st.session_state.is_finished = [], [], False
            st.rerun()
        elif "undo" in raw:
            if st.session_state.history: st.session_state.history.pop()
        elif "game completed" in raw:
            st.session_state.is_finished = True
            # Save to log
            log_entry = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "players": list(st.session_state.players),
                "history": list(st.session_state.history)
            }
            st.session_state.game_log.append(log_entry)
            st.balloons()
        elif "winner" in raw:
            score_data = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
            winner_match = re.search(r'winner\s*([a-zA-Z]+)', raw)
            if winner_match:
                winner_name = winner_match.group(1).capitalize()
                new_round = {p: 0 for p in st.session_state.players}
                sum_p = 0
                for p_n, p_v in score_data:
                    p_n = p_n.capitalize()
                    if p_n in new_round:
                        new_round[p_n] = -int(p_v)
                        sum_p += int(p_v)
                if winner_name in new_round:
                    new_round[winner_name] = sum_p
                    st.session_state.history.append(new_round)
        else:
            names = [n.capitalize() for n in raw.replace(",", " ").split() if n not in ["and", "complete"]]
            for n in names:
                if n not in st.session_state.players: st.session_state.players.append(n)

    if st.session_state.players:
        sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.is_finished)
        st.image(sheet, use_container_width=True)
        buf = io.BytesIO()
        sheet.save(buf, format="PNG")
        st.download_button("📥 Save Image", buf.getvalue(), "scores.png", "image/png")

else:
    st.title("📜 Game History Log")
    if not st.session_state.game_log:
        st.write("No completed games yet.")
    else:
        for idx, entry in enumerate(reversed(st.session_state.game_log)):
            with st.expander(f"Game on {entry['date']}"):
                st.write(f"Players: {', '.join(entry['players'])}")
                # Re-generate the image for this history entry
                hist_sheet = generate_sheet(entry['history'], entry['players'], True)
                st.image(hist_sheet, use_container_width=True)
