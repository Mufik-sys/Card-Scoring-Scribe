import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. PAGE SETUP
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. FILE PATHS (The 'Hidden' Files)
CHECKPOINT_FILE = "active_game_checkpoint.json"
RECOVERY_FILE = "scribe_stable_v3.json"

# 3. THE "CLEANER" LOGIC
def hard_reset():
    for f in [CHECKPOINT_FILE, RECOVERY_FILE, "scribe_data.json"]:
        if os.path.exists(f):
            os.remove(f)
    st.session_state.clear()
    st.rerun()

# 4. INITIALIZE STATE
if 'players' not in st.session_state:
    st.session_state.update({
        "players": [], "history": [], "dealer_idx": 0,
        "current_picks": {}, "phase": "setup", "msg": ""
    })

# 5. DRAWING ENGINE (Clean & Stable)
def draw_sheet(history, players, dealer_idx, picks):
    w, h = max(1200, (len(players)+1)*200), max(2000, 1000+(len(history)*210))
    img = Image.new('RGB', (w, h), (255,255,255))
    draw = ImageDraw.Draw(img)
    for y in range(100, h, 80): draw.line([(0,y),(w,y)], (225,235,250), 2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 80)
    except: font = ImageFont.load_default()

    cx = w // (len(players)+2)
    draw.text((cx, 260), "Rd", (130,130,130), font, anchor="mt")
    for i, p in enumerate(players):
        x, name = (i+2)*cx, p[:4].capitalize()
        if i == dealer_idx: name += " (D)"
        draw.text((x, 260), name, (40,40,100), font, anchor="mt")
        pk = picks.get(p, 0)
        if pk > 0: draw.text((x, 150), "|"*pk, (240,0,0), font, anchor="mt")

    y, totals = 380, {p:0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, y), str(r_idx), (160,160,160), font, anchor="mt")
        for i, p in enumerate(players):
            v = r_sc.get(p, 0); totals[p] += v
            draw.text(((i+2)*cx, y), str(v), (50,50,50), font, anchor="mt")
        y += 100
        if r_idx >= 1:
            draw.line([(50, y), (w-50, y)], (255,150,0), 3)
            y += 15
            for i, p in enumerate(players):
                draw.text(((i+2)*cx, y), str(totals[p]), (255,130,0), font, anchor="mt")
            y += 110
    return img

# 6. UI
st.title("🎙️ Score Scribe Pro")

# EMERGENCY BUTTONS (Top of page for visibility)
if st.button("🚨 HARD RESET (Fix Loop)"):
    hard_reset()

cmd = st.text_input("Command:", key="cmd_box")

if cmd:
    raw = cmd.lower().strip()
    if "winner" in raw:
        st.session_state.phase = "play"
        sc = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        wm = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if wm:
            winner = wm.group(1).capitalize()
            new_r = {p: 0 for p in st.session_state.players}
            pot = sum(int(v) for _, v in sc)
            for p_n, p_v in sc:
                p_n = p_n.capitalize()
                if p_n in new_r: new_r[p_n] = -int(p_v)
            if winner in new_r:
                new_r[winner] = pot
                st.session_state.history.append(new_r)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                st.rerun()
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.current_picks[p] = min(3, st.session_state.current_picks.get(p, 0) + 1)
                st.rerun()
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; st.rerun()
    elif st.session_state.phase == "setup":
        names = [n.capitalize() for n in raw.replace(","," ").split() if not n.isdigit() and n != "and"]
        for n in names:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        st.rerun()

# 7. RENDER
if st.session_state.players:
    st.write(f"**Dealer:** {st.session_state.players[st.session_state.dealer_idx]}")
    img = draw_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(img, use_container_width=True)
else:
    st.info("Type player names to begin.")
