import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, io, datetime, json, time

# 1. CRITICAL SETUP
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 2. LIGHTWEIGHT PERSISTENCE
SAVE_FILE = "scribe_recovery.json"

def save_game():
    data = {
        "p": st.session_state.players,
        "h": st.session_state.history,
        "d": st.session_state.dealer_idx,
        "pk": st.session_state.current_picks,
        "ph": st.session_state.phase
    }
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.players = d.get("p", [])
                st.session_state.history = d.get("h", [])
                st.session_state.dealer_idx = d.get("d", 0)
                st.session_state.current_picks = d.get("pk", {})
                st.session_state.phase = d.get("ph", "setup")
            return True
        except: return False
    return False

# 3. INITIALIZE
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup"})

# 4. SIMPLE DRAWING ENGINE
def generate_sheet(history, players, dealer_idx, current_picks):
    w, h = max(1200, (len(players)+1)*200), max(2200, 1100+(len(history)*210))
    img = Image.new('RGB', (w, h), (255,255,255))
    draw = ImageDraw.Draw(img)
    for y in range(100, h, 80): draw.line([(0,y),(w,y)], (225,235,250), 2)
    
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 80)
    except: font = ImageFont.load_default()

    cx = w // (len(players)+2)
    draw.text((cx, 260), "Rd", (120,120,120), font, anchor="mt")
    for i, p in enumerate(players):
        x = (i+2)*cx
        name = p[:4].capitalize()
        if i == dealer_idx: name += " (D)"
        draw.text((x, 260), name, (40,40,100), font, anchor="mt")
        pk = current_picks.get(p, 0)
        if pk > 0: draw.text((x, 140), "|"*pk, (240,0,0), font, anchor="mt")

    y, totals = 380, {p:0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, y), str(r_idx), (160,160,160), font, anchor="mt")
        for i, p in enumerate(players):
            v = r_sc.get(p, 0); totals[p] += v
            draw.text(((i+2)*cx, y), (f"+{v}" if v>0 else str(v)), (50,50,50), font, anchor="mt")
        y += 100
        if r_idx > 1:
            draw.line([(60, y-10), (w-60, y-10)], (255,140,0), 4)
            y += 20
            for i, p in enumerate(players):
                draw.text(((i+2)*cx, y), str(totals[p]), (255,130,0), font, anchor="mt")
            y += 110
    return img

# 5. UI
st.title("🎙️ Score Scribe Pro")
cmd = st.text_input("Command:", key="in")

if st.button("🗑️ Reset Everything"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer_idx":0, "current_picks":{}, "phase":"setup"})
    st.rerun()

if cmd:
    raw = cmd.lower().strip()
    if "winner" in raw:
        st.session_state.phase = "play"
        sc = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw)
        wm = re.search(r'winner\s*([a-zA-Z]+)', raw)
        if wm:
            winner = wm.group(1).capitalize()
            new_r = {p: 0 for p in st.session_state.players}
            total_l = 0
            for p_n, p_v in sc:
                p_n = p_n.capitalize()
                if p_n in new_r: new_r[p_n] = -int(p_v); total_l += int(p_v)
            if winner in new_r:
                new_r[winner] = total_l
                st.session_state.history.append(new_r)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.current_picks = {p:0 for p in st.session_state.players}
                save_game(); st.rerun()
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw: st.session_state.dealer_idx = i; save_game(); st.rerun()
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                cur = st.session_state.current_picks.get(p, 0)
                if cur < 3: st.session_state.current_picks[p] = cur + 1; save_game(); st.rerun()
                break
    elif st.session_state.phase == "setup":
        nms = [w.capitalize() for w in raw.replace(","," ").split() if w not in ["and"] and not w.isdigit()]
        for n in nms:
            if n not in st.session_state.players: st.session_state.players.append(n); st.session_state.current_picks[n]=0
        save_game()

# 6. RENDER
if st.session_state.players:
    if st.session_state.phase == "play": st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
    sheet = generate_sheet(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.current_picks)
    st.image(sheet, use_container_width=True)
