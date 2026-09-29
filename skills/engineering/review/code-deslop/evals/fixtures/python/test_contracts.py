"""Protected behavior tests for the local fixture; not a real-application benchmark."""
import unittest
import subject


class ContractTests(unittest.TestCase):
    def test_runtime_registration_is_live(self):
        self.assertEqual(subject.dispatch("comma", "one,two"), ["one", "two"])

    def test_dispatch_preserves_missing_handler_error(self):
        with self.assertRaises(KeyError):
            subject.dispatch("missing", "one")

    def test_name_normalization(self):
        for value, expected in (("  Ada\n", "Ada"), ("", ""), (" A B ", "A B")):
            self.assertEqual(subject.normalize_name(value), expected)

    def test_presence_is_not_truthiness(self):
        for value in (0, False, [], {}):
            self.assertTrue(subject.has_value(value))
        self.assertFalse(subject.has_value(None))
        self.assertFalse(subject.has_value(""))

    def test_success_closes_resource_after_work(self):
        events = []
        class Resource:
            def close(self):
                events.append("close")
        resource = Resource()
        def work(received):
            self.assertIs(received, resource)
            events.append("work")
            return 7
        self.assertEqual(subject.use_resource(resource, work), 7)
        self.assertEqual(events, ["work", "close"])

    def test_failure_closes_resource_and_preserves_error(self):
        events = []
        failure = ValueError("failed")
        class Resource:
            def close(self):
                events.append("close")
        def work(resource):
            events.append("work")
            raise failure
        with self.assertRaises(ValueError) as caught:
            subject.use_resource(Resource(), work)
        self.assertIs(caught.exception, failure)
        self.assertEqual(events, ["work", "close"])


if __name__ == "__main__":
    unittest.main()
