import torch
import torch.nn as nn
import torch.nn.functional as F

import numpy as np

import copy

class AI(nn.Module):
    def __init__(self):
        super(AI, self).__init__()
        self.network = nn.Sequential(
            # Convolutional Block
            nn.Conv2d(1, 20, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
            nn.Dropout(0.25),
            
            # Flattening for Fully Connected Layers
            nn.Flatten(start_dim=1),
            
            # Fully Connected Block
            nn.Linear(3920, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 10),
            nn.LogSoftmax(dim=1)
        )

    def forward(self, x):
        x = self.network(x)
        return x


def train(model, device, train_loader, optimizer):
    model.train()
    losses = []

    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.cross_entropy(output, target)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return np.mean(losses)

    

def test(model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.cross_entropy(output, target, reduction='sum').item()  # sum up batch loss

    test_loss /= len(test_loader.dataset)

    return test_loss

def load_model(path, device = torch.device("cpu")) -> torch.nn.Sequential:
    model = AI().network
    model.load_state_dict(torch.load(path))
    model.to(device)
    return model

def fed_avg(models: list[torch.nn.Sequential],
            data_sizes: list[int]) -> torch.nn.Sequential:
    """
    Perform Federated Averaging on a list of model shares.
    
    params:
        - models (list[torch.nn.Sequential]): A list of model shares to be averaged.
        - data_sizes (list[int]): A list of the number of samples in each client's training dataset.
    returns:
        - global_model (torch.nn.Sequential): The resulting global model after averaging the shares.
    """
    global_model = copy.deepcopy(models[0])
    
    for layer_i in range(len(global_model)):
        if not hasattr(global_model[layer_i], 'weight') or not hasattr(global_model[layer_i], 'bias'):
            continue
        # Averaging the weights and biases across all models
        avg_weight = np.sum([model[layer_i].weight.detach().cpu().numpy()*data_size for model, data_size in zip(models, data_sizes)], axis=0) / sum(data_sizes)
        avg_bias = np.sum([model[layer_i].bias.detach().cpu().numpy()*data_size for model, data_size in zip(models, data_sizes)], axis=0) / sum(data_sizes)

        global_model[layer_i].weight = torch.nn.Parameter(torch.tensor(avg_weight))
        global_model[layer_i].bias = torch.nn.Parameter(torch.tensor(avg_bias))
    
    return global_model