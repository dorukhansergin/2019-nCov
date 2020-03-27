from bokeh.io import curdoc
from bokeh.layouts import layout, column
from bokeh.models import Select, Div, Button
from bokeh.plotting import figure

from .helpers import refresh_layout
from .models.quarantine_two import QuarantineTwo

MODELS = {"Quarantine #2": QuarantineTwo}
model_menu = list(MODELS.keys())
model = MODELS[model_menu[0]]()


def get_dynamic_control_panel():
    return l.children[1].children[0].children[3]


def set_dynamic_control_panel(new_dynamic_control_panel):
    l.children[1].children[0].children[3] = new_dynamic_control_panel
    refresh_layout(l)


def update_control_widget_by_model(attr, old_model, new_model):
    # Refresh control menu based on new value of dropdown selection
    model = MODELS[new_model]()
    set_dynamic_control_panel(model.dynamic_control_panel())


def set_plot_panel(new_plot_panel):
    l.children[1].children[1].children[0] = new_plot_panel


def update_figures_scale(attr, old_active, new_active, l):
    new_y_scale = "log" if new_active == 1 else "linear"
    # Run Model and store data to plot
    model = MODELS[model_select.value]()
    model.run_with_the_input_from_control_panel(get_dynamic_control_panel())
    # Update plot panel
    set_plot_panel(model.plot_panel(y_scale=new_y_scale))
    refresh_layout(l)


def run_and_plot(event):
    # Run Model and store data to plot
    model = MODELS[model_select.value]()
    model.run_with_the_input_from_control_panel(get_dynamic_control_panel())
    # Update plot panel
    set_plot_panel(model.plot_panel())
    refresh_layout(l)
    pass


# Create plots and widgets
heading = Div(text="""<h1>ASU 2019-nCov Demo</h1><p>The Dashboard</p>""", height=100, id="main-header")
model_select = Select(title="Model", value=model_menu[0], options=model_menu, id="model-select")
run_button = Button(label="Run", button_type="success", id="run-button")

# Add callbacks
model_select.on_change("value", update_control_widget_by_model)
run_button.on_click(run_and_plot)

fixed_control_panel = column(children=[model_select, run_button], id="fixed-control-panel")

# Arrange plots and widgets in layouts
scenario_header = Div(text="""<h2>Scenario</h2>""", height=50, id="scenario-header", sizing_mode="stretch_width")

config_header = Div(text="""<h2>Scenario Configuration</h2>""", height=50, id="config-header",
                    sizing_mode="stretch_width")

dynamic_widgets = model.dynamic_control_panel()

control_panel = column(*(scenario_header, fixed_control_panel, config_header, dynamic_widgets),
                       sizing_mode="scale_height", width=350, background="whitesmoke", id="control-panel")

plot_column = column(*(figure(title=""),), sizing_mode="scale_width", id="plot-panel")

l = layout([
    [heading],
    [control_panel, plot_column],
], sizing_mode="stretch_both")

curdoc().add_root(l)
