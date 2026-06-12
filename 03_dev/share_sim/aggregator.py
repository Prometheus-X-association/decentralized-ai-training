import torch
import utils

class Aggregator:
    def __init__(self, aggregator_id: int, client_list: list[str], client_data_sizes: list[int]):
        self.aggregator_id = aggregator_id
        self.client_list = client_list
        self.client_data_sizes = client_data_sizes

    def aggregate(self, model_path: str) -> torch.nn.Sequential:
        models = []
        for client_id in self.client_list:
            model = utils.load_model(f"{model_path}/share_{client_id}_{self.aggregator_id}.pth")
            models.append(model)
        self.model = utils.fed_avg(models, self.client_data_sizes)
        return self.model
    
    def save_model(self, output_path: str, target_aggregator_id: int):
        torch.save(self.model.state_dict(), f"{output_path}/share_{self.aggregator_id}_{target_aggregator_id}.pth")
