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
        self.obj = obj
        self.name = name

    def run(self):
        window = gtk.Window()
        window.set_title("Zyfra Debug Browse GTK v" + version)
        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)
        window.set_size_request(800, 500)
        
        
        # vpane
        vpaned = gtk.HPaned()
        
        # left view, navigation
        self.b_hide_builtin = gtk.CheckButton(label='Hide Builtin')
        self.b_hide_builtin.set_active(True)
        self.b_hide_builtin.connect("clicked",
                                    self.on_button_hide_builtin_toggle)
        self.tree_model = model.ObjectModel(self.obj, self.name,
                                      self.b_hide_builtin.get_active())
        cell = gtk.CellRendererText()
        col_name = gtk.TreeViewColumn('Name', cell, markup=0)
        self.treeview = gtk.TreeView()
        self.treeview.connect("cursor-changed", self.on_cursor_changed)
        self.treeview.set_model(self.tree_model)
        self.treeview.set_enable_tree_lines(True)
        self.treeview.append_column(col_name)
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.add(self.treeview)
        
        vbox = gtk.VBox()
        vbox.pack_start(scrolledwindow, True, True)
        hbox = gtk.HBox()
        self.path_label = gtk.Entry()
        self.path_label.set_editable(False)
        hbox.pack_start(gtk.Label('Path: '), False, False)
        hbox.pack_start(self.path_label, True, True)
        hbox.pack_start(self.b_hide_builtin, False, False)
        b_refresh = gtk.Button(label='Refresh')
        b_refresh.connect("clicked", self.on_button_refresh_click)
        hbox.pack_end(b_refresh, False, False)
        vbox.pack_end(hbox, expand=False, fill=False, padding=5)
        vpaned.add1(vbox)
        
        # Right view (sources)
        right_view =  gtk.VBox()
        self.source_def = gtk.Label('')
        right_view.pack_start(self.source_def, False, False)
        
        source_scroll = gtk.ScrolledWindow()
        lang = python_lang.lang
        self.source_content = CodeBuffer(lang=lang)
        source_tv = gtk.TextView(self.source_content)
        source_tv.set_editable(False)
        source_scroll.add_with_viewport(source_tv)
        
        right_view.pack_start(source_scroll, True, True)
        
        #right Bottom
        right_bottom_view = gtk.HBox()
        right_bottom_view.pack_start(gtk.Label('Source file path:'), False, 
                                     False)
        
        self.source_file = gtk.Entry()
        self.source_file.set_editable(False)
        right_bottom_view.pack_start(self.source_file, True, True)
        
        right_view.pack_start(right_bottom_view, False, False)
        
        source_frame = gtk.Frame('Source code')
        source_frame.add(right_view)
        vpaned.add2(source_frame)
        
        window.add(vpaned)
        window.show_all()
        gtk.main()

    def delete_event(self, widget, event, data=None):
        # return True = avoid quitting application
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

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

    def update_path_label(self, path):
        path_txt = self.tree_model.get_path_txt(path)
        self.path_label.set_text(path_txt)

    def update_source(self, obj, name):
        
        self.source_def.set_text(source.get_def(obj, name))
        self.source_content.set_text(source.get_source(obj))
        self.source_file.set_text(source.get_path(obj))
        
