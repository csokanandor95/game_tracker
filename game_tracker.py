#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Tracker - Simple GUI app to track games to play and completed ones with ratings.

Requirements:
- Python 3.8+
- Uses only the Python standard library (tkinter + json + pathlib).

Usage:
    python game_tracker.py

Data:
- Stored as JSON in a file named "games_data.json" in the same folder as this script.
"""

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

APP_TITLE = "Game Tracker"
DATA_FILE = Path(__file__).with_name("games_data.json")

STATUS_TBP = "to be played"
STATUS_COMPLETED = "completed"

VALID_STATUSES = (STATUS_TBP, STATUS_COMPLETED)


class GameTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x520")
        self.minsize(680, 460)

        # In-memory store: list of dicts -> {"title": str, "status": str, "rating": int|None}
        self.games = []
        self.sort_by = ("title", True)  # (field, ascending)

        self._build_ui()
        self._bind_events()

        # Load persisted data (if any) and render
        self.load_data()
        self.refresh_table()

    # ---------- Persistence ----------
    def load_data(self):
        """Load games from JSON file; if not present, start empty."""
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                # Basic validation / migration
                self.games = []
                for item in data:
                    title = str(item.get("title", "")).strip()
                    status = item.get("status", STATUS_TBP)
                    rating = item.get("rating", None)
                    if status not in VALID_STATUSES or not title:
                        continue
                    if status == STATUS_COMPLETED:
                        # Normalize rating to int 1..10 or None
                        try:
                            rating = int(rating)
                        except (TypeError, ValueError):
                            rating = None
                        if rating is not None:
                            rating = min(10, max(1, rating))
                    else:
                        rating = None
                    self.games.append({"title": title, "status": status, "rating": rating})
            except Exception as e:
                messagebox.showwarning("Load error", f"Could not read data file.\n\n{e}")
                self.games = []
        else:
            self.games = []

    def save_data(self):
        """Save games to JSON file (atomic write)."""
        try:
            payload = json.dumps(self.games, ensure_ascii=False, indent=2)
            tmp = DATA_FILE.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(DATA_FILE)
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save data.\n\n{e}")

    # ---------- UI ----------
    def _build_ui(self):
        # Top frame: input controls
        frm_top = ttk.Frame(self, padding=10)
        frm_top.pack(side=tk.TOP, fill=tk.X)

        # Title input
        ttk.Label(frm_top, text="Title").grid(row=0, column=0, sticky="w")
        self.var_title = tk.StringVar()
        self.ent_title = ttk.Entry(frm_top, textvariable=self.var_title, width=36)
        self.ent_title.grid(row=1, column=0, padx=(0, 10), sticky="we")

        # Status dropdown
        ttk.Label(frm_top, text="Status").grid(row=0, column=1, sticky="w")
        self.var_status = tk.StringVar(value=STATUS_TBP)
        self.cmb_status = ttk.Combobox(frm_top, textvariable=self.var_status, state="readonly", width=18)
        self.cmb_status["values"] = VALID_STATUSES
        self.cmb_status.grid(row=1, column=1, padx=(0, 10), sticky="w")

        # Rating (only for completed)
        ttk.Label(frm_top, text="Rating (1-10, completed only)").grid(row=0, column=2, sticky="w")
        self.var_rating = tk.StringVar(value="")
        self.spn_rating = ttk.Spinbox(frm_top, from_=1, to=10, textvariable=self.var_rating, width=10, state="disabled")
        self.spn_rating.grid(row=1, column=2, padx=(0, 10), sticky="w")

        # Buttons
        self.btn_add_update = ttk.Button(frm_top, text="Add / Update", command=self.on_add_update)
        self.btn_add_update.grid(row=1, column=3, padx=(0, 10))

        self.btn_clear = ttk.Button(frm_top, text="Clear", command=self.clear_form)
        self.btn_clear.grid(row=1, column=4)

        # Stretch config
        frm_top.columnconfigure(0, weight=2)
        frm_top.columnconfigure(1, weight=1)
        frm_top.columnconfigure(2, weight=1)

        # Middle frame: actions row
        frm_actions = ttk.Frame(self, padding=(10, 0, 10, 6))
        frm_actions.pack(side=tk.TOP, fill=tk.X)

        self.btn_mark_completed = ttk.Button(frm_actions, text="Mark as Completed", command=self.mark_selected_completed)
        self.btn_mark_completed.pack(side=tk.LEFT)

        self.btn_mark_tbp = ttk.Button(frm_actions, text="Mark as To Be Played", command=self.mark_selected_tbp)
        self.btn_mark_tbp.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_delete = ttk.Button(frm_actions, text="Delete Selected", command=self.delete_selected)
        self.btn_delete.pack(side=tk.LEFT, padx=(8, 0))

        # Filter/search
        ttk.Label(frm_actions, text="Filter:").pack(side=tk.LEFT, padx=(20, 4))
        self.var_filter = tk.StringVar()
        self.ent_filter = ttk.Entry(frm_actions, textvariable=self.var_filter, width=24)
        self.ent_filter.pack(side=tk.LEFT)
        self.ent_filter.bind("<KeyRelease>", lambda e: self.refresh_table())

        # Treeview table
        frm_table = ttk.Frame(self, padding=(10, 0, 10, 10))
        frm_table.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("title", "status", "rating")
        self.tree = ttk.Treeview(frm_table, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("title", text="Title", command=lambda: self.sort_by_column("title"))
        self.tree.heading("status", text="Status", command=lambda: self.sort_by_column("status"))
        self.tree.heading("rating", text="Rating", command=lambda: self.sort_by_column("rating"))
        self.tree.column("title", width=360, anchor="w")
        self.tree.column("status", width=140, anchor="center")
        self.tree.column("rating", width=100, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        vsb = ttk.Scrollbar(frm_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self.var_statusbar = tk.StringVar(value="Ready")
        lbl_status = ttk.Label(self, textvariable=self.var_statusbar, padding=(10, 4))
        lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        # Style tweaks for nicer look
        style = ttk.Style(self)
        try:
            # Use native theme if available
            style.theme_use(style.theme_use())
        except Exception:
            pass

        self._sync_rating_state()

    def _bind_events(self):
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.cmb_status.bind("<<ComboboxSelected>>", lambda e: self._sync_rating_state())

        # Keyboard shortcuts
        self.bind("<Return>", lambda e: self.on_add_update())
        self.bind("<Delete>", lambda e: self.delete_selected())
        self.bind("<Control-s>", lambda e: self.save_data())
        self.bind("<Escape>", lambda e: self.clear_form())

    def _sync_rating_state(self):
        """Enable rating only when status is 'completed'."""
        if self.var_status.get() == STATUS_COMPLETED:
            self.spn_rating.configure(state="normal")
            if not self.var_rating.get():
                self.var_rating.set("7")  # sensible default
        else:
            self.spn_rating.configure(state="disabled")
            self.var_rating.set("")

    # ---------- Table / data ops ----------
    def refresh_table(self):
        """Render the games list in the tree, applying filter and sort."""
        # Clear current rows
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Filter
        needle = self.var_filter.get().strip().lower()
        items = self.games
        if needle:
            items = [g for g in items if needle in g["title"].lower()]

        # Sort
        field, ascending = self.sort_by
        def sort_key(g):
            v = g.get(field)
            # Ensure predictable sorting for None ratings
            if field == "rating":
                return (-1 if v is None else v)
            return ("" if v is None else v)
        items = sorted(items, key=sort_key, reverse=not ascending)

        # Insert rows
        for g in items:
            rating_str = "" if g["status"] != STATUS_COMPLETED or g["rating"] is None else str(g["rating"])
            self.tree.insert("", "end", values=(g["title"], g["status"], rating_str))

        self.var_statusbar.set(f"{len(items)} item(s) shown ({len(self.games)} total)")

    def sort_by_column(self, field):
        """Toggle sort order for given field and refresh."""
        if field not in ("title", "status", "rating"):
            return
        if self.sort_by[0] == field:
            self.sort_by = (field, not self.sort_by[1])  # toggle
        else:
            self.sort_by = (field, True)  # default asc
        self.refresh_table()

    def on_tree_select(self, event=None):
        """When a row is selected, load into form."""
        item = self._get_selected_item()
        if not item:
            return
        self.var_title.set(item["title"])
        self.var_status.set(item["status"])
        self.var_rating.set("" if item["rating"] is None else str(item["rating"]))
        self._sync_rating_state()

    def _get_selected_item(self):
        """Return the selected game dict (by title match), or None."""
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        title = values[0]
        for g in self.games:
            if g["title"] == title:
                return g
        return None

    def clear_form(self):
        """Clear input fields and selection."""
        self.tree.selection_remove(self.tree.selection())
        self.var_title.set("")
        self.var_status.set(STATUS_TBP)
        self.var_rating.set("")
        self._sync_rating_state()
        self.ent_title.focus_set()

    def on_add_update(self):
        """Add a new game or update existing (by title as unique key)."""
        title = self.var_title.get().strip()
        status = self.var_status.get()
        rating_raw = self.var_rating.get().strip()

        # Validate
        if not title:
            messagebox.showinfo("Validation", "Title is required.")
            return
        if status not in VALID_STATUSES:
            messagebox.showinfo("Validation", "Invalid status.")
            return
        rating = None
        if status == STATUS_COMPLETED:
            if not rating_raw:
                messagebox.showinfo("Validation", "Please provide a rating (1-10) for completed games.")
                return
            try:
                rating = int(rating_raw)
            except ValueError:
                messagebox.showinfo("Validation", "Rating must be an integer (1-10).")
                return
            if not (1 <= rating <= 10):
                messagebox.showinfo("Validation", "Rating must be between 1 and 10.")
                return

        # Check if title exists -> update, else add
        existing = next((g for g in self.games if g["title"].lower() == title.lower()), None)
        if existing:
            existing["status"] = status
            existing["rating"] = rating if status == STATUS_COMPLETED else None
            action = "updated"
        else:
            self.games.append({"title": title, "status": status, "rating": rating if status == STATUS_COMPLETED else None})
            action = "added"

        self.save_data()
        self.refresh_table()
        self.var_statusbar.set(f'Item "{title}" {action}.')
        self.clear_form()

    def delete_selected(self):
        """Delete the selected game."""
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("Delete", "Please select a row to delete.")
            return
        if messagebox.askyesno("Delete", f'Delete "{item["title"]}"?'):
            self.games = [g for g in self.games if g is not item]
            self.save_data()
            self.refresh_table()
            self.var_statusbar.set(f'Deleted "{item["title"]}".')
            self.clear_form()

    def mark_selected_completed(self):
        """Set selected game to completed and prompt for rating if missing."""
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("Update", "Please select a row first.")
            return
        item["status"] = STATUS_COMPLETED
        if item["rating"] is None:
            # Prompt simple dialog for rating
            rating = self._prompt_for_rating(initial=7)
            if rating is None:
                # user canceled -> revert to TBP if no rating
                item["status"] = STATUS_TBP
                return
            item["rating"] = rating
        self.save_data()
        self.refresh_table()
        self.var_statusbar.set(f'Marked "{item["title"]}" as completed.')

    def mark_selected_tbp(self):
        """Set selected game to to-be-played and clear rating."""
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("Update", "Please select a row first.")
            return
        item["status"] = STATUS_TBP
        item["rating"] = None
        self.save_data()
        self.refresh_table()
        self.var_statusbar.set(f'Marked "{item["title"]}" as to be played.')

    def _prompt_for_rating(self, initial=7):
        """Small modal dialog to ask for rating 1..10. Returns int or None if canceled."""
        dialog = tk.Toplevel(self)
        dialog.title("Set Rating")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Rating (1-10):").grid(row=0, column=0, padx=10, pady=(10, 0))
        var = tk.IntVar(value=initial)
        spn = ttk.Spinbox(dialog, from_=1, to=10, textvariable=var, width=8)
        spn.grid(row=1, column=0, padx=10, pady=6)
        spn.focus_set()

        result = {"value": None}

        def on_ok():
            val = var.get()
            try:
                val = int(val)
            except Exception:
                messagebox.showinfo("Validation", "Rating must be an integer (1-10).", parent=dialog)
                return
            if not (1 <= val <= 10):
                messagebox.showinfo("Validation", "Rating must be between 1 and 10.", parent=dialog)
                return
            result["value"] = val
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_row = ttk.Frame(dialog)
        btn_row.grid(row=2, column=0, pady=(0, 10))
        ttk.Button(btn_row, text="OK", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=6)

        dialog.wait_window()
        return result["value"]

def main():
    app = GameTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
