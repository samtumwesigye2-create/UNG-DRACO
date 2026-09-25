import pytest
from app.services.math_analytics import vector_norm,weighted_sum,derivative,integral_trapezoid,gradient_1d,threshold,approximately_equal,convergence,sigma_residual

def test_vector_norm_and_weighted_sum():
    assert vector_norm([3,4]) == 5
    assert weighted_sum([0,10],[1,3]) == 7.5

def test_temporal_math():
    assert derivative(10,4,2) == 3
    assert integral_trapezoid([0,2,4],1) == 4
    assert gradient_1d([0,2,4],1) == [2,2,2]

def test_predicates_and_convergence():
    assert threshold(5,">=",5)
    assert approximately_equal(1.0,1.01,.02)
    assert convergence([1,1.001],.01)

def test_sigma_residual():
    assert sigma_residual(12,10,2) == 1
