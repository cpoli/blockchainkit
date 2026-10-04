"""
Elliptic-curve cryptography: a finite group you can draw (Miller and Koblitz 1985)
==================================================================================

Replace modular exponentiation with repeated addition of curve points.
The public key Q=xG is easy to compute; recovering x is the discrete-log
problem. Our 19-element example is small enough to solve exhaustively.

What to look for
----------------

Follow repeated addition around a tiny set of points. Exhaustive search recovers the
private step count here because this example is deliberately small.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

curve = bk.crypto.TOY_CURVE
points = [(x, y) for x in range(curve.p) for y in range(curve.p) if curve.contains((x, y))]
assert len(points) + 1 == curve.order  # Include infinity.
assert bk.crypto.multiply(curve.order, curve.generator, curve) is None
public = bk.crypto.public_key(7, curve)
recovered = next(k for k in range(1, curve.order) if bk.crypto.public_key(k, curve) == public)
assert recovered == 7
print("Public key:", public, "; recovered tiny private key:", recovered)

# %%
fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(*zip(*points, strict=True), color="#2563eb", s=55)
for k in (1, 2, 3, 7):
    x, y = bk.crypto.public_key(k, curve)
    ax.annotate(f"{k}G", (x, y), xytext=(6, 6), textcoords="offset points")
ax.set(
    xlabel="x modulo 17",
    ylabel="y modulo 17",
    title="y² = x³ + 2x + 2 over F₁₇",
    xlim=(-1, 17),
    ylim=(-1, 17),
)
ax.set_aspect("equal")
ax.grid(alpha=0.2)
fig.tight_layout()

# %%
# Larger parameters, same API
# ---------------------------
large_public = bk.crypto.public_key(7)  # secp256k1 by default.
assert bk.crypto.SECP256K1.contains(large_public)
print("secp256k1 public point:", bk.crypto.encode_point(large_public).hex())

# %%
# Exercise
# --------
# Verify G + (-G) = infinity and (a+b)G = aG+bG. Explain why the plot consists
# of isolated points rather than a smooth curve. Inspect double-and-add and
# identify where its control flow depends on private scalar bits.
