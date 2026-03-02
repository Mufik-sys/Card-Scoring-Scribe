import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# --- 1. SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- 2. STORAGE ---
SAVE_FILE = "scribe_v101_final.json"

def save_game():
    try:
        data = {
            "p": st.session_state.players, "h": st.session_state.history,
            "d": st.session_state.dealer_idx, "pk": st.session_state.current_picks,
            "ph": st.session_state.phase
        }
        with open(SAVE_FILE, "w") as f: json.dump(data, f)
    except: pass

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.update({"players": d['p'], "history": d['h'], "dealer_idx": d['d'], "current_picks": d['pk'], "phase": d['ph']})
            return True
        except: return False
    return False

# --- 3. INITIALIZE ---
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup", "log_msg": ""})

# --- 4. NEW ROBUST DRAWING ENGINE ---
def get_sheet(history, players, dealer_idx, current_picks):
    num_p = len(players)
    width = max(1200, (num_p + 1) * 200)
    # Dynamic height: 800px base + 150px per round
    height = 800 + (len(history) * 150)
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Notebook Lines
    for y in range(100, height, 80): draw.line([(0, y), (width, y)], (225, 235, 250), 2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 85)
    except: font = ImageFont.load_default()

    cx = width // (num_p + 2)
    
    # Headers
    draw.text((cx, 260), "Rd", (130, 130, 130), font, anchor="mt")
    for i, p in enumerate(players):
        x = (i + 2) * cx
        # Tally marks
        pk = current_picks.get(p, 0)
        if pk > 0: draw.text((x, 140), "|" * pk, (240, 0, 0), font, anchor="mt")
        # Name + (D)
        txt = p[:4].capitalize()
        if i == dealer_idx: txt += " (D)"
        draw.text((x, 260), txt, (40, 40, 100), font, anchor="mt")

    # DRAW SCORES (Simplified Spacing)
    curr_y = 380
    totals = {p: 0 for p in players}
    
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, curr_y), str(r_idx), (160, 160, 160), font, anchor="mt")
        for i, p in enumerate(players):
            val = r_sc.get(p, 0)
            totals[p] += val
            draw.text(((i+2)*cx, curr_y), str(val), (50, 50, 50), font, anchor="mt")
        
        # Draw subtotal line every round to be safe
        curr_y += 100
        draw.line([(50, curr_y), (width-50, curr_y)], (255, 150, 0), 2)
        curr_y += 20
        for i, p in enumerate(players):
            draw.text(((i + 2) * cx, curr_y), str(totals[p]), (255, 130, 0), font, anchor="mt")
        curr_y += 110 # Space for next round
        
    return img

# --- 5. UI ---
st.title("🎙️ Score Scribe Pro")

if st.button("🚨 Reset All Data"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup", "log_msg": "System Reset"})
    st.rerun()

if st.session_state.log_msg:
    st.info(f"Last Action: {st.session_state.log_msg}")

cmd = st.text_input("Command (Names or Scores):", key="main_input")

# --- 6. AGGRESSIVE LOGIC ---
if cmd:
    raw = cmd.lower().strip()
    
    if st.session_state.phase == "setup" and "winner" not in raw:
        new_names = [n.capitalize() for n in raw.replace(",", " ").split() if not n.isdigit() and n != "and"]
        for n in new_names:
            if n not in st.session_state.players:
                st.session_state.players.append(n); st.session_state.current_picks[n] = 0
        st.session_state.log_msg = f"Players: {', '.join(st.session_state.players)}"
        save_game()

    if "winner" in raw:
        st.session_state.phase = "play"
        nums = re.findall(r'\d+', raw)
        winner_p = None
        for p in st.session_state.players:
            if p.lower() in raw: winner_p = p # Grab the mentioned winner
        
        if winner_p and nums:
            new_round = {p: 0 for p in st.session_state.players}
            # Pair scores to other players mentioned
            others = [p for p in st.session_state.players if p != winner_p]
            for i, val in enumerate(nums):
                if i < len(others): new_round[others[i]] = -int(val)
            
            new_round[winner_p] = abs(sum(new_round.values()))
            st.session_state.history.append(new_round)
            st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
            st.session_state.current_picks = {p:0 for p in st.session_state.players}
            st.session_state.log_msg = f"Round Saved! {winner_p} wins {new_round[winner_p]}"
            save_game(); st.rerun()

    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.current_picks[p] = min(3, st.session_state.current_picks.get(p, 0) + 1)
                st.session_state.log_msg = f"Pick for {p}"; save_game(); st.rerun()

# --- 7. RENDER ---
if st.session_state.players:
    if st.session_state.phase == "setup":
        if st.button("🚀 Start Game"):
            st.session_state.phase = "play"; save_game(); st.rerun()
    
    if st.session_state.phase == "play":
        st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
        if st.button("↩️ Undo last"):
            if st.session_state.history:
                st.session_state.history.pop()
                st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_game(); st.rerun()
    
    # 1. DRAW IMAGE
    sheet = get_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(sheet, use_container_width=True)
    
    # 2. BACKUP TABLE (In case image fails)
    if st.session_state.history:
        st.write("### 📊 Quick View Totals")
        final_totals = {p: 0 for p in st.session_state.players}
        for rnd in st.session_state.history:
            for p in st.session_state.players: final_totals[p] += rnd.get(p, 0)
        st.table([final_totals])
else:
    st.info("Step 1: Type names. Step 2: Hit Start Game.")
