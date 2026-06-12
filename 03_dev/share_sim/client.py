import numpy as np
import torch
import utils
from share_tools import create_shares

class Client:
    def __init__(self, client_id: int, n_aggregators: int,
                 train_data_loader: torch.utils.data.DataLoader,
                 device: torch.device, share_scale=0.01):
        self.client_id = client_id
        self.model = utils.AI().network.to(device)
        self.optimizer = torch.optim.SGD(self.model.parameters(), lr=0.01)
        self.criterion = torch.nn.CrossEntropyLoss()
        self.train_data_loader = train_data_loader
        self.device = device

        self.n_aggregators = n_aggregators
        self.share_scale = share_scale

    def train(self, epochs: int):
        train_losses = []
        for epoch in range(epochs):
            train_loss = utils.train(self.model, self.device, self.train_data_loader, self.optimizer)
            train_losses.append(train_loss)
        return train_losses
    
    def save_shares(self, output_dir: str, target_aggregator_ids: list[int]):
        shares = create_shares(self.model, self.n_aggregators, self.share_scale)
        for i, share in enumerate(shares):
            torch.save(share.state_dict(), f'{output_dir}/share_{self.client_id}_{target_aggregator_ids[i]}.pth')