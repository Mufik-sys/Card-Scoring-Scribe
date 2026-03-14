import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, json, zlib, base64
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(page_title="Game Hub Pro", layout="wide")

def pack_state():
    data = {
        "ag": st.session_state.active_game,
        "p": st.session_state.players, "h": st.session_state.history,
        "d": st.session_state.dealer, "pk": st.session_state.picks,
        "m": st.session_state.mode, "a": st.session_state.archive,
        "jp": st.session_state.j_players, "jh": st.session_state.j_history,
        "jd": st.session_state.j_dealer, "jb": st.session_state.j_bids,
        "jm": st.session_state.j_mode
    }
    json_str = json.dumps(data)
    compressed = zlib.compress(json_str.encode())
    b64_str = base64.urlsafe_b64encode(compressed).decode()
    st.query_params["save"] = b64_str
    return b64_str

def unpack_state(b64_str):
    try:
        b64_str = b64_str.strip()
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        compressed = base64.urlsafe_b64decode(b64_str.encode())
        json_str = zlib.decompress(compressed).decode()
        d = json.loads(json_str)
        st.session_state.update({
            "active_game": d.get('ag'),
            "players": d.get('p', []), "history": d.get('h', []), "dealer": d.get('d', 0), 
            "picks": d.get('pk', {}), "mode": d.get('m', 'setup'), "archive": d.get('a', []),
            "j_players": d.get('jp', []), "j_history": d.get('jh', []), "j_dealer": d.get('jd', 0),
            "j_bids": d.get('jb', {}), "j_mode": d.get('jm', 'setup')
        })
        return True
    except: return False

if 'active_game' not in st.session_state:
    loaded = False
    if "save" in st.query_params: loaded = unpack_state(st.query_params["save"])
    if not loaded:
        st.session_state.update({
            "active_game": None, "players": [], "history": [], "dealer": 0, 
            "picks": {}, "mode": "setup", "archive": [],
            "j_players": [], "j_history": [], "j_dealer": 0, "j_bids": {}, "j_mode": "setup"
        })

# --- 2. DRAWING ENGINES ---

# Engine A: Grand Fan (Standard Layout)
def draw_notebook(history, players, dealer_idx, picks):
    num_p = len(players)
    width = max(1000, num_p * 250)
    height = max(800, 400 + (len(history) * 200))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(80, height, 80): draw.line([(0, y), (width, y)], fill=(220, 230, 245), width=2)
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: font = ImageFont.load_default()
    cx = width / num_p
    for i, p in enumerate(players):
        x = (i + 0.5) * cx
        tk = picks.get(p, 0)
        if tk > 0: draw.text((x, 60), "|" * tk, fill=(230, 0, 0), font=font, anchor="mt")
        disp = p.capitalize()
        if i == dealer_idx: disp += " (D)"
        draw.text((x, 150), disp, fill=(40, 40, 100), font=font, anchor="mt")
    y = 280
    totals = {p: 0 for p in players}
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((40, y), str(r_idx), fill=(160, 160, 160), font=font, anchor="mt")
        for i, p in enumerate(players):
            x = (i + 0.5) * cx
            val = r_sc.get(p, 0); totals[p] += val
            draw.text((x, y), str(val), fill=(50, 50, 50), font=font, anchor="mt")
        y += 80
        draw.line([(20, y), (width-20, y)], fill=(255, 140, 0), width=3)
        y += 10
        max_score = max(totals.values()) if totals else -9999
        for i, p in enumerate(players):
            x = (i + 0.5) * cx
            score_txt = str(totals[p])
            if totals[p] == max_score and len(history) > 0: 
                score_txt += " *"
                draw.text((x, y), score_txt, fill=(230, 0, 0), font=font, anchor="mt")
            else:
                draw.text((x, y), score_txt, fill=(255, 130, 0), font=font, anchor="mt")
        y += 100
    return img

# Engine B: Judgement (Grid Layout with 'Rd' Column)
def draw_judgement_notebook(history, players, dealer_idx, current_bids, mode):
    num_p = len(players)
    width = max(1000, (num_p + 1) * 230) # +1 space for 'Rd' column
    height = max(800, 400 + (len(history) * 200) + (150 if mode in ['bid', 'actual'] else 0))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(80, height, 80): draw.line([(0, y), (width, y)], fill=(220, 230, 245), width=2)
    try: font = ImageFont.truetype("Caveat-Regular.ttf", 75)
    except: font = ImageFont.load_default()
    cx = width / (num_p + 1)
    
    # Headers
    draw.text((cx * 0.5, 150), "Rd", fill=(100, 100, 100), font=font, anchor="mt")
    for i, p in enumerate(players):
        disp = p.capitalize()
        if i == dealer_idx: disp += " (D)"
        draw.text((cx * (i + 1.5), 150), disp, fill=(40, 40, 100), font=font, anchor="mt")

    y = 280
    totals = {p: 0 for p in players}
    # History
    for r_idx, r_sc in enumerate(history, 1):
        draw.text((cx * 0.5, y), str(r_idx), fill=(160, 160, 160), font=font, anchor="mt")
        for i, p in enumerate(players):
            val = r_sc.get(p, 0); totals[p] += val
            draw.text((cx * (i + 1.5), y), str(val), fill=(50, 50, 50), font=font, anchor="mt")
        y += 80
        draw.line([(20, y), (width-20, y)], fill=(255, 140, 0), width=3)
        y += 10
        max_score = max(totals.values()) if totals else -9999
        for i, p in enumerate(players):
            score_txt = str(totals[p])
            if totals[p] == max_score and len(history) > 0: 
                score_txt += " *"
                draw.text((cx * (i + 1.5), y), score_txt, fill=(230, 0, 0), font=font, anchor="mt")
            else:
                draw.text((cx * (i + 1.5), y), score_txt, fill=(255, 130, 0), font=font, anchor="mt")
        y += 100

    # Live Bidding Row
    if mode in ["bid", "actual"]:
        label = "Bids" if mode == "bid" else "Bids (Locked)"
        color = (150, 150, 150) if mode == "bid" else (220, 100, 100)
        draw.text((cx * 0.5, y), label, fill=color, font=font, anchor="mt")
        for i, p in enumerate(players):
            bid_val = current_bids.get(p, 0)
            draw.text((cx * (i + 1.5), y), str(bid_val), fill=color, font=font, anchor="mt")
    return img

# ==========================================
# --- 3. PAGE ROUTING & TOP UI ---
# ==========================================

if st.session_state.active_game is None:
    st.markdown("<h1 style='font-size: 26px; padding-top: 0;'>🎲 Select Game (v18)</h1>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎴 Grand Fan Pro", use_container_width=True, type="primary"):
            st.session_state.active_game = "Grand Fan"; pack_state(); st.rerun()
    with col2:
        if st.button("⚖️ Judgement", use_container_width=True, type="primary"):
            st.session_state.active_game = "Judgement"; pack_state(); st.rerun()

elif st.session_state.active_game == "Grand Fan":
    st.markdown("<h1 style='font-size: 26px; padding-top: 0;'>🎴 Grand Fan Pro</h1>", unsafe_allow_html=True)
    col_back, col_reset = st.columns(2)
    with col_back:
        if st.button("⬅️ Back to Menu", use_container_width=True):
            st.session_state.active_game = None; pack_state(); st.rerun()
    with col_reset:
        if st.button("🚨 Wipe Board", use_container_width=True):
            st.session_state.update({"players": [], "history": [], "dealer": 0, "picks": {}, "mode": "setup"}); pack_state(); st.rerun()

    with st.form("input_form", clear_on_submit=True):
        cmd = st.text_input("Enter Command (Names or Scores):")
        submitted = st.form_submit_button("Submit Command", use_container_width=True)

    if submitted and cmd:
        raw = cmd.strip()
        if st.session_state.mode == "setup" and "winner" not in raw.lower():
            words = [w.strip(",").capitalize() for w in raw.split() if not w.isdigit() and w.lower() != "and"]
            for w in words:
                if w not in st.session_state.players: st.session_state.players.append(w); st.session_state.picks[w] = 0
            pack_state(); st.rerun()
        elif "winner" in raw.lower():
            st.session_state.mode = "play"
            nums = [int(n) for n in re.findall(r'\d+', raw)]
            win_match = re.search(r'winner\s+([a-zA-Z]+)', raw, re.IGNORECASE)
            winner_name = None
            if win_match:
                w_str = win_match.group(1).lower()
                for p in st.session_state.players:
                    if w_str in p.lower() or p.lower() in w_str: winner_name = p; break
            if winner_name and nums:
                losers = []
                for word in raw.split():
                    for p in st.session_state.players:
                        if p != winner_name and (p.lower() in word.lower() or word.lower() in p.lower()):
                            if p not in losers: losers.append(p)
                new_r = {p: 0 for p in st.session_state.players}
                pot = 0
                for i, loser in enumerate(losers):
                    if i < len(nums): new_r[loser] = -nums[i]; pot += nums[i]
                new_r[winner_name] = pot
                st.session_state.history.append(new_r)
                st.session_state.dealer = (st.session_state.dealer + 1) % len(st.session_state.players)
                st.session_state.picks = {p: 0 for p in st.session_state.players}
                pack_state(); st.rerun()
        elif "pick" in raw.lower():
            for p in st.session_state.players:
                if p.lower() in raw.lower(): st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1); pack_state(); st.rerun()

    if st.session_state.players:
        if st.session_state.mode == "setup":
            if st.button("🚀 LOCK NAMES & START", use_container_width=True): st.session_state.mode = "play"; pack_state(); st.rerun()
        if st.session_state.mode == "play":
            st.success(f"🎴 Current Dealer: {st.session_state.players[st.session_state.dealer]}")
            colA, colB = st.columns(2)
            with colA:
                if st.button("↩️ Undo last round", use_container_width=True):
                    if st.session_state.history:
                        st.session_state.history.pop()
                        st.session_state.dealer = (st.session_state.dealer - 1) % len(st.session_state.players)
                        pack_state(); st.rerun()
            with colB:
                if st.button("🏁 End Game & Archive", type="primary", use_container_width=True):
                    totals = {p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}
                    st.session_state.archive.append({"game_type": "Grand Fan", "date": datetime.now().strftime("%b %d, %I:%M %p"), "totals": totals})
                    st.session_state.update({"players": [], "history": [], "dealer": 0, "picks": {}, "mode": "setup"})
                    pack_state(); st.rerun()
        
        paper = draw_notebook(st.session_state.history, st.session_state.players, st.session_state.dealer, st.session_state.picks)
        st.image(paper, use_container_width=True)

elif st.session_state.active_game == "Judgement":
    st.markdown("<h1 style='font-size: 26px; padding-top: 0;'>⚖️ Judgement</h1>", unsafe_allow_html=True)
    col_back, col_reset = st.columns(2)
    with col_back:
        if st.button("⬅️ Back to Menu", use_container_width=True): st.session_state.active_game = None; pack_state(); st.rerun()
    with col_reset:
        if st.button("🚨 Wipe Board", use_container_width=True):
            st.session_state.update({"j_players": [], "j_history": [], "j_dealer": 0, "j_bids": {}, "j_mode": "setup"})
            pack_state(); st.rerun()

    bids = {} # Keep track of live bids
    
    # PHASE 1: SETUP
    if st.session_state.j_mode == "setup":
        with st.form("j_input_form", clear_on_submit=True):
            cmd = st.text_input("Enter Player Names (space separated):")
            if st.form_submit_button("Submit Names", use_container_width=True) and cmd:
                words = [w.strip(",").capitalize() for w in cmd.split() if not w.isdigit() and w.lower() != "and"]
                for w in words:
                    if w not in st.session_state.j_players: st.session_state.j_players.append(w)
                pack_state(); st.rerun()
        if st.session_state.j_players:
            if st.button("🚀 LOCK NAMES & START", use_container_width=True, type="primary"):
                st.session_state.j_mode = "bid"; pack_state(); st.rerun()

    # PHASE 2: BIDDING
    elif st.session_state.j_mode == "bid":
        st.success(f"🎴 Current Dealer: {st.session_state.j_players[st.session_state.j_dealer]}")
        st.write("### 🔮 Bidding Phase")
        for p in st.session_state.j_players:
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"**{p}**")
            bids[p] = c2.number_input(f"bid_{p}", min_value=0, step=1, label_visibility="collapsed")
            
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        c1.markdown("### TOTAL BIDS:")
        c2.markdown(f"### {sum(bids.values())}") 
        
        if st.button("🔒 Lock Bids & Play Hand", use_container_width=True, type="primary"):
            st.session_state.j_bids = bids
            st.session_state.j_mode = "actual"
            pack_state(); st.rerun()

    # PHASE 3: ACTUALS
    elif st.session_state.j_mode == "actual":
        st.warning("### 🎯 Enter Actual Hands Won")
        actuals = {}
        for p in st.session_state.j_players:
            c1, c2 = st.columns([2, 1])
            bid_val = st.session_state.j_bids.get(p, 0)
            c1.markdown(f"**{p}** *(Bid: {bid_val})*")
            actuals[p] = c2.number_input(f"act_{p}", min_value=0, step=1, label_visibility="collapsed")
            
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        c1.markdown("### TOTAL HANDS:")
        c2.markdown(f"### {sum(actuals.values())}") 
        
        if st.button("🧮 Calculate & Save Round", use_container_width=True, type="primary"):
            new_r = {}
            for p in st.session_state.j_players:
                bid = st.session_state.j_bids.get(p, 0)
                act = actuals[p]
                if bid == act: new_r[p] = 10 if bid == 0 else bid * 10
                else: new_r[p] = -10 if bid == 0 else bid * -10
            st.session_state.j_history.append(new_r)
            st.session_state.j_dealer = (st.session_state.j_dealer + 1) % len(st.session_state.j_players)
            st.session_state.j_mode = "bid"
            pack_state(); st.rerun()

    # RENDER JUDGEMENT BOARD
    if st.session_state.j_players and st.session_state.j_mode != "setup":
        colA, colB = st.columns(2)
        with colA:
            if st.button("↩️ Undo last round", use_container_width=True):
                if st.session_state.j_mode == "actual": st.session_state.j_mode = "bid"
                elif st.session_state.j_history:
                    st.session_state.j_history.pop()
                    st.session_state.j_dealer = (st.session_state.j_dealer - 1) % len(st.session_state.j_players)
                    st.session_state.j_mode = "bid"
                pack_state(); st.rerun()
        with colB:
            if st.button("🏁 End Game & Archive", type="primary", use_container_width=True):
                totals = {p: sum(r.get(p,0) for r in st.session_state.j_history) for p in st.session_state.j_players}
                st.session_state.archive.append({"game_type": "Judgement", "date": datetime.now().strftime("%b %d, %I:%M %p"), "totals": totals})
                st.session_state.update({"j_players": [], "j_history": [], "j_dealer": 0, "j_bids": {}, "j_mode": "setup"})
                pack_state(); st.rerun()
                
        # Determine which bids to show on paper
        current_drawing_bids = bids if st.session_state.j_mode == "bid" else st.session_state.j_bids
        paper = draw_judgement_notebook(st.session_state.j_history, st.session_state.j_players, st.session_state.j_dealer, current_drawing_bids, st.session_state.j_mode)
        st.image(paper, use_container_width=True)


# ==========================================
# --- 4. GLOBAL ARCHIVE & BACKUP ---
# ==========================================

st.markdown("---")
st.header("📁 Global Game Archive")

if st.session_state.archive:
    sorted_archive = sorted(st.session_state.archive, key=lambda x: x.get('date', ''), reverse=True)
    for game in sorted_archive:
        game_type = game.get('game_type', 'Grand Fan')
        with st.expander(f"🏆 {game_type} - {game.get('date', '')}"):
            sorted_scores = sorted(game['totals'].items(), key=lambda item: item[1], reverse=True)
            for rank, (p, score) in enumerate(sorted_scores, 1):
                star = "⭐" if rank == 1 else ""
                st.write(f"**{rank}. {p}**: {score} {star}")
                
    archive_json = json.dumps(st.session_state.archive, indent=2)
    st.download_button(
        label="💾 Download Archive to iPhone",
        data=archive_json,
        file_name=f"ScoreArchive_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True
    )
else:
    st.info("Finished games will appear here.")

with st.expander("⚠️ SERVER SLEEP PROTECTION & ARCHIVE LOADER"):
    st.warning("Save your game if taking a break.")
    save_code_str = pack_state()
    st.text_area("👇 Tap inside here, press 'Select All', then 'Copy':", value=save_code_str, height=120)
    with st.form("restore_form", clear_on_submit=True):
        restore_code = st.text_input("Paste an active game code here:")
        if st.form_submit_button("Restore Active Game", use_container_width=True):
            if unpack_state(restore_code.strip()): st.rerun()
            else: st.error("Invalid Code! Make sure you copied the whole block of text.")
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload a saved .json Archive File", type=["json"])
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.getvalue().decode("utf-8")
            loaded_data = json.loads(file_content)
            existing_dates = [g.get("date") for g in st.session_state.archive]
            added_new = False
            for game in loaded_data:
                if game.get("date") not in existing_dates: 
                    st.session_state.archive.append(game)
                    added_new = True
            if added_new:
                pack_state(); st.rerun()
        except Exception as e: st.error("There was an issue reading this file.")
