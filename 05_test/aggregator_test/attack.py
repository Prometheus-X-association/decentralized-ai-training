from typing import Dict, Tuple, List
from dataclasses import dataclass
import numpy as np

# -----------------------------
# Attacks on model updates (delta)
# -----------------------------
WeightList = List[np.ndarray]
def sign_flip(delta: WeightList) -> WeightList:
    return [(-weights).copy() for weights in delta]

def scaled_sign_flip(delta: WeightList, scale_factor: float) -> WeightList:
    return [(-weights * scale_factor).copy() for weights in delta]

def add_noise(delta: WeightList, sigma: float) -> WeightList:
    return [
        (weights + sigma * np.random.randn(*weights.shape)).astype(weights.dtype)
        for weights in delta
    ]
@dataclass
class AttackSpec:
    attack_type: str
    scale_factor: float = 5.0 # gamma
    noise_level: float = 0.1  # sigma

class AttackManager:
    def __init__(self, client_specs: Dict[int, AttackSpec]):
        self.client_specs = client_specs
    def apply(self, client_id: int, delta: WeightList, round: int) -> Tuple[WeightList, str]:
        spec = self.client_specs.get(client_id, AttackSpec("none"))
        type = spec.attack_type.lower()
        if type == "none":
            return delta, "none"
        attacked_delta = [w.copy() for w in delta]
        if type == "sign_flip":
            attacked_delta = sign_flip(attacked_delta)
        elif type == "scaled":
            attacked_delta = scaled_sign_flip(attacked_delta, spec.scale_factor)
        elif type == "random_noise":
            attacked_delta = add_noise(attacked_delta, spec.noise_level)

        return attacked_delta, type