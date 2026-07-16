"""GTK4 Organiser view — 4-pane master-detail (zones/accounts/docs/catalogue)."""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..platform_utils import open_with_default_app  # noqa: E402
from ..ui_prefs import format_date, freshness_label  # noqa: E402
from ..workspace import PathOutsideWorkspaceError  # noqa: E402


class OrganiserView(Gtk.Box):
    def __init__(self, window) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.window = window
        self._zone_key = None
        self._account = None
        self._document = None
        self._suspend = False

        self.append(self._pane("Zones", self._build_zone_list()))
        self.append(Gtk.Separator())
        self.append(self._pane("Accounts", self._build_account_pane()))
        self.append(Gtk.Separator())
        self.append(self._pane("Documents", self._build_document_pane()))
        self.append(Gtk.Separator())
        self.append(self._pane("File catalogue", self._build_catalogue_pane()))

    # ---- generic pane wrapper ---------------------------------------
    def _pane(self, title: str, child) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_hexpand(True)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        lbl = Gtk.Label(label=title, xalign=0.0)
        lbl.add_css_class("heading")
        box.append(lbl)
        box.append(child)
        return box

    @staticmethod
    def _scrolled(child) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True)
        sw.set_child(child)
        return sw

    # ---- Pane 1: zones ----------------------------------------------
    def _build_zone_list(self):
        self.zone_list = Gtk.ListBox()
        self.zone_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.zone_list.connect("row-selected", self._on_zone_selected)
        return self._scrolled(self.zone_list)

    # ---- Pane 2: accounts -------------------------------------------
    def _build_account_pane(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.account_list = Gtk.ListBox()
        self.account_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.account_list.connect("row-selected", self._on_account_selected)
        box.append(self._scrolled(self.account_list))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_account_btn = Gtk.Button(label="Add account…")
        self.add_account_btn.connect("clicked", self._on_add_account)
        self.del_account_btn = Gtk.Button(label="Remove")
        self.del_account_btn.connect("clicked", self._on_remove_account)
        row.append(self.add_account_btn); row.append(self.del_account_btn)
        box.append(row)

        self.account_group = Adw.PreferencesGroup()
        self.acc_periodic = Adw.SwitchRow(title="Periodic")
        self.acc_periodic.connect("notify::active", self._on_account_changed)
        self.acc_cycle = Adw.SpinRow.new_with_range(0, 3650, 1)
        self.acc_cycle.set_title("Cycle (days)")
        self.acc_cycle.connect("notify::value", self._on_account_changed)
        self.acc_notes = Adw.EntryRow(title="Notes")
        self.acc_notes.connect("notify::text", self._on_account_changed)
        self.account_group.add(self.acc_periodic)
        self.account_group.add(self.acc_cycle)
        self.account_group.add(self.acc_notes)
        box.append(self.account_group)
        return box

    # ---- Pane 3: documents ------------------------------------------
    def _build_document_pane(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.doc_list = Gtk.ListBox()
        self.doc_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.doc_list.connect("row-selected", self._on_doc_selected)
        self.doc_list.connect("row-activated", lambda *_: self._open_doc())
        box.append(self._scrolled(self.doc_list))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_doc_btn = Gtk.Button(label="Add file…")
        self.add_doc_btn.connect("clicked", self._on_add_document)
        self.open_doc_btn = Gtk.Button(label="Open")
        self.open_doc_btn.connect("clicked", lambda *_: self._open_doc())
        self.del_doc_btn = Gtk.Button(label="Remove")
        self.del_doc_btn.connect("clicked", self._on_remove_document)
        row.append(self.add_doc_btn); row.append(self.open_doc_btn)
        row.append(self.del_doc_btn)
        box.append(row)
        return box

    # ---- Pane 4: catalogue ------------------------------------------
    def _build_catalogue_pane(self):
        self.catalogue_group = Adw.PreferencesGroup()
        self.cat_stmt = Adw.EntryRow(title="Statement no.")
        self.cat_stmt.connect("notify::text", self._on_catalogue_changed)
        self.cat_date = Adw.EntryRow(title="Date issued (YYYY-MM-DD)")
        self.cat_date.connect("notify::text", self._on_catalogue_changed)
        self.cat_notes = Adw.EntryRow(title="Notes")
        self.cat_notes.connect("notify::text", self._on_catalogue_changed)
        self.cat_path = Adw.ActionRow(title="Stored path", subtitle="—")
        self.catalogue_group.add(self.cat_stmt)
        self.catalogue_group.add(self.cat_date)
        self.catalogue_group.add(self.cat_notes)
        self.catalogue_group.add(self.cat_path)
        return self.catalogue_group

    def _ws(self):
        return self.window.workspace

    # ---- row builders -----------------------------------------------
    @staticmethod
    def _icon_row(icon: str, title: str, subtitle: str = "") -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6); box.set_margin_bottom(6)
        box.set_margin_start(6); box.set_margin_end(6)
        if icon:
            box.append(Gtk.Image.new_from_icon_name(icon))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        t = Gtk.Label(label=title, xalign=0.0)
        text.append(t)
        if subtitle:
            s = Gtk.Label(label=subtitle, xalign=0.0)
            s.add_css_class("dim-label")
            text.append(s)
        box.append(text)
        row.set_child(box)
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
            for z in ws.zones():
                row = self._icon_row(z.icon, z.label)
                row._zone_key = z.key
                self.zone_list.append(row)
        self._reload_accounts()

    def _reload_accounts(self) -> None:
        self._clear(self.account_list)
        ws = self._ws()
        if ws and self._zone_key:
            for a in ws.accounts_for_zone(self._zone_key):
                row = self._icon_row("", a.name, freshness_label(ws.is_fresh(a)))
                row._account_id = a.id
                self.account_list.append(row)
        self._account = None
        self._reload_documents()
        self._sync_account_editor()
        self._update_sensitivity()

    def _reload_documents(self) -> None:
        self._clear(self.doc_list)
        if self._account:
            for d in self._account.documents:
                row = self._icon_row("", os.path.basename(d.path),
                                     format_date(d.date_issued))
                row._doc_id = d.id
                self.doc_list.append(row)
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
        self._sync_account_editor()
        self._update_sensitivity()

    def _on_doc_selected(self, _lb, row) -> None:
        if row and self._account:
            doc_id = getattr(row, "_doc_id", "")
            self._document = next(
                (d for d in self._account.documents if d.id == doc_id), None)
        else:
            self._document = None
        self._sync_catalogue()
        self._update_sensitivity()

    # ---- account editor ---------------------------------------------
    def _sync_account_editor(self) -> None:
        acc = self._account
        self.account_group.set_sensitive(acc is not None)
        self._suspend = True
        self.acc_periodic.set_active(acc.periodic if acc else False)
        self.acc_cycle.set_value(acc.cycle_days if acc else 0)
        self.acc_notes.set_text(acc.notes if acc else "")
        self._suspend = False

    def _on_account_changed(self, *_a) -> None:
        if self._suspend or not self._account:
            return
        acc = self._account
        acc.periodic = self.acc_periodic.get_active()
        acc.cycle_days = int(self.acc_cycle.get_value())
        acc.notes = self.acc_notes.get_text()
        self._ws().save_account(acc)
        self._refresh_selected_account_subtitle()

    def _refresh_selected_account_subtitle(self) -> None:
        row = self.account_list.get_selected_row()
        if row and self._account:
            self._reload_accounts_preserving()

    def _reload_accounts_preserving(self) -> None:
        aid = self._account.id if self._account else None
        self._reload_accounts()
        if aid:
            self.select_account_row(aid)

    # ---- catalogue editor -------------------------------------------
    def _sync_catalogue(self) -> None:
        doc = self._document
        self.catalogue_group.set_sensitive(doc is not None)
        self._suspend = True
        self.cat_stmt.set_text(doc.statement_number if doc else "")
        self.cat_date.set_text(doc.date_issued if doc else "")
        self.cat_notes.set_text(doc.notes if doc else "")
        self.cat_path.set_subtitle(doc.path if doc else "—")
        self._suspend = False

    def _on_catalogue_changed(self, *_a) -> None:
        if self._suspend or not self._document:
            return
        doc = self._document
        doc.statement_number = self.cat_stmt.get_text()
        doc.date_issued = self.cat_date.get_text().strip()
        doc.notes = self.cat_notes.get_text()
        self._ws().save_account(self._account)

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
            self._ws().add_account(self._zone_key, entry.get_text())
            self._reload_accounts()
        dlg.destroy()

    def _on_remove_account(self, *_a) -> None:
        if self._account and self._ws():
            self._ws().delete_account(self._account)
            self._reload_accounts()

    # ---- add / remove document --------------------------------------
    def _on_add_document(self, *_a) -> None:
        ws = self._ws()
        if not ws or not self._account:
            return
        dlg = Gtk.FileDialog(title="Choose a file inside the workspace")
        from gi.repository import Gio
        root = Gio.File.new_for_path(ws.root)
        dlg.set_initial_folder(root)
        dlg.open(self.window, None, self._on_document_chosen)

    def _on_document_chosen(self, dlg, result) -> None:
        try:
            gfile = dlg.open_finish(result)
        except Exception:
            return
        try:
            self._ws().add_document(self._account, gfile.get_path())
        except PathOutsideWorkspaceError:
            self.window._error(
                "That file is outside the workspace data folder. "
                "Only files inside the workspace can be added as documents.")
            return
        self._reload_documents()

    def _on_remove_document(self, *_a) -> None:
        if self._document and self._account and self._ws():
            self._ws().remove_document(self._account, self._document.id)
            self._reload_documents()

    def _open_doc(self) -> None:
        if self._document and self._ws():
            open_with_default_app(self._ws().absolutise(self._document.path))

    # ---- sensitivity ------------------------------------------------
    def _update_sensitivity(self) -> None:
        self.add_account_btn.set_sensitive(self._zone_key is not None)
        self.del_account_btn.set_sensitive(self._account is not None)
        self.add_doc_btn.set_sensitive(self._account is not None)
        self.open_doc_btn.set_sensitive(self._document is not None)
        self.del_doc_btn.set_sensitive(self._document is not None)

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
