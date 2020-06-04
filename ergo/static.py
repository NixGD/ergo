from functools import partial

from jax import grad, jit, vmap
import jax.numpy as np
import jax.scipy as scipy

# Multi-condition loss, jitting entire function


@partial(jit, static_argnums=(0, 2))
def jitted_condition_loss(dist_class, dist_params, cond_classes, cond_params):
    print(
        f"Tracing {dist_class.__name__} loss for {[c.__name__ for c in cond_classes]}"
    )
    dist = dist_class.from_params(dist_params)
    total_loss = 0.0
    for (cond_class, cond_param) in zip(cond_classes, cond_params):
        condition = cond_class.structure(cond_param)
        total_loss += condition.loss(dist)
    return total_loss * 100


jitted_condition_loss_grad = jit(
    grad(jitted_condition_loss, argnums=1), static_argnums=(0, 2)
)


# Multi-condition loss, jitting only individual condition losses


def condition_loss(dist_class, dist_params, cond_classes, cond_params):
    total_loss = 0.0
    for (cond_class, cond_param) in zip(cond_classes, cond_params):
        total_loss += single_condition_loss(
            dist_class, dist_params, cond_class, cond_param
        )
    return total_loss


def condition_loss_grad(dist_class, dist_params, cond_classes, cond_params):
    total_grad = 0.0
    for (cond_class, cond_param) in zip(cond_classes, cond_params):
        total_grad += single_condition_loss_grad(
            dist_class, dist_params, cond_class, cond_param
        )
    return total_grad


@partial(jit, static_argnums=(0, 2))
def single_condition_loss(dist_class, dist_params, cond_class, cond_param):
    print(
        f"Tracing {dist_class.__name__} condition loss for"
        f" {cond_class.__name__} with params {cond_param}"
    )
    dist = dist_class.from_params(dist_params, traceable=True)
    condition = cond_class.structure(cond_param)
    return condition.loss(dist) * 100


single_condition_loss_grad = jit(
    grad(single_condition_loss, argnums=1), static_argnums=(0, 2)
)


# Description of distribution/condition fit


@partial(jit, static_argnums=(0, 2))
def describe_fit(dist_class, dist_params, cond_class, cond_params):
    dist = dist_class.structure(dist_params)
    condition = cond_class.structure(cond_params)
    return condition._describe_fit(dist)


# General negative log likelihood


@partial(jit, static_argnums=0)
def dist_logloss(dist_class, params, data):
    dist = dist_class.from_params(params)
    return -dist.logpdf(data)


dist_grad_logloss = jit(grad(dist_logloss, argnums=1), static_argnums=0)


# Logistic mixture


@jit
def logistic_logpdf(x, loc, scale):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.logistic.html
    y = (x - loc) / scale
    return scipy.stats.logistic.logpdf(y) - np.log(scale)


@jit
def logistic_mixture_logpdf(params, data):
    if data.size == 1:
        return logistic_mixture_logpdf1(params, data)
    scores = vmap(partial(logistic_mixture_logpdf1, params))(data)
    return np.sum(scores)


@jit
def logistic_mixture_logpdf1(params, datum):
    structured_params = params.reshape((-1, 3))
    component_scores = []
    probs = np.array([p[2] for p in structured_params])
    logprobs = np.log(probs)
    for p, weight in zip(structured_params, logprobs):
        loc = p[0]
        scale = np.max([p[1], 0.01])  # Find a better solution?
        component_scores.append(logistic_logpdf(datum, loc, scale) + weight)
    return scipy.special.logsumexp(np.array(component_scores))


logistic_mixture_grad_logpdf = jit(grad(logistic_mixture_logpdf, argnums=0))


# Wasserstein distance


@jit
def wasserstein_distance(xs, ys):
    diffs = np.cumsum(xs - ys)
    abs_diffs = np.abs(diffs)
    return np.sum(abs_diffs)
