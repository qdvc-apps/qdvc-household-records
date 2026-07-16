"""GTK4 Organiser view — sidebar (zones) + master-detail (accounts/docs/catalogue).

Layout:
  * Pane 1 (zones) is a SIDEBAR via Adw.OverlaySplitView, not a normal column.
  * Panes 2 & 3 (accounts, documents) live in a Gtk.Paned with an explicit,
    persistent divider position so they do NOT auto-resize as the user
    navigates. Pane 4 (catalogue) is docked on the right.

Each account points at a FOLDER inside the (read-only) data folder; the
top-level PDFs there are its documents, discovered on demand. The app never
writes to the data folder. Selecting a document does not open it.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ..platform_utils import open_with_default_app  # noqa: E402
from ..ui_prefs import document_label, format_date, freshness_label  # noqa: E402
from ..workspace import PathOutsideDataFolderError  # noqa: E402
from .gtk4_dialogs import account_settings_dialog, catalogue_date_dialog  # noqa: E402


class OrganiserView(Adw.Bin):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self._zone_key = None
        self._account = None
        self._document = None
        self._scan = None
        self._suspend = False

        # Sidebar split view: Pane 1 is the sidebar.
        self.split = Adw.OverlaySplitView()
        self.split.set_min_sidebar_width(200)
        self.split.set_max_sidebar_width(340)
        self.set_child(self.split)

        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())

    # ---- sidebar toggle (called by the window's header button) ------
    def toggle_sidebar(self) -> None:
        self.split.set_show_sidebar(not self.split.get_show_sidebar())

    # ---- Pane 1: zones (sidebar) ------------------------------------
    def _build_sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        heading = Gtk.Label(label="Zones", xalign=0.0)
        heading.add_css_class("heading")
        box.append(heading)
        self.zone_list = Gtk.ListBox()
        self.zone_list.add_css_class("navigation-sidebar")
        self.zone_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.zone_list.connect("row-selected", self._on_zone_selected)
        box.append(self._scrolled(self.zone_list, vexpand=True))
        return box

    # ---- content: Paned(accounts | documents) + catalogue ----------
    def _build_content(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # Accounts | Documents share a Paned with a fixed divider so they don't
        # auto-resize during navigation.
        self.master_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.master_paned.set_position(320)
        self.master_paned.set_wide_handle(True)
        self.master_paned.set_hexpand(True)
        self.master_paned.set_start_child(self._pane("Accounts",
                                                     self._build_account_pane()))
        self.master_paned.set_resize_start_child(False)
        self.master_paned.set_shrink_start_child(False)
        self.master_paned.set_end_child(self._pane("Documents",
                                                   self._build_document_pane()))
        self.master_paned.set_resize_end_child(True)
        self.master_paned.set_shrink_end_child(False)
        outer.append(self.master_paned)

        outer.append(Gtk.Separator())
        catalogue = self._pane("File catalogue", self._build_catalogue_pane(),
                               expand=False)
        # As narrow as possible while keeping all rows fully usable.
        catalogue.set_hexpand(False)
        catalogue.set_halign(Gtk.Align.FILL)
        catalogue.set_size_request(240, -1)
        outer.append(catalogue)
        return outer

    def _pane(self, title: str, child, expand: bool = True) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_hexpand(expand)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        lbl = Gtk.Label(label=title, xalign=0.0)
        lbl.add_css_class("heading")
        box.append(lbl)
        box.append(child)
        return box

    @staticmethod
    def _scrolled(child, vexpand=True) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(vexpand)
        sw.set_child(child)
        return sw

    # ---- Pane 2: accounts -------------------------------------------
    def _build_account_pane(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.account_list = Gtk.ListBox()
        self.account_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.account_list.connect("row-selected", self._on_account_selected)
        scroller = self._scrolled(self.account_list)
        # Right-click on empty list space -> add-account menu for current zone.
        empty_gesture = Gtk.GestureClick()
        empty_gesture.set_button(3)
        empty_gesture.connect("pressed", self._on_account_blank_right_click)
        self.account_list.add_controller(empty_gesture)
        box.append(scroller)
        return box

    # ---- Pane 3: documents ------------------------------------------
    def _build_document_pane(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self.subfolder_bar = Adw.Banner()
        self.subfolder_bar.set_title(
            "Folder contains subfolders — only top-level PDFs are shown.")
        self.subfolder_bar.set_revealed(False)
        box.append(self.subfolder_bar)

        self.folder_info = Gtk.Label(label="", xalign=0.0)
        self.folder_info.add_css_class("dim-label")
        self.folder_info.set_wrap(True)
        box.append(self.folder_info)

        self.doc_list = Gtk.ListBox()
        self.doc_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.doc_list.connect("row-selected", self._on_doc_selected)
        box.append(self._scrolled(self.doc_list))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.open_doc_btn = Gtk.Button()
        open_content = Adw.ButtonContent()
        open_content.set_icon_name("application-pdf")
        open_content.set_label("Open")
        self.open_doc_btn.set_child(open_content)
        self.open_doc_btn.connect("clicked", lambda *_: self._open_doc())
        self.rescan_btn = Gtk.Button(label="Rescan folder")
        self.rescan_btn.connect("clicked", lambda *_: self._reload_documents())
        row.append(self.open_doc_btn)
        row.append(self.rescan_btn)
        box.append(row)
        return box

    # ---- Pane 4: catalogue ------------------------------------------
    def _build_catalogue_pane(self):
        self.catalogue_group = Adw.PreferencesGroup()
        self.cat_file = Adw.ActionRow(title="File", subtitle="—")
        self.cat_stmt = Adw.EntryRow(title="Statement no.")
        self.cat_stmt.connect("notify::text", self._on_catalogue_changed)
        self.cat_date = Adw.ActionRow(title="Date issued", subtitle="—")
        date_btn = Gtk.Button(label="Pick…")
        date_btn.set_valign(Gtk.Align.CENTER)
        date_btn.connect("clicked", lambda *_: self._pick_date())
        self.cat_date.add_suffix(date_btn)
        self.cat_notes = Adw.EntryRow(title="Notes")
        self.cat_notes.connect("notify::text", self._on_catalogue_changed)
        for r in (self.cat_file, self.cat_stmt, self.cat_date, self.cat_notes):
            self.catalogue_group.add(r)
        return self.catalogue_group

    def _ws(self):
        return self.window.workspace

    # ---- row builders -----------------------------------------------
    @staticmethod
    def _icon_row(icon, title, subtitle="", dim=False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b.set_margin_top(6); b.set_margin_bottom(6)
        b.set_margin_start(6); b.set_margin_end(6)
        if icon:
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_valign(Gtk.Align.CENTER)
            b.append(img)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0.0)
        if dim:
            t.add_css_class("dim-label")
        text.append(t)
        if subtitle:
            s = Gtk.Label(label=subtitle, xalign=0.0)
            s.add_css_class("dim-label")
            text.append(s)
        b.append(text)
        row.set_child(b)
        return row

    @staticmethod
    def _zone_row(icon, label, count) -> Gtk.ListBoxRow:
        """A sidebar row: icon + label (vertically centered) + count badge."""
        row = Gtk.ListBoxRow()
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b.set_margin_top(6); b.set_margin_bottom(6)
        b.set_margin_start(6); b.set_margin_end(6)
        img = Gtk.Image.new_from_icon_name(icon or "folder-symbolic")
        img.set_valign(Gtk.Align.CENTER)
        b.append(img)
        lbl = Gtk.Label(label=label, xalign=0.0)
        lbl.set_valign(Gtk.Align.CENTER)
        lbl.set_hexpand(True)
        lbl.set_ellipsize(0)  # PANGO_ELLIPSIZE_NONE — never truncate
        b.append(lbl)
        badge = Gtk.Label(label=str(count))
        badge.set_valign(Gtk.Align.CENTER)
        badge.add_css_class("dim-label")
        badge.add_css_class("numeric")
        b.append(badge)
        row.set_child(b)
        return row

    @staticmethod
    def _document_row(doc) -> Gtk.ListBoxRow:
        """Single-line row: PDF icon + document_label (never the filename)."""
        row = Gtk.ListBoxRow()
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b.set_margin_top(6); b.set_margin_bottom(6)
        b.set_margin_start(6); b.set_margin_end(6)
        img = Gtk.Image.new_from_icon_name("application-pdf")
        img.set_valign(Gtk.Align.CENTER)
        b.append(img)
        lbl = Gtk.Label(label=document_label(doc), xalign=0.0)
        lbl.set_valign(Gtk.Align.CENTER)
        lbl.set_hexpand(True)
        if getattr(doc, "present", True) is False:
            lbl.add_css_class("dim-label")
        b.append(lbl)
        row.set_child(b)
        row._doc_filename = doc.filename
        row._doc_label = lbl
        return row

    def _account_row(self, account) -> Gtk.ListBoxRow:
        row = self._icon_row("", account.name,
                             freshness_label(self._ws().is_fresh(account)))
        row._account_id = account.id
        gesture = Gtk.GestureClick()
        gesture.set_button(3)
        gesture.connect("pressed", self._on_account_right_click, row)
        row.add_controller(gesture)
        return row

    @staticmethod
    def _clear(listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            listbox.remove(child)
            child = nxt

    # ---- refresh ----------------------------------------------------
    def refresh(self) -> None:
        self._reload_zones()

    def _reload_zones(self) -> None:
        self._clear(self.zone_list)
        ws = self._ws()
        if ws:
            for z in sorted(ws.zones(), key=lambda z: z.label.lower()):
                count = len(ws.accounts_for_zone(z.key))
                row = self._zone_row(z.icon, z.label, count)
                row._zone_key = z.key
                gesture = Gtk.GestureClick()
                gesture.set_button(3)
                gesture.connect("pressed", self._on_zone_right_click, row)
                row.add_controller(gesture)
                self.zone_list.append(row)
        self._fit_sidebar_width()
        self._reload_accounts()

    def _fit_sidebar_width(self) -> None:
        """Pin the sidebar to the minimum width that shows every label in full
        (plus a little breathing room), and stop it resizing with the window."""
        natural = 240
        longest_label = 0
        ws = self._ws()
        if ws:
            for z in ws.zones():
                longest_label = max(longest_label, len(z.label))
        # Heuristic floor (~8px per char + icon + badge + padding), used when
        # measure() is unreliable (e.g. before the widget is realized).
        heuristic = 88 + longest_label * 8
        child = self.zone_list.get_first_child()
        while child is not None:
            inner = child.get_child()
            if inner is not None:
                try:
                    # GTK4: measure(orientation, for_size) -> (min, nat, minb, natb)
                    result = inner.measure(Gtk.Orientation.HORIZONTAL, -1)
                    nat_w = result[1]
                    natural = max(natural, int(nat_w) + 40)
                except (TypeError, ValueError, IndexError):
                    pass  # fall back to the heuristic below
            child = child.get_next_sibling()
        natural = max(natural, heuristic)
        natural = min(natural, 480)  # sane ceiling
        # Fix the width: equal min == max means it cannot resize with the window.
        self.split.set_min_sidebar_width(natural)
        self.split.set_max_sidebar_width(natural)

    def _reload_accounts(self) -> None:
        self._clear(self.account_list)
        ws = self._ws()
        if ws and self._zone_key:
            for a in ws.accounts_for_zone(self._zone_key):
                self.account_list.append(self._account_row(a))
        self._account = None
        self._reload_documents()
        self._update_sensitivity()

    def _reload_documents(self) -> None:
        self._clear(self.doc_list)
        self._scan = None
        ws = self._ws()
        acc = self._account
        if acc and ws:
            self._scan = ws.scan_account(acc)
            for d in self._scan.documents:
                row = self._document_row(d)
                self.doc_list.append(row)
            self.subfolder_bar.set_revealed(bool(self._scan.has_subfolders))
            if not acc.folder:
                self.folder_info.set_text("No folder set. Use ‘Set folder…’.")
            elif not self._scan.exists:
                self.folder_info.set_text(f"Folder not found: {acc.folder}")
            else:
                self.folder_info.set_text(f"Folder: {acc.folder}")
        else:
            self.subfolder_bar.set_revealed(False)
            self.folder_info.set_text("")
        self._document = None
        self._sync_catalogue()
        self._update_sensitivity()

    # ---- selection handlers -----------------------------------------
    def _on_zone_selected(self, _lb, row) -> None:
        self._zone_key = getattr(row, "_zone_key", None) if row else None
        self._reload_accounts()

    def _on_account_selected(self, _lb, row) -> None:
        ws = self._ws()
        self._account = (ws.account_by_id(getattr(row, "_account_id", ""))
                         if (row and ws) else None)
        self._reload_documents()
        self._update_sensitivity()

    def _on_doc_selected(self, _lb, row) -> None:
        if row and self._scan:
            fname = getattr(row, "_doc_filename", "")
            self._document = next(
                (d for d in self._scan.documents if d.filename == fname), None)
        else:
            self._document = None
        self._sync_catalogue()
        self._update_sensitivity()

    # ---- add-account via right-click (zone row / blank list) --------
    def _on_zone_right_click(self, _gesture, _n, _x, _y, row) -> None:
        self.zone_list.select_row(row)  # also sets _zone_key via selection
        self._zone_key = getattr(row, "_zone_key", None)
        self._show_add_account_menu(row)

    def _on_account_blank_right_click(self, _gesture, _n, _x, _y) -> None:
        if not self._zone_key:
            return
        # anchor the popover on the account list itself
        self._show_add_account_menu(self.account_list)

    def _show_add_account_menu(self, anchor) -> None:
        if not self._zone_key:
            return
        ws = self._ws()
        zone = ws.zone_by_key(self._zone_key) if ws else None
        label = f"Add account to {zone.label}…" if zone else "Add account here…"
        menu = Gio.Menu()
        menu.append(label, "orgzone.add")
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(anchor)
        self._install_zone_actions()
        popover.popup()

    def _install_zone_actions(self) -> None:
        if getattr(self, "_zone_actions", None):
            return
        group = Gio.SimpleActionGroup()
        act = Gio.SimpleAction.new("add", None)
        act.connect("activate", lambda _a, _p: self._on_add_account())
        group.add_action(act)
        self.insert_action_group("orgzone", group)
        self._zone_actions = group

    # ---- account settings (right-click) -----------------------------
    def _on_account_right_click(self, _gesture, _n, _x, _y, row) -> None:
        self.account_list.select_row(row)
        self._show_account_menu(row)

    def _show_account_menu(self, row) -> None:
        menu = Gio.Menu()
        menu.append("Settings…", "orgacct.settings")
        menu.append("Set folder…", "orgacct.setfolder")
        if self._account and self._account.folder:
            menu.append("Clear folder", "orgacct.clearfolder")
        menu.append("Remove account", "orgacct.remove")
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(row)
        self._install_account_actions()
        popover.popup()

    def _install_account_actions(self) -> None:
        if getattr(self, "_acct_actions", None):
            return
        group = Gio.SimpleActionGroup()
        specs = {
            "settings": self._open_account_settings,
            "setfolder": self._set_folder,
            "clearfolder": self._clear_folder,
            "remove": self._on_remove_account,
        }
        for name, cb in specs.items():
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda _a, _p, c=cb: c())
            group.add_action(act)
        self.insert_action_group("orgacct", group)
        self._acct_actions = group

    def _open_account_settings(self, *_a) -> None:
        if not self._account or not self._ws():
            return
        account_settings_dialog(self.window, self._account,
                                self._save_account_settings)

    def _save_account_settings(self, vals) -> None:
        acc = self._account
        if not acc:
            return
        self._ws().update_account_settings(
            acc, vals["periodic"], vals["cycle_days"], vals["notes"])
        aid = acc.id
        self._reload_accounts()
        self.select_account_row(aid)

    # ---- folder selection -------------------------------------------
    def _set_folder(self, *_a) -> None:
        ws = self._ws()
        acc = self._account
        if not ws or not acc:
            return
        dlg = Gtk.FileDialog(title="Choose this account's folder")
        start = ws.absolutise(acc.folder) if acc.folder else ws.data_folder
        dlg.set_initial_folder(Gio.File.new_for_path(start))
        dlg.select_folder(self.window, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
        except Exception:
            return
        try:
            self._ws().set_account_folder(self._account, folder.get_path())
        except PathOutsideDataFolderError:
            self.window._error(
                "That folder is outside the data folder. An account's folder "
                "must be inside the data folder (configurable in Preferences).")
            return
        aid = self._account.id
        self._reload_accounts()
        self.select_account_row(aid)

    def _clear_folder(self, *_a) -> None:
        if self._account and self._ws():
            self._ws().clear_account_folder(self._account)
            aid = self._account.id
            self._reload_accounts()
            self.select_account_row(aid)

    # ---- catalogue editor -------------------------------------------
    def _sync_catalogue(self) -> None:
        doc = self._document
        self.catalogue_group.set_sensitive(doc is not None)
        self._suspend = True
        self.cat_file.set_subtitle(
            (doc.filename + ("  (missing)" if not doc.present else ""))
            if doc else "—")
        self.cat_stmt.set_text(doc.statement_number if doc else "")
        self.cat_date.set_subtitle(format_date(doc.date_issued) if doc else "—")
        self.cat_notes.set_text(doc.notes if doc else "")
        self._suspend = False

    def _on_catalogue_changed(self, *_a) -> None:
        if self._suspend or not self._document:
            return
        doc = self._document
        doc.statement_number = self.cat_stmt.get_text()
        doc.notes = self.cat_notes.get_text()
        self._save_current_catalogue()
        self._refresh_doc_row_label()

    def _refresh_doc_row_label(self) -> None:
        doc = self._document
        if not doc:
            return
        row = self.doc_list.get_selected_row()
        lbl = getattr(row, "_doc_label", None) if row else None
        if lbl is not None:
            lbl.set_label(document_label(doc))

    def _save_current_catalogue(self) -> None:
        doc = self._document
        if not doc or not self._account:
            return
        self._ws().set_catalogue(self._account, doc.filename,
                                 doc.statement_number, doc.date_issued, doc.notes)

    def _pick_date(self) -> None:
        if not self._document:
            return
        catalogue_date_dialog(self.window, self._document.date_issued,
                              self._save_date)

    def _save_date(self, vals) -> None:
        if not self._document:
            return
        self._document.date_issued = vals["iso"]
        self._save_current_catalogue()
        self.cat_date.set_subtitle(format_date(self._document.date_issued))
        aid = self._account.id if self._account else None
        fname = self._document.filename
        self._reload_accounts()
        if aid:
            self.select_account_row(aid)
        self._select_doc_row(fname)

    def _select_doc_row(self, fname) -> None:
        child = self.doc_list.get_first_child()
        while child is not None:
            if getattr(child, "_doc_filename", None) == fname:
                self.doc_list.select_row(child)
                return
            child = child.get_next_sibling()

    # ---- add / remove account ---------------------------------------
    def _on_add_account(self, *_a) -> None:
        if not self._ws() or not self._zone_key:
            return
        dlg = Adw.MessageDialog(transient_for=self.window,
                                heading="New account",
                                body="Enter a name for the new account.")
        entry = Gtk.Entry()
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("add", "Add")
        dlg.set_default_response("add")
        dlg.connect("response", self._on_add_account_response, entry)
        dlg.present()

    def _on_add_account_response(self, dlg, response, entry) -> None:
        if response == "add" and entry.get_text().strip():
            zk = self._zone_key
            self._ws().add_account(zk, entry.get_text())
            self._reload_accounts()
            self._refresh_zone_count(zk)
        dlg.destroy()

    def _on_remove_account(self, *_a) -> None:
        if self._account and self._ws():
            zk = self._account.zone_key
            self._ws().delete_account(self._account)
            self._reload_accounts()
            self._refresh_zone_count(zk)

    def _refresh_zone_count(self, zone_key) -> None:
        ws = self._ws()
        if not ws or not zone_key:
            return
        count = len(ws.accounts_for_zone(zone_key))
        child = self.zone_list.get_first_child()
        while child is not None:
            if getattr(child, "_zone_key", None) == zone_key:
                badge = child.get_child().get_last_child()
                if isinstance(badge, Gtk.Label):
                    badge.set_label(str(count))
                break
            child = child.get_next_sibling()

    def _open_doc(self) -> None:
        doc = self._document
        if doc and doc.present and self._account and self._ws():
            open_with_default_app(
                self._ws().document_path(self._account, doc.filename))

    # ---- sensitivity ------------------------------------------------
    def _update_sensitivity(self) -> None:
        doc = self._document
        self.rescan_btn.set_sensitive(self._account is not None)
        self.open_doc_btn.set_sensitive(bool(doc and doc.present))

    # ---- external navigation ----------------------------------------
    def select_account_row(self, account_id: str) -> None:
        child = self.account_list.get_first_child()
        while child is not None:
            if getattr(child, "_account_id", None) == account_id:
                self.account_list.select_row(child)
                return
            child = child.get_next_sibling()

    def select_account_by_id(self, account_id: str) -> None:
        ws = self._ws()
        if not ws:
            return
        acc = ws.account_by_id(account_id)
        if not acc:
            return
        child = self.zone_list.get_first_child()
        while child is not None:
            if getattr(child, "_zone_key", None) == acc.zone_key:
                self.zone_list.select_row(child)
                break
            child = child.get_next_sibling()
        self.select_account_row(account_id)
