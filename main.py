import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re

st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# 1. PURE SESSION STATE (No JSON files to cause silent crashes)
if 'players' not in st.session_state:
    st.session_state.update({
        'players': [], 'history': [], 'dealer': 0, 
        'picks': {}, 'phase': 'setup', 'msg': ''
    })

# 2. DRAWING ENGINE
def draw_paper():
    players = st.session_state.players
    history = st.session_state.history
    dealer = st.session_state.dealer
    picks = st.session_state.picks
    
    num_p = len(players)
    width = max(1000, num_p * 250)
    height = max(800, 400 + (len(history) * 200))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(80, height, 80):
        draw.line([(0, y), (width, y)], fill=(220, 230, 245), width=2)
        
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 70)
    except: font = ImageFont.load_default()
    
    cx = width / num_p
    
    for i, p in enumerate(players):
        x = (i + 0.5) * cx
        # Tallies
        tk = picks.get(p, 0)
        if tk > 0: draw.text((x, 60), "|" * tk, fill=(230, 0, 0), font=font, anchor="mt")
        
        # Full Names
        disp = p.capitalize()
        if i == dealer: disp += " (D)"
        draw.text((x, 140), disp, fill=(40, 40, 100), font=font, anchor="mt")

    curr_y = 260
    totals = {p: 0 for p in players}
    
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((40, curr_y), str(r_idx), fill=(160, 160, 160), font=font, anchor="mt")
        for i, p in enumerate(players):
            val = r_sc.get(p, 0)
            totals[p] += val
            draw.text(((i + 0.5) * cx, curr_y), str(val), fill=(50, 50, 50), font=font, anchor="mt")
        
        curr_y += 80
        draw.line([(20, curr_y), (width-20, curr_y)], fill=(255, 140, 0), width=3)
        curr_y += 10
        for i, p in enumerate(players):
            draw.text(((i + 0.5) * cx, curr_y), str(totals[p]), fill=(255, 130, 0), font=font, anchor="mt")
        curr_y += 100
        
    return img

# 3. UI
st.title("🎙️ Score Scribe Pro")

if st.button("🚨 HARD RESET"):
    st.session_state.clear()
    st.rerun()

# The Form bypasses the iPhone keyboard refresh glitch
with st.form("main_form", clear_on_submit=True):
    cmd = st.text_input("Enter Command (Names or Scores):")
    submitted = st.form_submit_button("Submit")

# 4. LOGIC
if submitted and cmd:
    raw = cmd.strip().lower()
    
    if st.session_state.phase == "setup" and "winner" not in raw:
        names = [w.capitalize() for w in raw.replace(",", " ").split() if not w.isdigit() and w != "and"]
        for n in names:
            if n not in st.session_state.players:
                st.session_state.players.append(n)
                st.session_state.picks[n] = 0
        st.rerun()
        
    elif "winner" in raw:
        st.session_state.phase = "play"
        nums = [int(n) for n in re.findall(r'\d+', raw)]
        
        winner = None
        for p in st.session_state.players:
            if f"winner {p.lower()}" in raw or f"{p.lower()} winner" in raw:
                winner = p
                break
        
        if not winner: 
            win_match = re.search(r'winner\s+([a-z]+)', raw)
            if win_match:
                w_str = win_match.group(1).capitalize()
                if w_str in st.session_state.players: winner = w_str
        
        if winner and nums:
            new_r = {p: 0 for p in st.session_state.players}
            pot = 0
            others = [p for p in st.session_state.players if p != winner]
            
            for i, other in enumerate(others):
                if i < len(nums):
                    new_r[other] = -nums[i]
                    pot += nums[i]
            
            new_r[winner] = pot
            st.session_state.history.append(new_r)
            st.session_state.dealer = (st.session_state.dealer + 1) % len(st.session_state.players)
            st.session_state.picks = {p: 0 for p in st.session_state.players}
            st.rerun()
            
    elif "pick" in raw:
        for p in st.session_state.players:
            if p.lower() in raw:
                st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1)
                st.rerun()
                
    elif "dealer" in raw:
        for i, p in enumerate(st.session_state.players):
            if p.lower() in raw:
                st.session_state.dealer = i
                st.rerun()

# 5. RENDER
if st.session_state.players:
    if st.session_state.phase == "setup":
        if st.button("🚀 START GAME"):
            st.session_state.phase = "play"
            st.rerun()
            
    if st.session_state.phase == "play":
        col1, col2 = st.columns(2)
        with col1: st.success(f"🎴 Dealer: {st.session_state.players[st.session_state.dealer]}")
        with col2: 
            if st.button("↩️ Undo Round") and st.session_state.history:
                st.session_state.history.pop()
                st.session_state.dealer = (st.session_state.dealer - 1) % len(st.session_state.players)
                st.rerun()
                
    st.image(draw_paper(), use_container_width=True)
    
    if st.session_state.history:
        st.write("### 📊 Backup Data Table")
        st.table([{p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}])
