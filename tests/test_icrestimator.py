import numpy as np
import math
import pytest
from swervedrive.icr import Estimator
from swervedrive.icr.kinematicmodel import cartesian_to_lambda as c2l


global tolerance
tolerance = 0.05


def init_icre(alphas, ls, bs):
    alphas = np.array(alphas)
    ls = np.array(ls)
    bs = np.array(bs)
    epsilon = np.zeros(shape=(3, 1))
    icre = Estimator(epsilon, alphas, ls, bs)
    return icre


def fuzz_q(q):
    q += (np.random.random_sample(q.shape) * 2 - 1) * 5 / 180 * math.pi
    return q


def m(icre, beta, q):
    # Metric defined in Section 4.1
    diff = icre.flip_wheel(q, beta)
    m = diff.dot(diff) / (len(diff) * math.pi ** 2)
    return m


def qua(icre, beta, q):
    # Metric defined in Section 4.1
    f = 500  # Chosen in the paper
    qua = 1 - math.log(f * m(icre, beta, q) + 1) / math.log(f + 1)
    return qua


def test_estimate_lambda():
    icre = init_icre([0, math.pi / 2, math.pi], [1, 1, 1], [0, 0, 0])

    q = np.zeros(shape=(3,))  # ICR on the robot's origin
    desired_lmda = c2l(0, 0).T
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)

    q = np.array([math.pi / 4, 0, -math.pi / 4])
    desired_lmda = c2l(0, -1).T
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)

    # driving along the y axis
    q = np.array([0, math.pi / 2, 0])
    # so the ICR should be on the U axis
    desired_lmda = c2l(1e20, 0).T  # Rotation about infinity on x-axis
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)

    # A square robot with 4 wheels, one at each corner, the difference between each
    # alpha value is pi/4 and the distance from the centre of the robot to each module
    # is the same
    alphas = np.arange(4) * math.pi / 2
    icre = init_icre(alphas, [1] * 4, [0, 0, 0, 0])

    # test case from the simulator
    q = np.array([0.0, 0.0, math.pi, math.pi])
    desired_lmda = np.array([0, 0, 1]).T
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)

    # ICR on a wheel, should be a singularity
    q = np.array([-math.pi / 4, 0, math.pi / 4, 0])
    desired_lmda = c2l(0, 1).T
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)
    singularity, wheel = icre.handle_singularities(lmda_e)
    # assert singularity
    # assert wheel == 1

    # Another square robot with side length of 2 to make calculations simpler
    alphas += math.pi / 4
    icre = init_icre(alphas, [math.sqrt(2)] * 4, [0] * 4)
    # ICR on one side of the robot frame between wheels 1 and 2
    q = np.array(
        [
            -(math.atan(2 / 1) - math.pi / 4),
            -math.pi / 4,
            math.pi / 4,
            math.atan(2 / 1) - math.pi / 4,
        ]
    )
    desired_lmda = c2l(-1, 0).T
    lmda_e = icre.estimate_lmda(q)
    assert np.allclose(desired_lmda, lmda_e, atol=tolerance)

    # # afaik this is the worst case scenario, 2 wheel singularities and a co-linear singularity
    # q = np.array([-math.pi/4, math.pi/4, math.pi/4, -math.pi/4])
    # icr = np.array([0.5, 0.5, 1/math.sqrt(2)])
    # desired_lmda = icr * 1 / np.linalg.norm(icr)
    # lmda_e = icre.estimate_lmda(q)
    # assert np.allclose(desired_lmda, lmda_e.T, atol=tolerance)


@pytest.mark.skip("Closeness calculations not quite working yet")
def test_estimate_lambda_under_uncertainty():
    # Previous tests with not-quite-converged q values
    req_closeness = 0.90
    icre = init_icre([0, math.pi / 2, math.pi], [1, 1, 1], [0, 0, 0])

    q = np.zeros(shape=(3,))  # ICR on the robot's origin
    q = fuzz_q(q)
    desired_lmda = c2l(0, 0).T
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness

    q = np.array([math.pi / 4, 0, -math.pi / 4])
    q = fuzz_q(q)
    desired_lmda = c2l(0, -1).T
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness

    # driving along the y axis
    q = np.array([0, math.pi / 2, 0])
    q = fuzz_q(q)
    # so the ICR should be on the U axis
    desired_lmda = c2l(1e20, 0).T  # Rotation about infinity on x-axis
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness

    # A square robot with 4 wheels, one at each corner, the difference between each
    # alpha value is pi/4 and the distance from the centre of the robot to each module
    # is the same
    alphas = np.arange(4) * math.pi / 2
    icre = init_icre(alphas, [1] * 4, [0, 0, 0, 0])

    # test case from the simulator
    q = np.array([0.0, 0.0, math.pi, math.pi])
    q = fuzz_q(q)
    desired_lmda = np.array([0, 0, 1]).T
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness

    # ICR on a wheel, should be a singularity
    q = np.array([-math.pi / 4, 0, math.pi / 4, 0])
    q = fuzz_q(q)
    desired_lmda = c2l(0, 1).T
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness
    singularity, wheel = icre.handle_singularities(lmda_e)
    # assert singularity
    # assert wheel == 1

    # Another square robot with side length of 2 to make calculations simpler
    alphas += math.pi / 4
    icre = init_icre(alphas, [math.sqrt(2)] * 4, [0] * 4)
    # ICR on one side of the robot frame between wheels 1 and 2
    q = np.array(
        [
            -(math.atan(2 / 1) - math.pi / 4),
            -math.pi / 4,
            math.pi / 4,
            math.atan(2 / 1) - math.pi / 4,
        ]
    )
    q = fuzz_q(q)
    desired_lmda = c2l(-1, 0).T
    lmda_e = icre.estimate_lmda(q)
    closeness = qua(icre, icre.S(lmda_e), q)
    assert closeness > req_closeness


def test_joint_space_conversion():
    icre = init_icre([math.pi / 4], [1], [0])
    lmda = np.array([0, 0, -1]).reshape(-1, 1)
    beta_target = np.array([0])
    assert np.allclose(beta_target, icre.S(lmda))
    lmda = np.array([0, -1, 0]).reshape(-1, 1)
    beta_target = np.array([math.pi / 4])
    assert np.allclose(beta_target, icre.S(lmda))

    # square robot with side length of 2 to make calculations simpler
    alpha = math.pi / 4
    alphas = [alpha, math.pi - alpha, -math.pi + alpha, -alpha]
    icre = init_icre(alphas, [math.sqrt(2)] * 4, [0] * 4)

    icr = np.array([-1, 0, 1])
    lmda = icr * 1 / np.linalg.norm(icr)
    beta_target = np.array(
        [
            -math.acos(6 / (2 * math.sqrt(10))),
            -math.pi / 4,
            math.pi / 4,
            math.acos(6 / (2 * math.sqrt(10))),
        ]
    )
    assert np.allclose(beta_target, icre.S(lmda), atol=tolerance)


def test_solve():
    # for now, check only for runtime errors until compute_derivatives works
    icre = init_icre([math.pi / 4, -math.pi / 4, math.pi], [1, 1, 1], [0, 0, 0])
    lmda = np.array([0, -1, 0]).reshape(-1, 1)
    S_u = np.array([1 / math.sqrt(2), 1 / math.sqrt(2), 0])
    S_v = np.array([0, 0, 1])
    q = np.array([0, 0, 0])
    icre.solve(S_u, S_v, q, lmda)


def test_compute_derivatives():
    # for now, check only for runtime errors
    icre = init_icre(
        [0, math.pi / 2, math.pi, math.pi * 3 / 4], [1, 1, 1, 1], [0, 0, 0, 0]
    )
    lmda = np.array([0, 0, -1]).reshape(-1, 1)
    S_u, S_v = icre.compute_derivatives(lmda)


def test_handle_singularities():
    icre = init_icre([0, math.pi / 2, math.pi], [1, 1, 1], [0, 0, 0])
    # icr on wheel 0 on the R^2 plane
    icr = np.array([1, 0, 1]).reshape(-1, 1)
    lmda = icr * 1 / np.linalg.norm(icr)
    singularity, wheel_number = icre.handle_singularities(lmda)
    assert singularity
    assert wheel_number is 0
    icr = np.array([100, 0, 1]).reshape(-1, 1)
    lmda = icr * 1 / np.linalg.norm(icr)
    singularity, wheel_number = icre.handle_singularities(lmda)
    assert not singularity
    assert wheel_number is None


def test_update_parameters():
    icre = init_icre([0, math.pi / 2, math.pi], [1, 1, 1], [0, 0, 0])
    q = np.zeros(shape=(3,))  # ICR on the robot's origin
    desired_lmda = np.array([0, 0, 1])
    u, v = -0.1, -0.1  # ICR estimate too negative
    lmda_estimate = np.array([u, v, math.sqrt(1 - np.linalg.norm([u, v]))]).reshape(
        -1, 1
    )
    delta_u, delta_v = 0.1, 0.1
    lmda_t, worse = icre.update_parameters(lmda_estimate, delta_u, delta_v, q)
    assert np.allclose(lmda_t.T, desired_lmda)
    assert not worse
    delta_u, delta_v = -0.1, -0.1
    lmda_t, worse = icre.update_parameters(lmda_estimate, delta_u, delta_v, q)
    assert worse


def test_select_starting_points():
    icre = init_icre([0, math.pi / 2, math.pi], [1, 1, 1], [0, 0, 0])
    q = np.zeros(shape=(3,))  # ICR on the robot's origin
    desired_lmda = np.array([0, 0, -1])
    starting_points = icre.select_starting_points(q)
    for sp in starting_points:
        assert np.allclose(desired_lmda[:2], sp[:2])

    q = np.array([math.pi / 4, 0, -math.pi / 4])
    icr = np.array([0, -1, 1]).reshape(-1, 1)
    desired_lmda = icr * 1 / np.linalg.norm(icr)
    starting_points = icre.select_starting_points(q)
    assert np.allclose(desired_lmda[:2], starting_points[0][:2])
    # should have unit norm
    for sp in starting_points:
        assert np.isclose(np.linalg.norm(sp), 1)

    # driving along the y axis
    q = np.array([0, math.pi / 2, 0])
    # so the ICR should be on the U axis
    desired_lmda = np.array([1, 0, 0]).reshape(-1, 1)
    starting_points = icre.select_starting_points(q)
    assert np.allclose(desired_lmda[:2], (starting_points[0][:2]))
    for sp in starting_points:
        assert np.isclose(np.linalg.norm(sp), 1)

    # A square robot with 4 wheels, one at each corner, the difference between each
    # alpha value is pi/4 and the distance from the centre of the robot to each module
    # is the same
    # test case from the simulator
    alpha = math.pi / 4
    alphas = [alpha, math.pi - alpha, -math.pi + alpha, -alpha]
    icre = init_icre(alphas, [1] * 4, [0] * 4)

    q = np.array([6.429e-04, -6.429e-04, 3.1422, 3.1409])
    desired_lmda = np.array([0, 0, 1])
    sp = icre.select_starting_points(q)
    close = []
    for p in sp:
        close.append(np.allclose(desired_lmda, p.T, atol=tolerance))
    assert any(close)

    # Another square robot with side length of 2 to make calculations simpler
    alpha = math.pi / 4
    alphas = [alpha, math.pi - alpha, -math.pi + alpha, -alpha]
    icre = init_icre(alphas, [math.sqrt(2)] * 4, [0] * 4)
    # Two wheels are pointing in the same direction (the lines between them are co-linear), the other
    # two perpendiculars meet at a point halfway between the first two wheel. - currently failing
    q = np.array(
        [
            -math.acos(6 / (2 * math.sqrt(10))),
            -math.pi / 4,
            math.pi / 4,
            math.acos(6 / (2 * math.sqrt(10))),
        ]
    )
    icr = np.array([-1, 0, 1])
    desired_lmda = icr * 1 / np.linalg.norm(icr)
    sp = icre.select_starting_points(q)
    close = []
    for p in sp:
        close.append(np.allclose(desired_lmda, p.T, atol=tolerance))
    assert any(close)


def test_shortest_distance():
    from swervedrive.icr.estimator import shortest_distance

    # S_lmda on robot origin
    alpha = math.pi / 4  # 45 degrees
    alphas = [alpha, math.pi - alpha, -math.pi + alpha, -alpha]
    q = np.array([2 * math.pi, 7 * math.pi, math.pi / 2, math.pi])
    icre = init_icre(alphas, [1] * 4, q)
    S_lmda = np.array([0] * 4)
    assert (
        np.linalg.norm(shortest_distance(q, S_lmda) - np.array([0, 0, math.pi / 2, 0]))
        < tolerance
    )

    q = np.array([-2 * math.pi, -7 * math.pi, -math.pi / 2, -math.pi])
    S_lmda = np.array([0] * 4)
    assert (
        np.linalg.norm(shortest_distance(q, S_lmda) - np.array([0, 0, -math.pi / 2, 0]))
        < tolerance
    )
