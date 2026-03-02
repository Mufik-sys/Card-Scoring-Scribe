import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. SETUP
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. STORAGE
SAVE_FILE = "scribe_precision_v1.json"

def save_game():
    data = {"p": st.session_state.players, "h": st.session_state.history, "d": st.session_state.dealer_idx, "pk": st.session_state.current_picks, "ph": st.session_state.phase}
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f); st.session_state.update({"players": d['p'], "history": d['h'], "dealer_idx": d['d'], "current_picks": d['pk'], "phase": d['ph']})
            return True
        except: return False
    return False

# 3. INITIALIZE
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup", "log": ""})

# 4. ROBUST DRAWING ENGINE
def get_sheet(history, players, dealer_idx, current_picks):
    num_p = len(players)
    width = max(1200, (num_p + 1) * 200)
    # Grow height: 600px base + 220px per round
    height = 600 + (len(history) * 220)
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(100, height, 80): draw.line([(0, y), (width, y)], (225, 235, 250), 2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 85)
    except: font = ImageFont.load_default()

    cx = width // (num_p + 2)
    draw.text((cx, 260), "Rd", (130, 130, 130), font, anchor="mt")
    for i, p in enumerate(players):
        x = (i + 2) * cx
        # Tallies
        pk = current_picks.get(p, 0)
        if pk > 0: draw.text((x, 140), "|" * pk, (240, 0, 0), font, anchor="mt")
        # Header
        txt = p[:4].capitalize()
        if i == dealer_idx: txt += " (D)"
        draw.text((x, 260), txt, (40, 40, 100), font, anchor="mt")

    # Scores
    y_ptr = 380
    totals = {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, y_ptr), str(r_idx), (160, 160, 160), font, anchor="mt")
        for i, p in enumerate(players):
            v = r_sc.get(p, 0); totals[p] += v
            draw.text(((i+2)*cx, y_ptr), (f"+{v}" if v > 0 else str(v)), (50, 50, 50), font, anchor="mt")
        # Orange Totals
        y_ptr += 100
        draw.line([(60, y_ptr), (width-60, y_ptr)], (255, 150, 0), 3)
        y_ptr += 20
        for i, p in enumerate(players):
            draw.text(((i+2)*cx, y_ptr), str(totals[p]), (255, 130, 0), font, anchor="mt")
        y_ptr += 100 # Reset for next round
    return img

# 5. UI
st.title("🎙️ Score Scribe Pro")
if st.button("🚨 Reset All Data"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup", "log": ""})
    st.rerun()

if st.session_state.log: st.info(st.session_state.log)

cmd = st.text_input("Command:", key="cmd_in")

# 6. PRECISION LOGIC
if cmd:
    raw = cmd.lower().strip()
    # Find numbers
    nums = [int(n) for n in re.findall(r'\d+', raw)]
    # Find Winner (Strict: Word immediately after 'winner')
    win_match = re.search(r'winner\s+([a-zA-Z]+)', raw)
    
    if win_match and nums:
        winner_name = win_match.group(1).capitalize()
        if winner_name in st.session_state.players:
            st.session_state.phase = "play"
            new_r = {p: 0 for p in st.session_state.players}
            # Match scores to other players in command order
            others = [p for p in st.session_state.players if p != winner_name]
            # Improved Pairing: Match mentioned names to numbers
            pot = 0
            for i, p_cand in enumerate(others):
                if p_cand.lower() in raw and len(nums) > 0:
                    val = nums.pop(0)
                    new_r[p_cand] = -val
                    pot += val
            new_r[winner_name] = pot
            st.session_state.history.append(new_r)
            st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
            st.session_state.current_picks = {p:0 for p in st.session_state.players}
            st.session_state.log = f"Saved: {winner_name} wins {pot}!"
            save_game(); st.rerun()

    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.current_picks[p] = min(3, st.session_state.current_picks.get(p, 0) + 1)
                st.session_state.log = f"Tally for {p}"; save_game(); st.rerun()

    elif st.session_state.phase == "setup":
        nms = [n.capitalize() for n in raw.replace(","," ").split() if not n.isdigit() and n != "and"]
        for n in nms:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        save_game(); st.rerun()

# 7. RENDER
if st.session_state.players:
    if st.session_state.phase == "play":
        st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
        if st.button("↩️ Undo last"):
            if st.session_state.history:
                st.session_state.history.pop(); st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_game(); st.rerun()
    
    img = get_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(img, use_container_width=True)
else:
    st.info("Step 1: Type player names and hit enter.")