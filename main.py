from bokeh.io import curdoc
from bokeh.layouts import layout, column, row
from bokeh.models import Select, Div, Button
from bokeh.plotting import figure

from models.basic import BasicModel

MODELS = {"Basic": BasicModel}


def get_dynamic_control_panel():
    return l.children[1].children[0].children[1]


def set_dynamic_control_panel(new_dynamic_control_panel):
    l.children[1].children[0].children[1] = new_dynamic_control_panel


def update_control_widget_by_model(attr, old_model, new_model):
    # Refresh control menu based on new value of dropdown selection
    set_dynamic_control_panel(MODELS[new_model]().dynamic_control_panel())


def run_and_plot(event):
    # Run Model and store data to plot
    model = MODELS[model_select.value]()
    model.run_with_the_input_from_control_panel(get_dynamic_control_panel())
    # Update plot panel
    l.children[1].children[1] = model.plot_panel()
    pass


# Create plots and widgets
heading = Div(text="""<h1>ASU 2019-nCov Demo</h1><p>Lorem ipsum dolor amet</p><hr>""", height=150, id="main-header", sizing_mode="stretch_width")
model_menu = list(MODELS.keys())
model_select = Select(title="Select Model", value=model_menu[0], options=model_menu, id="model-select")
run_button = Button(label="Run", button_type="success", id="run-button")

# Add callbacks
model_select.on_change("value", update_control_widget_by_model)
run_button.on_click(run_and_plot)

# Arrange plots and widgets in layouts
fixed_control_panel = row(model_select, run_button, id="fixed-control-panel")
dynamic_widgets = MODELS[model_menu[0]]().dynamic_control_panel()
control_panel = column(*(fixed_control_panel, dynamic_widgets), sizing_mode="fixed", height=250, width=700, id="control-panel")
plot_panel = column(*(figure(title=""),), sizing_mode="scale_width", id="plot-panel")

l = layout([
    [heading],
    [control_panel, plot_panel],
], sizing_mode="stretch_both")

c = curdoc()
c.add_root(l)
