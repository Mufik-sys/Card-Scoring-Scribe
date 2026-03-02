import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. SETUP
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. FILE PATH
SAVE_FILE = "scribe_interactive_v1.json"

def save_game():
    data = {
        "p": st.session_state.players, "h": st.session_state.history,
        "d": st.session_state.dealer_idx, "pk": st.session_state.current_picks,
        "ph": st.session_state.phase
    }
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.update({"players": d['p'], "history": d['h'], "dealer_idx": d['d'], "current_picks": d['pk'], "phase": d['ph']})
            return True
        except: return False
    return False

# 3. INITIALIZE
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup"})

# 4. DRAWING ENGINE
def get_sheet(history, players, dealer_idx, current_picks):
    num_p = len(players)
    width = max(1200, (num_p + 1) * 200)
    height = max(2200, 1100 + (len(history) * 210))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(100, height, 80): draw.line([(0, y), (width, y)], (225, 235, 250), 2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 80)
    except: font = ImageFont.load_default()

    cx = width // (num_p + 2)
    draw.text((cx, 260), "Rd", (130, 130, 130), font, anchor="mt")
    
    for i, p in enumerate(players):
        x = (i + 2) * cx
        # Tallies
        pk = current_picks.get(p, 0)
        if pk > 0: draw.text((x, 140), "|" * pk, (240, 0, 0), font, anchor="mt")
        # Name + (D)
        txt = p[:4].capitalize()
        if i == dealer_idx: txt += " (D)"
        draw.text((x, 260), txt, (40, 40, 100), font, anchor="mt")

    curr_y, totals = 380, {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, curr_y), str(r_idx), (160, 160, 160), font, anchor="mt")
        for i, p in enumerate(players):
            v = r_sc.get(p, 0); totals[p] += v
            draw.text(((i+2)*cx, curr_y), str(v), (50, 50, 50), font, anchor="mt")
        curr_y += 100
        if r_idx >= 1:
            draw.line([(50, curr_y), (width-50, curr_y)], (255, 150, 0), 4)
            curr_y += 20
            for i, p in enumerate(players):
                draw.text(((i+2)*cx, curr_y), str(totals[p]), (255, 130, 0), font, anchor="mt")
            curr_y += 110
    return img

# 5. MAIN UI
st.title("🎙️ Score Scribe Pro")

# Reset Button always available
if st.button("🚨 Reset All Data"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup"})
    st.rerun()

cmd = st.text_input("Command (Names, Picks, or Winner):", key="main_in")

# 6. LOGIC
if cmd:
    raw = cmd.lower().strip()
    
    # Adding Names in Setup
    if st.session_state.phase == "setup":
        new_names = [n.capitalize() for n in raw.replace(",", " ").split() if not n.isdigit() and n != "and"]
        for n in new_names:
            if n not in st.session_state.players:
                st.session_state.players.append(n); st.session_state.current_picks[n] = 0
        save_game()

    # Gameplay Commands
    if "winner" in raw:
        st.session_state.phase = "play"
        sc = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        wm = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if wm:
            winner, new_r, pot = wm.group(1).capitalize(), {p: 0 for p in st.session_state.players}, 0
            for p_n, p_v in sc:
                p_n = p_n.capitalize()
                if p_n in new_r: new_r[p_n] = -int(p_v); pot += int(p_v)
            if winner in new_r:
                new_r[winner] = pot; st.session_state.history.append(new_r)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                save_game(); st.rerun()

    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.current_picks[p] = min(3, st.session_state.current_picks.get(p, 0) + 1)
                save_game(); st.rerun()
    
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_game(); st.rerun()

# 7. RENDER
if st.session_state.players:
    # Explicit Start Button
    if st.session_state.phase == "setup":
        if st.button("🚀 LOCK NAMES & START"):
            st.session_state.phase = "play"; save_game(); st.rerun()
        st.write("**Players added:** " + ", ".join(st.session_state.players))
    
    # The Sheet
    if st.session_state.phase == "play":
        st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
        if st.button("↩️ Undo Round"):
            if st.session_state.history:
                st.session_state.history.pop()
                st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_game(); st.rerun()
    
    img = get_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(img, use_container_width=True)
else:
    st.info("Type player names and hit enter to begin.")
