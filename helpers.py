from bokeh.io import curdoc


def refresh_layout(l):
    curdoc().clear()
    curdoc().add_root(l)

