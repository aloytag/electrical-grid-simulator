# -*- coding: utf-8 -*-

from ui.dialogs import Power_Flow_Dialog


class Run_PF:
    def __init__(self, graph):
        self.graph = graph
        
    def __call__(self):
        """
        Shows the Balanced AC Power Flow calculation dialog.
        """
        dialog = Power_Flow_Dialog(self.graph.net, self.graph.config['pf'],
                                   self.graph.session_change_warning,
                                   self.graph.config['general']['theme'])
        dialog.w.exec()
