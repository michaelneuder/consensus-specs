from typing import Dict

from .base import BaseSpecBuilder
from ..constants import MAXEB


class MAXEBSpecBuilder(BaseSpecBuilder):
    fork: str = MAXEB

    @classmethod
    def imports(cls, preset_name: str):
        return super().imports(preset_name) + f'''
from eth2spec.deneb import {preset_name} as deneb
'''

## TODO: deal with changed gindices
    
    @classmethod
    def hardcoded_ssz_dep_constants(cls) -> Dict[str, str]:
        return {
            'FINALIZED_ROOT_GINDEX': 'GeneralizedIndex(169)',
            'CURRENT_SYNC_COMMITTEE_GINDEX': 'GeneralizedIndex(86)',
            'NEXT_SYNC_COMMITTEE_GINDEX': 'GeneralizedIndex(87)',
        }

