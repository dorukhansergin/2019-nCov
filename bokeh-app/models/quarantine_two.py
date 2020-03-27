from collections import defaultdict
from itertools import chain

from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models import TextInput, Slider, Panel, Tabs, HoverTool, ColumnDataSource
import pandas as pd

from .base import BaseModel

#TODO: move this to a helper library
def divide_by_hundred(x):
    return x / 100

pop_control_ui_params = {"S": {"widget": TextInput, "kwargs": {"value": "7278717", "title": "Susceptible Population"}, "type": int},
                         "NI_RNT": {"widget": TextInput, "kwargs": {"value": "10", "title": "Native or Recovered Immune"}, "type": int},
                         "IAS": {"widget": TextInput, "kwargs": {"value": "10", "title": "Infected-Asymptomatic"}, "type": int},
                         "IPS": {"widget": TextInput, "kwargs": {"value": "10", "title": "Infected-PreSymptomatic"}, "type": int},
                         "IS": {"widget": TextInput, "kwargs": {"value": "10", "title": "Infected-Symptomatic"}, "type": int}
                         }

non_ui_stocks = ["S_TWR", "NI_TWR", "IA_TWR", "IPS_TWR", "IS_TWR", "IAS_CCP", "IPS_CCP", "IS_CCP", "D", "RWT"]
all_stock_keys = list(pop_control_ui_params.keys()) + non_ui_stocks
spread_factors_control_panel_ui_params = {
    "beta": {"widget": TextInput, "kwargs": {"value": "0.304", "title": "beta: Infection Rate"}, "type": float},
    "x": {"widget": TextInput, "kwargs": {"value": "1e-5", "title": "x: % of No-Symptom Tested"}, "type": float},
    "y": {"widget": TextInput, "kwargs": {"value": "0.5", "title": "y: % of Symptom Tested"}, "type": float},
    "t_d": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 3, "step": 1, "title": "Testing Delay(days)"}, "type": float},
    "t_i": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 14, "step": 1, "title": "Recovery Delay(days)"}, "type": float},
    "t_l": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 1, "step": 1, "title": "Latency Period Delay(days)"}, "type": float},
    "t_p": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 4, "step": 1, "title": "Presymptomatic Period Delay(days)"}, "type": float},
    "t_c": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 1, "step": 1, "title": "Delay till Taking Test(days)"}, "type": float},
    "p_sa": {"widget": Slider, "kwargs": {"start": 0, "end": 100, "value": 100, "step": 1, "title": "Serological Attack Prob(%)"}, "type": float, "post_ui_process": divide_by_hundred},
    "p_a": {"widget": Slider, "kwargs": {"start": 0, "end": 100, "value": 60, "step": 1, "title": "Asymptomatic infection probability(%)"}, "type": float, "post_ui_process": divide_by_hundred},
    "p_r": {"widget": Slider, "kwargs": {"start": 0, "end": 100, "value": 98, "step": 1, "title": "Recovery Prob(%)"}, "type": float, "post_ui_process": divide_by_hundred},
    "NumDays": {"widget": Slider, "kwargs": {"start": 1, "end": 760, "value": 200, "step": 10, "title": "Simulation Steps(days)"}, "type": int}
}


class QuarantineTwo(BaseModel):
    def __init__(self):
        self.engine = QuarantineTwoEngine()
        self.source = ColumnDataSource()

    def dynamic_control_panel(self):
        # Population Control UI
        pop_control_panel = column(sizing_mode="stretch_width")
        for id, ui_item in pop_control_ui_params.items():
            new_ui_item = ui_item["widget"](id=id, **ui_item["kwargs"])
            pop_control_panel.children.append(new_ui_item)

        # Spread Factors UI
        spread_factors_panel = column(sizing_mode="stretch_width")
        for id, ui_item in spread_factors_control_panel_ui_params.items():
            new_ui_item = ui_item["widget"](id=id, **ui_item["kwargs"])
            spread_factors_panel.children.append(new_ui_item)

        return row(Tabs(tabs=[Panel(child=pop_control_panel, title="Initial Variables of Stocks"),
                              Panel(child=spread_factors_panel, title="Parameters")]), id="dynamic-control-panel")

    def run_with_the_input_from_control_panel(self, control_panel):
        self.engine.run(*self.parse_control_panel_values_to_engine_init(control_panel))

    def parse_control_panel_values_to_engine_init(self, control_panel):
        pop_control_panel, spread_factors = control_panel.children[0].tabs[0].child, control_panel.children[0].tabs[1].child
        population_initials_dict = {key: int(value) for key, value in zip(list(pop_control_ui_params.keys()), [child.value for child in pop_control_panel.children])}
        spread_factors_dict = dict()
        for dict_item, new_value in zip(list(spread_factors_control_panel_ui_params.items()), [child.value for child in spread_factors.children]):
            key, post_ui_process, type = dict_item[0], dict_item[1].get("post_ui_process", None), dict_item[1].get("type")
            if post_ui_process:
                new_value = post_ui_process(type(new_value))
            else:
                new_value = type(new_value)
            spread_factors_dict[key] = new_value
        return population_initials_dict, spread_factors_dict

    def plot_panel(self, y_scale="linear"):
        #TODO: put legend outside of figure
        #TODO: Plot 2 needs sliders for x and y +
        #TODO: daily and total tests sed on hover
        #TODO: quarantine one, TWR is involved in TI
        #TODO: quarantine three, IS is not involved in TI
        p1 = figure(title="Plot 1", aspect_ratio=2, plot_width=800, margin=10, y_axis_type=y_scale)
        p2 = figure(title="Plot 2", aspect_ratio=2, plot_width=800, margin=10, y_axis_type=y_scale)
        p3 = figure(title="Deads", aspect_ratio=2, plot_width=800, margin=10, y_axis_type=y_scale)

        hist_df = self.engine.history_as_pandas_df()
        hist_df["NI/RNT+RWT"] = hist_df["NI_RNT"] + hist_df["RWT"]
        hist_df["IS-Total"] = hist_df["IS"] + hist_df["IS_TWR"] + hist_df["IS_CCP"]
        hist_df["IS-Max"] = hist_df["IS-Total"].max()
        hist_df["IS-AUC"] = hist_df["IS-Total"].sum()
        hist_df["Day"] = pd.Series(range(len(hist_df)))

        self.source = ColumnDataSource(hist_df)
        renderer_line_key = "S"
        for key, line_color in zip(["S", "NI/RNT+RWT", "D"], ["blue", "green", "red"]):
            if key == renderer_line_key:
                renderer_line = p1.line("Day", key, source=self.source, line_color=line_color, legend_label=key)
            else:
                p1.line("Day", key, source=self.source, line_color=line_color, legend_label=key)

        hover_tool = HoverTool(
            tooltips=[
                ('Day', '@Day'),
                ('S', '@{S}{0.00 a}'),
                ('NI/RNT+RWT', '@{NI/RNT+RWT}{0.00 a}'),
                ('D', '@{D}{0.00 a}')
            ],
            renderers=[renderer_line],
            # display a tooltip whenever the cursor is vertically in line with a glyph
            mode='vline'
        )
        p1.add_tools(hover_tool)

        p2.line("Day", "IS-Total", source=self.source, legend_label="IS-Total")

        hover_tool = HoverTool(
            tooltips=[
                ('Day', '@Day'),
                ('IS-Total', '@{IS-Total}{0.00 a}'),
                ('IS-Max', '@{IS-Max}{0.00 a}'),
                ('IS-AUC', '@{IS-AUC}{0.00 a}'),
            ],
            # display a tooltip whenever the cursor is vertically in line with a glyph
            mode='vline'
        )
        p2.add_tools(hover_tool)

        p3.line("Day", "D", source=self.source, legend_label="Dead", line_color="red")
        hover_tool = HoverTool(
            tooltips=[
                ('Day', '@Day'),
                ('D', '@{D}{0.00 a}')
            ],
            # display a tooltip whenever the cursor is vertically in line with a glyph
            mode='vline'
        )
        p3.add_tools(hover_tool)

        panel_p1 = Panel(child=column(p1, p3), title="Plot 1")
        panel_p2 = Panel(child=p2, title="Plot 2")
        tabs = Tabs(tabs=[panel_p1, panel_p2])
        # TODO, plot panel sizingmode margin etc should be set in main.py
        return tabs
        # return column(*(tabs,), sizing_mode="scale_width", background="whitesmoke", id="plot-panel")


class QuarantineTwoEngine:
    def __init__(self):
        self.history = defaultdict(list)

    def run(self, S, P):
        A = dict()  # AUXILIARY VARIABLES
        P["N"] = 0
        for name, init_value in S.items():
            # Total population is the sum of each initial non-zero stock that comes from the UI
            P["N"] += init_value

        for name in non_ui_stocks:
            # We assume stocks outside UI begin at 0
            S[name] = 0

        for step in range(1, P["NumDays"]+1):
            # Compute Auxiliaries
            A = self.compute_auxiliaries(A, S, P)
            # Record History of Each Stock and Auxiliary Variable
            self.record_history(S, A)
            # Update Stocks
            S.update(self.update_stocks(S, A, P))

            # TODO: do we have to post process stock to see if there is any negative?

    def update_stocks(self, S: dict, A: dict, P: dict):
        # TODO: consider unpacking S, A and P here
        S_NEW = defaultdict(float)
        # Eq [1]
        S_NEW["S"] = S["S"] + (S["S_TWR"] / P["t_d"]) - (P["x"] * S["S"]) - A["E"]
        # Eq [2]
        S_NEW["S_TWR"] = S["S_TWR"] + (P["x"] * S["S"])- (S["S_TWR"] / P["t_d"])
        # Eq [3]
        S_NEW["NI_RNT"] = S["NI_RNT"] + ((1 - P["p_sa"]) * A["E"]) + (S["IAS"] / P["t_i"]) + (P["p_r"] * S["IS"] / P["t_i"]) + (S["NI_TWR"] / P["t_d"]) - (P["x"] * S["NI_RNT"])
        # Eq [4]
        S_NEW["NI_TWR"] = S["NI_TWR"] + (P["x"] * S["NI_RNT"]) - (S["NI_TWR"] / P["t_d"])
        # Eq [5]
        S_NEW["IPS"] = S["IPS"] + (P["p_sa"] * A["E"]) - (P["x"] * S["IPS"]) - (S["IPS"] / P["t_p"])
        # Eq [6]
        S_NEW["IAS"] = S["IAS"] + (P["p_a"] * S["IPS"] / P["t_p"]) - (S["IAS"] / P["t_i"]) - (P["x"] * S["IAS"])
        # Eq [7]
        S_NEW["IS"] = S["IS"] + ((1 - P["p_a"]) * S["IPS"] / P["t_p"]) - (S["IS"] / P["t_i"]) - (P["y"] * S["IS"])
        # Eq [8]
        S_NEW["IA_TWR"] = S["IA_TWR"] + P["x"] * S["IAS"] + P["p_a"] * S["IPS_TWR"] / P["t_p"] - S["IA_TWR"] / P["t_d"] - S["IA_TWR"] / P["t_i"]
        # Eq [9]
        S_NEW["IPS_TWR"] = S["IPS_TWR"] + P["x"] * S["IPS"] - S["IPS_TWR"] / P["t_d"] - S["IPS_TWR"] / P["t_p"]
        # Eq [10]
        S_NEW["IS_TWR"] = S["IS_TWR"] + P["y"] * S["IS"] + (1 - P["p_sa"]) * S["IPS_TWR"] / P["t_p"] - S["IS_TWR"] / P["t_d"] - S["IS_TWR"] / P["t_i"]
        # Eq [11]
        S_NEW["IAS_CCP"] = S["IAS_CCP"] + S["IA_TWR"] / P["t_d"] + P["p_a"] * S["IPS_CCP"] / P["t_p"] - S["IAS_CCP"] / P["t_i"]
        # Eq [12]
        S_NEW["IS_CCP"] = S["IS_CCP"] + S["IS_TWR"] / P["t_d"] + (1- P["p_a"]) * S["IPS_CCP"] / P["t_p"] - S["IS_CCP"] / P["t_i"]
        # Eq [13]
        S_NEW["IPS_CCP"] = S["IPS_CCP"] + S["IPS_TWR"] / P["t_d"] - S["IPS_CCP"] / P["t_p"]
        # Eq [14]
        S_NEW["RWT"] = S["RWT"] + S["IA_TWR"] / P["t_i"] + P["p_r"] * S["IS_TWR"] / P["t_i"] + S["IAS_CCP"] / P["t_i"] + P["p_r"] * S["IS_CCP"] / P["t_i"]
        # Eq [15]
        S_NEW["D"] = S["D"] + (1 - P["p_r"]) * S["IS"] / P["t_i"] + (1 - P["p_r"]) * S["IS_TWR"] / P["t_i"] + (1 - P["p_r"]) * S["IS_CCP"] / P["t_i"]
        return S_NEW

    def compute_auxiliaries(self, A, S, P):
        # Total Infected
        A["TI"] = sum([S[key] for key in ["IAS", "IPS", "IS"]])
        # Exposed
        A["E"] = S["S"] * A["TI"] * P["beta"] / P["N"]
        return A

    def record_history(self, S, A):
        for key, value in chain(S.items(), A.items()):
            self.history[key].append(value)

    def history_as_pandas_df(self):
        return pd.DataFrame(self.history)


