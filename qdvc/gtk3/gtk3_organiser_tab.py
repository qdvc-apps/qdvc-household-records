"""GTK3 Organiser tab — 4-pane master-detail view.

Pane 1: zones   Pane 2: accounts   Pane 3: documents   Pane 4: file catalogue

Each account points at a FOLDER inside the data folder; the top-level PDFs there
are its documents (discovered read-only). The app never modifies the data
folder. Clicking a document does NOT open the PDF; use the Open button.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..platform_utils import open_with_default_app  # noqa: E402
from ..ui_prefs import document_label, format_date, freshness_label  # noqa: E402
from ..workspace import PathOutsideDataFolderError  # noqa: E402
from .gtk3_dialogs import account_settings_dialog, date_dialog  # noqa: E402


class OrganiserTab(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.window = window
        self._current_zone_key = None
        self._current_account = None
        self._current_document = None  # a models.Document (discovered)
        self._scan = None

        paned_outer = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned_inner = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned_last = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(paned_outer, True, True, 0)
        paned_outer.pack1(self._build_zones_pane(), True, False)
        paned_outer.pack2(paned_inner, True, False)
        paned_inner.pack1(self._build_accounts_pane(), True, False)
        paned_inner.pack2(paned_last, True, False)
        paned_last.pack1(self._build_documents_pane(), True, False)
        paned_last.pack2(self._build_catalogue_pane(), True, False)

    # ---- Pane 1: zones ----------------------------------------------
    def _build_zones_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="Zones", xalign=0.0), False, False, 0)
        self.zone_store = Gtk.ListStore(str, str, str, str)  # icon, label, key, count
        self.zone_view = Gtk.TreeView(model=self.zone_store)
        self.zone_view.set_headers_visible(False)
        col = Gtk.TreeViewColumn("Zone")
        icon = Gtk.CellRendererPixbuf()
        col.pack_start(icon, False)
        col.add_attribute(icon, "icon-name", 0)
        text = Gtk.CellRendererText()
        col.pack_start(text, True)
        col.add_attribute(text, "text", 1)
        count = Gtk.CellRendererText()
        count.set_property("xalign", 1.0)
        count.set_property("foreground", "#888888")
        col.pack_start(count, False)
        col.add_attribute(count, "text", 3)
        self.zone_view.append_column(col)
        self.zone_view.get_selection().connect("changed", self._on_zone_selected)
        self.zone_view.connect("button-press-event", self._on_zone_click)
        box.pack_start(self._scrolled(self.zone_view), True, True, 0)
        return box

    # ---- Pane 2: accounts -------------------------------------------
    def _build_accounts_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="Accounts", xalign=0.0), False, False, 0)
        self.account_store = Gtk.ListStore(str, str, str)  # name, freshness, id
        self.account_view = Gtk.TreeView(model=self.account_store)
        self.account_view.append_column(
            Gtk.TreeViewColumn("Account", Gtk.CellRendererText(), text=0))
        self.account_view.append_column(
            Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=1))
        self.account_view.get_selection().connect("changed",
                                                   self._on_account_selected)
        self.account_view.connect("button-press-event", self._on_account_click)
        box.pack_start(self._scrolled(self.account_view), True, True, 0)
        return box

    # ---- Pane 3: documents ------------------------------------------
    def _build_documents_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="Documents", xalign=0.0), False, False, 0)

        # subfolder warning bar (hidden unless subfolders present)
        self.subfolder_bar = Gtk.InfoBar()
        self.subfolder_bar.set_message_type(Gtk.MessageType.WARNING)
        self.subfolder_bar.set_show_close_button(False)
        self.subfolder_bar.get_content_area().pack_start(
            Gtk.Label(
                label="This folder contains subfolders. Only top-level PDFs are "
                      "shown; files in subfolders are ignored.",
                xalign=0.0, wrap=True), True, True, 0)
        box.pack_start(self.subfolder_bar, False, False, 0)

        self.folder_info = Gtk.Label(label="", xalign=0.0)
        self.folder_info.get_style_context().add_class("dim-label")
        self.folder_info.set_line_wrap(True)
        box.pack_start(self.folder_info, False, False, 0)

        # store: pdf-icon, label, id, fg-color
        self.doc_store = Gtk.ListStore(str, str, str, str)
        self.doc_view = Gtk.TreeView(model=self.doc_store)
        self.doc_view.set_headers_visible(False)
        dcol = Gtk.TreeViewColumn("Document")
        picon = Gtk.CellRendererPixbuf()
        dcol.pack_start(picon, False)
        dcol.add_attribute(picon, "icon-name", 0)
        drenderer = Gtk.CellRendererText()
        dcol.pack_start(drenderer, True)
        dcol.add_attribute(drenderer, "text", 1)
        dcol.add_attribute(drenderer, "foreground", 3)
        self.doc_view.append_column(dcol)
        self.doc_view.get_selection().connect("changed", self._on_doc_selected)
        # NOTE: row-activated intentionally NOT connected (no open on click).
        box.pack_start(self._scrolled(self.doc_view), True, True, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.open_doc_btn = Gtk.Button()
        open_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        open_content.pack_start(
            Gtk.Image.new_from_icon_name("application-pdf", Gtk.IconSize.BUTTON),
            False, False, 0)
        open_content.pack_start(Gtk.Label(label="Open"), False, False, 0)
        self.open_doc_btn.add(open_content)
        self.open_doc_btn.connect("clicked", lambda *_: self._open_current_doc())
        self.refresh_docs_btn = Gtk.Button(label="Rescan folder")
        self.refresh_docs_btn.connect("clicked", lambda *_: self._reload_documents())
        row.pack_start(self.open_doc_btn, False, False, 0)
        row.pack_start(self.refresh_docs_btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    # ---- Pane 4: file catalogue -------------------------------------
    def _build_catalogue_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="File catalogue", xalign=0.0), False, False, 0)
        grid = Gtk.Grid(row_spacing=6, column_spacing=6)

        grid.attach(Gtk.Label(label="File", xalign=0.0), 0, 0, 1, 1)
        self.cat_file = Gtk.Label(label="—", xalign=0.0)
        self.cat_file.set_selectable(True)
        self.cat_file.set_line_wrap(True)
        grid.attach(self.cat_file, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Statement no.", xalign=0.0), 0, 1, 1, 1)
        self.cat_stmt = Gtk.Entry()
        self.cat_stmt.connect("changed", self._on_catalogue_changed)
        grid.attach(self.cat_stmt, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Date issued", xalign=0.0), 0, 2, 1, 1)
        date_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.cat_date_label = Gtk.Label(label="—", xalign=0.0)
        self.cat_date_btn = Gtk.Button(label="Pick…")
        self.cat_date_btn.connect("clicked", lambda *_: self._pick_date())
        date_row.pack_start(self.cat_date_label, True, True, 0)
        date_row.pack_start(self.cat_date_btn, False, False, 0)
        grid.attach(date_row, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="Notes", xalign=0.0), 0, 3, 1, 1)
        self.cat_notes = Gtk.Entry()
        self.cat_notes.connect("changed", self._on_catalogue_changed)
        grid.attach(self.cat_notes, 1, 3, 1, 1)
        box.pack_start(grid, False, False, 6)
        self.catalogue_grid = grid
        return box

    # ---- helpers -----------------------------------------------------
    @staticmethod
    def _scrolled(child) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(child)
        return sw

    def _ws(self):
        return self.window.workspace

    # ---- refresh (external) -----------------------------------------
    def refresh(self) -> None:
        self._reload_zones()

    def _reload_zones(self) -> None:
        self.zone_store.clear()
        ws = self._ws()
        if ws:
            for z in sorted(ws.zones(), key=lambda z: z.label.lower()):
                count = len(ws.accounts_for_zone(z.key))
                self.zone_store.append([z.icon, z.label, z.key, str(count)])
        self._reload_accounts()

    def _reload_accounts(self) -> None:
        self.account_store.clear()
        ws = self._ws()
        if ws and self._current_zone_key:
            for a in ws.accounts_for_zone(self._current_zone_key):
                self.account_store.append(
                    [a.name, freshness_label(ws.is_fresh(a)), a.id])
        self._current_account = None
        self._reload_documents()
        self._update_sensitivity()

    def _reload_documents(self) -> None:
        self.doc_store.clear()
        self._scan = None
        acc = self._current_account
        ws = self._ws()
        if acc and ws:
            self._scan = ws.scan_account(acc)
            for d in self._scan.documents:
                color = "#888888" if not d.present else None
                self.doc_store.append(
                    ["application-pdf", document_label(d), d.filename, color])
            self.subfolder_bar.set_visible(bool(self._scan.has_subfolders))
            if not acc.folder:
                self.folder_info.set_text("No folder set for this account. "
                                          "Use ‘Set folder…’.")
            elif not self._scan.exists:
                self.folder_info.set_text(f"Folder not found: {acc.folder}")
            else:
                self.folder_info.set_text(f"Folder: {acc.folder}")
        else:
            self.subfolder_bar.set_visible(False)
            self.folder_info.set_text("")
        self._current_document = None
        self._sync_catalogue()
        self._update_sensitivity()

    # ---- selection handlers -----------------------------------------
    def _on_zone_selected(self, selection) -> None:
        model, it = selection.get_selected()
        self._current_zone_key = model[it][2] if it else None
        self._reload_accounts()

    def _on_account_selected(self, selection) -> None:
        model, it = selection.get_selected()
        ws = self._ws()
        self._current_account = ws.account_by_id(model[it][2]) if (it and ws) else None
        self._reload_documents()
        self._update_sensitivity()

    def _on_doc_selected(self, selection) -> None:
        model, it = selection.get_selected()
        if it and self._scan:
            fname = model[it][2]
            self._current_document = next(
                (d for d in self._scan.documents if d.filename == fname), None)
        else:
            self._current_document = None
        self._sync_catalogue()
        self._update_sensitivity()

    # ---- right-click zone menu (add account here) -------------------
    def _on_zone_click(self, treeview, event) -> bool:
        if event.button != 3:
            return False
        info = treeview.get_path_at_pos(int(event.x), int(event.y))
        if info is None:
            return False
        treeview.get_selection().select_path(info[0])
        self._current_zone_key = self.zone_store[info[0]][2]
        self._popup_add_account_menu(event)
        return True

    def _popup_add_account_menu(self, event) -> None:
        if not self._current_zone_key:
            return
        zone = self._ws().zone_by_key(self._current_zone_key) if self._ws() else None
        label = f"Add account to {zone.label}…" if zone else "Add account here…"
        menu = Gtk.Menu()
        item = Gtk.MenuItem(label=label)
        item.connect("activate", lambda *_: self._on_add_account())
        menu.append(item)
        menu.show_all()
        menu.popup_at_pointer(event)

    # ---- right-click account context menu ---------------------------
    def _on_account_click(self, treeview, event) -> bool:
        if event.button != 3:
            return False
        info = treeview.get_path_at_pos(int(event.x), int(event.y))
        if info is None:
            # right-click on empty space -> add-account menu for current zone
            if self._current_zone_key:
                self._popup_add_account_menu(event)
                return True
            return False
        treeview.get_selection().select_path(info[0])
        model, it = treeview.get_selection().get_selected()
        if it:
            self._current_account = self._ws().account_by_id(model[it][2])
        menu = Gtk.Menu()
        settings = Gtk.MenuItem(label="Settings…")
        settings.connect("activate", lambda *_: self._open_account_settings())
        menu.append(settings)
        setf = Gtk.MenuItem(label="Set folder…")
        setf.connect("activate", lambda *_: self._set_folder())
        menu.append(setf)
        if self._current_account and self._current_account.folder:
            clearf = Gtk.MenuItem(label="Clear folder")
            clearf.connect("activate", lambda *_: self._clear_folder())
            menu.append(clearf)
        menu.append(Gtk.SeparatorMenuItem())
        remove = Gtk.MenuItem(label="Remove account")
        remove.connect("activate", lambda *_: self._on_remove_account())
        menu.append(remove)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _open_account_settings(self) -> None:
        acc = self._current_account
        if not acc or not self._ws():
            return
        vals = account_settings_dialog(self.window, acc)
        if vals is None:
            return
        self._ws().update_account_settings(
            acc, vals["periodic"], vals["cycle_days"], vals["notes"])
        aid = acc.id
        self._reload_accounts()
        self._select_account_row(aid)

    # ---- folder selection -------------------------------------------
    def _set_folder(self) -> None:
        ws = self._ws()
        acc = self._current_account
        if not ws or not acc:
            return
        dlg = Gtk.FileChooserDialog(
            title="Choose this account's folder (inside the data folder)",
            parent=self.window, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Select", Gtk.ResponseType.OK)
        start = ws.absolutise(acc.folder) if acc.folder else ws.data_folder
        dlg.set_current_folder(start)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            dlg.destroy()
            try:
                ws.set_account_folder(acc, path)
            except PathOutsideDataFolderError:
                self.window._error(
                    "That folder is outside the data folder.\n"
                    "An account's folder must be inside the data folder "
                    "(configurable in Preferences).")
                return
            self._reload_documents()
            self._refresh_account_status_row()
        else:
            dlg.destroy()

    def _clear_folder(self) -> None:
        if self._current_account and self._ws():
            self._ws().clear_account_folder(self._current_account)
            self._reload_documents()
            self._refresh_account_status_row()

    def _refresh_account_status_row(self) -> None:
        model, it = self.account_view.get_selection().get_selected()
        if it and self._current_account:
            model[it][1] = freshness_label(self._ws().is_fresh(self._current_account))

    # ---- catalogue editor -------------------------------------------
    def _sync_catalogue(self) -> None:
        doc = self._current_document
        self.catalogue_grid.set_sensitive(doc is not None)
        self._suspend_cat = True
        if doc:
            self.cat_file.set_text(doc.filename +
                                   ("  (missing)" if not doc.present else ""))
            self.cat_stmt.set_text(doc.statement_number)
            self.cat_date_label.set_text(format_date(doc.date_issued))
            self.cat_notes.set_text(doc.notes)
        else:
            self.cat_file.set_text("—")
            self.cat_stmt.set_text("")
            self.cat_date_label.set_text("—")
            self.cat_notes.set_text("")
        self._suspend_cat = False

    def _on_catalogue_changed(self, *_a) -> None:
        if getattr(self, "_suspend_cat", False) or not self._current_document:
            return
        doc = self._current_document
        doc.statement_number = self.cat_stmt.get_text()
        doc.notes = self.cat_notes.get_text()
        self._save_current_catalogue()
        self._refresh_doc_row_label()

    def _refresh_doc_row_label(self) -> None:
        doc = self._current_document
        if not doc:
            return
        model, it = self.doc_view.get_selection().get_selected()
        if it:
            model[it][1] = document_label(doc)

    def _save_current_catalogue(self) -> None:
        doc = self._current_document
        if not doc or not self._current_account:
            return
        self._ws().set_catalogue(
            self._current_account, doc.filename,
            doc.statement_number, doc.date_issued, doc.notes)

    def _pick_date(self) -> None:
        doc = self._current_document
        if not doc:
            return
        result = date_dialog(self.window, doc.date_issued)
        if result is None:
            return
        doc.date_issued = result["iso"]
        self._save_current_catalogue()
        self.cat_date_label.set_text(format_date(doc.date_issued))
        self._refresh_doc_row_label()
        self._refresh_account_status_row()

    # ---- add / remove account ---------------------------------------
    def _on_add_account(self, *_a) -> None:
        if not self._ws() or not self._current_zone_key:
            return
        dlg = Gtk.Dialog(title="New account", transient_for=self.window, modal=True)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Add", Gtk.ResponseType.OK)
        box = dlg.get_content_area(); box.set_border_width(10); box.set_spacing(6)
        box.pack_start(Gtk.Label(label="Account name", xalign=0.0), False, False, 0)
        entry = Gtk.Entry(); entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK and entry.get_text().strip():
            self._ws().add_account(self._current_zone_key, entry.get_text())
            self._reload_accounts()
            self._refresh_zone_count(self._current_zone_key)
        dlg.destroy()

    def _on_remove_account(self, *_a) -> None:
        if self._current_account and self._ws():
            zk = self._current_account.zone_key
            self._ws().delete_account(self._current_account)
            self._reload_accounts()
            self._refresh_zone_count(zk)

    def _refresh_zone_count(self, zone_key) -> None:
        ws = self._ws()
        if not ws or not zone_key:
            return
        count = str(len(ws.accounts_for_zone(zone_key)))
        for row in self.zone_store:
            if row[2] == zone_key:
                row[3] = count
                break

    # ---- open --------------------------------------------------------
    def _open_current_doc(self) -> None:
        doc = self._current_document
        if doc and doc.present and self._current_account and self._ws():
            open_with_default_app(
                self._ws().document_path(self._current_account, doc.filename))

    # ---- sensitivity -------------------------------------------------
    def _update_sensitivity(self) -> None:
        doc = self._current_document
        self.refresh_docs_btn.set_sensitive(self._current_account is not None)
        self.open_doc_btn.set_sensitive(bool(doc and doc.present))

    # ---- external navigation ----------------------------------------
    def _select_account_row(self, account_id: str) -> None:
        for i, row in enumerate(self.account_store):
            if row[2] == account_id:
                self.account_view.get_selection().select_iter(
                    self.account_store.get_iter(Gtk.TreePath(i)))
                break

    def select_account_by_id(self, account_id: str) -> None:
        ws = self._ws()
        if not ws:
            return
        acc = ws.account_by_id(account_id)
        if not acc:
            return
        for i, row in enumerate(self.zone_store):
            if row[2] == acc.zone_key:
                self.zone_view.get_selection().select_iter(
                    self.zone_store.get_iter(Gtk.TreePath(i)))
                break
        self._select_account_row(account_id)
