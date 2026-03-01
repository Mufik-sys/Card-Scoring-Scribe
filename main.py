import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import re, os, io, datetime, json, time

# --- PAGE SETUP ---
st.set_page_config(page_title="Score Scribe Pro", layout="wide")

# --- PERSISTENCE (Lightweight - No Photos in JSON) ---
SAVE_FILE = "active_game_checkpoint.json"

def save_checkpoint():
    try:
        data = {
            "players": st.session_state.players,
            "history": st.session_state.history,
            "redo_stack": st.session_state.redo_stack,
            "phase": st.session_state.phase,
            "dealer_idx": st.session_state.dealer_idx,
            "picks": st.session_state.current_picks
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def load_checkpoint():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                st.session_state.players = data.get("players", [])
                st.session_state.history = data.get("history", [])
                st.session_state.redo_stack = data.get("redo_stack", [])
                st.session_state.phase = data.get("phase", "setup")
                st.session_state.dealer_idx = data.get("dealer_idx", 0)
                st.session_state.current_picks = data.get("picks", {})
            return True
        except: return False
    return False

# --- INITIALIZE STATE ---
if 'players' not in st.session_state:
    if not load_checkpoint():
        st.session_state.players, st.session_state.history, st.session_state.redo_stack = [], [], []
        st.session_state.phase, st.session_state.dealer_idx = "setup", 0
        st.session_state.current_picks = {}
if 'game_log' not in st.session_state: st.session_state.game_log = []
if 'profiles' not in st.session_state: st.session_state.profiles = {}
if 'last_msg' not in st.session_state: st.session_state.last_msg = ""
if 'msg_time' not in st.session_state: st.session_state.msg_time = 0

def set_status(msg):
    st.session_state.last_msg = msg
    st.session_state.msg_time = time.time()

# --- IMAGE GENERATOR ---
def generate_sheet(history, players, is_finished, dealer_idx, current_picks, status=""):
    num_rounds, num_players = len(history), len(players)
    width = max(1200, (num_players + 1) * 200) 
    calculated_height = max(2200, 1100 + (num_rounds * 210))
    img = Image.new('RGB', (width, calculated_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Paper Lines
    for y in range(100, calculated_height, 80):
        draw.line([(0, y), (width, y)], fill=(225, 235, 250), width=2)

    font_path = "Caveat-Regular.ttf"
    if os.path.exists(font_path):
        f_scale = max(55, 95 - (num_players * 4))
        header_font = ImageFont.truetype(font_path, f_scale)
        score_font = ImageFont.truetype(font_path, f_scale - 5)
        tally_font = ImageFont.truetype(font_path, f_scale + 30)
    else: header_font = score_font = tally_font = ImageFont.load_default()

    col_width = width // (num_players + 2)
    current_y = 260 
    
    draw.text((col_width, current_y), "Rd", fill=(120, 120, 120), font=header_font, anchor="mt")
    for i, name in enumerate(players):
        x = (i + 2) * col_width
        
        # 1. Tallies (Picks)
        count = current_picks.get(name, 0)
        if count > 0 and not is_finished:
            draw.text((x, current_y - 120), "|" * count, fill=(240, 0, 0), font=tally_font, anchor="mt")
        
        # 2. Names & Dealer Underline (Thick Red)
        display_name = name[:4].capitalize()
        draw.text((x, current_y), display_name, fill=(40, 40, 100), font=header_font, anchor="mt")
        if i == dealer_idx and not is_finished:
            bbox = draw.textbbox((x, current_y), display_name, font=header_font, anchor="mt")
            draw.line([(bbox[0]-10, bbox[3]+10), (bbox[2]+10, bbox[3]+10)], fill=(255, 0, 0), width=12)
            draw.line([(bbox[0]-10, bbox[3]+24), (bbox[2]+10, bbox[3]+24)], fill=(255, 0, 0), width=12)
    
    current_y += 110
    totals = {p: 0 for p in players}
    for round_idx, round_scores in enumerate(history, 1):
        draw.text((col_width, current_y), str(round_idx), fill=(160, 160, 160), font=score_font, anchor="mt")
        for i, p in enumerate(players):
            val = round_scores.get(p, 0); totals[p] += val
            x, txt = (i + 2) * col_width, (f"+{val}" if val > 0 else str(val))
            draw.text((x, current_y), txt, fill=(50, 50, 50), font=score_font, anchor="mt")
        current_y += 100 
        
        # Orange Subtotals
        if round_idx > 1 and not is_finished:
            max_s = max(totals.values()) if totals else 0
            draw.line([(60, current_y-10), (width-60, current_y-10)], fill=(255, 140, 0), width=4) 
            current_y += 20
            for i, p in enumerate(players):
                x, s_txt = (i + 2) * col_width, str(totals[p])
                if totals[p] == max_s and max_s != 0: s_txt += "*"
                draw.text((x, current_y), s_txt, fill=(255, 130, 0), font=score_font, anchor="mt")
            current_y += 110 

    if is_finished:
        max_t = max(totals.values()) if totals else 0
        current_y += 40
        draw.line([(60, current_y), (width-60, current_y)], fill=(0, 0, 0), width=6)
        draw.line([(60, current_y+15), (width-60, current_y+15)], fill=(0, 0, 0), width=6)
        current_y += 40
        label = "End" if status != "Terminated" else "TG"
        draw.text((col_width, current_y), label, fill=(220, 0, 0), font=header_font, anchor="mt")
        for i, p in enumerate(players):
            x, f_txt = (i + 2) * col_width, str(totals[p])
            if totals[p] == max_t and max_t != 0: f_txt += "*" 
            draw.text((x, current_y), f_txt, fill=(220, 0, 0), font=header_font, anchor="mt")
    return img

# --- SIDEBAR ---
st.sidebar.title("Score Scribe")
nav = st.sidebar.radio("Navigation", ["Active Game", "History Log"])

with st.sidebar.expander("👤 Profile Photos (Log Only)"):
    if st.session_state.players:
        p_sel = st.selectbox("Player:", st.session_state.players)
        img_f = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'], key=f"up_{p_sel}")
        if img_f: st.session_state.profiles[p_sel] = img_f.read(); st.success("Saved!")
    else: st.info("Add players first.")

# --- MAIN SCREEN LOGIC ---
if nav == "Active Game":
    # 1. STATUS BAR (Flashes 4 seconds)
    if time.time() - st.session_state.msg_time < 4:
        st.info(f"⚡ **Last Action:** {st.session_state.last_msg}")

    st.title("🎙️ Score Scribe Pro")
    cmd = st.text_input("Command:", key="input_box")
    
    # 2. VERTICAL BUTTON STACK (For Mobile Stability)
    if st.button("↩️ Undo"):
        if st.session_state.history:
            st.session_state.redo_stack.append(st.session_state.history.pop())
            st.session_state.dealer_idx = (st.session_state.dealer_idx - 1) % len(st.session_state.players)
            set_status("Undone last round."); save_checkpoint(); st.rerun()
    if st.button("↪️ Redo"):
        if st.session_state.redo_stack:
            st.session_state.history.append(st.session_state.redo_stack.pop())
            st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
            set_status("Redone round."); save_checkpoint(); st.rerun()
    if st.button("🚫 TG (Terminate Midway)"):
        if st.session_state.players and st.session_state.history:
            st.session_state.game_log.append({
                "id": time.time(), "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Terminated", "players": list(st.session_state.players),
                "history": list(st.session_state.history)
            })
            st.session_state.players, st.session_state.history, st.session_state.phase = [], [], "setup"
            set_status("Game Terminated Midway."); st.rerun()

    # 3. COMMAND PROCESSING
    if cmd:
        raw = cmd.lower().strip()
        if "new game" in raw:
            st.session_state.players, st.session_state.history, st.session_state.phase = [], [], "setup"
            st.session_state.dealer_idx, st.session_state.current_picks = 0, {}
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            set_status("New Game started."); st.rerun()
        
        elif "dealer" in raw:
            for i, p in enumerate(st.session_state.players):
                if p.lower() in raw:
                    st.session_state.dealer_idx = i
                    set_status(f"Dealer set to {p}."); save_checkpoint(); st.rerun()

        elif st.session_state.phase == "setup":
            if "start" in raw or "complete" in raw:
                if len(st.session_state.players) >= 2: 
                    st.session_state.phase = "play"; set_status("Game On!"); save_checkpoint(); st.rerun()
            else:
                words = raw.replace(",", " ").split()
                names = [w.capitalize() for w in words if w not in ["and", "winner", "start", "game"] and not w.isdigit()]
                for n in names:
                    if n not in st.session_state.players: 
                        st.session_state.players.append(n); st.session_state.current_picks[n] = 0
                save_checkpoint()

        elif st.session_state.phase == "play":
            if "pick" in raw:
                for p in st.session_state.players:
                    if p.lower() in raw:
                        cur = st.session_state.current_picks.get(p, 0)
                        if cur < 3:
                            st.session_state.current_picks[p] = cur + 1
                            set_status(f"{p} pick ({cur+1}/3)"); save_checkpoint(); st.rerun()
                        break # Only one tally per command

            elif "winner" in raw:
                score_data = re.findall(r'([a-zA-Z]+)\s*(\d+)', raw); winner_match = re.search(r'winner\s*([a-zA-Z]+)', raw)
                if winner_match:
                    w_name = winner_match.group(1).capitalize(); new_round = {p: 0 for p in st.session_state.players}; sum_p = 0
                    for p_n, p_v in score_data:
                        p_n = p_n.capitalize()
                        if p_n in new_round: new_round[p_n] = -int(p_v); sum_p += int(p_v)
                    if w_name in new_round:
                        new_round[w_name] = sum_p; st.session_state.history.append(new_round); st.session_state.redo_stack = []
                        st.session_state.dealer_idx = (st.session_state.dealer_idx + 1) % len(st.session_state.players)
                        for p in st.session_state.players: st.session_state.current_picks[p] = 0
                        set_status(f"Winner: {w_name}"); save_checkpoint(); st.rerun()

    # 4. RENDER
    if st.session_state.phase == "play":
        st.success(f"🎴 **Dealer:** {st.session_state.players[st.session_state.dealer_idx]}")

    if st.session_state.players:
        sheet = generate_sheet(st.session_state.history, st.session_state.players, False, st.session_state.dealer_idx, st.session_state.current_picks)
        st.image(sheet, use_container_width=True)

else:
    st.title("📜 History & Standings")
    if st.session_state.game_log:
        win_counts = {}
        for entry in st.session_state.game_log:
            totals = {p: 0 for p in entry['players']}
            for rnd in entry['history']:
                for p in entry['players']: totals[p] += rnd.get(p, 0)
            winner = max(totals, key=totals.get); win_counts[winner] = win_counts.get(winner, 0) + 1
        st.subheader("🏆 Leaderboard")
        l_cols = st.columns(len(win_counts))
        for i, (player, wins) in enumerate(win_counts.items()):
            with l_cols[i]:
                if player in st.session_state.profiles: st.image(st.session_state.profiles[player], width=110)
                st.metric(player, f"{wins} Wins")
    for idx, entry in enumerate(reversed(st.session_state.game_log)):
        with st.expander(f"Game: {entry['date']} ({entry.get('status', 'End')})"):
            st.image(generate_sheet(entry['history'], entry['players'], True, 0, {}, status=entry.get('status', "")), use_container_width=True)
            if st.button(f"Delete Game {idx}", key=f"del_{idx}"):
                st.session_state.game_log.pop(len(st.session_state.game_log)-1-idx); st.rerun()
