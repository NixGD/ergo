"""
Mixtures of logistic distributions

Jax jitting and scipy optimization don't handle classes well so we'll
partially have to work with arrays directly (all the params_*
classmethods).
"""

from dataclasses import dataclass, field
from functools import partial
from typing import List, Type

from jax import grad, jit, scipy, vmap
import jax.numpy as np

from .location_scale_family import Logistic
from .mixture import LSMixture


@dataclass
class LogisticMixture(LSMixture):
    components: List[Logistic]
    probs: List[float]
    component_type: Type[Logistic] = field(default=Logistic, repr=False)

    ## Static functions for Jax compatibility

    @staticmethod
    def params_gradlogpdf(params, data):
        return static_mixture_params_gradlogpdf(params, data)

    @staticmethod
    def params_logpdf(params, data):
        return static_mixture_params_logpdf(params, data)

    @staticmethod
    def params_logpdf1(params, datum):
        return static_mixture_params_logpdf1(params, datum)


@jit
def static_mixture_params_logpdf(params, data):
    scores = vmap(partial(LogisticMixture.params_logpdf1, params))(data)
    return np.sum(scores)


@jit
def static_mixture_params_logpdf1(params, datum):
    structured_params = params.reshape((-1, 3))
    component_scores = []
    probs = np.array([p[2] for p in structured_params])
    logprobs = np.log(probs)
    for p, weight in zip(structured_params, logprobs):
        loc = p[0]
        scale = np.max([p[1], 0.01])  # Find a better solution?
        component_scores.append(Logistic.params_logpdf(datum, loc, scale) + weight)
    return scipy.special.logsumexp(np.array(component_scores))


static_mixture_params_gradlogpdf = jit(grad(static_mixture_params_logpdf, argnums=0))


@dataclass
class TruncatedLogisticMixture(LogisticMixture):
    floor: float = 0
    ceiling: float = 1

    def pdf1(self, x):
        p_below = super().cdf(self.floor)
        p_above = 1 - super().cdf(self.ceiling)
        p_inside = 1 - (p_below + p_above)
        p_at_x = super().pdf1(x) * (1 / p_inside)
        # this line shouldn't be necessary: in practice, we don't
        # expect to encounter xs outside the range.
        return np.where(x < self.floor, 0, np.where(x > self.ceiling, 0, p_at_x))
