import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re
import os
import io

st.set_page_config(page_title="Score Scribe", layout="wide")

# Initialize State
if 'players' not in st.session_state: st.session_state.players = []
if 'history' not in st.session_state: st.session_state.history = []
if 'is_finished' not in st.session_state: st.session_state.is_finished = False

def generate_sheet(history, players, is_finished):
    # Make the canvas even bigger for high-res fonts
    width, height = 1200, 2000
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw Blue Lined Paper
    for y in range(100, height, 80):
        draw.line([(0, y), (width, y)], fill=(200, 220, 240), width=2)

    # FONT LOADING - EXTRA ROBUST
    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        header_font = ImageFont.truetype(font_path, 110) # Massive Headers
        score_font = ImageFont.truetype(font_path, 90)   # Massive Scores
    else:
        st.error(f"🚨 FONT ERROR: '{font_path}' not found on GitHub. Please upload it!")
        header_font = score_font = ImageFont.load_default()

    col_width = width // (len(players) + 1)
    current_y = 110 
    
    # 1. Names
    for i, name in enumerate(players):
        x = (i + 1) * col_width
        draw.text((x, current_y), name, fill=(40, 40, 90), font=header_font, anchor="mt")
    
    current_y += 100
    totals = {p: 0 for p in players}

    # 2. Rounds
    for round_idx, round_scores in enumerate(history):
        for i, p in enumerate(players):
            val = round_scores.get(p, 0)
            totals[p] += val
            x = (i + 1) * col_width
            txt = f"+{val}" if val > 0 else str(val)
            draw.text((x, current_y), txt, fill=(60, 60, 60), font=score_font, anchor="mt")
        
        current_y += 80

        # Subtotal lines every 2 rounds
        if (round_idx + 1) % 2 == 0 and not is_finished:
            draw.line([(50, current_y), (width-50, current_y)], fill=(180, 180, 180), width=3)
            current_y += 15
            for i, p in enumerate(players):
                x = (i + 1) * col_width
                draw.text((x, current_y), str(totals[p]), fill=(20, 20, 20), font=score_font, anchor="mt")
            current_y += 100

    # 3. GRAND TOTAL (Red)
    if is_finished:
        current_y += 30
        draw.line([(50, current_y), (width-50, current_y)], fill=(0, 0, 0), width=6)
        draw.line([(50, current_y+12), (width-50, current_y+12)], fill=(0, 0, 0), width=6)
        current_y += 40
        for i, p in enumerate(players):
            x = (i + 1) * col_width
            draw.text((x, current_y), str(totals[p]), fill=(220, 0, 0), font=header_font, anchor="mt")
            
    return img

# --- INTERFACE ---
st.title("🎙️ Score Scribe Pro")

# Helper instruction
st.markdown("""**Commands:** 1. Type/Say Names first (e.g., *Amena Maz Arwa*)  
2. Record Scores: *Mufi 40 Arwa 80 winner Amena* 3. Say *Undo* or *Game Completed*""")

cmd = st.text_input("Voice/Text Input:", key="input_box")

if cmd:
    raw_text = cmd.lower().strip()
    
    if "new game" in raw_text:
        st.session_state.players, st.session_state.history, st.session_state.is_finished = [], [], False
        st.success("New game started!")

    elif "undo" in raw_text:
        if st.session_state.history:
            st.session_state.history.pop()
            st.toast("Undone!")
        else: st.warning("Nothing to undo.")

    elif "game completed" in raw_text:
        st.session_state.is_finished = True
        st.balloons()

    elif "winner" in raw_text:
        # Improved Regex: Looks for a name and a number
        score_data = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw_text)
        winner_match = re.search(r'winner\s*([a-zA-Z]+)', raw_text)
        
        if winner_match and st.session_state.players:
            winner_name = winner_match.group(1).capitalize()
            new_round = {p: 0 for p in st.session_state.players}
            sum_points = 0
            
            for p_name, p_val in score_data:
                p_name = p_name.capitalize()
                if p_name in new_round:
                    new_round[p_name] = -int(p_val)
                    sum_points += int(p_val)
            
            if winner_name in new_round:
                new_round[winner_name] = sum_points
                st.session_state.history.append(new_round)
                st.success(f"Recorded! {winner_name} wins {sum_points}")
            else:
                st.error(f"Winner '{winner_name}' not found in player list!")
        else:
            st.error("Make sure to say 'winner [Name]'")

    else:
        # Assume it's a list of names
        potential_names = [n.capitalize() for n in raw_text.replace(",", " ").split() if n not in ["and", "complete"]]
        for name in potential_names:
            if name not in st.session_state.players:
                st.session_state.players.append(name)
        st.info(f"Current Players: {', '.join(st.session_state.players)}")

# Render
if st.session_state.players:
    final_img = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.is_finished)
    st.image(final_img, use_container_width=True)
    
    # Download Button
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    st.download_button("📥 Save Score Sheet", buf.getvalue(), "scores.png", "image/png")
