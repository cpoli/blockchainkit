r"""
Quadratic arithmetic programs and Pinocchio: a circuit as one divisibility (2013)
=================================================================================

Gennaro, Gentry, Parno and Raykova turned a whole circuit into a single
polynomial identity. Write the computation as rank-1 constraints
:math:`\langle a_j, z\rangle \cdot \langle b_j, z\rangle = \langle c_j, z\rangle`,
put constraint :math:`j` at the point :math:`\omega^j`, and interpolate each
column into polynomials :math:`A_i, B_i, C_i`. Then all the constraints hold
exactly when

.. math::

   A(X) B(X) - C(X) = H(X) \, t(X), \qquad t(X) = X^n - 1,

with :math:`A = \sum z_i A_i` and so on. Pinocchio (Parno, Howell, Gentry
and Raykova) checked this at one hidden random point with pairings, and was
the first SNARK fast enough to use; Zcash's first version ran on its
descendants.

The statement here is Vitalik Buterin's classic: I know :math:`x` with
:math:`x^3 + x + 5 = 35`.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The circuit and its R1CS
# ------------------------


def cubic(x):
    circuit = bk.proofs.Circuit()
    out = circuit.public(35)
    secret = circuit.private(x)
    circuit.assert_equal(circuit.mul(circuit.mul(secret, secret), secret) + secret + 5, out)
    return circuit


circuit = cubic(3)
r1cs = circuit.r1cs()
print("witness (1, out, x, x^2, x^3):", circuit.witness())
print("constraints:", r1cs.num_constraints)
assert r1cs.is_satisfied(circuit.witness())

# %%
# The QAP: divisible for the right witness only
# ---------------------------------------------

qap = bk.proofs.r1cs_to_qap(r1cs)
good = bk.proofs.qap_divide(qap, circuit.witness())
bad = bk.proofs.qap_divide(qap, (1, 35, 4, 16, 64))  # x = 4 satisfies the gates, not the output.
print("remainder for x = 3:", good.remainder, "| for x = 4:", bad.remainder[:3], "...")
assert good.satisfied and not bad.satisfied

# %%
# Pinocchio's idea: test the identity at one random point
# -------------------------------------------------------

r = 1234567
P = bk.proofs.FIELD_PRIME
lhs = (
    bk.proofs.poly_eval(good.left, r) * bk.proofs.poly_eval(good.right, r)
    - bk.proofs.poly_eval(good.output, r)
) % P
rhs = bk.proofs.poly_eval(good.quotient, r) * bk.proofs.poly_eval(qap.target, r) % P
assert lhs == rhs

points = bk.proofs.domain(qap.domain_size)
fig, ax = plt.subplots(figsize=(8, 4.5))
for division, label, color, offset in (
    (good, "x = 3", "#2563eb", -0.15),
    (bad, "x = 4", "#dc2626", 0.15),
):
    residual = [
        (
            bk.proofs.poly_eval(division.left, w) * bk.proofs.poly_eval(division.right, w)
            - bk.proofs.poly_eval(division.output, w)
        )
        % P
        != 0
        for w in points
    ]
    ax.bar([j + offset for j in range(len(points))], residual, width=0.3, color=color, label=label)
ax.set_xticks(range(len(points)), [f"w^{j}" for j in range(len(points))])
ax.set(xlabel="domain point (one per constraint)", ylabel="A B - C is nonzero")
ax.set_title("A wrong witness breaks a constraint, so t(X) cannot divide")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# How many multiplication constraints does x**16 need with repeated squaring,
# and how many with repeated multiplication by x? Build both circuits and
# compare their QAP domain sizes.
# A worked solution is in :doc:`/exercises/proofs`.
