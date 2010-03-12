#-*- coding:utf-8 -*-

##############################################################################
#
#    Copyright (C) 2010 De Smet Nicolas (<http://ndesmet.be>).
#    All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import gtk
from threading import Thread

from gtkcodebuffer import CodeBuffer, SyntaxLoader 
import python_lang

import model
import source

version = '0.0.1'

class DebugGuiThread(Thread):
    def __init__(self, obj, name):
        Thread.__init__(self)
        window = gtk.Window()
        window.set_title("Zyfra Debug Browse GTK v" + version)
        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)
        window.set_default_size(800, 500)
        
        self.notebook = gtk.Notebook()
        
        window.add(self.notebook)
        self.add_tab(obj, name)
        
        window.show_all()

    def run(self):
        gtk.main()

    def delete_event(self, widget, event, data=None):
        # return True = avoid quitting application
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()
        
    def add_tab(self, obj, name):
        DebugView(obj, name, self.notebook)
        
class DebugView(object):
    def __init__(self, obj, name, notebook):
        self.notebook = notebook
        self.obj = obj
        self.name = name
        
        # vpane
        self.page = gtk.HPaned()
        
        # left view, navigation
        left_view = gtk.VBox()
        
        nav_frame = gtk.Frame('Navigation')
        self.treeview = gtk.TreeView()
        self.treeview.connect("cursor-changed", self.on_cursor_changed)
        self.treeview.connect("row-activated", self.on_row_activated)
        self.treeview.set_headers_visible(False)
        self.treeview.set_enable_tree_lines(True)
        col_name = gtk.TreeViewColumn('Name', gtk.CellRendererText(), markup=0)
        self.treeview.append_column(col_name)
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.add_with_viewport(self.treeview)
        nav_frame.add(scrolledwindow)
        left_view.pack_start(nav_frame, True, True)
        
        np_frame = gtk.Frame('Navigation path')
        self.path_label = gtk.Entry()
        self.path_label.set_editable(False)
        np_frame.add(self.path_label)
        left_view.pack_start(np_frame, False, False)
        
        no_frame = gtk.Frame('Navigation options')
        no_hbox = gtk.HBox()
        self.b_hide_builtin = gtk.CheckButton(label='Hide Builtin')
        self.b_hide_builtin.set_active(True)
        self.b_hide_builtin.connect("clicked",
                                    self.on_button_hide_builtin_toggle)
        no_hbox.pack_start(self.b_hide_builtin, False, False)
        b_refresh = gtk.Button(label='Refresh')
        b_refresh.connect("clicked", self.on_button_refresh_click)
        no_hbox.pack_end(b_refresh, False, False)
        no_frame.add(no_hbox)
        left_view.pack_end(no_frame, expand=False, fill=False, padding=5)
        
        self.page.add1(left_view)
        
        # Right view (sources)
        right_view =  gtk.VBox()
        
        sd_frame = gtk.Frame('Definition')
        self.source_def = gtk.Entry()
        self.source_def.set_editable(False)
        sd_frame.add(self.source_def)
        right_view.pack_start(sd_frame, False, False)
        
        source_frame = gtk.Frame('Source code')
        source_scroll = gtk.ScrolledWindow()
        source_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC) 
        lang = python_lang.lang
        self.source_content = CodeBuffer(lang=lang)
        source_tv = gtk.TextView(self.source_content)
        source_tv.set_editable(False)
        source_scroll.add_with_viewport(source_tv)
        source_frame.add(source_scroll)
        right_view.pack_start(source_frame, True, True)

        sfp_frame = gtk.Frame('Source file path')
        self.source_file = gtk.Entry()
        self.source_file.set_editable(False)
        sfp_frame.add(self.source_file)
        right_view.pack_start(sfp_frame, False, False)

        self.page.add2(right_view)
        
        self.tree_model = model.ObjectModel(self.obj, self.name,
                                      self.b_hide_builtin.get_active())
        self.treeview.set_model(self.tree_model)
        
        self.page.show_all()
        
        # Notebook tab Label control
        nbt_view = gtk.HBox()
        nbt_label = gtk.Label(name)
        nbt_view.pack_start(nbt_label, False, False)
        #nbt_close_btn = gtk.Button('x')
        image_close = gtk.Image()
        
        nbt_close_btn = gtk.Button()
        nbt_close_btn.set_relief(gtk.RELIEF_NONE)
        nbt_close_btn.set_focus_on_click(False)
        nbt_close_btn.set_tooltip_text("Close Tab")
        image_close.set_from_stock(gtk.STOCK_CLOSE,gtk.ICON_SIZE_MENU)
        #nbt_close_btn.get_settings()
        nbt_close_btn.add(image_close)
        nbt_close_btn.connect("style-set", self.on_style_set)
        #set_relief(button,gtk.RELIEF_NONE)

        #nbt_close_btn = gtk.Button(None, gtk.STOCK_CLOSE)
        
        nbt_close_btn.connect("clicked", self.on_close_btn_clicked)
        nbt_view.pack_end(nbt_close_btn, False, False)
        nbt_view.show_all()
        notebook.append_page(self.page, nbt_view)
        notebook.set_tab_reorderable(self.page, True)
        self.check_show_tab()
        
    def on_style_set(self, widget, prevstyle):
        settings = widget.get_settings()
        x, y = gtk.icon_size_lookup_for_settings(settings, gtk.ICON_SIZE_MENU)
        widget.set_size_request(x + 2,y + 2)

    def on_button_refresh_click(self, widget, data=None):
        self.tree_model = model.ObjectModel(self.obj, self.name,
                                      self.b_hide_builtin.get_active())
        self.treeview.set_model(self.tree_model)
        self.update_path_label((0,))

    def on_button_hide_builtin_toggle(self, widget, data=None):
        self.tree_model.set_hide_builtin(widget.get_active())

    def on_cursor_changed(self, treeview):
        path, column = treeview.get_cursor()
        self.update_path_label(path)
        iter = self.tree_model.iters[self.tree_model.on_get_iter(path)]
        self.update_source(iter.obj, iter.name)
        
    def on_row_activated(self, treeview, path, view_column):
        # Open a new tab with the selected object
        iter = self.tree_model.iters[self.tree_model.on_get_iter(path)]
        DebugView(iter.obj, iter.name, self.notebook)
        
    def on_close_btn_clicked(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))
        self.check_show_tab()
        del self # Hara-kiri
        
    def check_show_tab(self):
        self.notebook.set_show_tabs(self.notebook.get_n_pages()>1)

    def update_path_label(self, path):
        path_txt = self.tree_model.get_path_txt(path)
        self.path_label.set_text(path_txt)

    def update_source(self, obj, name):
        self.source_def.set_text(source.get_def(obj, name))
        self.source_content.set_text(source.get_source(obj))
        self.source_file.set_text(source.get_path(obj))