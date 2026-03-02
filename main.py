import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import re, json, zlib, base64
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

def pack_state():
    data = {
        "p": st.session_state.players, "h": st.session_state.history,
        "d": st.session_state.dealer, "pk": st.session_state.picks,
        "m": st.session_state.mode, "a": st.session_state.archive
    }
    json_str = json.dumps(data)
    compressed = zlib.compress(json_str.encode())
    b64_str = base64.urlsafe_b64encode(compressed).decode()
    st.query_params["save"] = b64_str
    return b64_str

def unpack_state(b64_str):
    try:
        compressed = base64.urlsafe_b64decode(b64_str.encode())
        json_str = zlib.decompress(compressed).decode()
        d = json.loads(json_str)
        st.session_state.update({
            "players": d['p'], "history": d['h'], "dealer": d['d'], 
            "picks": d['pk'], "mode": d['m'], "archive": d.get('a', [])
        })
        return True
    except: return False

if 'players' not in st.session_state:
    loaded = False
    if "save" in st.query_params: loaded = unpack_state(st.query_params["save"])
    if not loaded:
        st.session_state.update({
            "players": [], "history": [], "dealer": 0, 
            "picks": {}, "mode": "setup", "archive": []
        })

# --- 2. THE DRAWING ENGINE ---
def draw_notebook(history, players, dealer_idx, picks):
    num_p = len(players)
    width = max(1000, num_p * 250)
    height = max(800, 400 + (len(history) * 200))
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(80, height, 80):
        draw.line([(0, y), (width, y)], fill=(220, 230, 245), width=2)
    
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
        
        # LEADER STAR INDICATOR (*)
        max_score = max(totals.values()) if totals else 0
        for i, p in enumerate(players):
            x = (i + 0.5) * cx
            score_txt = str(totals[p])
            
            # If this player is the leader, add a distinct star and make it red
            if totals[p] == max_score and len(history) > 0: 
                score_txt += " *"
                draw.text((x, y), score_txt, fill=(230, 0, 0), font=font, anchor="mt")
            else:
                draw.text((x, y), score_txt, fill=(255, 130, 0), font=font, anchor="mt")
        y += 100
    return img

# --- 3. MAIN UI ---
st.title("🎙️ Score Scribe Pro")

# The Form (Bypasses iPhone Keyboard Bug)
with st.form("input_form", clear_on_submit=True):
    cmd = st.text_input("Enter Command (Names or Scores):")
    submitted = st.form_submit_button("Submit Command", use_container_width=True)

if submitted and cmd:
    raw = cmd.strip()
    
    if st.session_state.mode == "setup" and "winner" not in raw.lower():
        words = [w.strip(",").capitalize() for w in raw.split() if not w.isdigit() and w.lower() != "and"]
        for w in words:
            if w not in st.session_state.players:
                st.session_state.players.append(w); st.session_state.picks[w] = 0
        pack_state(); st.rerun()
        
    elif "winner" in raw.lower():
        st.session_state.mode = "play"
        nums = [int(n) for n in re.findall(r'\d+', raw)]
        win_match = re.search(r'winner\s+([a-zA-Z]+)', raw, re.IGNORECASE)
        
        winner_name = None
        if win_match:
            w_str = win_match.group(1).lower()
            for p in st.session_state.players:
                if w_str in p.lower() or p.lower() in w_str:
                    winner_name = p; break
                    
        if winner_name and nums:
            losers = []
            for word in raw.split():
                for p in st.session_state.players:
                    if p != winner_name and (p.lower() in word.lower() or word.lower() in p.lower()):
                        if p not in losers: losers.append(p)
                        
            new_r = {p: 0 for p in st.session_state.players}
            pot = 0
            for i, loser in enumerate(losers):
                if i < len(nums):
                    new_r[loser] = -nums[i]; pot += nums[i]
                    
            new_r[winner_name] = pot
            st.session_state.history.append(new_r)
            st.session_state.dealer = (st.session_state.dealer + 1) % len(st.session_state.players)
            st.session_state.picks = {p: 0 for p in st.session_state.players}
            pack_state(); st.rerun()
            
    elif "pick" in raw.lower():
        for p in st.session_state.players:
            if p.lower() in raw.lower():
                st.session_state.picks[p] = min(3, st.session_state.picks.get(p, 0) + 1)
                pack_state(); st.rerun()

# --- 4. RENDER THE GAME BOARD ---
if st.session_state.players:
    if st.session_state.mode == "setup":
        if st.button("🚀 LOCK NAMES & START", use_container_width=True):
            st.session_state.mode = "play"; pack_state(); st.rerun()
            
    if st.session_state.mode == "play":
        st.success(f"🎴 Current Dealer: {st.session_state.players[st.session_state.dealer]}")
        
        # Mobile-Friendly 2-Column Buttons
        colA, colB = st.columns(2)
        with colA:
            if st.button("↩️ Undo last round", use_container_width=True):
                if st.session_state.history:
                    st.session_state.history.pop()
                    st.session_state.dealer = (st.session_state.dealer - 1) % len(st.session_state.players)
                    pack_state(); st.rerun()
        with colB:
            # MOVED: End Game Button is now massive and unmissable
            if st.button("🏁 End Game & Archive", type="primary", use_container_width=True):
                totals = {p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}
                st.session_state.archive.append({
                    "date": datetime.now().strftime("%b %d, %I:%M %p"),
                    "totals": totals
                })
                st.session_state.update({"players": [], "history": [], "dealer": 0, "picks": {}, "mode": "setup"})
                pack_state(); st.rerun()
    
    # Draw Paper
    paper = draw_notebook(st.session_state.history, st.session_state.players, st.session_state.dealer, st.session_state.picks)
    st.image(paper, use_container_width=True)
    
    if st.session_state.history:
        st.write("### 📊 Live Totals")
        st.table([{p: sum(r.get(p,0) for r in st.session_state.history) for p in st.session_state.players}])

# --- 5. THE ARCHIVE SECTION (MOVED FROM SIDEBAR TO MAIN PAGE) ---
st.markdown("---")
st.header("📁 Game Archive")

if st.session_state.archive:
    sorted_archive = sorted(st.session_state.archive, key=lambda x: x['date'], reverse=True)
    
    for game in sorted_archive:
        with st.expander(f"🏆 {game['date']}"):
            sorted_scores = sorted(game['totals'].items(), key=lambda item: item[1], reverse=True)
            for rank, (p, score) in enumerate(sorted_scores, 1):
                star = "⭐" if rank == 1 else ""
                st.write(f"**{rank}. {p}**: {score} {star}")
                
    # Download Button
    archive_json = json.dumps(st.session_state.archive, indent=2)
    st.download_button(
        label="💾 Download Archive to iPhone",
        data=archive_json,
        file_name=f"ScoreArchive_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True
    )
else:
    st.info("Finished games will appear here after you tap 'End Game & Archive'.")

# Backup Loader
with st.expander("🛠️ Load Past Archive File"):
    uploaded_file = st.file_uploader("Upload a saved .json archive", type=["json"])
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            existing_dates = [g["date"] for g in st.session_state.archive]
            for game in loaded_data:
                if game["date"] not in existing_dates:
                    st.session_state.archive.append(game)
            st.success("Archive Loaded! Please refresh page.")
            pack_state()
        except: st.error("File error.")
