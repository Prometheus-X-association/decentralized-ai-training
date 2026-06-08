import numpy as np
import tensorflow as tf
from tensorflow import keras

from model import ClassifierModel


################### FEDAVG ALGORITHM ###################
def fed_avg(models: dict[str | keras.Sequential],
            n_samples: list[int]) -> keras.Sequential:
    '''
        Computes the FedAvg aggregation.
        Parameters:
            - models: dictionary of models
            - n_samples: list of number of training samples
        Returns:
            - the FedAvg'd model
    '''
    avg_model = ClassifierModel()
    total_samples = np.sum(n_samples)
    mods = list(models.values())

    for li in range(len(avg_model.neural_network.layers)):
        weights = []
        for mi in range(len(mods)):
            if len(weights) == 0:
                for w in mods[mi].layers[li].get_weights():
                    weights.append(n_samples[mi] / total_samples * w)
            else:
                for i, w in enumerate(mods[mi].layers[li].get_weights()):
                    weights[i] += n_samples[mi] / total_samples * w

        avg_model.neural_network.layers[li].set_weights(
            weights
        )

    return avg_model


#################### DeltaRep ALGORITHM ##################
def _compute_global_loss(global_model: keras.Sequential, x_test: np.ndarray, y_test: np.ndarray) -> float:
    return -global_model.evaluate(x_test, y_test)[0]


def _measure_actual_contribution(global_loss: float,
                                 local_model: keras.Sequential, global_model: keras.Sequential,
                                 x_test: np.ndarray, y_test: np.ndarray) -> float:
    l_g = global_loss
    l_l = -local_model.evaluate(x_test, y_test)[0]
    return l_l - l_g


def _round_normalization(contributions: dict[str | float], eps: float = 1e-8) -> dict[str | float]:
    contrib_values = list(contributions.values())
    mean_contrib = np.mean(contrib_values)
    std_contrib = np.std(contrib_values)
    normalized_contributions = {k: (v - mean_contrib) / std_contrib
                                for k, v in contributions.items()}
    return normalized_contributions


def _update_reputations(reputations: dict[str | float],
                        norm_contributions: dict[str | float], rho: float = 0.8) -> dict[str | float]:
    for participant, contribution in norm_contributions.items():
        reputations[participant] = rho * reputations[participant] + (1 - rho) * contribution
    return reputations


def _adjust_reputations_with_confidence(reputations: dict[str | float],
                                        participation_counts: dict[str | float],
                                        lamda: float = 5) -> dict[str | float]:
    adjusted_reputations = {}
    for participant, reputation in reputations.items():
        count = participation_counts[participant]
        adjusted_reputations[participant] = reputation * count / (count + lamda)
    return adjusted_reputations


def _compute_delta(global_model: keras.Sequential, local_model: keras.Sequential) -> list[np.ndarray]:
    global_weights = global_model.get_weights()
    local_weights = local_model.get_weights()
    deltas = [local - glob for local, glob in zip(local_weights, global_weights)]
    return deltas


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def _update_global_model(global_model: keras.Sequential, delta_server: list[np.ndarray]) -> keras.Sequential:
    global_weights = global_model.get_weights()
    updated_weights = [glob + delta for glob, delta in zip(global_weights, delta_server)]
    global_model.set_weights(updated_weights)
    return global_model


def delta_rep(model_updates: dict[str | keras.Sequential],
              global_model: keras.Sequential,
              x_test: np.ndarray, y_test: np.ndarray,
              n_samples: dict[str | float],
              participation_counts: dict[str | float],
              reputations: dict[str | float],
              reputation_scale_a: float = 5.0,
              reputation_learning_rate_rho: float = 0.8,
              participation_scale_down_lambda: float = 5.0
              ) -> tuple[keras.Sequential, dict[str | float]]:
    global_loss = _compute_global_loss(global_model, x_test, y_test)
    contributions = {}
    for participant in model_updates:
        local_model = model_updates[participant]
        contribution = _measure_actual_contribution(global_loss, local_model, global_model, x_test, y_test)
        contributions[participant] = contribution
    norm_contributions = _round_normalization(contributions)
    updated_reputations = _update_reputations(
        reputations,
        norm_contributions,
        reputation_learning_rate_rho
    )
    adjusted_reputations = _adjust_reputations_with_confidence(
        updated_reputations,
        participation_counts,
        participation_scale_down_lambda
    )

    deltas = {participant: _compute_delta(global_model, model_updates[participant])
              for participant in model_updates}

    reputation_weights = {}
    for participant in model_updates:
        reputation_weights[participant] = n_samples[participant] * _sigmoid(
            reputation_scale_a * adjusted_reputations[participant])

    total_weight = sum(reputation_weights.values())
    normalized_weights = {participant: weight / total_weight for participant, weight in reputation_weights.items()}

    delta_server = None
    for participant in model_updates:
        weighted_delta = [normalized_weights[participant] * delta for delta in deltas[participant]]
        if delta_server is None:
            delta_server = weighted_delta
        else:
            delta_server = [d_s + w_d for d_s, w_d in zip(delta_server, weighted_delta)]
    global_model = _update_global_model(global_model, delta_server)

    return_model = ClassifierModel()
    return_model.set_model(global_model)
    return return_model, updated_reputations
