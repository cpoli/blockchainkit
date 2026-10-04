"""Execution engines and the programs, languages and models built on them."""

from blockchainkit.vm.systems.assembler import assemble
from blockchainkit.vm.systems.expressions import compile_expression, to_rpn
from blockchainkit.vm.systems.programs import batch_transfer, vending_machine
from blockchainkit.vm.systems.reentrancy import drain_bank
from blockchainkit.vm.systems.script import (
    encode_public_key,
    encode_signature,
    htlc_locking,
    number,
    p2pkh_locking,
    p2pkh_unlocking,
    verify_script,
)
from blockchainkit.vm.systems.stack_machine import execute, validate_program
from blockchainkit.vm.systems.turing import busy_beaver, enumerate_machines, run_turing_machine
from blockchainkit.vm.systems.verifier import verify_bytecode

__all__ = [
    "assemble",
    "compile_expression",
    "to_rpn",
    "batch_transfer",
    "vending_machine",
    "drain_bank",
    "encode_public_key",
    "encode_signature",
    "htlc_locking",
    "number",
    "p2pkh_locking",
    "p2pkh_unlocking",
    "verify_script",
    "execute",
    "validate_program",
    "busy_beaver",
    "enumerate_machines",
    "run_turing_machine",
    "verify_bytecode",
]
