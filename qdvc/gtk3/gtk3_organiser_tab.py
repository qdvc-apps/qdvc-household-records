"""GTK3 Organiser tab — 4-pane master-detail view.

Pane 1: zones   Pane 2: accounts   Pane 3: documents   Pane 4: file catalogue
"""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..platform_utils import open_with_default_app  # noqa: E402
from ..ui_prefs import format_date, freshness_label  # noqa: E402
from ..workspace import PathOutsideWorkspaceError  # noqa: E402


class OrganiserTab(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.window = window
        self._current_zone_key: str | None = None
        self._current_account = None
        self._current_document = None

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
        # store: icon, label, key
        self.zone_store = Gtk.ListStore(str, str, str)
        self.zone_view = Gtk.TreeView(model=self.zone_store)
        self.zone_view.set_headers_visible(False)
        col = Gtk.TreeViewColumn("Zone")
        icon = Gtk.CellRendererPixbuf()
        col.pack_start(icon, False)
        col.add_attribute(icon, "icon-name", 0)
        text = Gtk.CellRendererText()
        col.pack_start(text, True)
        col.add_attribute(text, "text", 1)
        self.zone_view.append_column(col)
        self.zone_view.get_selection().connect("changed", self._on_zone_selected)
        box.pack_start(self._scrolled(self.zone_view), True, True, 0)
        return box

    # ---- Pane 2: accounts -------------------------------------------
    def _build_accounts_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="Accounts", xalign=0.0), False, False, 0)
        # store: name, freshness, account_id
        self.account_store = Gtk.ListStore(str, str, str)
        self.account_view = Gtk.TreeView(model=self.account_store)
        self.account_view.append_column(
            Gtk.TreeViewColumn("Account", Gtk.CellRendererText(), text=0))
        self.account_view.append_column(
            Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=1))
        self.account_view.get_selection().connect("changed",
                                                   self._on_account_selected)
        box.pack_start(self._scrolled(self.account_view), True, True, 0)

        # add-account controls
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_account_btn = Gtk.Button(label="Add account…")
        self.add_account_btn.connect("clicked", self._on_add_account)
        self.del_account_btn = Gtk.Button(label="Remove")
        self.del_account_btn.connect("clicked", self._on_remove_account)
        row.pack_start(self.add_account_btn, True, True, 0)
        row.pack_start(self.del_account_btn, False, False, 0)
        box.pack_start(row, False, False, 0)

        # account detail editor
        self.account_editor = self._build_account_editor()
        box.pack_start(self.account_editor, False, False, 0)
        return box

    def _build_account_editor(self) -> Gtk.Widget:
        frame = Gtk.Frame(label="Account details")
        grid = Gtk.Grid(row_spacing=4, column_spacing=6, border_width=6)
        frame.add(grid)

        self.acc_periodic = Gtk.CheckButton(label="Periodic")
        self.acc_periodic.connect("toggled", self._on_account_field_changed)
        grid.attach(self.acc_periodic, 0, 0, 2, 1)

        grid.attach(Gtk.Label(label="Cycle (days)", xalign=0.0), 0, 1, 1, 1)
        self.acc_cycle = Gtk.SpinButton.new_with_range(0, 3650, 1)
        self.acc_cycle.connect("value-changed", self._on_account_field_changed)
        grid.attach(self.acc_cycle, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Notes", xalign=0.0), 0, 2, 1, 1)
        self.acc_notes = Gtk.Entry()
        self.acc_notes.connect("changed", self._on_account_field_changed)
        grid.attach(self.acc_notes, 1, 2, 1, 1)
        self.account_editor_grid = grid
        return frame

    # ---- Pane 3: documents ------------------------------------------
    def _build_documents_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="Documents", xalign=0.0), False, False, 0)
        # store: filename, date, doc_id
        self.doc_store = Gtk.ListStore(str, str, str)
        self.doc_view = Gtk.TreeView(model=self.doc_store)
        self.doc_view.append_column(
            Gtk.TreeViewColumn("File", Gtk.CellRendererText(), text=0))
        self.doc_view.append_column(
            Gtk.TreeViewColumn("Date issued", Gtk.CellRendererText(), text=1))
        self.doc_view.get_selection().connect("changed", self._on_doc_selected)
        self.doc_view.connect("row-activated", self._on_doc_activated)
        box.pack_start(self._scrolled(self.doc_view), True, True, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_doc_btn = Gtk.Button(label="Add file…")
        self.add_doc_btn.connect("clicked", self._on_add_document)
        self.open_doc_btn = Gtk.Button(label="Open")
        self.open_doc_btn.connect("clicked", lambda *_: self._open_current_doc())
        self.del_doc_btn = Gtk.Button(label="Remove")
        self.del_doc_btn.connect("clicked", self._on_remove_document)
        row.pack_start(self.add_doc_btn, True, True, 0)
        row.pack_start(self.open_doc_btn, False, False, 0)
        row.pack_start(self.del_doc_btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    # ---- Pane 4: file catalogue -------------------------------------
    def _build_catalogue_pane(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(6)
        box.pack_start(Gtk.Label(label="File catalogue", xalign=0.0), False, False, 0)
        grid = Gtk.Grid(row_spacing=6, column_spacing=6)

        grid.attach(Gtk.Label(label="Statement no.", xalign=0.0), 0, 0, 1, 1)
        self.cat_stmt = Gtk.Entry()
        self.cat_stmt.connect("changed", self._on_catalogue_changed)
        grid.attach(self.cat_stmt, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Date issued (YYYY-MM-DD)", xalign=0.0),
                    0, 1, 1, 1)
        self.cat_date = Gtk.Entry()
        self.cat_date.set_placeholder_text("2026-01-31")
        self.cat_date.connect("changed", self._on_catalogue_changed)
        grid.attach(self.cat_date, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Notes", xalign=0.0), 0, 2, 1, 1)
        self.cat_notes = Gtk.Entry()
        self.cat_notes.connect("changed", self._on_catalogue_changed)
        grid.attach(self.cat_notes, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="Stored path", xalign=0.0), 0, 3, 1, 1)
        self.cat_path = Gtk.Label(label="—", xalign=0.0)
        self.cat_path.set_selectable(True)
        self.cat_path.set_line_wrap(True)
        grid.attach(self.cat_path, 1, 3, 1, 1)
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
            for z in ws.zones():
                self.zone_store.append([z.icon, z.label, z.key])
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
        self._sync_account_editor()
        self._update_sensitivity()

    def _reload_documents(self) -> None:
        self.doc_store.clear()
        if self._current_account:
            for d in self._current_account.documents:
                self.doc_store.append(
                    [os.path.basename(d.path), format_date(d.date_issued), d.id])
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
        self._sync_account_editor()
        self._update_sensitivity()

    def _on_doc_selected(self, selection) -> None:
        model, it = selection.get_selected()
        if it and self._current_account:
            doc_id = model[it][2]
            self._current_document = next(
                (d for d in self._current_account.documents if d.id == doc_id), None)
        else:
            self._current_document = None
        self._sync_catalogue()
        self._update_sensitivity()

    def _on_doc_activated(self, *_a) -> None:
        self._open_current_doc()

    # ---- account editor ---------------------------------------------
    def _sync_account_editor(self) -> None:
        acc = self._current_account
        self.account_editor_grid.set_sensitive(acc is not None)
        self._suspend = True
        if acc:
            self.acc_periodic.set_active(acc.periodic)
            self.acc_cycle.set_value(acc.cycle_days)
            self.acc_notes.set_text(acc.notes)
        else:
            self.acc_periodic.set_active(False)
            self.acc_cycle.set_value(0)
            self.acc_notes.set_text("")
        self._suspend = False

    def _on_account_field_changed(self, *_a) -> None:
        if getattr(self, "_suspend", False) or not self._current_account:
            return
        acc = self._current_account
        acc.periodic = self.acc_periodic.get_active()
        acc.cycle_days = int(self.acc_cycle.get_value())
        acc.notes = self.acc_notes.get_text()
        self._ws().save_account(acc)
        # refresh freshness label in Pane 2
        model, it = self.account_view.get_selection().get_selected()
        if it:
            model[it][1] = freshness_label(self._ws().is_fresh(acc))

    # ---- catalogue editor -------------------------------------------
    def _sync_catalogue(self) -> None:
        doc = self._current_document
        self.catalogue_grid.set_sensitive(doc is not None)
        self._suspend_cat = True
        if doc:
            self.cat_stmt.set_text(doc.statement_number)
            self.cat_date.set_text(doc.date_issued)
            self.cat_notes.set_text(doc.notes)
            self.cat_path.set_text(doc.path)
        else:
            self.cat_stmt.set_text("")
            self.cat_date.set_text("")
            self.cat_notes.set_text("")
            self.cat_path.set_text("—")
        self._suspend_cat = False

    def _on_catalogue_changed(self, *_a) -> None:
        if getattr(self, "_suspend_cat", False) or not self._current_document:
            return
        doc = self._current_document
        doc.statement_number = self.cat_stmt.get_text()
        doc.date_issued = self.cat_date.get_text().strip()
        doc.notes = self.cat_notes.get_text()
        self._ws().save_account(self._current_account)
        # reflect date + freshness
        model, it = self.doc_view.get_selection().get_selected()
        if it:
            model[it][1] = format_date(doc.date_issued)
        amodel, ait = self.account_view.get_selection().get_selected()
        if ait:
            amodel[ait][1] = freshness_label(self._ws().is_fresh(self._current_account))

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
        dlg.destroy()

    def _on_remove_account(self, *_a) -> None:
        if self._current_account and self._ws():
            self._ws().delete_account(self._current_account)
            self._reload_accounts()

    # ---- add / remove document --------------------------------------
    def _on_add_document(self, *_a) -> None:
        ws = self._ws()
        if not ws or not self._current_account:
            return
        dlg = Gtk.FileChooserDialog(
            title="Choose a file inside the workspace", parent=self.window,
            action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Add", Gtk.ResponseType.OK)
        dlg.set_current_folder(ws.root)
        flt = Gtk.FileFilter(); flt.set_name("PDF documents"); flt.add_pattern("*.pdf")
        dlg.add_filter(flt)
        allf = Gtk.FileFilter(); allf.set_name("All files"); allf.add_pattern("*")
        dlg.add_filter(allf)
        if dlg.run() == Gtk.ResponseType.OK:
            path = dlg.get_filename()
            dlg.destroy()
            try:
                ws.add_document(self._current_account, path)
            except PathOutsideWorkspaceError:
                self.window._error(
                    "That file is outside the workspace data folder.\n"
                    "Only files inside the workspace can be added as documents.")
                return
            self._reload_documents()
        else:
            dlg.destroy()

    def _on_remove_document(self, *_a) -> None:
        if self._current_document and self._current_account and self._ws():
            self._ws().remove_document(self._current_account,
                                       self._current_document.id)
            self._reload_documents()

    def _open_current_doc(self) -> None:
        if self._current_document and self._ws():
            open_with_default_app(self._ws().absolutise(self._current_document.path))

    # ---- sensitivity -------------------------------------------------
    def _update_sensitivity(self) -> None:
        has_zone = self._current_zone_key is not None
        has_acc = self._current_account is not None
        has_doc = self._current_document is not None
        self.add_account_btn.set_sensitive(has_zone)
        self.del_account_btn.set_sensitive(has_acc)
        self.add_doc_btn.set_sensitive(has_acc)
        self.open_doc_btn.set_sensitive(has_doc)
        self.del_doc_btn.set_sensitive(has_doc)

    # ---- external navigation ----------------------------------------
    def select_account_by_id(self, account_id: str) -> None:
        ws = self._ws()
        if not ws:
            return
        acc = ws.account_by_id(account_id)
        if not acc:
            return
        # select the zone first
        for i, row in enumerate(self.zone_store):
            if row[2] == acc.zone_key:
                self.zone_view.get_selection().select_iter(
                    self.zone_store.get_iter(Gtk.TreePath(i)))
                break
        # then the account
        for i, row in enumerate(self.account_store):
            if row[2] == account_id:
                self.account_view.get_selection().select_iter(
                    self.account_store.get_iter(Gtk.TreePath(i)))
                break
