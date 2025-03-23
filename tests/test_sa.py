import unittest

import factoriocalc
from factoriocalc import *

from .common import *

class BonusImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origGameInfo = setGameConfig('custom-sa', testDir / 'sa.json')

    @classmethod
    def tearDownClass(cls):
        config.gameInfo.reset(cls.origGameInfo)

    def testProcessingUnitProdBonus(self):
        gi = config.gameInfo.get()
        # make sure that the productivity bonus was correctly imported
        self.assertEqual(gi.recipeProductivityBonus[rcp.processing_unit], frac('1.3'))
        pu = withSettings({config.machinePrefs: presets.MP_LEGENDARY},
                          lambda: rcp.processing_unit())
        # test that the productivity is capped at 3 (1.75 + 1.3 > 3)
        self.assertEqual(pu.bonus().productivity, 3)
