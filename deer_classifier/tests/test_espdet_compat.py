"""Preserve parameter-free legacy activations without depending on torch."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from espdet_compat import restore_sppf_activations


class Activation:
    def __init__(self, relu):
        self.relu = relu
        self.mutable_state = []

    def __call__(self, values):
        return [max(0, x) if self.relu else x for x in values]


class SPPF:
    def __init__(self, activation):
        self.cv1 = SimpleNamespace(act=activation)


class Model:
    def __init__(self, block, name="model.9"):
        self.block, self.name = block, name

    def named_modules(self):
        return iter((("", self), (self.name, self.block)))


class SourceActivationTests(unittest.TestCase):
    def test_legacy_cat_relu_and_existing_deer_identity_are_preserved(self):
        for source_relu in (True, False):
            with self.subTest(source_relu=source_relu):
                source = Model(SPPF(Activation(source_relu)))
                target = Model(SPPF(Activation(not source_relu)))
                self.assertEqual(restore_sppf_activations(target, source), 1)
                self.assertEqual(source.block.cv1.act([-2, 0, 2]), target.block.cv1.act([-2, 0, 2]))
                self.assertIsNot(source.block.cv1.act, target.block.cv1.act)
                target.block.cv1.act.mutable_state.append("target only")
                self.assertEqual(source.block.cv1.act.mutable_state, [])

    def test_unmatched_names_or_non_sppf_blocks_are_not_changed(self):
        source = Model(SPPF(Activation(True)))
        target = Model(SPPF(Activation(False)), name="different")
        self.assertEqual(restore_sppf_activations(target, source), 0)
        target = Model(SimpleNamespace(cv1=SimpleNamespace(act=Activation(False))))
        self.assertEqual(restore_sppf_activations(target, source), 0)


if __name__ == "__main__":
    unittest.main()
