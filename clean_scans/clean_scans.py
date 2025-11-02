from krita import Krita, Selection, Extension


FILTER_DEFAULTS = {'threshold': {'threshold': 200},
                   'levels': {'blackvalue': 100, 'whitevalue': 200},
                   'hsvadjustment': {'s': 100}}


class CleanScans(Extension):
    filters = {}
    doc = None
    root = None
    s = None

    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass


    def init_filters(self):
        """ Initialize the filters with the settings in FILTER_DEFAULTS. """
        for f in FILTER_DEFAULTS:
            self.filters[f] = Krita.instance().filter(f)
            conf = self.filters[f].configuration()
            for key, value in FILTER_DEFAULTS[f].items():
                conf.setProperty(key, value)
            self.filters[f].setConfiguration(conf)


    def get_layers_in_group(self, group):
        """ List the first- and second-level layers in a group."""
        layers = []
        for layer in group.childNodes():
            layers.append(layer)
            for l in layer.childNodes():
                layers.append(l)
        return layers


    def setup_filters(self, layer, i):
        """ Create a group containing the layer and its filters with default values. """
        self.s.selectAll(layer, 255)
        original = layer.clone() # can't move layer, so use a copy
        original.setName(f'Page {i+1}')
        original.setChildNodes([
            self.doc.createFilterMask(f'Levels {i+1}', self.filters['levels'], self.s),
            self.doc.createFilterMask(f'HSV {i+1}', self.filters['hsvadjustment'], self.s)])
        copy = self.doc.createFilterLayer(f'Mask {i+1}', self.filters['threshold'] , self.s)
        copy.setBlendingMode('add')
        group = self.doc.createGroupLayer(f'Group {i+1}')
        group.setChildNodes([original, copy])
        self.root.addChildNode(group, layer)
        group.setCollapsed(True)
        layer.remove()


    def modify_global_filter_config(self, group):
        """ Modify the configuration of the global filters based on current group. """
        for layer in self.get_layers_in_group(group):
            if layer.type() in ('filtermask', 'filterlayer'):
                filter = layer.filter()
                name = filter.name()
                conf = filter.configuration()
                self.filters[name].setConfiguration(conf)


    def update_filters(self, group):
        """ Update the configuration of the filters in the current group. """
        for layer in self.get_layers_in_group(group):
            if layer.type() in ('filtermask', 'filterlayer'):
                filter = layer.filter()
                name = filter.name()
                if name in self.filters:
                    conf = self.filters[name].configuration()
                    filter.setConfiguration(conf)
                    layer.setFilter(filter)


    def clean_scans(self):
        self.doc = Krita.instance().activeDocument()
        if self.doc is None:
            return
        self.root = self.doc.rootNode()
        self.s = Selection()
        self.init_filters()

        for i, layer in enumerate(self.doc.topLevelNodes()[::-1]):
            layer_type = layer.type()
            if layer_type == 'paintlayer':
                print(f'layer {i} "{layer.name()}": {layer_type} → setup filters')
                self.setup_filters(layer, i)
            elif layer_type == 'grouplayer':
                if i == 0:
                    print(f'layer {i} "{layer.name()}": {layer_type} → use as reference')
                    self.modify_global_filter_config(layer)
                else:
                    print(f'layer {i} "{layer.name()}": {layer_type} → update filters')
                    self.update_filters(layer)
        self.doc.refreshProjection()


    def createActions(self, window):
        action = window.createAction("clean_scans", "Clean up scanned PDFs")
        action.triggered.connect(self.clean_scans)
