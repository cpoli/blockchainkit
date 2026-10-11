r"""
PLONK: permutation arguments and a universal setup (2019)
=========================================================

Gabizon, Williamson and Ciobotaru wrote circuits as uniform gates,
:math:`q_L a + q_R b + q_O c + q_M ab + q_C = 0`, and enforced that wires
sharing a variable carry the same value with a *permutation argument*. With
random :math:`\beta, \gamma`, the grand product

.. math::

   \prod_{\text{positions}} \frac{w + \beta\,\mathrm{id} + \gamma}{w + \beta\,\sigma + \gamma}

equals 1 whp only if the values are constant on every cycle of the wiring
permutation :math:`\sigma`. The prover commits to the running product
:math:`z(X)` with KZG, and everything reduces to one quotient polynomial
checked at a random point. Its setup is *universal*: one powers-of-tau
string serves every circuit up to a size, with no ceremony per circuit.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.proofs.visualizers import plot_copy_constraints

# %%
# One setup, two circuits
# -----------------------

srs = bk.proofs.trusted_setup(200, secret=24680)
circuit = bk.proofs.PlonkCircuit()
x = circuit.variable(3)
circuit.assert_constant(circuit.add(circuit.mul(circuit.mul(x, x), x), x), 30)  # x**3 + x = 30
key = bk.proofs.plonk_setup(circuit, srs)
proof = bk.proofs.plonk_prove(key, srs, circuit.wire_values())
assert bk.proofs.plonk_verify(key, srs, proof)

power = bk.proofs.PlonkCircuit()
v = power.variable(2)
for _ in range(40):
    v = power.mul(v, power.variable(2))
power.assert_constant(v, 2**41 % bk.proofs.FIELD_PRIME)
power_key = bk.proofs.plonk_setup(power, srs)
assert bk.proofs.plonk_verify(
    power_key, srs, bk.proofs.plonk_prove(power_key, srs, power.wire_values())
)
print(f"the same string served circuits of {key.n} and {power_key.n} rows")

# %%
# Breaking a copy constraint
# --------------------------
# Change the first gate to 2 * 2 = 4: the gate still holds, but x is now 2
# there and 3 elsewhere. Only the permutation argument notices.

rows = [list(row) for row in circuit.wire_values()]
rows[0] = [2, 2, 4]
honest = bk.proofs.permutation_product(key, circuit.wire_values(), beta=11, gamma=13)
broken = bk.proofs.permutation_product(key, rows, beta=11, gamma=13)
print("grand product, honest:", honest[-1], "| broken copy:", broken[-1])
assert honest[-1] == 1 and broken[-1] != 1
try:
    bk.proofs.plonk_prove(key, srs, rows)
except ValueError as error:
    print("the prover cannot continue:", error)

fig, ax = plt.subplots(figsize=(5, 4.5))
plot_copy_constraints(key, ax=ax)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A PLONK proof here is 5 points, 14 field elements and 2 more points,
# whatever the circuit. Measure ``len(proof.evaluations)`` for both circuits
# above, and count how many gates the second circuit needed.
