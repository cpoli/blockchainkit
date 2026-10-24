"""k-anonymity and anonymity sets: how many people a record could belong to (2002).

Sweeney showed that a ZIP code, a birth date and a sex, released without
names, still single out most Americans: joined with a voter list, they
named the Governor of Massachusetts in "anonymous" hospital records. A
table is *k-anonymous* if every combination of those *quasi-identifiers*
is shared by at least ``k`` rows, so each person hides among ``k``.

The same year, Serjantov and Danezis, and Díaz, Seys, Claessens and
Preneel, measured anonymity on networks the same way: by the *anonymity
set* of possible senders. Counting the set overstates it when an attacker
finds some members likelier than others, so they weighted it by the
Shannon entropy of the attacker's guess: :math:`2^{H}` equally likely
senders give the same uncertainty.
"""

from collections import Counter
from collections.abc import Hashable, Iterable, Mapping, Sequence
from math import isclose, log2


def equivalence_classes(
    rows: Iterable[Mapping[str, Hashable]], quasi_identifiers: Sequence[str]
) -> dict[tuple[Hashable, ...], int]:
    """Count the rows sharing each combination of the quasi-identifiers.

    >>> from blockchainkit.privacy import equivalence_classes
    >>> rows = [{"zip": "021*", "sex": "F"}] * 2 + [{"zip": "022*", "sex": "M"}]
    >>> equivalence_classes(rows, ["zip", "sex"])
    {('021*', 'F'): 2, ('022*', 'M'): 1}
    """
    if not quasi_identifiers:
        raise ValueError("name at least one quasi-identifier")
    return dict(Counter(tuple(row[column] for column in quasi_identifiers) for row in rows))


def k_anonymity(rows: Iterable[Mapping[str, Hashable]], quasi_identifiers: Sequence[str]) -> int:
    """The ``k`` of a table: the size of its smallest equivalence class.

    Raises
    ------
    ValueError
        The table is empty.
    """
    classes = equivalence_classes(rows, quasi_identifiers)
    if not classes:
        raise ValueError("the table is empty")
    return min(classes.values())


def entropy_bits(probabilities: Iterable[float]) -> float:
    """Shannon entropy, in bits, of an attacker's probabilities over the possible senders.

    Raises
    ------
    ValueError
        A probability is negative, or they do not add up to 1.
    """
    values = list(probabilities)
    if any(not 0 <= p <= 1 for p in values) or not isclose(sum(values), 1.0):
        raise ValueError("probabilities must lie in [0, 1] and add up to 1")
    return -sum(p * log2(p) for p in values if p > 0)


def effective_anonymity_set(probabilities: Iterable[float]) -> float:
    """``2**H``: the number of equally likely senders that leave the same uncertainty.

    >>> from blockchainkit.privacy import effective_anonymity_set
    >>> effective_anonymity_set([0.25] * 4)
    4.0
    >>> round(effective_anonymity_set([0.7, 0.1, 0.1, 0.1]), 2)
    2.56
    """
    return float(2 ** entropy_bits(probabilities))
