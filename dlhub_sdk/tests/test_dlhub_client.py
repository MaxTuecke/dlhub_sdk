import pandas as pd
from unittest import TestCase, skip

from dlhub_sdk.models.servables.python import PythonStaticMethodModel
from dlhub_sdk.client import DLHubClient


class TestClient(TestCase):

    def setUp(self):
        self.dl = DLHubClient(http_timeout=10)

    def test_dlhub_init(self):
        self.assertIsInstance(self.dl, DLHubClient)

    def test_get_servables(self):
        r = self.dl.get_servables()
        self.assertIsInstance(r, list)
        self.assertIn('dlhub', r[0])

        # Make sure there are no duplicates
        self.assertEqual(len(r), len(set(i['dlhub']['shorthand_name'] for i in r)))

        # Get with all versions of the model
        r = self.dl.get_servables(False)
        self.assertNotEqual(len(r), len(set(i['dlhub']['shorthand_name'] for i in r)))

        # Get all servable names
        r = self.dl.list_servables()
        self.assertIsInstance(r, list)
        self.assertGreater(len(r), 0)
        self.assertIn('dlhub.test_gmail/1d_norm', r)

    def test_run(self):
        user = "ryan_globusid"
        name = "noop"
        data = {"data": ["V", "Co", "Zr"]}

        # Test sending the data as JSON
        res = self.dl.run("{}/{}".format(user, name), data, input_type='json')
        self.assertEqual({}, res)

        # Test sending the data as pickle
        res = self.dl.run("{}/{}".format(user, name), data, input_type='python')
        self.assertEqual({}, res)

    def test_submit(self):
        # Make an example function
        model = PythonStaticMethodModel.create_model('numpy.linalg', 'norm')
        model.set_name('1d_norm')
        model.set_title('Norm of a 1D Array')
        model.set_inputs('ndarray', 'Array to be normed', shape=[None])
        model.set_outputs('number', 'Norm of the array')

        # Submit the model
        self.dl.publish_servable(model)

    def test_describe_model(self):
        # Find the 1d_norm function from the test user (should be there)
        description = self.dl.describe_servable('dlhub.test_gmail', '1d_norm')
        self.assertEqual('dlhub.test_gmail', description['dlhub']['owner'])
        self.assertEqual('1d_norm', description['dlhub']['name'])

        # Give it a bogus name, check the error
        with self.assertRaises(AttributeError) as exc:
            self.dl.describe_servable('dlhub.test_gmail', 'nonexistant')
        self.assertIn('No such servable', str(exc.exception))

        # Get only the method details
        expected = dict(description['servable']['methods'])
        del expected['run']['method_details']
        methods = self.dl.describe_methods('dlhub.test_gmail', '1d_norm')
        self.assertEqual(expected, methods)

        method = self.dl.describe_methods('dlhub.test_gmail', '1d_norm', 'run')
        self.assertEqual(expected['run'], method)

    def test_search_by_servable(self):
        with self.assertRaises(ValueError) as exc:
            self.dl.search_by_servable()
        self.assertTrue(str(exc.exception).startswith("One of"))

        # Search for all models owned by "dlhub.test_gmail"
        res = self.dl.search_by_servable(owner="dlhub.test_gmail", only_latest=False)
        self.assertIsInstance(res, list)
        self.assertGreater(len(res), 1)

        # TODO: This test will break if we ever delete models after unit tests
        # Get only those that are named 1d_norm
        res = self.dl.search_by_servable(owner="dlhub.test_gmail", servable_name="1d_norm",
                                         only_latest=False)
        self.assertEqual({'1d_norm'}, set(x['dlhub']['name'] for x in res))
        # TODO: Converting to int is a hack to deal with strings in Search
        most_recent = max(int(x['dlhub']['publication_date']) for x in res)

        # Get only the latest one
        res = self.dl.search_by_servable(owner="dlhub.test_gmail", servable_name="1d_norm",
                                         only_latest=True)
        self.assertEqual(1, len(res))
        self.assertEqual(most_recent, int(res[0]['dlhub']['publication_date']))

        # Specify a version
        res = self.dl.search_by_servable(owner="dlhub.test_gmail", servable_name="1d_norm",
                                         version=most_recent)
        self.assertEqual(1, len(res))
        self.assertEqual(most_recent, int(res[0]['dlhub']['publication_date']))

        # Get the latest one, and return search information
        res, info = self.dl.search_by_servable(owner="dlhub.test_gmail", servable_name="1d_norm",
                                               only_latest=False, get_info=True)
        self.assertGreater(len(res), 0)
        self.assertIsInstance(info, dict)
        self.assertIn('dlhub', res[0])

    def test_query_authors(self):
        # Make sure we get at least one author
        res = self.dl.search_by_authors('Cherukara')
        self.assertGreater(len(res), 0)

        # Search with firstname and last name
        res = self.dl.search_by_authors('Cherukara, Mathew')
        self.assertGreater(len(res), 0)

        # Test with the middle initial
        res = self.dl.search_by_authors(['Cherukara, Mathew J'])
        self.assertGreater(len(res), 0)

        # Test searching with multiple authors, allow partial matches
        res = self.dl.search_by_authors(['Cherukara, Mathew J',
                                         'Not, Aperson'], match_all=False)
        self.assertGreater(len(res), 0)

        # Test with authors from the paper, and require all
        res = self.dl.search_by_authors(['Cherukara, Mathew J',
                                         'Not, Aperson'], match_all=True)
        self.assertEqual(len(res), 0)

    def test_query_by_paper(self):
        res = self.dl.search_by_related_doi("10.1038/s41598-018-34525-1")
        self.assertGreater(len(res), 0)
