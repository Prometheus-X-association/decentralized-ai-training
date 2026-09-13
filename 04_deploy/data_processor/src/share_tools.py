import numpy as np
import tensorflow as tf
import copy

def create_shares(model: tf.keras.Sequential, n_aggregators: int, scale=0.01) -> list[tf.keras.Sequential]:
    """
    Create shares of the model parameters for secure aggregation.
    
    params:
        - model (tf.keras.Sequential): The neural network model whose parameters are to be shared.
        - n_aggregators (int): The number of aggregators among which the shares will be distributed.
        - scale (float): The scale of the random shares. Default is 0.01 to ensure that the shares are small and do not significantly affect the training process.
                         scale=1.0 refers to a Uniform distribution in the range of  [-0.5, 0.5)
    returns:
        - shares (list[tf.keras.Sequential]): A list of model shares, one for each aggregator.
    """
    if n_aggregators % 2 != 0:
        raise ValueError("Number of aggregators must be even for secure aggregation.")
    
    shares = []
    for mi in range(0, n_aggregators, 2):
        share1 = copy.deepcopy(model)
        share2 = copy.deepcopy(model)
        
        for layer_i in range(len(model.layers)):
            weights = model.layers[layer_i].get_weights()
            #generating appropriate noise fo uniform distribution:
            weight_noise = tf.random.normal(shape=weights[0].shape, stddev=scale)
            bias_noise = tf.random.normal(shape=weights[1].shape, stddev=scale)
            #setting the weights and biases of the shares, ensuring that they sum up to the original model parameters:
            share1.layers[layer_i].set_weights([weights[0] + weight_noise, weights[1] + bias_noise])
            share2.layers[layer_i].set_weights([weights[0] - weight_noise, weights[1] - bias_noise])
            
        shares.append(share1)
        shares.append(share2)
    return shares
