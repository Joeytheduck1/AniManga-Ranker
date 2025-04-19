import requests
import tkinter as tk
import tkinter.font as tkFont
from PIL import Image, ImageTk
from io import BytesIO
import random
import threading
import logging
import math
from itertools import groupby

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ANILIST_API_URL = "https://graphql.anilist.co"

QUERIES = {
    "ANIME": (
        "query ($name: String) { MediaListCollection(userName: $name, type: ANIME, status: COMPLETED) { "
        "lists { entries { score media { id title { english romaji } coverImage { large } } } } } }"
    ),
    "MANGA": (
        "query ($name: String) { MediaListCollection(userName: $name, type: MANGA, status: COMPLETED) { "
        "lists { entries { score media { id title { english romaji } coverImage { large } } } } } }"
    )
}

class AniMangaRankerApp:
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("AniManga Ranker")
        # Start maximized
        self.parent.state('zoomed')
        self.previous_state = self.parent.state()
        self.parent.configure(bg="grey14")
        self.session = requests.Session()

        # Tournament state & caches:
        # Each entry is stored as a tuple: (media_id, title, cover_url, user_score)
        self.unsorted_list = []
        self.sorted_list = []
        self.current_index = 0  # Next unsorted item to insert
        self.low_index = 0      # Lower bound for binary search insertion
        self.high_index = 0     # Upper bound for binary search insertion
        self.last_mid = None
        self.image_cache = {}
        self.resized_image_cache = {}
        self.DEFAULT_FONT = tkFont.Font(family="Arial", size=12)

        # For the edit-window:
        self.edit_window_open = False
        self.edit_listbox = None
        self.edited_sorted_order = None
        self.setup_gui()

    # ------------------ GUI Setup ------------------
    def setup_gui(self):
        self.control_frame = tk.Frame(self.parent, bg="grey14")
        self.control_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Username entry.
        tk.Label(
            self.control_frame,
            text="Enter AniList Username:",
            font=("Arial", 12),
            bg="grey14",
            fg="snow"
        ).pack(pady=5)
        self.username_entry = tk.Entry(self.control_frame, font=("Arial", 12), width=30, justify="center")
        self.username_entry.pack(pady=5)

        # Fetch buttons.
        self.fetch_frame = tk.Frame(self.control_frame, bg="grey14")
        self.fetch_frame.pack(fill="x", pady=5)
        tk.Button(
            self.fetch_frame,
            text="Fetch Anime List",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.start_fetch_thread("ANIME")
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(
            self.fetch_frame,
            text="Fetch Manga List",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.start_fetch_thread("MANGA")
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        for i in range(2):
            self.fetch_frame.columnconfigure(i, weight=1)

        # Progress and instruction labels.
        self.progress_label = tk.Label(self.control_frame, text="", font=("Arial", 12), bg="grey14", fg="snow")
        self.progress_label.pack(pady=5)
        self.instruction_label = tk.Label(
            self.control_frame,
            text="Comparison instructions will appear here",
            font=("Arial", 14),
            wraplength=700,
            justify="center",
            bg="grey14",
            fg="snow"
        )
        self.instruction_label.pack(pady=10)

        # Edit sorted list button.
        tk.Button(
            self.control_frame,
            text="Edit Sorted List",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=self.edit_sorted_list
        ).pack(pady=5)

        # Comparison buttons.
        self.button_frame = tk.Frame(self.parent, bg="grey14")
        self.button_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        for i in range(2):
            self.button_frame.columnconfigure(i, weight=1)
        self.button_frame.rowconfigure(0, weight=1)
        self.comp_button1 = tk.Button(
            self.button_frame,
            text="NEW wins",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            bd=0,
            relief="flat",
            activebackground="grey28",
            activeforeground="snow",
            command=self.handle_new_win
        )
        self.comp_button1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.comp_button2 = tk.Button(
            self.button_frame,
            text="Candidate wins",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            bd=0,
            relief="flat",
            activebackground="grey28",
            activeforeground="snow",
            command=self.handle_candidate_win
        )
        self.comp_button2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.resize_job = None
        self.parent.bind("<Configure>", self.on_parent_configure)

    def on_parent_configure(self, _event):
        # Check if window state has changed.
        new_state = self.parent.state()
        if new_state != self.previous_state:
            if new_state == "normal":
                # When unmaximized, force window size to 1280x720.
                self.parent.geometry("1280x720")
            self.previous_state = new_state

        if self.resize_job is not None:
            self.parent.after_cancel(self.resize_job)
        self.resize_job = self.parent.after(200, self.schedule_resize_update)

    def schedule_resize_update(self):
        if self.last_mid is not None and self.current_index < len(self.unsorted_list):
            self.update_comparison_gui((self.low_index + self.high_index) // 2)

    # ------------------ Data Fetching ------------------
    def fetch_user_completed_list(self, username, media_type):
        try:
            res = self.session.post(
                ANILIST_API_URL,
                json={"query": QUERIES[media_type], "variables": {"name": username}},
                timeout=10
            )
            res.raise_for_status()
        except Exception as e:
            logging.error("Error fetching %s list for '%s': %s", media_type, username, e)
            return []
        seen = set()
        result = []
        raw_lists = res.json().get("data", {}).get("MediaListCollection", {}).get("lists", [])
        for lst in raw_lists:
            for entry in lst.get("entries", []):
                media = entry.get("media")
                if media:
                    mid = media.get("id")
                    if mid not in seen:
                        seen.add(mid)
                        title = (media.get("title", {}).get("english") or
                                 media.get("title", {}).get("romaji") or
                                 "Unknown")
                        cover = media.get("coverImage", {}).get("large", "")
                        score = entry.get("score", 0)
                        result.append((mid, title, cover, score))
        result.sort(key=lambda x: x[3], reverse=True)
        new_result = []
        for score, group in groupby(result, key=lambda x: x[3]):
            group_list = list(group)
            random.shuffle(group_list)
            new_result.extend(group_list)
        return new_result

    def start_fetch_thread(self, media_type):
        threading.Thread(target=lambda: self.thread_fetch(media_type), daemon=True).start()

    def thread_fetch(self, media_type):
        username = self.username_entry.get().strip()
        if not username:
            self.parent.after(0, lambda: self.progress_label.config(text="Please enter a username!"))
            return
        self.parent.after(0, lambda: self.progress_label.config(text="Fetching data, please wait..."))
        items = self.fetch_user_completed_list(username, media_type)
        if not items:
            self.parent.after(0, lambda: self.progress_label.config(text=f"No completed {media_type.lower()} found for {username}"))
            return
        self.unsorted_list = items

        # Seed the tournament with the top-scored item.
        self.sorted_list = [self.unsorted_list[0]]
        self.current_index = 1
        self.low_index = 0
        self.high_index = len(self.sorted_list)
        self.parent.after(0, lambda: (self.update_progress(),
                                      self.update_comparison_gui((self.low_index + self.high_index) // 2)))
        if self.current_index >= len(self.unsorted_list):
            self.parent.after(0, self.show_final_results)

    # ------------------ Tournament Comparison Logic ------------------
    def update_progress(self):
        total = len(self.unsorted_list)
        inserted = len(self.sorted_list)
        remaining_items = total - inserted
        progress_percentage = (inserted / total * 100) if total > 0 else 0
        current_range = self.high_index - self.low_index + 1
        current_estimate = math.ceil(math.log2(current_range)) if current_range > 0 else 0
        later_estimate = sum(math.ceil(math.log2(len(self.sorted_list) + i + 1))
                             for i in range(remaining_items)) if remaining_items > 0 else 0
        total_estimated_remaining = current_estimate + later_estimate
        self.progress_label.config(
            text=(f"Inserted {inserted} of {total}. Remaining: {remaining_items} items "
                  f"({progress_percentage:.1f}% complete).\n"
                  f"Total estimated comparisons remaining: {total_estimated_remaining}.")
        )

        # Update the edit window if it's open and not actively focused.
        if self.edit_window_open and self.edit_listbox is not None:
            if self.parent.focus_get() != self.edit_listbox:
                self.refresh_edit_listbox()

    def update_comparison_gui(self, mid):
        self.last_mid = mid
        self.parent.update_idletasks()
        control_height = self.control_frame.winfo_height()
        avail_height = max(self.parent.winfo_height() - control_height - 40, 300)
        avail_width = max(self.parent.winfo_width() - 40, 400)
        btn_pixel_width = max((avail_width // 2) - 20, 200)
        if self.current_index >= len(self.unsorted_list):
            return
        new_item = self.unsorted_list[self.current_index]
        candidate = self.sorted_list[mid]
        self.instruction_label.config(text=f"Compare:\n\n{new_item[1]}\nvs.\n{candidate[1]}")
        font = self.DEFAULT_FONT
        new_title = self.truncate_text(new_item[1], btn_pixel_width, font)
        cand_title = self.truncate_text(candidate[1], btn_pixel_width, font)
        new_img = ImageTk.PhotoImage(self.get_resized_image(new_item, btn_pixel_width, avail_height - 50))
        cand_img = ImageTk.PhotoImage(self.get_resized_image(candidate, btn_pixel_width, avail_height - 50))
        width_in_chars = max(1, btn_pixel_width // font.measure("0"))
        self.comp_button1.config(
            image=new_img,
            text=new_title,
            compound="top",
            anchor="center",
            justify="center",
            width=width_in_chars,
            font=font,
            wraplength=btn_pixel_width
        )
        self.comp_button1.image = new_img
        self.comp_button2.config(
            image=cand_img,
            text=cand_title,
            compound="top",
            anchor="center",
            justify="center",
            width=width_in_chars,
            font=font,
            wraplength=btn_pixel_width
        )
        self.comp_button2.image = cand_img
        self.update_progress()

    def compare_current(self):
        if self.low_index >= self.high_index:
            self.sorted_list.insert(self.low_index, self.unsorted_list[self.current_index])
            self.current_index += 1
            self.update_progress()
            if self.current_index < len(self.unsorted_list):
                self.reset_search_range()
                self.update_comparison_gui((self.low_index + self.high_index) // 2)
            else:
                self.show_final_results()
            return
        self.update_comparison_gui((self.low_index + self.high_index) // 2)

    def reset_search_range(self):
        self.low_index = 0
        self.high_index = len(self.sorted_list)

    def handle_comparison(self, new_item_wins):
        mid = (self.low_index + self.high_index) // 2
        if new_item_wins:
            if mid == 0:
                self.sorted_list.insert(0, self.unsorted_list[self.current_index])
                self.current_index += 1
                self.reset_search_range()
                self.update_progress()
                if self.current_index < len(self.unsorted_list):
                    self.update_comparison_gui((self.low_index + self.high_index) // 2)
                else:
                    self.show_final_results()
                return
            else:
                self.high_index = mid
        else:
            if mid == len(self.sorted_list) - 1:
                self.sorted_list.append(self.unsorted_list[self.current_index])
                self.current_index += 1
                self.reset_search_range()
                self.update_progress()
                if self.current_index < len(self.unsorted_list):
                    self.update_comparison_gui((self.low_index + self.high_index) // 2)
                else:
                    self.show_final_results()
                return
            else:
                self.low_index = mid + 1
        self.compare_current()

    def handle_new_win(self):
        self.handle_comparison(True)

    def handle_candidate_win(self):
        self.handle_comparison(False)

    # ------------------ Final Results ------------------
    def show_final_results(self):
        win = tk.Toplevel(self.parent)
        win.title("Tournament Results")
        win.geometry("600x720")
        txt = tk.Text(win, wrap="word", font=("Arial", 12), bg="grey14", fg="snow", width=72, height=20)
        sb = tk.Scrollbar(win, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.insert("1.0", "Final Ranking (Best to Worst):\n\n")
        for i, comp in enumerate(self.sorted_list):
            txt.insert(tk.END, f"{i+1}. {comp[1]}\n")
        txt.config(state="disabled")

    # ------------------ Edit Window and Drag/Drop ------------------
    def edit_sorted_list(self):
        self.edit_window_open = True
        self.edited_sorted_order = list(self.sorted_list)
        win = tk.Toplevel(self.parent)
        win.title("Edit Sorted List")
        win.geometry("600x720")
        win.configure(bg="grey14")
        main_frame = tk.Frame(win, bg="grey14", bd=2, relief="solid")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        listbox = tk.Listbox(
            main_frame,
            font=("Arial", 12),
            width=50,
            height=20,
            bg="grey14",
            fg="snow",
            selectbackground="darkgrey"
        )
        listbox.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        for item in self.edited_sorted_order:
            listbox.insert(tk.END, item[1])
        self.edit_listbox = listbox
        listbox.bind("<ButtonPress-1>", self.on_listbox_button_press)
        listbox.bind("<B1-Motion>", self.on_listbox_drag)
        listbox.bind("<ButtonRelease-1>", self.on_listbox_drop)
        btn_frame = tk.Frame(main_frame, bg="grey14")
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        tk.Button(
            btn_frame,
            text="↑",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.move_item_up(listbox)
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="↓",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.move_item_down(listbox)
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Save",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.save_edited_list(listbox)
        ).pack(side="right", padx=5)
        tk.Button(
            btn_frame,
            text="Close",
            font=("Arial", 12),
            bg="grey14",
            fg="snow",
            activebackground="grey28",
            activeforeground="snow",
            command=lambda: self.close_edit_window(win)
        ).pack(side="right", padx=5)

    def close_edit_window(self, win):
        win.destroy()
        self.edit_window_open = False
        self.edit_listbox = None

    def on_listbox_button_press(self, event):
        widget = event.widget
        self._drag_data = {"index": widget.nearest(event.y)}

    def on_listbox_drag(self, event):
        widget = event.widget
        new_index = widget.nearest(event.y)
        widget.selection_clear(0, tk.END)
        widget.selection_set(new_index)
        self._drag_data["new_index"] = new_index

    def on_listbox_drop(self, event):
        widget = event.widget
        old_index = self._drag_data.get("index")
        new_index = self._drag_data.get("new_index", old_index)
        if new_index != old_index:
            self.edited_sorted_order.insert(new_index, self.edited_sorted_order.pop(old_index))
            self.refresh_listbox(widget)

    def move_item_up(self, listbox):
        selection = listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index == 0:
            return
        self.edited_sorted_order[index], self.edited_sorted_order[index - 1] = (
            self.edited_sorted_order[index - 1],
            self.edited_sorted_order[index]
        )
        self.refresh_listbox(listbox)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index - 1)

    def move_item_down(self, listbox):
        selection = listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= listbox.size() - 1:
            return
        self.edited_sorted_order[index], self.edited_sorted_order[index + 1] = (
            self.edited_sorted_order[index + 1],
            self.edited_sorted_order[index]
        )
        self.refresh_listbox(listbox)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index + 1)

    def refresh_listbox(self, listbox):
        listbox.delete(0, tk.END)
        for item in self.edited_sorted_order:
            listbox.insert(tk.END, item[1])

    def refresh_edit_listbox(self):
        if self.edit_listbox is None or not self.edit_listbox.winfo_exists():
            self.edit_listbox = None
            return
        self.edited_sorted_order = list(self.sorted_list)
        try:
            self.edit_listbox.delete(0, tk.END)
            for item in self.sorted_list:
                self.edit_listbox.insert(tk.END, item[1])
        except tk.TclError:
            self.edit_listbox = None

    def save_edited_list(self, listbox):
        self.sorted_list = self.edited_sorted_order
        self.refresh_listbox(listbox)

    # ------------------ Image Loading and Resizing ------------------
    def load_image(self, data):
        mid = data[0]
        if mid in self.image_cache:
            return self.image_cache[mid]
        try:
            r = self.session.get(data[2], timeout=10)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGB")
        except Exception as e:
            logging.error("Error loading image for '%s': %s", data[1], e)
            img = Image.new("RGB", (200, 300), color="gray")
        self.image_cache[mid] = img
        return img

    def resize_image(self, img, max_w, max_h):
        ow, oh = img.size
        aspect = ow / oh
        if max_w / aspect <= max_h:
            new_w = min(max_w, ow)
            new_h = int(new_w / aspect)
        else:
            new_h = min(max_h, oh)
            new_w = int(new_h * aspect)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def get_resized_image(self, data, max_w, max_h):
        key = (data[0], max_w, max_h)
        if key in self.resized_image_cache:
            return self.resized_image_cache[key]
        img = self.load_image(data)
        resized = self.resize_image(img, max_w, max_h)
        self.resized_image_cache[key] = resized
        return resized

    def truncate_text(self, text, max_pixels, font):
        if font.measure(text) <= max_pixels:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            if font.measure(text[:mid] + "...") > max_pixels:
                hi = mid
            else:
                lo = mid + 1
        return text[:max(0, lo - 1)] + "..."

if __name__ == "__main__":
    root = tk.Tk()
    app = AniMangaRankerApp(root)
    root.mainloop()
