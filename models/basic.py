from collections import defaultdict
from itertools import chain

from bokeh.plotting import figure

from .base import BaseModel

from bokeh.layouts import column, row
from bokeh.models import TextInput, Div, Slider

pop_control_ui_params = {"S0": {"widget": TextInput, "kwargs": {"value": "7278717", "title": "Susceptible"}, "type": int},
                         "IA": {"widget": TextInput, "kwargs": {"value": "300", "title": "Infected-Asymptomatic"}, "type": int},
                         "IPs": {"widget": TextInput, "kwargs": {"value": "300", "title": "Infected-PreSymptomatic"}, "type": int},
                         "ISHome": {"widget": TextInput, "kwargs": {"value": "66", "title": "Infected-Symptomatic-AtHome"}, "type": int},
                         "ISHomp": {"widget": TextInput, "kwargs": {"value": "34", "title": "Infected-Symptomatic-Hospitalized"}, "type": int}
                         }

spread_factors_control_panel_ui_params = {
    "R0": {"widget": TextInput, "kwargs": {"value": "0.304", "title": "R0"}, "type": float},
    "SAR": {"widget": Slider, "kwargs": {"start": 0, "end": 100, "value": 60, "step": 1, "title": "Serological Attack Rate(%)"}, "type": float},
    "InfAR": {"widget": Slider, "kwargs": {"start": 0, "end": 100, "value": 50, "step": 1, "title": "Prop of Infections that are Asymptomatic(%)"}, "type": float},
    "TtSO": {"widget": Slider, "kwargs": {"start": 1, "end": 14, "value": 5, "step": 1, "title": "Time to Symptom Onset(days)"}, "type": int},
    "SCHR": {"widget": Slider, "kwargs": {"start": 1, "end": 100, "value": 33, "step": 1, "title": "Symp Case Hosp Rate(%)"}, "type": int},
    "DR": {"widget": Slider, "kwargs": {"start": 1, "end": 100, "value": 2, "step": 1, "title": "Death Rate(%)"}, "type": int},
    "NDtRI": {"widget": Slider, "kwargs": {"start": 1, "end": 20, "value": 14, "step": 1, "title": "Time to Resolve Symptoms(days)"}, "type": int},
    "RBR": {"widget": Slider, "kwargs": {"start": 1, "end": 100, "value": 35, "step": 1, "title": "ICU Ratio(%)"}, "type": int},
    "ICUR": {"widget": Slider, "kwargs": {"start": 1, "end": 100, "value": 20, "step": 1, "title": "ICU Ratio(%)"}, "type": int},
    "NumDays": {"widget": Slider, "kwargs": {"start": 1, "end": 300, "value": 200, "step": 10, "title": "Simulation Steps(days)"}, "type": int}
}


class BasicModel(BaseModel):
    def dynamic_control_panel(self):
        # Population Control UI
        pop_control_panel = column(sizing_mode="stretch_width")
        pop_control_panel.children.append(Div(text="""<h3>Population Initials</h3>""", height=40))
        for id, ui_item in pop_control_ui_params.items():
            new_ui_item = ui_item["widget"](id=id, **ui_item["kwargs"])
            pop_control_panel.children.append(new_ui_item)

        # Spread Factors UI
        spread_factors_panel = column(sizing_mode="stretch_width")
        spread_factors_panel.children.append(Div(text="""<h3>Spread Factors</h3>""", height=40))
        for id, ui_item in spread_factors_control_panel_ui_params.items():
            new_ui_item = ui_item["widget"](id=id, **ui_item["kwargs"])
            spread_factors_panel.children.append(new_ui_item)

        return row(*(pop_control_panel, spread_factors_panel))

    def run_with_the_input_from_control_panel(self, control_panel):
        self.engine = BasicEngine()
        self.engine.run(*self.parse_control_panel_values_to_engine_init(control_panel))

    def parse_control_panel_values_to_engine_init(self, control_panel):
        pop_control_panel, spread_factors = control_panel.children[0], control_panel.children[1]
        population_initials_dict = {key: int(value) for key, value in zip(["S", "IA", "IPs", "ISHome", "ISHosp"], [child.value for child in pop_control_panel.children[1:]])}
        R0, SAR, InfAR, TtSO, SCHR, DR, NDtRI, RBR, ICUR, NumDays = [child.value for child in spread_factors.children[1:]]
        return population_initials_dict, float(R0), float(SAR)/100, float(InfAR)/100, int(TtSO), float(SCHR)/100, float(DR)/100, int(NDtRI), float(RBR)/100, float(ICUR)/100, NumDays

    def plot_panel(self):
        p = figure(title="Population Levels Per Day")
        print(self.engine.history["S"])
        p.line(range(len(self.engine.history["S"])), self.engine.history["S"], line_color="tomato", legend_label="Susceptible")
        p.line(range(len(self.engine.history["IA"])), self.engine.history["IA"], line_color="blue", legend_label="Infected-Asymptomatic")
        model_diagram = Div(text="""<iframe allowfullscreen style="width:960px; height:720px" src="https://www.lucidchart.com/documents/embeddedchart/6bc70cef-a783-49d3-877c-c271c78ed2c4" id="eBWIQhS5aeGB"></iframe>""")
        return column(p, model_diagram, sizing_mode="stretch_width")


class BasicEngine:
    def __init__(self):
        self.history = defaultdict(list)

    def run(self, population_initials_dict, R0, SAR, InfAR, TtSO, SCHR, DR, NDtRI, RBR, ICUR, NumDays):
        S = defaultdict(float)  # STOCKS
        F = defaultdict(float)  # FLOWS
        A = defaultdict(float)  # AUXILIARY VARIABLES

        for name, init_value in population_initials_dict.items():
            S[name] = init_value
        S["NI"] = 0
        S["R"] = 0
        S["D"] = 0
        total_pop = S["S"]

        for step in range(1, NumDays+1):
            # Compute Auxiliaries
            A["TotalInfected"] = sum([S[key] for key in ["IA", "IPs", "ISHome", "ISHosp"]])
            A["Exposed"] = S["S"] * A["TotalInfected"] * R0 / total_pop
            A["Regular Bed"] = S["ISHosp"] * RBR
            A["ICU"] = S["ISHosp"] * ICUR
            A["Ventilator"] = S["ISHosp"] * (1 - RBR - ICUR)

            # Compute Flows
            F["Becomes Naturally Immune"] = A["Exposed"] * SAR
            F["Becomes Asymptomatic"] = A["Exposed"] * (1 - SAR) * InfAR
            F["Becomes Presymptomatic"] = A["Exposed"] * (1 - SAR) * (1-InfAR)
            F["Asymptomatic Recovers"] = S["IA"] / NDtRI
            F["Symptomatic Recovers at Home"] = S["ISHome"] * (1 - DR) / NDtRI
            F["Symptomatic Recovers at Hospital"] = S["ISHosp"] * (1 - DR) / NDtRI
            F["Presymptomatic Stays Home to Recover"] = S["IPs"] * (1 - SCHR) / TtSO
            F["Presymptomatic Becomes Hospitalized"] = S["IPs"] * SCHR / TtSO
            F["Symptomatic Dies at Hospital"] = S["ISHosp"] * DR / NDtRI
            F["Symptomatic Dies at Home"] = S["ISHome"] * DR / NDtRI

            self.record_history(S, F, A)

            # Update Stocks
            S["S"] = S["S"] - F["Becomes Naturally Immune"]  - F["Becomes Asymptomatic"] - F["Becomes Presymptomatic"]
            S["NI"] = S["NI"] + F["Becomes Naturally Immune"]
            S["IA"] = S["IA"] + F["Becomes Asymptomatic"] - F["Asymptomatic Recovers"]
            S["IPs"] = S["IPs"] + F["Becomes Presymptomatic"] - F["Presymptomatic Stays Home to Recover"] - F["Presymptomatic Becomes Hospitalized"]
            S["ISHome"] = S["ISHome"] + F["Presymptomatic Stays Home to Recover"] - F["Symptomatic Dies at Home"]
            S["ISHosp"] = S["ISHosp"] + F["Presymptomatic Becomes Hospitalized"] - F["Symptomatic Dies at Hospital"]
            S["R"] = S["R"] + F["Asymptomatic Recovers"] + F["Symptomatic Recovers at Home"] + F["Symptomatic Recovers at Hospital"]
            S["D"] = S["D"] + F["Symptomatic Dies at Hospital"] + F["Symptomatic Dies at Home"]

    def record_history(self, S, F, A):
        for key, value in chain(S.items(), F.items(), A.items()):
            self.history[key].append(value)







