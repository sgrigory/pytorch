# Owner(s): ["oncall: distributed"]

from collections import OrderedDict
import torch

import torch.distributed.checkpoint.traverse as traverse
from torch.distributed.checkpoint.metadata import STATE_DICT_TYPE
from torch.testing._internal.common_utils import run_tests, TestCase


# TODO: add comments for TestTraverse
class TestTraverse(TestCase):
    def test_traverse_shallow(self) -> None:
        state_dict = {
            "key0": 1,
            "key1": [1, 2],
            "key2": {1: 2, 2: 3},
            "key3": torch.tensor([1]),
        }

        data = {}

        def collect_data(path, value):
            nonlocal data
            data[path] = value

        traverse.traverse_state_dict(state_dict, collect_data)

        self.assertIn(("key0",), data)
        self.assertEqual(data[("key0",)], 1)

        self.assertIn(("key1",), data)
        self.assertEqual(data[("key1",)], [1, 2])

        self.assertIn(("key2",), data)
        self.assertEqual(data[("key2",)], {1: 2, 2: 3})

        self.assertIn(("key3",), data)
        self.assertEqual(data[("key3",)], torch.tensor([1]))

    def test_traverse_nested_list(self) -> None:
        state_dict = {
            "key1": [
                torch.tensor([1]),
                [33, torch.tensor([2]), [44, 55]],
                [66, 77],
            ],
        }

        data = {}

        def collect_data(path, value):
            nonlocal data
            data[path] = value

        traverse.traverse_state_dict(state_dict, collect_data)

        self.assertNotIn(("key1"), data)

        self.assertIn(("key1", 0), data)
        self.assertEqual(data[("key1", 0)], torch.tensor([1]))

        self.assertIn(("key1", 1, 0), data)
        self.assertEqual(data[("key1", 1, 0)], 33)

        self.assertIn(("key1", 1, 1), data)
        self.assertEqual(data[("key1", 1, 1)], torch.tensor([2]))

        self.assertIn(("key1", 1, 2), data)
        self.assertEqual(data[("key1", 1, 2)], [44, 55])
        self.assertNotIn(("key1", 1, 2, 0), data)

        self.assertIn(("key1", 2), data)
        self.assertEqual(data[("key1", 2)], [66, 77])

    def test_traverse_nested_dict(self) -> None:
        state_dict = {
            "key0": {"key1": 99, "key2": torch.tensor([1])},
        }

        data = {}

        def collect_data(path, value):
            nonlocal data
            data[path] = value

        traverse.traverse_state_dict(state_dict, collect_data)

        self.assertNotIn(("key0",), data)

        self.assertIn(("key0", "key1"), data)
        self.assertEqual(data[("key0", "key1")], 99)

        self.assertIn(("key0", "key2"), data)
        self.assertEqual(data[("key0", "key2")], torch.tensor([1]))

    def test_traverse_doesnt_ignore_intermediate_collections(self) -> None:
        state_dict: STATE_DICT_TYPE = {
            "key0": [{"key1": {"key2": torch.tensor([1])}}]
        }

        data = {}

        def collect_data(path, value):
            nonlocal data
            data[path] = value

        traverse.traverse_state_dict(state_dict, collect_data)

        self.assertIn(("key0", 0, "key1", "key2"), data)
        self.assertEqual(
            data[("key0", 0, "key1", "key2")],
            torch.tensor([1]),
        )

    def test_traverse_with_ordered_dict(self) -> None:
        state_dict = OrderedDict(
            {
                "key0": [
                    99,
                    torch.tensor([3]),
                ]
            }
        )

        data = {}

        def collect_data(path, value):
            nonlocal data
            data[path] = value

        traverse.traverse_state_dict(state_dict, collect_data)

        self.assertIn(("key0", 0), data)
        self.assertEqual(data[("key0", 0)], 99)

        self.assertIn(("key0", 1), data)
        self.assertEqual(data[("key0", 1)], torch.tensor([3]))

    def test_set_element(self) -> None:
        state_dict: STATE_DICT_TYPE = {}

        traverse.set_element(state_dict, ("k",), 10)
        self.assertEqual(state_dict["k"], 10)

        traverse.set_element(state_dict, ("k1", 2), 1)
        self.assertEqual(state_dict["k1"], [None, None, 1])

        traverse.set_element(state_dict, ("k1", 1), 99)
        self.assertEqual(state_dict["k1"], [None, 99, 1])

        traverse.set_element(state_dict, ("k1", 3), 88)
        self.assertEqual(state_dict["k1"], [None, 99, 1, 88])

        traverse.set_element(state_dict, ("k2", "k3"), 3)
        self.assertEqual(state_dict["k2"], {"k3": 3})

        traverse.set_element(state_dict, ("k2", "k4", 0, 0), 99)
        self.assertEqual(state_dict["k2"]["k4"][0], [99])

    def test_get_element(self) -> None:
        state_dict = {"a": [0, 1], "b": [2, {"c": "d"}]}
        self.assertEqual(traverse.get_element(state_dict, ("a",)), [0, 1])
        self.assertEqual(traverse.get_element(state_dict, ("b", 0)), 2)
        self.assertEqual(traverse.get_element(state_dict, ("b", 1, "c")), "d")

        self.assertIsNone(traverse.get_element(state_dict, ("c",)))
        self.assertIsNone(traverse.get_element(state_dict, ("a", 33)))
        self.assertIsNone(traverse.get_element(state_dict, ("b", 88)))
        self.assertIsNone(traverse.get_element(state_dict, ("b", 0, 2)))
        self.assertIsNone(traverse.get_element(state_dict, ("b", 1, 2)))
        self.assertIsNone(traverse.get_element(state_dict, ("b", 1, "d")))


if __name__ == "__main__":
    run_tests()
