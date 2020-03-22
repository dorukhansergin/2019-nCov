from abc import ABC


class BaseModel(ABC):
    def control_panel(self):
        raise NotImplementedError

    def run_with_the_input_from_control_panel(self, control_panel):
        raise NotImplementedError

    def plot_panel(self):
        raise NotImplementedError