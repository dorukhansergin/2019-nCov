from bokeh.io import curdoc
from bokeh.layouts import layout, column, row, widgetbox
from bokeh.models import Select, Div, Button
from bokeh.plotting import figure

from models.basic import BasicModel
from models.quarantine_two import QuarantineTwo

MODELS = {"Quarantine #2": QuarantineTwo}


def refresh_layout():
    curdoc().clear()
    curdoc().add_root(l)


def get_dynamic_control_panel():
    return l.children[1].children[0].children[3]


def set_dynamic_control_panel(new_dynamic_control_panel):
    l.children[1].children[0].children[3] = new_dynamic_control_panel
    refresh_layout()

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
heading = Div(text="""<h1>ASU 2019-nCov Demo</h1><p>The Dashboard</p><hr>""", height=75, id="main-header",
              sizing_mode="stretch_width")
model_menu = list(MODELS.keys())
model_select = Select(title="Model", value=model_menu[0], options=model_menu, id="model-select")
run_button = Button(label="Run", button_type="success", id="run-button")

# Add callbacks
model_select.on_change("value", update_control_widget_by_model)
run_button.on_click(run_and_plot)

# Arrange plots and widgets in layouts
scenario_header = Div(text="""<h2>Scenario</h2>""", height=50, id="scenario-header", sizing_mode="stretch_width")
config_header = Div(text="""<h2>Scenario Configuration</h2>""", height=50, id="config-header", sizing_mode="stretch_width")
fixed_control_panel = widgetbox(children=[model_select, run_button], id="fixed-control-panel")
dynamic_widgets = MODELS[model_menu[0]]().dynamic_control_panel()
control_panel = column(*(scenario_header, fixed_control_panel, config_header, dynamic_widgets), sizing_mode="fixed", height=250, width=350, margin=25,
                       id="control-panel")
plot_panel = column(*(figure(title=""),), sizing_mode="scale_width", margin=25, id="plot-panel")

l = layout([
    [heading],
    [control_panel, plot_panel],
], sizing_mode="stretch_both")

curdoc().add_root(l)
