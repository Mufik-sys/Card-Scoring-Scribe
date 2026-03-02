import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, os, json, time

# 1. PAGE CONFIG
st.set_page_config(page_title="Score Scribe", layout="wide")

# 2. SIMPLEST STORAGE POSSIBLE
SAVE_FILE = "game_state.json"

def save_it():
    data = {
        "p": st.session_state.players, "h": st.session_state.history,
        "d": st.session_state.dealer_idx, "pk": st.session_state.picks,
        "mode": st.session_state.mode
    }
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

def load_it():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                d = json.load(f)
                st.session_state.players = d['p']
                st.session_state.history = d['h']
                st.session_state.dealer_idx = d['d']
                st.session_state.picks = d['pk']
                st.session_state.mode = d['mode']
            return True
        except: return False
    return False

# 3. INITIALIZE
if 'players' not in st.session_state:
    if not load_it():
        st.session_state.update({"players":[], "history":[], "dealer_idx":0, "picks":{}, "mode":"setup", "msg":""})

# 4. THE DRAWING ENGINE (Simplified to avoid crashes)
def draw_paper(history, players, dealer_idx, picks):
    num_p = len(players)
    width = max(1000, (num_p + 1) * 200)
    height = 800 + (len(history) * 250) # Extra tall for scores
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Notebook lines
    for line_y in range(100, height, 80): 
        draw.line([(0, line_y), (width, line_y)], (225, 235, 250), 2)
    
    try: f = ImageFont.truetype("Caveat-Regular.ttf", 80)
    except: f = ImageFont.load_default()

    cx = width // (num_p + 2)
    draw.text((cx, 250), "Rd", (130, 130, 130), f, anchor="mt")
    
    # Header Names
    for i, p in enumerate(players):
        x = (i + 2) * cx
        # Tally Marks
        tk = picks.get(p, 0)
        if tk > 0: draw.text((x, 140), "|" * tk, (230, 0, 0), f, anchor="mt")
        # Name + (D)
        txt = p[:4].capitalize()
        if i == dealer_idx: txt += " (D)"
        draw.text((x, 250), txt, (40, 40, 100), f, anchor="mt")

    # DRAW EVERY ROUND
    curr_y = 380
    running_totals = {p: 0 for p in players}
    
    for r_idx, r_score in enumerate(history, 1):
        # Draw Round Number
        draw.text((cx, curr_y), str(r_idx), (150, 150, 150), f, anchor="mt")
        
        # Draw Scores
        for i, p in enumerate(players):
            v = r_score.get(p, 0)
            running_totals[p] += v
            draw.text(((i+2)*cx, curr_y), str(v), (50, 50, 50), f, anchor="mt")
        
        # Draw Running Total (Orange Line)
        curr_y += 100
        draw.line([(50, curr_y), (width-50, curr_y)], (255, 140, 0), 3)
        curr_y += 15
        for i, p in enumerate(players):
            draw.text(((i+2)*cx, curr_y), str(running_totals[p]), (255, 130, 0), f, anchor="mt")
        
        curr_y += 120 # Move down for next round
        
    return img

# 5. UI & COMMANDS
st.title("🎙️ Score Scribe Pro")

if st.button("🚨 Reset System"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.update({"players":[], "history":[], "dealer_idx":0, "picks":{}, "mode":"setup", "msg":""})
    st.rerun()

cmd = st.text_input("Command:", key="cmd_in")

if cmd:
    raw = cmd.lower().strip()
    
    # Mode 1: Setup Names
    if st.session_state.mode == "setup" and "winner" not in raw:
        names = [n.capitalize() for n in raw.replace(","," ").split() if not n.isdigit() and n != "and"]
        for n in names:
            if n not in st.session_state.players:
                st.session_state.players.append(n)
                st.session_state.picks[n] = 0
        save_it()

    # Mode 2: Scoring (Strict Logic)
    if "winner" in raw:
        st.session_state.mode = "play"
        nums = [int(n) for n in re.findall(r'\d+', raw)]
        # WINNER NAME: Must come immediately after the word 'winner'
        win_search = re.search(r'winner\s+([a-zA-Z]+)', raw)
        
        if win_search and nums:
            winner = win_search.group(1).capitalize()
            if winner in st.session_state.players:
                new_round = {p: 0 for p in st.session_state.players}
                pot = 0
                others = [p for p in st.session_state.players if p != winner]
                
                # Pair the scores to the other players
                for i, other_player in enumerate(others):
                    if i < len(nums):
                        val = nums[i]
                        new_round[other_player] = -val
                        pot += val
                
                new_round[winner] = pot
                st.session_state.history.append(new_round)
                st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                st.session_state.picks = {p: 0 for p in st.session_state.players} # Clear picks
                st.session_state.msg = f"Saved! {winner} won {pot}"
                save_it(); st.rerun()

    # Mode 3: Picks
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1)
                save_it(); st.rerun()

# 6. SHOW THE PAPER
if st.session_state.players:
    if st.session_state.mode == "setup":
        if st.button("🚀 Start Game"):
            st.session_state.mode = "play"; save_it(); st.rerun()
    
    if st.session_state.mode == "play":
        st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer_idx]}")
        if st.button("↩️ Undo last"):
            if st.session_state.history:
                st.session_state.history.pop()
                st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
                save_it(); st.rerun()
    
    # This draws the image every time names exist
    paper = draw_paper(st.session_state.history, st.session_state.players, st.session_state.dealer_idx, st.session_state.picks)
    st.image(paper, use_container_width=True)
    
    if st.session_state.msg: st.info(st.session_state.msg)
else:
    st.info("Enter names (e.g., Mufi Mazher Arwa) to begin.")
