import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, json, time

# --- 1. ROBUST SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- 2. THE VAULT (Simplified Storage) ---
SAVE_FILE = "final_scribe_v5.json"

def save_game():
    try:
        data = {
            "p": st.session_state.players, "h": st.session_state.history,
            "d": st.session_state.dealer, "pk": st.session_state.picks,
            "mode": st.session_state.mode
        }
        with open(SAVE_FILE, "w") as f: json.dump(data, f)
    except: pass

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.update({"players": d['p'], "history": d['h'], "dealer": d['d'], "picks": d['pk'], "mode": d['mode']})
            return True
        except: return False
    return False

# --- 3. INITIALIZE ALL KEYS (Prevents AttributeError) ---
if 'players' not in st.session_state:
    if not load_game():
        st.session_state.update({
            "players": [], "history": [], "dealer": 0,
            "picks": {}, "mode": "setup", "msg": ""
        })

# --- 4. THE NOTEBOOK ENGINE ---
def draw_notebook(history, players, dealer_idx, picks):
    num_p = len(players)
    width = max(1000, (num_p + 1) * 200)
    # Extra height to prevent "Broken Stream" errors
    height = 800 + (len(history) * 280)
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Notebook lines
    for line_y in range(100, height, 80): 
        draw.line([(0, line_y), (width, line_y)], (225, 230, 245), 2)
    
    try: f = ImageFont.truetype("Caveat-Regular.ttf", 85)
    except: f = ImageFont.load_default()

    cx = width // (num_p + 2)
    draw.text((cx, 250), "Rd", (140, 140, 140), f, anchor="mt")
    
    for i, p in enumerate(players):
        x = (i + 2) * cx
        # Tally Marks (Max 3)
        tk = picks.get(p, 0)
        if tk > 0: draw.text((x, 140), "|" * tk, (230, 0, 0), f, anchor="mt")
        # Header: Name + (D)
        disp = p[:4].capitalize()
        if i == dealer_idx: disp += " (D)"
        draw.text((x, 250), disp, (40, 40, 100), f, anchor="mt")

    # DRAW ROWS
    curr_y, totals = 380, {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx, curr_y), str(r_idx), (160, 160, 160), f, anchor="mt")
        for i, p in enumerate(players):
            val = r_sc.get(p, 0); totals[p] += val
            draw.text(((i+2)*cx, curr_y), str(val), (50, 50, 50), f, anchor="mt")
        # Totals Line
        curr_y += 100
        draw.line([(50, curr_y), (width-50, curr_y)], (255, 140, 0), 4)
        curr_y += 20
        for i, p in enumerate(players):
            draw.text(((i+2)*cx, curr_y), str(totals[p]), (255, 130, 0), f, anchor="mt")
        curr_y += 130 # Move to next round
    return img

# --- 5. UI ---
st.title("🎙️ Score Scribe Pro")

if st.button("🚨 EMERGENCY RESET"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer":0, "picks":{}, "mode":"setup", "msg":""})
    st.rerun()

cmd = st.text_input("Command (Names or Scores):", key="main_input")

if cmd:
    raw = cmd.lower().strip()
    
    # SETUP
    if st.session_state.mode == "setup" and "winner" not in raw:
        nms = [n.capitalize() for n in raw.replace(","," ").split() if not n.isdigit() and n != "and"]
        for n in nms:
            if n not in st.session_state.players:
                st.session_state.players.append(n); st.session_state.picks[n] = 0
        save_game()

    # SCORING (STRICT WINNER LOGIC)
    if "winner" in raw:
        st.session_state.mode = "play"
        nums = [int(n) for n in re.findall(r'\d+', raw)]
        # Find winner name: looks specifically for word AFTER "winner"
        match = re.search(r'winner\s+([a-zA-Z]+)', raw)
        
        if match and nums:
            winner_p = match.group(1).capitalize()
            if winner_p in st.session_state.players:
                new_row, pot = {p: 0 for p in st.session_state.players}, 0
                others = [p for p in st.session_state.players if p != winner_p]
                
                # Pair numbers to losers
                for i, p_oth in enumerate(others):
                    if i < len(nums):
                        val = nums[i]; new_row[p_oth] = -val; pot += val
                
                new_row[winner_p] = pot
                st.session_state.history.append(new_row)
                st.session_state.dealer = (st.session_state.dealer + 1) % len(st.session_state.players)
                st.session_state.picks = {p: 0 for p in st.session_state.players}
                st.session_state.msg = f"Saved: {winner_p} won {pot}"
                save_game(); st.rerun()

    # TALLY
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1)
                save_game(); st.rerun()

# --- 6. RENDER ---
if st.session_state.players:
    if st.session_state.mode == "setup":
        if st.button("🚀 LOCK NAMES & START"):
            st.session_state.mode = "play"; save_game(); st.rerun()
    
    if st.session_state.mode == "play":
        st.success(f"🎴 Current Dealer: {st.session_state.players[st.session_state.dealer]}")
    
    # VIEW 1: THE NOTEBOOK (The primary view)
    paper = draw_notebook(st.session_state.history, st.session_state.players, st.session_state.dealer, st.session_state.picks)
    st.image(paper, use_container_width=True)
    
    # VIEW 2: THE DIGITAL BACKUP (Always works even if image breaks)
    if st.session_state.history:
        st.write("### 📊 Live Totals (Backup)")
        sum_totals = {p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}
        st.table([sum_totals])

    if st.session_state.msg: st.info(st.session_state.msg)
else:
    st.info("Step 1: Type player names and hit enter.")
